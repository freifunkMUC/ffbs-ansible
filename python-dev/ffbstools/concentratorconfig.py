#!/usr/bin/env python3
import asyncio
import json
import random
import os
import requests
import string
import subprocess
import time
import traceback
from tempfile import NamedTemporaryFile

import ipaddress

from aioetcd3.help import range_prefix

from .etcd import etcd_client
from . import wireguard, util

CONFIG_PREFIX = '/config/'

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

async def get_nodes():
    nodes = {}
    raw = await etcd_client.range(key_range=range_prefix(CONFIG_PREFIX))
    for (k, v, meta) in raw:
        k = k[len(CONFIG_PREFIX):].decode('ascii')
        v = v.decode('ascii')
        confkey, k = k.rsplit('/', 1)
        if confkey in {'default'}:
            continue
        # FIXME convert key
        try:
            pubkey = util.key_to_pubkey(confkey).decode('ascii')
        except ValueError:
            print('bad etcd node key {}'.format(confkey))
            continue
        node = nodes.setdefault(pubkey, {})
        node[k] = v
    return nodes

def update_nodes(nodes):
    current_peers = wireguard.get_dict()['wg-nodes']['peers']
    old_peers = set(current_peers)
    new_peers = set(nodes)
    print(old_peers, new_peers)
    for peerkey in sorted(new_peers):
        peer_current = current_peers.get(peerkey, {})
        peer_target = {
                'allowed_ips': [
                    nodes[peerkey]['range4'],
                    nodes[peerkey]['range6'],
                ],
                'persistent_keepalive': 15,
        }
        wireguard.update_peer('wg-nodes', peerkey, peer_current, peer_target)
        print(peerkey, peer_target)
    for peerkey in sorted(old_peers - new_peers):
        wireguard.update_peer('wg-nodes', peerkey, {}, {})
        print(peerkey, {})

async def run():
    while True:
        try:
            nodes = await get_nodes()
            update_nodes(nodes)
        except:
            traceback.print_exc()
        await asyncio.sleep(60)

def main():
    loop = asyncio.get_event_loop()
    runner = loop.create_task(run())
    loop.run_forever()

if __name__ == "__main__":
    main()

