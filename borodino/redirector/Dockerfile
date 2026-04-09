FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    libnginx-mod-http-headers-more-filter \
    openvpn \
    openssl \
    ca-certificates \
    curl \
    socat \
    iproute2 \
    iptables \
    gettext-base \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# acme.sh — téléchargement direct du script (pas d'installer pour éviter les échecs silencieux)
RUN curl -fsSL https://raw.githubusercontent.com/acmesh-official/acme.sh/master/acme.sh \
      -o /usr/local/bin/acme.sh \
    && chmod +x /usr/local/bin/acme.sh

RUN mkdir -p /var/www/acme /etc/nginx/ssl /etc/acme.sh

COPY nginx.conf /etc/nginx/nginx.conf
COPY --chmod=755 entrypoint.sh /usr/bin/entrypoint.sh
COPY loki-shipper.py /usr/bin/loki-shipper.py
RUN python3 -m compileall -b /usr/bin/loki-shipper.py \
    && rm /usr/bin/loki-shipper.py

EXPOSE 80 443

ENTRYPOINT ["/usr/bin/entrypoint.sh"]
