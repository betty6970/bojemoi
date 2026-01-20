FROM alpine:latest

# Métadonnées
LABEL maintainer="votre-email@example.com"
LABEL description="OWASP ZAP sur Alpine Linux"
LABEL version="1.0"

# Variables d'environnement
ENV ZAP_VERSION=2.16.1 \
    ZAP_USER=zap \
    ZAP_UID=1000 \
    ZAP_GID=1000 \
    ZAP_HOME=/opt/zaproxy \
    ZAP_DATA=/home/zap/.ZAP \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk \
    POSTGRES_HOST=postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=owasp_zap \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=bojemoi

# Installation des dépendances système
RUN apk update && \
    apk add --no-cache \
        openjdk17-jre \
        postgresql-client \
        java-postgresql-jdbc \
        bash \
        curl \
        wget \
        ca-certificates \
        python3 \
        py3-pip \
        firefox \
        xvfb \
        dbus \
        ttf-dejavu \
        py3-requests \
        py3-pyyaml-env-tag \
        && \
    rm -rf /var/cache/apk/*

# Création de l'utilisateur ZAP
RUN addgroup -g ${ZAP_GID} ${ZAP_USER} && \
    adduser -D -u ${ZAP_UID} -G ${ZAP_USER} -h /home/${ZAP_USER} ${ZAP_USER}

# Téléchargement et installation de OWASP ZAP
RUN mkdir -p ${ZAP_HOME} && \
    wget -q "https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz" -O /tmp/zap.tar.gz && \
    tar -xzf /tmp/zap.tar.gz -C ${ZAP_HOME} --strip-components=1 && \
    rm /tmp/zap.tar.gz && \
    chown -R ${ZAP_USER}:${ZAP_USER} ${ZAP_HOME}

# Création des répertoires de travail
RUN mkdir -p ${ZAP_DATA} /home/${ZAP_USER}/reports /home/${ZAP_USER}/scripts && \
    chown -R ${ZAP_USER}:${ZAP_USER} /home/${ZAP_USER}

# Configuration des permissions
RUN chmod +x ${ZAP_HOME}/zap.sh

# Copie du script entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Exposition des ports
EXPOSE 8080 8090

# Configuration utilisateur
USER ${ZAP_USER}
WORKDIR /home/${ZAP_USER}

# Définition des volumes
VOLUME ["${ZAP_DATA}", "/home/${ZAP_USER}/reports"]

# Point d'entrée
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["zap-daemon"]


