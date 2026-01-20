import structlog
import xmlrpc.client
from typing import Optional, Dict, Any, List
from config import settings
from models import VMDeploymentConfig

logger = structlog.get_logger()


class XenServerManager:
    """Gestionnaire de l'API XenServer"""
    
    def __init__(self):
        self.session = None
        self.url = settings.xenserver_url
        self.username = settings.xenserver_user
        self.password = settings.xenserver_password
    
    def connect(self):
        """Établit une connexion à XenServer"""
        try:
            # Connexion via XML-RPC
            self.session = xmlrpc.client.ServerProxy(self.url)
            result = self.session.session.login_with_password(self.username, self.password)
            
            if result['Status'] != 'Success':
                raise Exception(f"XenServer login failed: {result}")
            
            self.session_id = result['Value']
            logger.info("xenserver_connected", url=self.url)
            return self.session_id
            
        except Exception as e:
            logger.error("xenserver_connection_failed", error=str(e))
            raise
    
    def disconnect(self):
        """Ferme la session XenServer"""
        if self.session and self.session_id:
            try:
                self.session.session.logout(self.session_id)
                logger.info("xenserver_disconnected")
            except Exception as e:
                logger.warning("xenserver_disconnect_failed", error=str(e))
    
    def find_template(self, template_name: str) -> Optional[str]:
        """Trouve un template VM par son nom"""
        try:
            result = self.session.VM.get_all_records(self.session_id)
            
            if result['Status'] != 'Success':
                raise Exception(f"Failed to get VM records: {result}")
            
            vms = result['Value']
            
            for vm_ref, vm_record in vms.items():
                if (vm_record.get('is_a_template') and 
                    vm_record.get('name_label') == template_name):
                    logger.info("template_found", template=template_name, ref=vm_ref)
                    return vm_ref
            
            logger.warning("template_not_found", template=template_name)
            return None
            
        except Exception as e:
            logger.error("find_template_failed", error=str(e), template=template_name)
            raise
    
    def clone_vm(self, template_ref: str, vm_name: str) -> str:
        """Clone une VM depuis un template"""
        try:
            result = self.session.VM.clone(self.session_id, template_ref, vm_name)
            
            if result['Status'] != 'Success':
                raise Exception(f"VM clone failed: {result}")
            
            vm_ref = result['Value']
            logger.info("vm_cloned", vm_name=vm_name, vm_ref=vm_ref)
            return vm_ref
            
        except Exception as e:
            logger.error("clone_vm_failed", error=str(e), vm_name=vm_name)
            raise
    
    def configure_vm(self, vm_ref: str, config: VMDeploymentConfig):
        """Configure les ressources d'une VM"""
        try:
            # Configuration CPU
            self.session.VM.set_VCPUs_max(self.session_id, vm_ref, str(config.vcpus))
            self.session.VM.set_VCPUs_at_startup(self.session_id, vm_ref, str(config.vcpus))
            
            # Configuration mémoire (conversion MB -> bytes)
            memory_bytes = str(config.memory_mb * 1024 * 1024)
            self.session.VM.set_memory_limits(
                self.session_id, 
                vm_ref,
                memory_bytes,  # static_min
                memory_bytes,  # static_max
                memory_bytes,  # dynamic_min
                memory_bytes   # dynamic_max
            )
            
            # Tags
            if config.tags:
                for key, value in config.tags.items():
                    self.session.VM.add_to_other_config(
                        self.session_id,
                        vm_ref,
                        key,
                        value
                    )
            
            logger.info("vm_configured", vm_ref=vm_ref, vcpus=config.vcpus, memory_mb=config.memory_mb)
            
        except Exception as e:
            logger.error("configure_vm_failed", error=str(e), vm_ref=vm_ref)
            raise
    
    def set_cloud_init_config(self, vm_ref: str, config: VMDeploymentConfig):
        """Configure cloud-init via xenstore-data"""
        try:
            if not config.cloud_init_role:
                return
            
            # Construire l'URL du datasource cloud-init
            cloud_init_url = (
                f"{settings.cloud_init_datasource_url}/"
                f"{config.environment.value}/"
                f"{config.cloud_init_role}"
            )
            
            # Configuration cloud-init dans xenstore-data
            xenstore_data = {
                "vm-data/cloud-init/datasource": cloud_init_url,
                "vm-data/cloud-init/role": config.cloud_init_role,
                "vm-data/cloud-init/environment": config.environment.value
            }
            
            # Ajouter les paramètres additionnels
            if config.cloud_init_params:
                for key, value in config.cloud_init_params.items():
                    xenstore_data[f"vm-data/cloud-init/params/{key}"] = str(value)
            
            # Appliquer la configuration
            for key, value in xenstore_data.items():
                self.session.VM.add_to_xenstore_data(
                    self.session_id,
                    vm_ref,
                    key,
                    value
                )
            
            logger.info("cloud_init_configured", vm_ref=vm_ref, role=config.cloud_init_role)
            
        except Exception as e:
            logger.error("set_cloud_init_failed", error=str(e), vm_ref=vm_ref)
            raise
    
    def start_vm(self, vm_ref: str):
        """Démarre une VM"""
        try:
            result = self.session.VM.start(self.session_id, vm_ref, False, False)
            
            if result['Status'] != 'Success':
                raise Exception(f"VM start failed: {result}")
            
            logger.info("vm_started", vm_ref=vm_ref)
            
        except Exception as e:
            logger.error("start_vm_failed", error=str(e), vm_ref=vm_ref)
            raise
    
    def get_vm_info(self, vm_ref: str) -> Dict[str, Any]:
        """Récupère les informations d'une VM"""
        try:
            result = self.session.VM.get_record(self.session_id, vm_ref)
            
            if result['Status'] != 'Success':
                raise Exception(f"Failed to get VM info: {result}")
            
            return result['Value']
            
        except Exception as e:
            logger.error("get_vm_info_failed", error=str(e), vm_ref=vm_ref)
            raise
    
    def deploy_vm(self, config: VMDeploymentConfig) -> Dict[str, Any]:
        """Déploie une VM complète"""
        vm_ref = None
        
        try:
            # Connexion
            self.connect()
            
            # Trouver le template
            template_ref = self.find_template(config.template)
            if not template_ref:
                raise Exception(f"Template not found: {config.template}")
            
            # Cloner la VM
            vm_ref = self.clone_vm(template_ref, config.name)
            
            # Configurer la VM
            self.configure_vm(vm_ref, config)
            
            # Configurer cloud-init
            self.set_cloud_init_config(vm_ref, config)
            
            # Démarrer la VM
            self.start_vm(vm_ref)
            
            # Récupérer les infos finales
            vm_info = self.get_vm_info(vm_ref)
            
            logger.info("vm_deployed_successfully", vm_name=config.name, vm_ref=vm_ref)
            
            return {
                "vm_ref": vm_ref,
                "vm_name": config.name,
                "status": "running",
                "info": vm_info
            }
            
        except Exception as e:
            logger.error("deploy_vm_failed", error=str(e), vm_name=config.name)
            # Cleanup en cas d'erreur
            if vm_ref:
                try:
                    self.session.VM.destroy(self.session_id, vm_ref)
                except:
                    pass
            raise
            
        finally:
            self.disconnect()


# Instance globale
xenserver = XenServerManager()
