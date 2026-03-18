FROM python:3.11-alpine

# System dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-client \
    tor \
    torsocks

WORKDIR /app

# Python dependencies
RUN pip install --no-cache-dir \
    requests \
    urllib3 \
    psycopg2-binary \
    aiohttp

# Tor minimal config (SOCKS5 on 9050)
RUN mkdir -p /etc/tor && \
    echo "SocksPort 9050" > /etc/tor/torrc && \
    echo "Log notice stdout" >> /etc/tor/torrc

# Application
COPY breachforum_onion_discovery.py .
COPY breachforum_discovery_api.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import psycopg2; print('OK')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
