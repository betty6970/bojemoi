from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)

deployments_total = Counter("deployments_total", "Total deployments", ["deployment_type", "status"])
deployments_duration = Histogram("deployment_duration_seconds", "Deployment duration", ["deployment_type"])
deployments_in_progress = Gauge("deployments_in_progress", "Deployments in progress", ["deployment_type"])

class MetricsCollector:
    @staticmethod
    def record_deployment_start(deployment_type: str):
        deployments_in_progress.labels(deployment_type=deployment_type).inc()
    
    @staticmethod
    def record_deployment_end(deployment_type: str, status: str, duration: float):
        deployments_total.labels(deployment_type=deployment_type, status=status).inc()
        deployments_duration.labels(deployment_type=deployment_type).observe(duration)
        deployments_in_progress.labels(deployment_type=deployment_type).dec()

