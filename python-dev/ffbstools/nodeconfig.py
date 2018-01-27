#!/usr/bin/env python3
import json
import random
import os
import requests
import string
import subprocess
import time
import traceback
import socket
from tempfile import NamedTemporaryFile

import ipaddress

from . import wireguard

def resolve(endpoint):
    host, port = endpoint.split(':')
    port = int(port)
    addrinfo = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
    if not addrinfo:
        return endpoint
    host, port = addrinfo[0][4]
    return '{}:{}'.format(host, port)

def addresses_from_number(num):
    """calculates the client's addresses from its 14bit number"""
    v6base = 0x20010bf70381 << 80
    range_size = 10
    def as_v4(n):
        return str(ipaddress.IPv4Address(n))
    def as_v6(n):
        return str(ipaddress.IPv6Address(n))
    address4 = as_v4(0xac110000 | num)
    range4 = as_v4(0x0a000000 | (num << range_size))+'/'+str(32-range_size)
    address6 = as_v6(v6base | (num << 64) + 1)
    range6 = as_v6(v6base | (num << 64))+'/64'
    return dict(address4=address4, range4=range4, address6=address6, range6=range6)

HOST = 'concentrator1'
TEMPDIR = '/tmp/ff-ka7Ohp1i/'

def fetch_config(pubkey):
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    files = ['config', 'config.sig']
    text = dict()
    for fname in files:
        r = requests.get('http://{}/{}'.format(HOST, fname),
                params={'pubkey': pubkey, 'nonce': nonce})
        if r.status_code == 200:
            with open(TEMPDIR+fname, 'w') as f:
                f.write(r.text)
                text[fname] = r.text
        else:
            print(r)
            return None
    rtn = subprocess.call(['signify-openbsd','-V','-p','/etc/ffbs/node-config-pub.key','-m',TEMPDIR+'config'])
    if rtn != 0:
        return None
    conf = json.loads(text['config'])
    if nonce != conf['nonce']:
        return None
    del conf['nonce']
    return conf

def apply_config(conf, privkey):
    concentrators_by_ifname = {}
    for concentrator in conf['concentrators']:
        concentrators_by_ifname["wg-c{}".format(concentrator['id'])] = concentrator.copy()
    current = wireguard.get_dict()
    old_ifs = set(current)
    new_ifs = set(concentrators_by_ifname)
    print(old_ifs, new_ifs)
    for ifname in sorted(new_ifs - old_ifs):
        subprocess.check_call("ip link add {} type wireguard".format(ifname).split())
        subprocess.check_call("ip addr add {}/32 peer {} dev {}".format(
            conf['address4'], concentrator['address4'], ifname,
            ).split())
        subprocess.check_call("ip addr add {}/128 peer {} dev {}".format(
            conf['address6'], concentrator['address6'], ifname,
            ).split())
        subprocess.check_call("ip link set {} up".format(ifname).split())
    for ifname in old_ifs - new_ifs:
        subprocess.check_call("ip link del {}".format(ifname).split())
    for ifname, concentrator in concentrators_by_ifname.items():
        if_current = {
                'private_key': current.get(ifname, {}).get('private_key'),
                'listen_port': current.get(ifname, {}).get('listen_port'),
        }
        if_target = {
                'private_key': privkey,
                'listen_port': 2300+concentrator['id']
        }
        wireguard.update_if(ifname, if_current, if_target)
        peer_current = current.get(ifname, {}).get('peers', {}).get(concentrator['pubkey'], {})
        if peer_current:
            peer_current = {
                    'endpoint': peer_current.get('endpoint'),
                    'persistent_keepalive': peer_current.get('persistent_keepalive'),
                    'allowed_ips': peer_current.get('allowed_ips'),
            }
        peer_target = concentrators_by_ifname[ifname]
        peer_target = {
                'endpoint': resolve(peer_target['endpoint']),
                'persistent_keepalive': 15,
                'allowed_ips': ['0.0.0.0/0', '::/0'],
        }
        wireguard.update_peer(ifname, concentrator['pubkey'], peer_current, peer_target)

def main():
    keys = json.load(open('/etc/ffbs-wg.json'))
    print(keys)
    if not os.path.exists(TEMPDIR):
        os.makedirs(TEMPDIR)
    while True:
        conf = fetch_config(keys['pubkey'])
        print(conf)
        if conf:
            try:
                apply_config(conf, keys['privkey'])
            except:
                traceback.print_exc()
            time.sleep(conf['retry'])
        else:
            time.sleep(600)

if __name__ == '__main__':
    main()
