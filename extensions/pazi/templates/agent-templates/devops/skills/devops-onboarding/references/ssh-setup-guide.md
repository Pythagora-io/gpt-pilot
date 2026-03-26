# SSH Server Access Setup Guide

Instructions to give to the user (or their coding agent) for setting up read-only SSH access.

## Overview

The agent needs a dedicated, read-only user on each server. This guide covers:

1. Creating the user
2. Generating SSH keys
3. Installing the public key
4. Restricting permissions
5. Providing the private key to the agent

## Step-by-Step Instructions

### 1. Create a read-only user

```bash
# On each server — run as root or with sudo
sudo useradd -r -m -s /bin/bash devops-readonly
# -r: system account, -m: create home dir, -s: set shell
```

### 2. Generate an SSH key pair

Run this on a trusted machine (your laptop, not the server):

```bash
ssh-keygen -t ed25519 -C "devops-agent" -f devops-agent-key -N ""
# This creates:
#   devops-agent-key      (private — give to the agent)
#   devops-agent-key.pub  (public — install on servers)
```

### 3. Install the public key on the server

```bash
sudo mkdir -p /home/devops-readonly/.ssh
sudo cp devops-agent-key.pub /home/devops-readonly/.ssh/authorized_keys
sudo chown -R devops-readonly:devops-readonly /home/devops-readonly/.ssh
sudo chmod 700 /home/devops-readonly/.ssh
sudo chmod 600 /home/devops-readonly/.ssh/authorized_keys
```

### 4. Grant read-only access

**Basic log reading:**

```bash
sudo usermod -aG adm devops-readonly    # read syslog, auth.log, etc.
```

**If using Docker:**

```bash
# Option A: Add to docker group (can read container state)
sudo usermod -aG docker devops-readonly

# Option B: More restrictive — sudoers for specific docker commands only
echo 'devops-readonly ALL=(ALL) NOPASSWD: /usr/bin/docker ps, /usr/bin/docker logs *, /usr/bin/docker inspect *' \
  | sudo tee /etc/sudoers.d/devops-readonly-docker
```

**If using systemd:**

```bash
echo 'devops-readonly ALL=(ALL) NOPASSWD: /usr/bin/journalctl, /usr/bin/systemctl status *' \
  | sudo tee /etc/sudoers.d/devops-readonly-systemd
```

**If using supervisor:**

```bash
echo 'devops-readonly ALL=(ALL) NOPASSWD: /usr/bin/supervisorctl status, /usr/bin/supervisorctl tail *' \
  | sudo tee /etc/sudoers.d/devops-readonly-supervisor
```

**Application logs (adjust paths):**

```bash
# If app logs are in /var/log/myapp/
sudo setfacl -R -m u:devops-readonly:r /var/log/myapp/
sudo setfacl -R -d -m u:devops-readonly:r /var/log/myapp/
```

### 5. Verify the setup

```bash
# From your machine, test the connection
ssh -i devops-agent-key devops-readonly@<server-ip> whoami
# Should output: devops-readonly

# Verify can read logs
ssh -i devops-agent-key devops-readonly@<server-ip> 'sudo journalctl -n 5 --no-pager'

# Verify CANNOT write
ssh -i devops-agent-key devops-readonly@<server-ip> 'touch /tmp/write-test && echo "WRITE OK" || echo "WRITE BLOCKED"'
# Note: /tmp is usually writable — that's fine. The important thing is no sudo write access.
```

### 6. Give the private key to the agent

Send the contents of the `devops-agent-key` file (the private key) to the agent. The agent will:

1. Save it to `~/.ssh/devops-agent` with `chmod 600`
2. Test the connection
3. Confirm everything works

## Multiple Servers

If you have multiple servers, you can reuse the same key pair. Just install the public key on each server (step 3) and create the user on each (step 1).

## Security Notes

- The `devops-readonly` user has **no password** and **no sudo write access**
- Authentication is SSH key only (no password login)
- The user can read logs and check service status but cannot modify anything
- To revoke access: `sudo userdel -r devops-readonly` on each server
