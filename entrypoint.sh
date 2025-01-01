#!/bin/bash

if [ -z "$SSH_KEY_B64" ]; then
  echo "Environment variable SSH_KEY_B64 is not set. Exiting."
  exit 1
fi

echo "$SSH_KEY_B64" | base64 -d >> /home/devuser/.ssh/authorized_keys
chmod 600 /home/devuser/.ssh/authorized_keys

export MONGO_DB_DATA=$PYTHAGORA_DATA_DIR/mongodata
mkdir -p $MONGO_DB_DATA

mongod --dbpath "$MONGO_DB_DATA" --bind_ip_all >> $MONGO_DB_DATA/mongo_logs.txt 2>&1 &

export DB_DIR=$PYTHAGORA_DATA_DIR/database

mkdir -p $DB_DIR
chown -R devuser: $DB_DIR

/usr/sbin/sshd -D
