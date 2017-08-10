# LBCSSH

Easy SSH for admin ONLY !
Developped for @leboncoin

## Prerequisites

### Server

```bash
# Install lbcssh python 2 service dependencies
sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev libpq-dev
sudo apt-get install python-pip
pip install -r server/requirements_python2.txt
# or
sudo apt-get install python-psycopg2 python-webpy python-ldap python-configparser python-requests python-openssl

# Generate CA ssh key and revocation key file
mkdir test-keys
ssh-keygen -C CA -t rsa -b 4096 -o -a 100 -N "" -f test-keys/id_rsa_ca # without passphrase
ssh-keygen -k -f test-keys/revoked-keys
```

### Client

```bash
# Python 3
sudo apt-get install python3-pip
pip3 install -r requirements.txt

# Python 2
sudo apt-get install python-pip
pip install -r requirements.txt
```


Then, initialize a postgresql db. If you don't have one, install demo database.

### Optional: Demo database
```bash
sudo apt-get install docker.io

# Make a 'sudo' only if your user doesn't have docker rights, add your user into docker group
bash demo/server_init.sh

# Finally, start server
sed -i "s#__LBCSSH_PATH__#${PWD}#g" demo/lbcssh_dummy.conf
python server/server.py --config demo/lbcssh_dummy.conf
```

## Usage

### Client CLI

Add new key to lbcssh-server :
```
$ python lbcssh add
```

Sign pub key :
```
$ python lbcssh sign
```

Get public key status :
```
$ python lbcssh status
```

Get ca public key :
```
$ python lbcssh ca
```

Get ca krl :
```
python lbcssh krl
```

### Admin CLI

Active Client **username** key :
```
python lbcssh admin <username> active
```

Revoke Client **username** key :
```
python lbcssh admin <username> revoke
```

Delete Client **username** key :
```
python lbcssh admin <username> delete
```

Status Client **username** key :
```
python lbcssh admin <username> status
```


## Features

### Active SSL
```ini
[main]
ca = __LBCSSH_PATH__/test-keys/id_rsa_ca
krl = __LBCSSH_PATH__/test-keys/revoked-keys

[ssl]
private_key = __LBCSSH_PATH__/ssl/server.key
public_key = __LBCSSH_PATH__/ssl/server.pem
```

### Active LDAP
```ini
[main]
ca = __LBCSSH_PATH__/test-keys/id_rsa_ca
krl = __LBCSSH_PATH__/test-keys/revoked-keys

[ldap]
host = ad.domain.fr
bind_dn = CN=%%s,OU=Utilisateurs,DC=Domain,DC=fr
admin_cn = CN=Admin,OU=Groupes,DC=Domain,DC=fr
```


## Quick test

Generate key pair then sign it !

```bash
git clone https://github.com/Petlefeu/lbcssh.git /opt/lbcssh
cd /opt/lbcssh

# Generate key pair
mkdir test-keys
ssh-keygen -t rsa -b 4096 -o -a 100 -f test-keys/id_rsa

rm -f ~/.lbcssh
cat << EOF > ~/.lbcssh
[user]
name = user
key_path = ${PWD}/test-keys/id_rsa
key_signed_path = ${PWD}/test-keys/id_rsa_signed
url = http://localhost:8080
EOF

# List keys
python lbcssh status

# Add it into server
python lbcssh add

# ADMIN: Active key
python lbcssh admin user active

# Sign it !
python lbcssh sign
```
The output is the signing key.
