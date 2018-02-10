#!/bin/bash

mkdir -p ~/.ssh/control

if [ ! -d testinfra-venv ]; then
  echo "creating venv"
  python3 -m venv testinfra-venv
  testinfra-venv/bin/pip install textfsm 'git+https://github.com/philpep/testinfra@socket-ss#egg=testinfra'
fi

. testinfra-venv/bin/activate

echo "ControlMaster auto" > .vagrant/ssh-config
echo "ControlPath ~/.ssh/control/%h-%p-%r" >> .vagrant/ssh-config
echo "ControlPersist 5" >> .vagrant/ssh-config

echo "creating ssh config"
vagrant ssh-config $(./get_running.py) 2> /dev/null >> .vagrant/ssh-config || true

echo "running testinfra"
pytest --connection=ssh --ssh-config=.vagrant/ssh-config tests/ -v $*
