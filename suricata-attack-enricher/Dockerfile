FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared MITRE ATT&CK library
COPY bojemoi-mitre-attack/ /tmp/bojemoi-mitre-attack/
RUN pip install --no-cache-dir /tmp/bojemoi-mitre-attack/ && rm -rf /tmp/bojemoi-mitre-attack

COPY enricher.py .

RUN python -m compileall -b /app && \
    find /app -name "*.py" -delete

ENV PYTHONUNBUFFERED=1

CMD ["python", "enricher.pyc"]
