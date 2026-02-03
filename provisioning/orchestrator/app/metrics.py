"""Prometheus metrics for Bojemoi Orchestrator.

This module defines all Prometheus metrics used by the orchestrator for monitoring
deployments, API requests, blockchain operations, and service health.

Metrics are organized into categories:
- Application info
- Deployment metrics (VMs, containers)
- API request metrics
- Blockchain metrics
- Database metrics
- Service health metrics
- Cache metrics

Usage:
    from app.metrics import (
        deployment_counter,
        deployment_duration,
        record_deployment,
    )

    # Record a deployment
    record_deployment("vm", "success", "production")

    # Use context manager for timing
    with deployment_duration.labels(type="vm").time():
        await deploy_vm(...)
"""
import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# =============================================================================
# APPLICATION INFO
# =============================================================================

app_info = Info(
    "bojemoi_app",
    "Bojemoi Orchestrator application information"
)

# Set application info (call this on startup)
def set_app_info(version: str, environment: str = "production"):
    """Set application info metrics."""
    app_info.info({
        "version": version,
        "environment": environment,
        "service": "orchestrator",
    })


# =============================================================================
# DEPLOYMENT METRICS
# =============================================================================

# Counter for total deployments
deployment_total = Counter(
    "bojemoi_deployments_total",
    "Total number of deployment operations",
    ["type", "status", "environment"]
)

# Histogram for deployment duration
deployment_duration = Histogram(
    "bojemoi_deployment_duration_seconds",
    "Time taken to complete a deployment",
    ["type"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800]
)

# Gauge for active/running deployments
active_deployments = Gauge(
    "bojemoi_active_deployments",
    "Currently active deployments",
    ["type", "environment"]
)

# Counter for deployment errors by type
deployment_errors = Counter(
    "bojemoi_deployment_errors_total",
    "Total deployment errors",
    ["type", "error_type"]
)

# Gauge for VMs by state
vm_count = Gauge(
    "bojemoi_vms_total",
    "Total VMs by state",
    ["state", "environment"]
)

# Gauge for containers by state
container_count = Gauge(
    "bojemoi_containers_total",
    "Total containers by state",
    ["state", "stack"]
)


def record_deployment(
    deployment_type: str,
    status: str,
    environment: str = "production",
    duration: Optional[float] = None
):
    """Record a deployment operation.

    Args:
        deployment_type: Type of deployment (vm, container)
        status: Deployment status (success, failed, pending)
        environment: Deployment environment
        duration: Optional duration in seconds
    """
    deployment_total.labels(
        type=deployment_type,
        status=status,
        environment=environment
    ).inc()

    if duration is not None:
        deployment_duration.labels(type=deployment_type).observe(duration)


def record_deployment_error(deployment_type: str, error_type: str):
    """Record a deployment error.

    Args:
        deployment_type: Type of deployment
        error_type: Type of error (e.g., 'timeout', 'validation', 'api_error')
    """
    deployment_errors.labels(
        type=deployment_type,
        error_type=error_type
    ).inc()


# =============================================================================
# API REQUEST METRICS
# =============================================================================

# Counter for API requests
api_requests_total = Counter(
    "bojemoi_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"]
)

# Histogram for API request duration
api_request_duration = Histogram(
    "bojemoi_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

# Gauge for active requests
api_requests_in_progress = Gauge(
    "bojemoi_api_requests_in_progress",
    "Number of API requests currently being processed",
    ["method", "endpoint"]
)

# Counter for rate limit hits
rate_limit_hits = Counter(
    "bojemoi_rate_limit_hits_total",
    "Total rate limit violations",
    ["endpoint", "client_ip"]
)


def record_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float
):
    """Record an API request.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        status_code: HTTP response status code
        duration: Request duration in seconds
    """
    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()

    api_request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


# =============================================================================
# BLOCKCHAIN METRICS
# =============================================================================

# Gauge for total blocks
blockchain_blocks_total = Gauge(
    "bojemoi_blockchain_blocks_total",
    "Total number of blocks in the blockchain"
)

# Gauge for blockchain validity
blockchain_valid = Gauge(
    "bojemoi_blockchain_valid",
    "Blockchain integrity status (1=valid, 0=invalid)"
)

# Gauge for last verification timestamp
blockchain_last_verification = Gauge(
    "bojemoi_blockchain_last_verification_timestamp",
    "Unix timestamp of last blockchain verification"
)

# Counter for blockchain operations
blockchain_operations = Counter(
    "bojemoi_blockchain_operations_total",
    "Total blockchain operations",
    ["operation"]  # create_block, verify, query
)

# Histogram for block creation time
block_creation_duration = Histogram(
    "bojemoi_block_creation_duration_seconds",
    "Time to create a new blockchain block",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2]
)


def update_blockchain_metrics(total_blocks: int, is_valid: bool):
    """Update blockchain metrics.

    Args:
        total_blocks: Total number of blocks
        is_valid: Whether blockchain integrity is valid
    """
    blockchain_blocks_total.set(total_blocks)
    blockchain_valid.set(1 if is_valid else 0)
    blockchain_last_verification.set(time.time())


# =============================================================================
# DATABASE METRICS
# =============================================================================

# Gauge for database connections
db_connections_active = Gauge(
    "bojemoi_db_connections_active",
    "Number of active database connections",
    ["database"]
)

# Gauge for connection pool size
db_pool_size = Gauge(
    "bojemoi_db_pool_size",
    "Database connection pool size",
    ["database", "type"]  # type: min, max, current
)

# Histogram for query duration
db_query_duration = Histogram(
    "bojemoi_db_query_duration_seconds",
    "Database query duration",
    ["database", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

# Counter for database errors
db_errors = Counter(
    "bojemoi_db_errors_total",
    "Total database errors",
    ["database", "error_type"]
)


def record_db_query(database: str, operation: str, duration: float):
    """Record a database query.

    Args:
        database: Database name (deployments, karacho, ip2location)
        operation: Query operation (select, insert, update, delete)
        duration: Query duration in seconds
    """
    db_query_duration.labels(
        database=database,
        operation=operation
    ).observe(duration)


# =============================================================================
# SERVICE HEALTH METRICS
# =============================================================================

# Gauge for service health (1=up, 0=down)
service_health = Gauge(
    "bojemoi_service_health",
    "Health status of dependent services (1=up, 0=down)",
    ["service"]
)

# Counter for health check failures
health_check_failures = Counter(
    "bojemoi_health_check_failures_total",
    "Total health check failures",
    ["service"]
)

# Gauge for last successful health check
service_last_healthy = Gauge(
    "bojemoi_service_last_healthy_timestamp",
    "Unix timestamp of last successful health check",
    ["service"]
)


def update_service_health(service: str, is_healthy: bool):
    """Update service health metrics.

    Args:
        service: Service name (gitea, xenserver, docker, database, etc.)
        is_healthy: Whether service is healthy
    """
    service_health.labels(service=service).set(1 if is_healthy else 0)

    if is_healthy:
        service_last_healthy.labels(service=service).set(time.time())
    else:
        health_check_failures.labels(service=service).inc()


# =============================================================================
# XENSERVER METRICS
# =============================================================================

# Gauge for XenServer VMs
xenserver_vms = Gauge(
    "bojemoi_xenserver_vms_total",
    "Total VMs on XenServer",
    ["state"]  # running, halted, suspended
)

# Gauge for XenServer hosts
xenserver_hosts = Gauge(
    "bojemoi_xenserver_hosts_total",
    "Total XenServer hosts in pool"
)

# Counter for XenServer API errors
xenserver_api_errors = Counter(
    "bojemoi_xenserver_api_errors_total",
    "XenServer API errors",
    ["error_code"]
)

# Histogram for XenServer operation duration
xenserver_operation_duration = Histogram(
    "bojemoi_xenserver_operation_duration_seconds",
    "XenServer operation duration",
    ["operation"],  # create_vm, delete_vm, start_vm, stop_vm
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)


# =============================================================================
# CACHE METRICS
# =============================================================================

# Counter for cache hits/misses
cache_operations = Counter(
    "bojemoi_cache_operations_total",
    "Cache operations",
    ["cache", "operation"]  # operation: hit, miss, set, clear
)

# Gauge for cache size
cache_size = Gauge(
    "bojemoi_cache_size",
    "Number of items in cache",
    ["cache"]
)


def record_cache_operation(cache: str, operation: str):
    """Record a cache operation.

    Args:
        cache: Cache name (templates, gitea, etc.)
        operation: Operation type (hit, miss, set, clear)
    """
    cache_operations.labels(cache=cache, operation=operation).inc()


# =============================================================================
# HELPER FUNCTIONS AND DECORATORS
# =============================================================================

@contextmanager
def track_duration(histogram, **labels):
    """Context manager to track operation duration.

    Usage:
        with track_duration(deployment_duration, type="vm"):
            await deploy_vm(...)
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        histogram.labels(**labels).observe(duration)


def track_request_duration(method: str, endpoint: str):
    """Decorator to track API request duration.

    Usage:
        @track_request_duration("POST", "/api/v1/vm/deploy")
        async def deploy_vm(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            api_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).inc()

            start = time.time()
            try:
                result = await func(*args, **kwargs)
                status_code = 200
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start
                api_requests_in_progress.labels(
                    method=method,
                    endpoint=endpoint
                ).dec()
                record_request(method, endpoint, status_code, duration)

        return wrapper
    return decorator


def get_metrics() -> bytes:
    """Generate Prometheus metrics output.

    Returns:
        Prometheus metrics in text format
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST
