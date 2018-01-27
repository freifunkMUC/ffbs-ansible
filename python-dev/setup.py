#!/usr/bin/env python3

from setuptools import setup

setup(name='ffbstools',
      version='0.0.1',
      description='ffbs-tools to connect etcd and wireguard',
      author='Jan Luebbe, Hilko Boekhoff ',
      url='https://freifunk-bs.de',
      python_requires='>=3.6',
      packages=['ffbstools'],
      install_requires=[
          'aioetcd3',
          'aiohttp',
          'pyroute2',
          'requests',
      ],
      entry_points={
          'console_scripts': [
              'ffbs-etcd-watch = ffbstools.watch:main',
              'ffbs-etcd-put = ffbstools.put:main',
              'ffbs-etcd-config-web = ffbstools.etcdconfigweb:main',
              'ffbs-etcd-wireguard-export = ffbstools.etcdwireguardexport:main',
              'ffbs-concentrator-route = ffbstools.concentratorroute:main',
              'ffbs-node-config = ffbstools.nodeconfig:main',
              'ffbs-node-route = ffbstools.noderoute:main',
              'ffbs-wireguard = ffbstools.wireguard:main',
          ]
      },
)
