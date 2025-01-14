# Use Ubuntu 22.04 as the base image with multi-arch support
FROM ubuntu:22.04

# Set environment to prevent interactive prompts during builds
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Use buildx args for multi-arch support
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Update package list and install prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    build-essential \
    curl \
    git \
    gnupg \
    tzdata \
    openssh-server \
    inotify-tools \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA for Python 3.12 and install Python
RUN add-apt-repository ppa:deadsnakes/ppa -y && apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*


# Set Python 3.12 as the default python3 and python
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    python --version

RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    node --version && npm --version

# MongoDB installation with platform-specific approach
RUN case "$TARGETPLATFORM" in \
    "linux/amd64") \
    curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
    apt-get update && apt-get install -y mongodb-org \
    ;; \
    "linux/arm64"|"linux/arm64/v8") \
    curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-archive-keyring.gpg && \
    echo "deb [arch=arm64 signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
    apt-get update && apt-get install -y mongodb-org \
    ;; \
    *) \
    echo "Unsupported platform: $TARGETPLATFORM" && exit 1 \
    ;; \
    esac \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir -p /run/sshd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config \
    && sed -i 's/#ChallengeResponseAuthentication yes/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config

ENV PYTH_INSTALL_DIR=/pythagora

# Set up work directory
WORKDIR ${PYTH_INSTALL_DIR}/pythagora-core

# Add Python requirements
ADD requirements.txt .

# Create and activate a virtual environment, then install dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt

# Copy application files
ADD main.py .
ADD core core
ADD config-docker.json config.json

# Set the virtual environment to be automatically activated
ENV VIRTUAL_ENV=${PYTH_INSTALL_DIR}/pythagora-core/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHAGORA_DATA_DIR=${PYTH_INSTALL_DIR}/pythagora-core/data/
RUN mkdir -p data

# Expose MongoDB and application ports
EXPOSE 27017 8000

# Create a group named "devusergroup" with a specific GID (1000, optional)
RUN groupadd -g 1000 devusergroup

ARG USERNAME=devuser

# Create a user named "devuser" with a specific UID (1000) and assign it to "devusergroup"
RUN useradd -m -u 1000 -g devusergroup -s /bin/bash $USERNAME

# Add the user to sudoers for admin privileges
RUN echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Create an embedded entrypoint script
ADD entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN chown -R $USERNAME:devusergroup /pythagora

# Copy SSH public key from secret
#RUN --mount=type=secret,id=ssh_public_key \
#    mkdir -p /home/${USERNAME}/.ssh \
#    && cat /run/secrets/ssh_public_key > /home/${USERNAME}/.ssh/authorized_keys \
#    && chown -R ${USERNAME}:devusergroup /home/${USERNAME}/.ssh \
#    && chmod 700 /home/${USERNAME}/.ssh \
#    && chmod 600 /home/${USERNAME}/.ssh/authorized_keys

USER $USERNAME

RUN npx @puppeteer/browsers install chrome@stable

# add this before vscode... better caching of layers
ADD pythagora-vs-code.vsix /var/init_data/pythagora-vs-code.vsix

RUN mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys

# ARG commitHash
# # VS Code server installation with platform-specific handling
# RUN case "$TARGETPLATFORM" in \
#     "linux/amd64") \
#     mkdir -p ~/.vscode-server/cli/servers/Stable-${commitHash} && \
#     curl -fsSL https://update.code.visualstudio.com/commit:${commitHash}/server-linux-x64/stable -o server-linux-x64.tar.gz && \
#     tar -xz -f server-linux-x64.tar.gz -C ~/.vscode-server/cli/servers/Stable-${commitHash} && \
#     mv ~/.vscode-server/cli/servers/Stable-${commitHash}/vscode-server-linux-x64 ~/.vscode-server/cli/servers/Stable-${commitHash}/server \
#     ;; \
#     "linux/arm64"|"linux/arm64/v8") \
#     mkdir -p ~/.vscode-server/cli/servers/Stable-${commitHash} && \
#     curl -fsSL https://update.code.visualstudio.com/commit:${commitHash}/server-linux-arm64/stable -o server-linux-arm64.tar.gz && \
#     tar -xz -f server-linux-arm64.tar.gz -C ~/.vscode-server/cli/servers/Stable-${commitHash} && \
#     mv ~/.vscode-server/cli/servers/Stable-${commitHash}/vscode-server-linux-arm64 ~/.vscode-server/cli/servers/Stable-${commitHash}/server \
#     ;; \
#     *) \
#     echo "Unsupported platform: $TARGETPLATFORM" && exit 1 \
#     ;; \
#     esac


# Install VS Code extension (platform-agnostic)
# RUN ~/.vscode-server/cli/servers/Stable-${commitHash}/server/bin/code-server --install-extension pythagora-vs-code.vsix
ADD on-event-extension-install.sh /var/init_data/on-event-extension-install.sh

# Create a workspace directory
RUN mkdir -p ${PYTH_INSTALL_DIR}/pythagora-core/workspace

RUN mkdir -p /home/$USERNAME/.vscode-server/cli/servers

USER root

RUN chmod +x /var/init_data/on-event-extension-install.sh
RUN chown -R devuser: /var/init_data/

# Set the entrypoint to the main application
ENTRYPOINT ["/entrypoint.sh"]
