FROM debian:bookworm-slim

ARG RELAY_HOST=bojemoi.me
ARG RELAY_PORT=8443

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    libnginx-mod-http-geoip2 \
    libmaxminddb0 \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY nginx.conf      /etc/nginx/nginx.conf
COPY c2-proxy.conf   /etc/nginx/conf.d/c2-proxy.conf

# Bake relay target into config at build time
RUN sed -i "s|RELAY_HOST:RELAY_PORT|${RELAY_HOST}:${RELAY_PORT}|g" \
    /etc/nginx/conf.d/c2-proxy.conf

# Self-signed cert
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/self-signed.key \
        -out    /etc/nginx/ssl/self-signed.crt \
        -subj "/CN=redirector/O=C2/C=FR" 2>/dev/null

# GeoIP DB dir
RUN mkdir -p /usr/share/GeoIP

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
