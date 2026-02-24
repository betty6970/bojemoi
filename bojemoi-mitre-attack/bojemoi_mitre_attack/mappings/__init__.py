"""ATT&CK mapping modules for different data sources."""

from bojemoi_mitre_attack.mappings.osint import OSINT_PORT_MAPPING, OSINT_SERVICE_MAPPING
from bojemoi_mitre_attack.mappings.suricata import (
    SURICATA_CATEGORY_MAPPING,
    map_suricata_alert,
)
from bojemoi_mitre_attack.mappings.vulnerability import (
    VULN_PATTERN_MAPPING,
    map_vulnerability,
)
