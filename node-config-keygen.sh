#!/bin/sh

set -e

rm -f files/node-config.pub files/node-config.sec

signify-openbsd -G -p files/node-config.pub -s files/node-config.sec -n

ansible-vault encrypt < files/node-config.sec > files/node-config.sec.encrypted
mv files/node-config.sec.encrypted files/node-config.sec
