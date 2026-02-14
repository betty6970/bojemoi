import ipaddress
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    pg_host: str = "base_postgres"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = "postgres"
    pg_database: str = "msf"

    # Faraday
    faraday_url: str = "http://faraday:5985"
    faraday_token: str = ""
    faraday_user: str = "faraday"
    faraday_password: str = ""
    faraday_workspace: str = "honeypot"
    faraday_report_interval: int = 60

    # Honeypot
    ssh_port: int = 2222
    http_port: int = 8080
    rdp_port: int = 3389
    smb_port: int = 445
    ftp_port: int = 2121
    telnet_port: int = 2323
    metrics_port: int = 9200

    # Filtering
    ignore_networks: str = "10.0.0.0/8,172.16.0.0/12"

    model_config = {"env_prefix": ""}

    def is_ignored(self, ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
            for net in self.ignore_networks.split(","):
                net = net.strip()
                if net and addr in ipaddress.ip_network(net, strict=False):
                    return True
        except ValueError:
            pass
        return False


settings = Settings()
