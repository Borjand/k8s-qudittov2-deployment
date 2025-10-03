FROM ubuntu:22.04

# Instalar Python 3.10, pip y utilidades de red
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3.10-venv python3.10-distutils \
    sudo sshpass openssh-client ca-certificates bash \
    iproute2 iputils-ping net-tools \
 && rm -rf /var/lib/apt/lists/*

# Crear usuario qorch con sudo sin contraseña
RUN useradd -m -s /bin/bash quditto \
 && echo 'quditto:quditto' | chpasswd \
 && usermod -aG sudo quditto \
 && echo 'quditto ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER quditto
WORKDIR /home/quditto

# Mantener el pod vivo (como estación de control)
CMD ["sleep", "infinity"]
