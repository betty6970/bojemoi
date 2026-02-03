"""XenServer/XCP-ng client with robust error handling.

This module provides a production-ready XenAPI client with:
- Automatic session management and reconnection
- Comprehensive error handling for XenAPI failures
- Retry logic with exponential backoff
- SSL certificate handling (self-signed support)
- Integration with Prometheus metrics
- Async/await support via executor

Common XenAPI Error Codes:
- SESSION_INVALID: Session expired, need to re-authenticate
- SESSION_AUTHENTICATION_FAILED: Bad credentials
- HOST_IS_SLAVE: Connected to slave, need to connect to master
- SR_FULL: Storage repository is full
- HOST_NOT_ENOUGH_FREE_MEMORY: Insufficient RAM on host
- VM_BAD_POWER_STATE: VM is in wrong state for operation
- LICENCE_RESTRICTION: Feature requires license
- OPERATION_NOT_ALLOWED: Operation not permitted
- VDI_IN_USE: Disk is in use
- NETWORK_ALREADY_CONNECTED: Network interface already attached
"""
import asyncio
import logging
import ssl
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import partial, wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import XenAPI

logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')


class XenAPIErrorCode(str, Enum):
    """Common XenAPI error codes."""
    SESSION_INVALID = "SESSION_INVALID"
    SESSION_AUTHENTICATION_FAILED = "SESSION_AUTHENTICATION_FAILED"
    HOST_IS_SLAVE = "HOST_IS_SLAVE"
    SR_FULL = "SR_FULL"
    HOST_NOT_ENOUGH_FREE_MEMORY = "HOST_NOT_ENOUGH_FREE_MEMORY"
    VM_BAD_POWER_STATE = "VM_BAD_POWER_STATE"
    VM_IS_TEMPLATE = "VM_IS_TEMPLATE"
    LICENCE_RESTRICTION = "LICENCE_RESTRICTION"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    VDI_IN_USE = "VDI_IN_USE"
    VDI_NOT_AVAILABLE = "VDI_NOT_AVAILABLE"
    NETWORK_ALREADY_CONNECTED = "NETWORK_ALREADY_CONNECTED"
    HANDLE_INVALID = "HANDLE_INVALID"
    UUID_INVALID = "UUID_INVALID"
    VM_HVM_REQUIRED = "VM_HVM_REQUIRED"
    CANNOT_CONTACT_HOST = "CANNOT_CONTACT_HOST"
    HOST_OFFLINE = "HOST_OFFLINE"
    POOL_JOINING_HOST_CANNOT_CONTAIN_SHARED_SRS = "POOL_JOINING_HOST_CANNOT_CONTAIN_SHARED_SRS"


@dataclass
class XenServerError(Exception):
    """Custom exception for XenServer errors with detailed info."""
    error_code: str
    message: str
    details: List[str]
    original_exception: Optional[Exception] = None

    def __str__(self):
        return f"XenServerError({self.error_code}): {self.message}"

    @classmethod
    def from_xenapi_failure(cls, failure: XenAPI.Failure) -> "XenServerError":
        """Create XenServerError from XenAPI.Failure."""
        details = list(failure.details) if failure.details else []
        error_code = details[0] if details else "UNKNOWN"
        message = " ".join(details[1:]) if len(details) > 1 else str(failure)

        return cls(
            error_code=error_code,
            message=message,
            details=details,
            original_exception=failure
        )

    @property
    def is_session_error(self) -> bool:
        """Check if this is a session-related error that requires reconnection."""
        return self.error_code in (
            XenAPIErrorCode.SESSION_INVALID.value,
            XenAPIErrorCode.SESSION_AUTHENTICATION_FAILED.value,
            XenAPIErrorCode.HANDLE_INVALID.value,
        )

    @property
    def is_retryable(self) -> bool:
        """Check if this error is potentially retryable."""
        retryable_codes = {
            XenAPIErrorCode.SESSION_INVALID.value,
            XenAPIErrorCode.HANDLE_INVALID.value,
            XenAPIErrorCode.CANNOT_CONTACT_HOST.value,
            XenAPIErrorCode.HOST_OFFLINE.value,
        }
        return self.error_code in retryable_codes


def run_in_executor(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to run sync XenAPI calls in executor for async compatibility."""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        bound_func = partial(func, self, *args, **kwargs)
        return await loop.run_in_executor(None, bound_func)
    return wrapper


class XenServerClient:
    """Client for interacting with XenServer/XCP-ng using XenAPI.

    Features:
    - Automatic session management with reconnection
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - SSL certificate handling (self-signed support)
    - Prometheus metrics integration

    Example:
        client = XenServerClient(
            url="https://xenserver.local",
            username="root",
            password="password",
            verify_ssl=False
        )

        # Check connection
        if await client.ping():
            # Create VM
            vm_uuid = await client.create_vm(
                name="my-vm",
                template="alpine-meta",
                cpu=2,
                memory=2048,
                disk=20
            )
    """

    # Default retry settings
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2  # seconds
    DEFAULT_RETRY_BACKOFF = 2  # exponential backoff multiplier

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        connection_timeout: int = 30
    ):
        """
        Initialize XenServer client.

        Args:
            url: XenServer URL (e.g., https://xenserver.local)
            username: Username (usually 'root')
            password: Password
            verify_ssl: Whether to verify SSL certificates (default: False for self-signed)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            connection_timeout: Connection timeout in seconds
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection_timeout = connection_timeout

        self._session: Optional[XenAPI.Session] = None
        self._session_lock = asyncio.Lock()
        self._last_activity = 0.0
        self._connected = False

        # Import metrics (optional, may not be available)
        try:
            from app.metrics import (
                xenserver_api_errors,
                xenserver_operation_duration,
                update_service_health,
            )
            self._metrics_available = True
            self._xenserver_api_errors = xenserver_api_errors
            self._xenserver_operation_duration = xenserver_operation_duration
            self._update_service_health = update_service_health
        except ImportError:
            self._metrics_available = False
            logger.debug("Prometheus metrics not available")

    def _record_error(self, error_code: str):
        """Record error metric if metrics are available."""
        if self._metrics_available:
            self._xenserver_api_errors.labels(error_code=error_code).inc()

    def _record_operation_duration(self, operation: str, duration: float):
        """Record operation duration metric if metrics are available."""
        if self._metrics_available:
            self._xenserver_operation_duration.labels(operation=operation).observe(duration)

    def _update_health(self, is_healthy: bool):
        """Update service health metric if metrics are available."""
        if self._metrics_available:
            self._update_service_health("xenserver", is_healthy)

    def _create_session(self) -> XenAPI.Session:
        """Create a new XenAPI session with SSL handling."""
        try:
            if self.verify_ssl:
                session = XenAPI.Session(self.url)
            else:
                # Disable SSL verification for self-signed certificates
                session = XenAPI.Session(self.url, ignore_ssl=True)

            return session
        except Exception as e:
            logger.error(f"Failed to create XenAPI session: {e}")
            raise

    def _login(self) -> XenAPI.Session:
        """
        Login to XenServer and get session.

        Returns:
            XenAPI Session

        Raises:
            XenServerError: If login fails
        """
        try:
            logger.info(f"Logging in to XenServer at {self.url}")

            session = self._create_session()
            session.login_with_password(
                self.username,
                self.password,
                "2.0",  # API version
                "Bojemoi Orchestrator"  # Originator
            )

            self._connected = True
            self._last_activity = time.time()
            self._update_health(True)

            logger.info("XenServer login successful")
            return session

        except XenAPI.Failure as e:
            error = XenServerError.from_xenapi_failure(e)
            self._record_error(error.error_code)
            self._update_health(False)

            if error.error_code == XenAPIErrorCode.HOST_IS_SLAVE.value:
                # Connected to slave, get master address
                master_address = error.details[1] if len(error.details) > 1 else None
                logger.warning(f"Connected to slave. Master is at: {master_address}")
                raise XenServerError(
                    error_code=error.error_code,
                    message=f"Connected to slave. Master is at: {master_address}",
                    details=error.details,
                    original_exception=e
                )
            elif error.error_code == XenAPIErrorCode.SESSION_AUTHENTICATION_FAILED.value:
                logger.error("Authentication failed - check credentials")
                raise XenServerError(
                    error_code=error.error_code,
                    message="Authentication failed - check username and password",
                    details=error.details,
                    original_exception=e
                )
            else:
                logger.error(f"XenServer login failed: {error}")
                raise error

        except Exception as e:
            self._update_health(False)
            logger.error(f"XenServer connection error: {e}")
            raise XenServerError(
                error_code="CONNECTION_ERROR",
                message=str(e),
                details=[str(e)],
                original_exception=e
            )

    def _logout(self):
        """Logout from XenServer session."""
        if self._session:
            try:
                self._session.xenapi.session.logout()
                logger.debug("XenServer session logged out")
            except Exception as e:
                logger.warning(f"Error during logout: {e}")
            finally:
                self._session = None
                self._connected = False

    def _ensure_session(self) -> XenAPI.Session:
        """Ensure we have a valid session, reconnecting if necessary."""
        if not self._session:
            self._session = self._login()
        return self._session

    def _handle_xenapi_failure(self, failure: XenAPI.Failure, operation: str) -> XenServerError:
        """
        Handle XenAPI failure and return appropriate error.

        Args:
            failure: XenAPI.Failure exception
            operation: Name of the operation that failed

        Returns:
            XenServerError with detailed information
        """
        error = XenServerError.from_xenapi_failure(failure)
        self._record_error(error.error_code)

        # Log with appropriate level based on error type
        if error.is_session_error:
            logger.warning(f"Session error during {operation}: {error}")
            self._session = None  # Clear invalid session
        elif error.error_code == XenAPIErrorCode.SR_FULL.value:
            logger.error(f"Storage full during {operation}: {error}")
        elif error.error_code == XenAPIErrorCode.HOST_NOT_ENOUGH_FREE_MEMORY.value:
            logger.error(f"Insufficient memory during {operation}: {error}")
        elif error.error_code == XenAPIErrorCode.LICENCE_RESTRICTION.value:
            logger.error(f"License restriction during {operation}: {error}")
        else:
            logger.error(f"XenAPI error during {operation}: {error}")

        return error

    def _retry_operation(
        self,
        operation: Callable[[], T],
        operation_name: str,
        max_retries: Optional[int] = None
    ) -> T:
        """
        Execute operation with retry logic.

        Args:
            operation: Callable to execute
            operation_name: Name for logging
            max_retries: Override default max retries

        Returns:
            Operation result

        Raises:
            XenServerError: If all retries fail
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error = None
        delay = self.retry_delay

        for attempt in range(retries + 1):
            try:
                self._ensure_session()
                start_time = time.time()

                result = operation()

                duration = time.time() - start_time
                self._record_operation_duration(operation_name, duration)
                self._last_activity = time.time()

                return result

            except XenAPI.Failure as e:
                last_error = self._handle_xenapi_failure(e, operation_name)

                if not last_error.is_retryable or attempt >= retries:
                    raise last_error

                logger.info(f"Retrying {operation_name} in {delay}s (attempt {attempt + 1}/{retries})")
                time.sleep(delay)
                delay *= self.DEFAULT_RETRY_BACKOFF

            except XenServerError:
                raise

            except Exception as e:
                logger.error(f"Unexpected error during {operation_name}: {e}")
                last_error = XenServerError(
                    error_code="UNEXPECTED_ERROR",
                    message=str(e),
                    details=[str(e)],
                    original_exception=e
                )

                if attempt >= retries:
                    raise last_error

                time.sleep(delay)
                delay *= self.DEFAULT_RETRY_BACKOFF

        raise last_error

    @run_in_executor
    def create_vm(
        self,
        name: str,
        template: str,
        cpu: int,
        memory: int,
        disk: int,
        network: str = "default",
        cloudinit_data: Optional[str] = None
    ) -> str:
        """
        Create a new VM.

        Args:
            name: VM name
            template: Template name to clone
            cpu: Number of vCPUs
            memory: Memory in MB
            disk: Disk size in GB
            network: Network name to attach
            cloudinit_data: Cloud-init user data (YAML string)

        Returns:
            VM UUID

        Raises:
            XenServerError: If VM creation fails
        """
        def _create():
            session = self._ensure_session()

            # 1. Find template by name
            templates = session.xenapi.VM.get_by_name_label(template)
            if not templates:
                raise XenServerError(
                    error_code="TEMPLATE_NOT_FOUND",
                    message=f"Template '{template}' not found",
                    details=[template]
                )
            template_ref = templates[0]

            # Verify it's actually a template
            if not session.xenapi.VM.get_is_a_template(template_ref):
                raise XenServerError(
                    error_code="NOT_A_TEMPLATE",
                    message=f"'{template}' is not a template",
                    details=[template]
                )

            # 2. Clone template
            logger.debug(f"Cloning template {template}")
            vm_ref = session.xenapi.VM.clone(template_ref, name)

            try:
                # 3. Configure VM
                logger.debug(f"Configuring VM {name}")

                session.xenapi.VM.set_name_label(vm_ref, name)
                session.xenapi.VM.set_name_description(
                    vm_ref,
                    f"VM created by Bojemoi Orchestrator"
                )

                # Set CPU count
                session.xenapi.VM.set_VCPUs_max(vm_ref, str(cpu))
                session.xenapi.VM.set_VCPUs_at_startup(vm_ref, str(cpu))

                # Set memory (convert MB to bytes)
                memory_bytes = str(memory * 1024 * 1024)
                session.xenapi.VM.set_memory_limits(
                    vm_ref,
                    memory_bytes,  # static_min
                    memory_bytes,  # static_max
                    memory_bytes,  # dynamic_min
                    memory_bytes   # dynamic_max
                )

                # 4. Configure disk
                vbds = session.xenapi.VM.get_VBDs(vm_ref)
                for vbd_ref in vbds:
                    vbd = session.xenapi.VBD.get_record(vbd_ref)
                    if vbd['type'] == 'Disk':
                        vdi_ref = vbd['VDI']
                        if vdi_ref != 'OpaqueRef:NULL':
                            disk_bytes = disk * 1024 * 1024 * 1024
                            session.xenapi.VDI.resize(vdi_ref, str(disk_bytes))
                            logger.debug(f"Resized disk to {disk}GB")

                # 5. Configure network
                networks = session.xenapi.network.get_by_name_label(network)
                if networks:
                    network_ref = networks[0]
                    vifs = session.xenapi.VM.get_VIFs(vm_ref)
                    if vifs:
                        session.xenapi.VIF.set_network(vifs[0], network_ref)
                    else:
                        vif_record = {
                            'device': '0',
                            'network': network_ref,
                            'VM': vm_ref,
                            'MAC': '',
                            'MTU': '1500',
                            'other_config': {},
                            'qos_algorithm_type': '',
                            'qos_algorithm_params': {}
                        }
                        session.xenapi.VIF.create(vif_record)
                else:
                    logger.warning(f"Network '{network}' not found, using default")

                # 6. Set cloud-init config-drive
                if cloudinit_data:
                    logger.debug("Setting cloud-init config-drive")
                    xenstore_data = {
                        'vm-data/cloud-init/user-data': cloudinit_data,
                        'vm-data/cloud-init/meta-data': f'{{"instance-id": "{name}", "local-hostname": "{name}"}}'
                    }
                    session.xenapi.VM.set_xenstore_data(vm_ref, xenstore_data)

                # 7. Provision VM
                session.xenapi.VM.provision(vm_ref)

                # 8. Start VM
                logger.info(f"Starting VM {name}")
                session.xenapi.VM.start(vm_ref, False, False)

                # Get VM UUID
                vm_uuid = session.xenapi.VM.get_uuid(vm_ref)
                logger.info(f"VM {name} created successfully with UUID: {vm_uuid}")

                return vm_uuid

            except Exception as e:
                # Cleanup on failure
                logger.error(f"VM creation failed, cleaning up: {e}")
                try:
                    # Try to destroy the partially created VM
                    power_state = session.xenapi.VM.get_power_state(vm_ref)
                    if power_state == 'Running':
                        session.xenapi.VM.hard_shutdown(vm_ref)
                    session.xenapi.VM.destroy(vm_ref)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup VM after error: {cleanup_error}")
                raise

        return self._retry_operation(_create, "create_vm")

    @run_in_executor
    def delete_vm(self, vm_uuid: str, force: bool = False) -> bool:
        """
        Delete a VM and its associated disks.

        Args:
            vm_uuid: VM UUID
            force: Force shutdown if VM is running

        Returns:
            True if successful

        Raises:
            XenServerError: If deletion fails
        """
        def _delete():
            session = self._ensure_session()

            logger.info(f"Deleting VM: {vm_uuid}")

            # Get VM reference from UUID
            try:
                vm_ref = session.xenapi.VM.get_by_uuid(vm_uuid)
            except XenAPI.Failure as e:
                if "UUID_INVALID" in str(e):
                    raise XenServerError(
                        error_code="VM_NOT_FOUND",
                        message=f"VM with UUID {vm_uuid} not found",
                        details=[vm_uuid],
                        original_exception=e
                    )
                raise

            # Check power state
            power_state = session.xenapi.VM.get_power_state(vm_ref)

            # Shutdown if running
            if power_state == 'Running':
                if force:
                    logger.debug(f"Force shutting down VM {vm_uuid}")
                    session.xenapi.VM.hard_shutdown(vm_ref)
                else:
                    logger.debug(f"Gracefully shutting down VM {vm_uuid}")
                    try:
                        session.xenapi.VM.clean_shutdown(vm_ref)
                    except XenAPI.Failure:
                        # If clean shutdown fails, try hard shutdown
                        session.xenapi.VM.hard_shutdown(vm_ref)

            # Get and destroy VBDs and VDIs (disks)
            vbds = session.xenapi.VM.get_VBDs(vm_ref)
            for vbd_ref in vbds:
                try:
                    vbd = session.xenapi.VBD.get_record(vbd_ref)
                    if vbd['type'] == 'Disk':
                        vdi_ref = vbd['VDI']
                        if vdi_ref != 'OpaqueRef:NULL':
                            session.xenapi.VDI.destroy(vdi_ref)
                            logger.debug(f"Destroyed VDI: {vdi_ref}")
                except Exception as e:
                    logger.warning(f"Failed to destroy disk: {e}")

            # Destroy VM
            session.xenapi.VM.destroy(vm_ref)

            logger.info(f"VM {vm_uuid} deleted successfully")
            return True

        return self._retry_operation(_delete, "delete_vm")

    @run_in_executor
    def get_vm_info(self, vm_uuid: str) -> Dict[str, Any]:
        """
        Get VM information.

        Args:
            vm_uuid: VM UUID

        Returns:
            VM information dictionary

        Raises:
            XenServerError: If VM not found or query fails
        """
        def _get_info():
            session = self._ensure_session()

            try:
                vm_ref = session.xenapi.VM.get_by_uuid(vm_uuid)
            except XenAPI.Failure as e:
                if "UUID_INVALID" in str(e):
                    raise XenServerError(
                        error_code="VM_NOT_FOUND",
                        message=f"VM with UUID {vm_uuid} not found",
                        details=[vm_uuid],
                        original_exception=e
                    )
                raise

            vm_record = session.xenapi.VM.get_record(vm_ref)

            # Get guest metrics if available
            guest_metrics = {}
            if vm_record.get('guest_metrics') != 'OpaqueRef:NULL':
                try:
                    gm_ref = vm_record['guest_metrics']
                    gm_record = session.xenapi.VM_guest_metrics.get_record(gm_ref)
                    guest_metrics = {
                        "os_version": gm_record.get('os_version', {}),
                        "networks": gm_record.get('networks', {}),
                        "memory": gm_record.get('memory', {})
                    }
                except Exception:
                    pass

            return {
                "uuid": vm_uuid,
                "name": vm_record['name_label'],
                "description": vm_record['name_description'],
                "power_state": vm_record['power_state'],
                "vcpus": int(vm_record['VCPUs_at_startup']),
                "memory_mb": int(vm_record['memory_static_max']) // (1024 * 1024),
                "is_template": vm_record['is_a_template'],
                "is_control_domain": vm_record['is_control_domain'],
                "guest_metrics": guest_metrics
            }

        return self._retry_operation(_get_info, "get_vm_info")

    @run_in_executor
    def start_vm(self, vm_uuid: str) -> bool:
        """Start a VM."""
        def _start():
            session = self._ensure_session()
            vm_ref = session.xenapi.VM.get_by_uuid(vm_uuid)
            power_state = session.xenapi.VM.get_power_state(vm_ref)

            if power_state == 'Running':
                logger.info(f"VM {vm_uuid} is already running")
                return True

            session.xenapi.VM.start(vm_ref, False, False)
            logger.info(f"VM {vm_uuid} started")
            return True

        return self._retry_operation(_start, "start_vm")

    @run_in_executor
    def stop_vm(self, vm_uuid: str, force: bool = False) -> bool:
        """Stop a VM."""
        def _stop():
            session = self._ensure_session()
            vm_ref = session.xenapi.VM.get_by_uuid(vm_uuid)
            power_state = session.xenapi.VM.get_power_state(vm_ref)

            if power_state != 'Running':
                logger.info(f"VM {vm_uuid} is not running")
                return True

            if force:
                session.xenapi.VM.hard_shutdown(vm_ref)
            else:
                try:
                    session.xenapi.VM.clean_shutdown(vm_ref)
                except XenAPI.Failure:
                    session.xenapi.VM.hard_shutdown(vm_ref)

            logger.info(f"VM {vm_uuid} stopped")
            return True

        return self._retry_operation(_stop, "stop_vm")

    @run_in_executor
    def restart_vm(self, vm_uuid: str, force: bool = False) -> bool:
        """Restart a VM."""
        def _restart():
            session = self._ensure_session()
            vm_ref = session.xenapi.VM.get_by_uuid(vm_uuid)

            if force:
                session.xenapi.VM.hard_reboot(vm_ref)
            else:
                try:
                    session.xenapi.VM.clean_reboot(vm_ref)
                except XenAPI.Failure:
                    session.xenapi.VM.hard_reboot(vm_ref)

            logger.info(f"VM {vm_uuid} restarted")
            return True

        return self._retry_operation(_restart, "restart_vm")

    @run_in_executor
    def list_vms(self, include_templates: bool = False) -> List[Dict[str, Any]]:
        """
        List all VMs.

        Args:
            include_templates: Whether to include templates

        Returns:
            List of VM info dictionaries
        """
        def _list():
            session = self._ensure_session()

            all_vms = session.xenapi.VM.get_all()
            vms = []

            for vm_ref in all_vms:
                try:
                    record = session.xenapi.VM.get_record(vm_ref)

                    # Skip control domains
                    if record['is_control_domain']:
                        continue

                    # Skip templates if not requested
                    if not include_templates and record['is_a_template']:
                        continue

                    vms.append({
                        "uuid": record['uuid'],
                        "name": record['name_label'],
                        "power_state": record['power_state'],
                        "vcpus": int(record['VCPUs_at_startup']),
                        "memory_mb": int(record['memory_static_max']) // (1024 * 1024),
                        "is_template": record['is_a_template']
                    })

                except Exception as e:
                    logger.warning(f"Failed to get VM record: {e}")
                    continue

            return vms

        return self._retry_operation(_list, "list_vms")

    @run_in_executor
    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates."""
        def _list():
            session = self._ensure_session()

            all_vms = session.xenapi.VM.get_all()
            templates = []

            for vm_ref in all_vms:
                try:
                    record = session.xenapi.VM.get_record(vm_ref)

                    if record['is_a_template'] and not record['is_control_domain']:
                        templates.append({
                            "uuid": record['uuid'],
                            "name": record['name_label'],
                            "description": record['name_description']
                        })

                except Exception:
                    continue

            return sorted(templates, key=lambda x: x['name'])

        return self._retry_operation(_list, "list_templates")

    @run_in_executor
    def get_host_info(self) -> Dict[str, Any]:
        """Get XenServer host information."""
        def _get_info():
            session = self._ensure_session()

            host = session.xenapi.session.get_this_host(session.handle)
            host_record = session.xenapi.host.get_record(host)

            metrics_ref = host_record.get('metrics', 'OpaqueRef:NULL')
            memory_info = {}
            if metrics_ref != 'OpaqueRef:NULL':
                try:
                    metrics = session.xenapi.host_metrics.get_record(metrics_ref)
                    memory_info = {
                        "total_mb": int(metrics.get('memory_total', 0)) // (1024 * 1024),
                        "free_mb": int(metrics.get('memory_free', 0)) // (1024 * 1024)
                    }
                except Exception:
                    pass

            software_version = host_record.get('software_version', {})

            return {
                "uuid": host_record['uuid'],
                "name": host_record['name_label'],
                "hostname": host_record.get('hostname', ''),
                "address": host_record.get('address', ''),
                "product_version": software_version.get('product_version', 'unknown'),
                "product_brand": software_version.get('product_brand', 'unknown'),
                "build_number": software_version.get('build_number', 'unknown'),
                "memory": memory_info,
                "cpu_count": int(host_record.get('cpu_info', {}).get('cpu_count', 0)),
                "enabled": host_record.get('enabled', False)
            }

        return self._retry_operation(_get_info, "get_host_info")

    async def ping(self) -> bool:
        """
        Check if XenServer is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            session = await loop.run_in_executor(None, self._login)

            if session:
                host = session.xenapi.session.get_this_host(session.handle)
                host_record = session.xenapi.host.get_record(host)

                version = host_record.get('software_version', {}).get('product_version', 'unknown')
                logger.info(f"XenServer connection OK - Version: {version}")

                self._session = session
                self._update_health(True)
                return True
            else:
                self._update_health(False)
                return False

        except Exception as e:
            logger.error(f"XenServer ping failed: {e}")
            self._update_health(False)
            return False

    async def close(self):
        """Close session."""
        if self._session:
            try:
                logger.info("Closing XenServer session")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._logout)
            except Exception as e:
                logger.error(f"Error closing XenServer session: {e}")
            finally:
                self._session = None
                self._connected = False
