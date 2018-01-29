import codecs
import ipaddress

def addresses_from_number(num):
    """calculates the client's addresses from its 14bit id"""
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

def pubkey_to_key(pubkey):
    raw = codecs.decode(pubkey, 'base64')
    assert len(raw) == 32
    return codecs.encode(raw, 'hex')

def key_to_pubkey(key):
    raw = codecs.decode(key, 'hex')
    assert len(raw) == 32
    return codecs.encode(raw, 'base64').rstrip()

