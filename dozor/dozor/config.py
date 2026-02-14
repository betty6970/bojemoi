from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": ""}

    # Feed URLs
    firehol_l1_url: str = "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"
    firehol_l2_url: str = "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level2.netset"
    threatfox_url: str = "https://threatfox.abuse.ch/export/csv/ip-port/recent/"
    urlhaus_url: str = "https://urlhaus.abuse.ch/downloads/text_online/"
    feodo_url: str = "https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt"

    # Polling
    poll_interval: int = 3600  # seconds

    # Suricata
    rules_output_path: str = "/var/lib/suricata/rules/blocklist.rules"
    suricata_socket_path: str = "/var/run/suricata/suricata-command.socket"

    # Prometheus
    metrics_port: int = 9302

    def get_feeds(self) -> list[dict[str, str]]:
        return [
            {"name": "firehol_l1", "url": self.firehol_l1_url, "parser": "netset"},
            {"name": "firehol_l2", "url": self.firehol_l2_url, "parser": "netset"},
            {"name": "threatfox", "url": self.threatfox_url, "parser": "threatfox_csv"},
            {"name": "urlhaus", "url": self.urlhaus_url, "parser": "urlhaus"},
            {"name": "feodo", "url": self.feodo_url, "parser": "plain_ip"},
        ]


settings = Settings()
