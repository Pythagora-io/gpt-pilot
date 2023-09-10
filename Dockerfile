FROM python:3

# Download precompiled ttyd binary from GitHub releases
RUN apt-get update && \
    apt-get install -y wget && \
    wget https://github.com/tsl0922/ttyd/releases/download/1.6.3/ttyd.x86_64 -O /usr/bin/ttyd && \
    chmod +x /usr/bin/ttyd && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m venv pilot-env
RUN /bin/bash -c "source pilot-env/bin/activate"

WORKDIR /usr/src/app/pilot
RUN pip install -r requirements.txt

EXPOSE 7681
CMD ["ttyd", "bash"]