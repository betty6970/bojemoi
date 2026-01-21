"""XenServer/XCP-ng client - REAL IMPLEMENTATION with XenAPI"""
import XenAPI
import logging
from typing import Optional, Dict, Any
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


def run_in_executor(func):
    """Decorator to run sync XenAPI calls in executor"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        # Use partial to properly bind kwargs
        from functools import partial
        bound_func = partial(func, self, *args, **kwargs)
        return await loop.run_in_executor(None, bound_func)
    return wrapper


class XenServerClient:
    """Client for interacting with XenServer/XCP-ng using XenAPI"""
    
    def __init__(self, url: str, username: str, password: str):
        """
        Initialize XenServer client
        
        Args:
            url: XenServer URL (e.g., https://xenserver.local)
            username: Username (usually 'root')
            password: Password
        """
        self.url = url
        self.username = username
        self.password = password
        self.session = None
    
    def _login(self) -> XenAPI.Session:
        """
        Login to XenServer and get session
        
        Returns:
            XenAPI Session
        """
        try:
            logger.info(f"Logging in to XenServer at {self.url}")
            
            # Create session (ignore SSL for self-signed certs)
            session = XenAPI.Session(self.url, ignore_ssl=True)
            session.login_with_password(self.username, self.password)
            
            logger.info("XenServer login successful")
            return session
            
        except XenAPI.Failure as e:
            logger.error(f"XenServer login failed: {e}")
            raise
        except Exception as e:
            logger.error(f"XenServer connection error: {e}")
            raise
    
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
        Create a new VM (synchronous, wrapped in executor)
        
        Args:
            name: VM name
            template: Template name
            cpu: Number of CPUs
            memory: Memory in MB
            disk: Disk size in GB
            network: Network name
            cloudinit_data: Cloud-init user data
        
        Returns:
            VM UUID
        """
        try:
            # Ensure we have a session
            if not self.session:
                self.session = self._login()
            
            logger.info(f"Creating VM: {name}")
            
            # 1. Find template by name
            templates = self.session.xenapi.VM.get_by_name_label(template)
            if not templates:
                raise ValueError(f"Template '{template}' not found")
            template_ref = templates[0]
            
            # 2. Clone template
            logger.debug(f"Cloning template {template}")
            vm_ref = self.session.xenapi.VM.clone(template_ref, name)
            
            # 3. Set VM properties
            logger.debug(f"Configuring VM {name}")
            
            # Set name and description
            self.session.xenapi.VM.set_name_label(vm_ref, name)
            self.session.xenapi.VM.set_name_description(vm_ref, f"VM created by Bojemoi Orchestrator")
            
            # Set CPU count
            self.session.xenapi.VM.set_VCPUs_max(vm_ref, str(cpu))
            self.session.xenapi.VM.set_VCPUs_at_startup(vm_ref, str(cpu))
            
            # Set memory (convert MB to bytes)
            memory_bytes = str(memory * 1024 * 1024)
            self.session.xenapi.VM.set_memory_limits(
                vm_ref,
                memory_bytes,  # static_min
                memory_bytes,  # static_max
                memory_bytes,  # dynamic_min
                memory_bytes   # dynamic_max
            )
            
            # 4. Configure disk
            vbds = self.session.xenapi.VM.get_VBDs(vm_ref)
            for vbd_ref in vbds:
                vbd = self.session.xenapi.VBD.get_record(vbd_ref)
                if vbd['type'] == 'Disk':
                    vdi_ref = vbd['VDI']
                    if vdi_ref != 'OpaqueRef:NULL':
                        # Resize disk (convert GB to bytes)
                        disk_bytes = disk * 1024 * 1024 * 1024
                        self.session.xenapi.VDI.resize(vdi_ref, str(disk_bytes))
                        logger.debug(f"Resized disk to {disk}GB")
            
            # 5. Configure network
            networks = self.session.xenapi.network.get_by_name_label(network)
            if networks:
                network_ref = networks[0]
                
                # Get VIFs (network interfaces)
                vifs = self.session.xenapi.VM.get_VIFs(vm_ref)
                if vifs:
                    # Update first VIF to use specified network
                    self.session.xenapi.VIF.set_network(vifs[0], network_ref)
                else:
                    # Create new VIF if none exists
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
                    self.session.xenapi.VIF.create(vif_record)
            
            # 6. Set cloud-init config-drive
            if cloudinit_data:
                logger.debug("Setting cloud-init config-drive")
                
                # Create xenstore data for cloud-init
                xenstore_data = {
                    'vm-data/cloud-init/user-data': cloudinit_data,
                    'vm-data/cloud-init/meta-data': f'{{"instance-id": "{name}", "local-hostname": "{name}"}}'
                }
                
                self.session.xenapi.VM.set_xenstore_data(vm_ref, xenstore_data)
            
            # 7. Provision VM (make it a real VM from template)
            self.session.xenapi.VM.provision(vm_ref)
            
            # 8. Start VM
            logger.info(f"Starting VM {name}")
            self.session.xenapi.VM.start(vm_ref, False, False)
            
            # Get VM UUID
            vm_uuid = self.session.xenapi.VM.get_uuid(vm_ref)
            
            logger.info(f"VM {name} created successfully with UUID: {vm_uuid}")
            return vm_uuid
            
        except XenAPI.Failure as e:
            logger.error(f"XenAPI error creating VM {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create VM {name}: {e}")
            raise
    
    @run_in_executor
    def delete_vm(self, vm_uuid: str) -> bool:
        """
        Delete a VM
        
        Args:
            vm_uuid: VM UUID
        
        Returns:
            True if successful
        """
        try:
            if not self.session:
                self.session = self._login()
            
            logger.info(f"Deleting VM: {vm_uuid}")
            
            # Get VM reference from UUID
            vm_ref = self.session.xenapi.VM.get_by_uuid(vm_uuid)
            
            # Check power state
            power_state = self.session.xenapi.VM.get_power_state(vm_ref)
            
            # Shutdown if running
            if power_state == 'Running':
                logger.debug(f"Shutting down VM {vm_uuid}")
                self.session.xenapi.VM.hard_shutdown(vm_ref)
            
            # Get and destroy VBDs and VDIs (disks)
            vbds = self.session.xenapi.VM.get_VBDs(vm_ref)
            for vbd_ref in vbds:
                vbd = self.session.xenapi.VBD.get_record(vbd_ref)
                if vbd['type'] == 'Disk':
                    vdi_ref = vbd['VDI']
                    if vdi_ref != 'OpaqueRef:NULL':
                        # Destroy VDI
                        try:
                            self.session.xenapi.VDI.destroy(vdi_ref)
                        except:
                            pass
            
            # Destroy VM
            self.session.xenapi.VM.destroy(vm_ref)
            
            logger.info(f"VM {vm_uuid} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_uuid}: {e}")
            raise
    
    @run_in_executor
    def get_vm_info(self, vm_uuid: str) -> Dict[str, Any]:
        """
        Get VM information
        
        Args:
            vm_uuid: VM UUID
        
        Returns:
            VM information dictionary
        """
        try:
            if not self.session:
                self.session = self._login()
            
            # Get VM reference from UUID
            vm_ref = self.session.xenapi.VM.get_by_uuid(vm_uuid)
            
            # Get VM record
            vm_record = self.session.xenapi.VM.get_record(vm_ref)
            
            return {
                "uuid": vm_uuid,
                "name": vm_record['name_label'],
                "description": vm_record['name_description'],
                "power_state": vm_record['power_state'],
                "vcpus": int(vm_record['VCPUs_at_startup']),
                "memory_mb": int(vm_record['memory_static_max']) // (1024 * 1024),
                "is_template": vm_record['is_a_template'],
                "is_control_domain": vm_record['is_control_domain']
            }
            
        except Exception as e:
            logger.error(f"Failed to get VM info {vm_uuid}: {e}")
            raise
    
    async def ping(self) -> bool:
        """
        Check if XenServer is accessible
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            # Try to login
            loop = asyncio.get_event_loop()
            session = await loop.run_in_executor(None, self._login)
            
            if session:
                # Get server version
                host = session.xenapi.session.get_this_host(session.handle)
                host_record = session.xenapi.host.get_record(host)
                
                logger.info(f"XenServer connection OK - Version: {host_record.get('software_version', {}).get('product_version', 'unknown')}")
                
                # Store session for reuse
                self.session = session
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"XenServer ping failed: {e}")
            return False
    
    async def close(self):
        """Close session"""
        if self.session:
            try:
                logger.info("Closing XenServer session")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.session.xenapi.session.logout)
                self.session = None
            except Exception as e:
                logger.error(f"Error closing XenServer session: {e}")
