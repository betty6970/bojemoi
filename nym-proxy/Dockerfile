FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libssl3 netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

ARG NYM_VERSION=v2026.7-tola
RUN curl -fsSL \
    "https://github.com/nymtech/nym/releases/download/nym-binaries-${NYM_VERSION}/nym-socks5-client" \
    -o /usr/local/bin/nym-socks5-client && \
    chmod +x /usr/local/bin/nym-socks5-client

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/root/.nym"]
EXPOSE 1080

ENTRYPOINT ["/entrypoint.sh"]
