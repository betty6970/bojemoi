#!/usr/bin/env python3
# /home/claude/metrics_exporter.py

from prometheus_client import start_http_server, Gauge, Counter
import redis
import time

# Metrics
tasks_queued = Gauge('pentest_tasks_queued', 'Number of tasks in queue', ['phase'])
tasks_completed = Counter('pentest_tasks_completed', 'Number of completed tasks', ['phase', 'tool'])
vulnerabilities_found = Counter('pentest_vulnerabilities_found', 'Vulnerabilities discovered', ['severity'])
hosts_discovered = Gauge('pentest_hosts_discovered', 'Number of discovered hosts')

def collect_metrics():
    redis_client = redis.Redis(host='redis', port=6379)
    
    while True:
        # Queue lengths
        for phase in ['discovery', 'enumeration', 'web_testing', 'exploitation']:
            queue_len = redis_client.llen(f"queue:{phase}")
            tasks_queued.labels(phase=phase).set(queue_len)
        
        # Hosts discovered
        hosts_count = redis_client.scard("discovered_hosts")
        hosts_discovered.set(hosts_count)
        
        time.sleep(15)

if __name__ == '__main__':
    start_http_server(9999)
    collect_metrics()

