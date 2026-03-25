FROM python:3.11-alpine AS builder

RUN apk add --no-cache gcc musl-dev

RUN pip install --no-cache-dir \
    requests \
    PySocks \
    urllib3 \
    psycopg2-binary \
    aiohttp

FROM python:3.11-alpine

RUN apk add --no-cache postgresql-client tor torsocks

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

RUN mkdir -p /etc/tor && \
    echo "SocksPort 9050" > /etc/tor/torrc && \
    echo "Log notice stdout" >> /etc/tor/torrc

COPY breachforum_onion_discovery.py .
COPY breachforum_discovery_api.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN python3 -m compileall -b /app && \
    find /app -name "*.py" -delete

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import psycopg2; print('OK')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
