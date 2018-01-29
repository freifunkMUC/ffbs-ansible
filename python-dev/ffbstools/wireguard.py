#!/usr/bin/env python3

import json, subprocess
from tempfile import NamedTemporaryFile


def get_dict():
    output = subprocess.check_output("wg show all dump".split()).decode('ascii')
    result = {}
    peers = None
    for line in output.splitlines():
        line = line.strip().split()
        if not line:
            continue
        device = result.setdefault(line[0], {})
        if not device:
            device['private_key'] = line[1]
            device['public_key'] = line[2]
            device['listen_port'] = int(line[3])
            peers = device['peers'] = {}
        else:
            peer = peers[line[1]] = {}
            if line[2] != "(none)":
                peer['preshared_key'] = line[2]
            peer['endpoint'] = line[3]
            peer['allowed_ips'] = line[4].split(',')
            peer['latest_handshake'] = int(line[5])
            peer['transfer_rx'] = int(line[6])
            peer['transfer_tx'] = int(line[7])
            peer['persistent_keepalive'] = int(line[8])
    return result

def get_json():
    return json.dumps(get_dict(), indent=2, sort_keys=True)

def update_if(ifname, current, target):
    args = []
    if target['private_key'] != current.get('private_key'):
        private_key_file = NamedTemporaryFile()
        private_key_file.write(target['private_key'].encode('ascii'))
        private_key_file.flush()
        args += ['private-key', private_key_file.name]
    if target['listen_port'] != current.get('listen_port'):
        args += ['listen-port', str(target['listen_port'])]
    if args:
        print(ifname, args)
        subprocess.check_call(["wg", "set", ifname]+args)

def update_peer(ifname, public_key, current, target):
    args = []
    if not target:
        args += ["remove"]
    elif target != current:
        print(target)
        print(current)
        if 'endpoint' in target:
            args += ["endpoint", target['endpoint']]
        args += ["persistent-keepalive", str(target['persistent_keepalive'])]
        args += ["allowed-ips", ','.join(target['allowed_ips'])]
    if args:
        print(ifname, public_key, args)
        subprocess.check_call(["wg", "set", ifname, "peer", public_key]+args)

def main():
    print(get_json())

if __name__ == "__main__":
    main()
