"""Cloud-init configuration generator"""
import yaml
import logging
from typing import Dict, Any, Optional
from jinja2 import Template

logger = logging.getLogger(__name__)


class CloudInitGenerator:
    """Generate cloud-init configurations"""
    
    def __init__(self, gitea_client):
        """
        Initialize CloudInit generator
        
        Args:
            gitea_client: GiteaClient instance for fetching templates
        """
        self.gitea_client = gitea_client
    
    def generate(
        self,
        template: str,
        vm_name: str,
        environment: str = "production",
        additional_vars: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cloud-init configuration from template
        
        Args:
            template: Template content (YAML with Jinja2)
            vm_name: VM name
            environment: Environment (production, staging, dev)
            additional_vars: Additional variables for template
        
        Returns:
            Generated cloud-init YAML as string
        """
        try:
            logger.debug(f"Generating cloud-init for VM: {vm_name}")
            
            # Prepare template variables
            template_vars = {
                "vm_name": vm_name,
                "hostname": vm_name,
                "environment": environment,
                "fqdn": f"{vm_name}.bojemoi.local"
            }
            
            # Add additional variables
            if additional_vars:
                template_vars.update(additional_vars)
            
            # Render template using Jinja2
            jinja_template = Template(template)
            rendered = jinja_template.render(**template_vars)
            
            # Validate YAML
            try:
                yaml.safe_load(rendered)
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML generated: {e}")
                raise ValueError(f"Generated cloud-init is not valid YAML: {e}")
            
            logger.debug(f"Cloud-init generated successfully for {vm_name}")
            return rendered
            
        except Exception as e:
            logger.error(f"Failed to generate cloud-init: {e}")
            raise
    
    def validate_template(self, template: str) -> bool:
        """
        Validate a cloud-init template
        
        Args:
            template: Template content
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to parse as YAML
            yaml.safe_load(template)
            return True
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid cloud-init template: {e}")
            return False
    
    async def get_common_scripts(self) -> Dict[str, str]:
        """
        Get common cloud-init scripts from Gitea
        
        Returns:
            Dictionary of script name -> content
        """
        try:
            # List common scripts directory
            scripts_path = "cloud-init/common"
            
            entries = await self.gitea_client.list_directory(scripts_path)
            
            scripts = {}
            for entry in entries:
                if entry.get('type') == 'file':
                    script_name = entry['name']
                    script_path = f"{scripts_path}/{script_name}"
                    
                    content = await self.gitea_client.get_file_content(script_path)
                    scripts[script_name] = content
            
            return scripts
            
        except Exception as e:
            logger.error(f"Failed to get common scripts: {e}")
            return {}


# Example cloud-init template with Jinja2:
#
# #cloud-config
# hostname: {{ hostname }}
# fqdn: {{ fqdn }}
#
# users:
#   - name: admin
#     sudo: ALL=(ALL) NOPASSWD:ALL
#     shell: /bin/bash
#     ssh_authorized_keys:
#       - ssh-rsa AAAA...
#
# packages:
#   - curl
#   - git
#   - docker
#
# runcmd:
#   - echo "Environment: {{ environment }}" > /etc/environment
#   - systemctl enable docker
#   - systemctl start docker
