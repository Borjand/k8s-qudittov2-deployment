FROM ubuntu:22.04

# Instalar paquetes necesarios
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3.10-venv python3.10-distutils \
    sudo openssh-server ca-certificates bash \
    iproute2 iputils-ping net-tools \
 && rm -rf /var/lib/apt/lists/*

# sshd necesita este directorio
RUN mkdir -p /var/run/sshd

# Crear usuario "quditto" con pass "quditto"
RUN useradd -m -s /bin/bash quditto \
 && echo 'quditto:quditto' | chpasswd \
 && usermod -aG sudo quditto \
 && echo 'quditto ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Configuración SSH
RUN echo 'PermitRootLogin no' >> /etc/ssh/sshd_config \
 && echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config \
 && echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config

# Exponer puerto SSH
EXPOSE 22

# Definir usuario y directorio por defecto
USER quditto
WORKDIR /home/quditto

# Arrancar sshd en foreground (desde quditto, pero con sudo sin password)
CMD ["sudo", "/usr/sbin/sshd", "-D", "-e"]
