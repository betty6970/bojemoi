FROM projectdiscovery/nuclei:latest

# Install Python + pip
RUN apk add --no-cache python3 py3-pip gettext iproute2

WORKDIR /app

# Install Python dependencies (baked into image — no runtime pip install)
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt \
    && rm requirements.txt

# Copy source and compile to .pyc, then remove .py
COPY main.py nuclei_ai.py ./
RUN python3 -m compileall -b /app \
    && find /app -name "*.py" -delete

COPY --chmod=755 entrypoint.sh /usr/bin/entrypoint.sh

ENV PYTHONUNBUFFERED=1

EXPOSE 8001

ENTRYPOINT ["/usr/bin/entrypoint.sh"]
