#!/bin/bash

set -xe

ORG="Freifunk München"
CA="etcd CA"

# After the CRL expires, signatures cannot be verified anymore
CRL="-crldays 5000"

DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
BASE="$DIR/output"
TARGET="$DIR/../files"

if [ -e $BASE ]; then
  echo "$BASE already exists"
  exit 1
fi

mkdir -p $BASE/{private,certs,flags}
touch $BASE/index.txt
echo 01 > $BASE/serial

cat > $BASE/openssl.cnf <<EOF
[ ca ]
default_ca      = CA_default            # The default ca section

[ CA_default ]

dir            = .                     # top dir
database       = \$dir/index.txt        # index file.
new_certs_dir  = \$dir/certs            # new certs dir

certificate    = \$dir/ca.cert.pem       # The CA cert
serial         = \$dir/serial           # serial no file
private_key    = \$dir/private/ca.key.pem# CA private key
RANDFILE       = \$dir/private/.rand    # random number file

default_startdate = 19700101000000Z
default_enddate = 99991231235959Z
default_crl_days= 30                   # how long before next CRL
default_md     = sha256                # md to use

policy         = policy_any            # default policy
email_in_dn    = no                    # Don't add the email into cert DN

name_opt       = ca_default            # Subject name display option
cert_opt       = ca_default            # Certificate display option
copy_extensions = none                 # Don't copy extensions from request

[ policy_any ]
organizationName       = match
commonName             = supplied

[ req ]
default_bits           = 2048
distinguished_name     = req_distinguished_name
x509_extensions        = v3_client
encrypt_key = no
default_md = sha256

[ req_distinguished_name ]
commonName                     = Common Name (eg, YOUR name)
commonName_max                 = 64

[ v3_ca ]
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer:always
basicConstraints = CA:TRUE

[ v3_server ]
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer:always
basicConstraints = CA:FALSE
extendedKeyUsage = serverAuth,clientAuth

[ v3_client ]
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer:always
basicConstraints = CA:FALSE
extendedKeyUsage = clientAuth
EOF

export OPENSSL_CONF=$BASE/openssl.cnf

echo "Root CA"
cd $BASE
openssl req -newkey rsa -keyout private/ca.key.pem -out ca.csr.pem -subj "/O=$ORG/CN=$ORG $CA Root"
openssl ca -batch -selfsign -extensions v3_ca -in ca.csr.pem -out ca.cert.pem -keyfile private/ca.key.pem

make_server_cert()
{
  NAME=$1
  IP=$2

  openssl req -newkey rsa -keyout private/$1-server.pem -out $1-server.csr.pem -subj "/O=$ORG/CN=$ORG $1 (server)"
  openssl ca -batch -extensions v3_server -in $1-server.csr.pem -out $1-server.cert.pem \
    -config <(cat $OPENSSL_CONF <(printf "[v3_server]\nsubjectAltName='IP:$IP'"))

  touch flags/$1
}

make_client_cert()
{
  NAME=$1

  openssl req -newkey rsa -keyout private/$1-client.pem -out $1-client.csr.pem -subj "/O=$ORG/CN=$ORG $1 (client)"
  openssl ca -batch -extensions v3_client -in $1-client.csr.pem -out $1-client.cert.pem

  touch flags/$1
}

make_server_cert parker-gw01 172.16.0.1
make_server_cert parker-gw02 172.16.0.2
make_server_cert parker-gw03 172.16.0.3
make_server_cert parker-gw04 172.16.0.4

make_client_cert parker-gw01
make_client_cert parker-gw02
make_client_cert parker-gw03
make_client_cert parker-gw04

mkdir -p $TARGET
cp $BASE/ca.cert.pem $TARGET/etcd-ca.pem
for flag in $(ls flags); do
  echo $flag

  mkdir -p $TARGET/$flag
  if [ -e $BASE/private/$flag-server.pem ]; then
    cp $BASE/$flag-server.cert.pem $TARGET/$flag/etcd-server.cert.pem
    cat $BASE/private/$flag-server.pem $TARGET/$flag/etcd-server.key.pem | \
      (cd $DIR/.. && ansible-vault encrypt) > $TARGET/$flag/etcd-server.key.pem
  fi
  if [ -e $BASE/private/$flag-client.pem ]; then
    cp $BASE/$flag-client.cert.pem $TARGET/$flag/etcd-client.cert.pem
    cat $BASE/private/$flag-client.pem $TARGET/$flag/etcd-client.key.pem | \
      (cd $DIR/.. && ansible-vault encrypt) > $TARGET/$flag/etcd-client.key.pem
  fi
done
