FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    openvpn \
    openssl \
    curl \
    iproute2 \
    iptables \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

COPY nginx.conf /etc/nginx/nginx.conf
COPY --chmod=755 entrypoint.sh /usr/bin/entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/usr/bin/entrypoint.sh"]
