FROM python:3.11-alpine

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY collector.py .

# Compile Python sources
RUN python3 -m compileall -b /app/collector.py && \
    rm /app/collector.py

CMD ["python", "-u", "collector.pyc"]
