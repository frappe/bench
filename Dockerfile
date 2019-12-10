## Dockerfile for quick build, not for production use.
FROM ubuntu:latest

RUN mkdir -p /erpnext

WORKDIR /erpnext

RUN DEBIAN_FRONTEND=noninteractive apt-get clean && apt-get update && \
    apt-get install -y python-minimal build-essential python-setuptools wget sudo dbus systemd locales && \
    wget https://raw.githubusercontent.com/frappe/bench/master/playbooks/install.py && \
    useradd -m -s /bin/bash erpnextuser && usermod -aG sudo erpnextuser && \
    echo "erpnextuser ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    echo "%erpnextuser  ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    chown -R erpnextuser /erpnext && \
    apt-get install dbus && mkdir -p /run/dbus && \
    service dbus start || true && \
    dbus-daemon --system || true

RUN apt-get -y install python-apt
RUN apt-get -y install cron
USER erpnextuser

## Password for mysql and admin is admin@123
RUN sudo service dbus start && sudo locale-gen en_US.UTF-8 && sudo localectl set-locale LANG=en_US.utf8 && \
    mkdir -p /home/erpnextuser/.npm; sudo chown -R $USER:$GROUP ~/.npm || true && \
    mkdir -p /home/erpnextuser/.config; sudo chown -R $USER:$GROUP ~/.config &&\
    yes "admin@123" | sudo python install.py --develop --container

WORKDIR /home/erpnextuser/frappe-bench
RUN cd /home/erpnextuser/frappe-bench/apps/erpnext; yarn install
RUN cd /home/erpnextuser/frappe-bench/apps/frappe; yarn install
RUN npm install socket.io redis express superagent cookie chalk --save

EXPOSE 8000/tcp
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
COPY entrypoint.sh /home/erpnextuser/frappe-bench/entrypoint.sh
CMD ["/bin/bash","entrypoint.sh"]
