"""
MITRE ATT&CK Mapper - Maps OSINT findings to ATT&CK framework.

Extracted from telegram bot's mitre_attack.py and extended for cross-component use.
"""

import logging
from typing import Any

from bojemoi_mitre_attack.models import TechniqueMapping, AttackMapping

logger = logging.getLogger(__name__)


class MITREAttackMapper:
    """Maps OSINT findings to MITRE ATT&CK framework."""

    TECHNIQUE_MAPPINGS = {
        "open_ports": {"id": "T1595", "name": "Active Scanning", "tactic": "reconnaissance"},
        "port_scanning": {"id": "T1595.001", "name": "Scanning IP Blocks", "tactic": "reconnaissance"},
        "service_enumeration": {"id": "T1595.002", "name": "Vulnerability Scanning", "tactic": "reconnaissance"},
        "proxy_detected": {"id": "T1090", "name": "Proxy", "tactic": "command-and-control"},
        "c2_ports": {"id": "T1071", "name": "Application Layer Protocol", "tactic": "command-and-control"},
        "web_protocol_c2": {"id": "T1071.001", "name": "Web Protocols", "tactic": "command-and-control"},
        "dns_c2": {"id": "T1071.004", "name": "DNS", "tactic": "command-and-control"},
        "tor_detected": {"id": "T1090.003", "name": "Multi-hop Proxy", "tactic": "defense-evasion"},
        "vpn_detected": {"id": "T1090.002", "name": "External Proxy", "tactic": "defense-evasion"},
        "ssh_open": {"id": "T1021.004", "name": "SSH", "tactic": "lateral-movement"},
        "rdp_open": {"id": "T1021.001", "name": "Remote Desktop Protocol", "tactic": "lateral-movement"},
        "smb_open": {"id": "T1021.002", "name": "SMB/Windows Admin Shares", "tactic": "lateral-movement"},
        "malicious_ip": {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "initial-access"},
        "phishing_domain": {"id": "T1566", "name": "Phishing", "tactic": "initial-access"},
        "drive_by": {"id": "T1189", "name": "Drive-by Compromise", "tactic": "initial-access"},
        "new_domain": {"id": "T1583.001", "name": "Domains", "tactic": "resource-development"},
        "no_ssl": {"id": "T1583", "name": "Acquire Infrastructure", "tactic": "resource-development"},
        "hosting_provider": {"id": "T1583.003", "name": "Virtual Private Server", "tactic": "resource-development"},
    }

    C2_PORTS = {4444, 5555, 6666, 8888, 9999, 1234, 12345, 31337, 6667, 6697}
    SSH_PORT = 22
    RDP_PORT = 3389
    SMB_PORTS = {445, 139}
    HTTP_PORTS = {80, 443, 8080, 8443}

    APT_TECHNIQUE_MAPPING = {
        "T1071": ["APT28", "APT29", "Lazarus Group", "APT41"],
        "T1566": ["APT29", "APT32", "FIN7", "Kimsuky"],
        "T1090": ["APT28", "APT41", "Turla"],
        "T1190": ["APT41", "Hafnium", "Lazarus Group"],
        "T1021": ["APT28", "APT29", "FIN6"],
    }

    def map_ip_osint(self, osint_result: Any) -> AttackMapping:
        """Map IP OSINT results to MITRE ATT&CK."""
        mapping = AttackMapping(target=osint_result.ip, scan_type="ip")

        open_ports = getattr(osint_result, 'open_ports', [])
        threat_score = getattr(osint_result, 'threat_score', 0)

        if open_ports:
            mapping.tactics.append('reconnaissance')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1595", technique_name="Active Scanning",
                tactic="reconnaissance", reason=f"{len(open_ports)} open ports detected",
                confidence="medium",
            ))

        c2_ports = [p for p in open_ports if p in self.C2_PORTS]
        if c2_ports:
            mapping.tactics.append('command-and-control')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1071", technique_name="Application Layer Protocol",
                tactic="command-and-control", reason=f"Suspicious C2 ports: {c2_ports}",
                confidence="high",
            ))

        if getattr(osint_result, 'is_tor', False):
            mapping.tactics.append('defense-evasion')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1090.003", technique_name="Multi-hop Proxy (Tor)",
                tactic="defense-evasion", reason="Tor exit node detected", confidence="high",
            ))
        elif getattr(osint_result, 'is_vpn', False):
            mapping.tactics.append('defense-evasion')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1090.002", technique_name="External Proxy (VPN)",
                tactic="defense-evasion", reason="VPN detected", confidence="medium",
            ))
        elif getattr(osint_result, 'is_proxy', False):
            mapping.tactics.append('defense-evasion')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1090", technique_name="Proxy",
                tactic="defense-evasion", reason="Proxy detected", confidence="medium",
            ))

        if self.SSH_PORT in open_ports:
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1021.004", technique_name="SSH",
                tactic="lateral-movement", reason="SSH port (22) open", confidence="low",
            ))
            mapping.tactics.append('lateral-movement')

        if self.RDP_PORT in open_ports:
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1021.001", technique_name="Remote Desktop Protocol",
                tactic="lateral-movement", reason="RDP port (3389) open", confidence="low",
            ))
            mapping.tactics.append('lateral-movement')

        if self.SMB_PORTS.intersection(set(open_ports)):
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1021.002", technique_name="SMB/Windows Admin Shares",
                tactic="lateral-movement", reason="SMB ports open", confidence="low",
            ))
            mapping.tactics.append('lateral-movement')

        abuse_reports = getattr(osint_result, 'abuse_reports', 0)
        if threat_score >= 50 or abuse_reports > 5:
            mapping.tactics.append('initial-access')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1190", technique_name="Exploit Public-Facing Application",
                tactic="initial-access",
                reason=f"High threat score ({threat_score}) or abuse reports ({abuse_reports})",
                confidence="high" if threat_score >= 70 else "medium",
            ))

        if getattr(osint_result, 'is_hosting', False):
            mapping.tactics.append('resource-development')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1583.003", technique_name="Virtual Private Server",
                tactic="resource-development", reason="Hosted on commercial infrastructure",
                confidence="low",
            ))

        mapping.tactics = list(set(mapping.tactics))
        mapping.potential_groups = self._get_potential_groups(mapping.techniques)
        mapping.recommendations = self._get_mitigations(mapping.techniques)
        return mapping

    def map_domain_osint(self, domain_result: Any) -> AttackMapping:
        """Map domain OSINT results to MITRE ATT&CK."""
        mapping = AttackMapping(target=domain_result.domain, scan_type="domain")
        threat_score = getattr(domain_result, 'threat_score', 0)

        mapping.tactics.append('reconnaissance')
        mapping.techniques.append(TechniqueMapping(
            technique_id="T1596", technique_name="Search Open Technical Databases",
            tactic="reconnaissance", reason="WHOIS and DNS records accessible",
            confidence="low",
        ))

        if not getattr(domain_result, 'has_ssl', True):
            mapping.tactics.append('resource-development')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1583", technique_name="Acquire Infrastructure",
                tactic="resource-development",
                reason="No SSL certificate (potentially malicious infrastructure)",
                confidence="medium",
            ))

        creation_date = getattr(domain_result, 'creation_date', '')
        if creation_date and ('2024' in str(creation_date) or '2025' in str(creation_date) or '2026' in str(creation_date)):
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1583.001", technique_name="Domains",
                tactic="resource-development",
                reason=f"Recently registered domain ({creation_date})",
                confidence="medium",
            ))

        if threat_score >= 50:
            mapping.tactics.append('initial-access')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1566", technique_name="Phishing",
                tactic="initial-access",
                reason=f"Domain flagged as malicious (score: {threat_score})",
                confidence="high" if threat_score >= 70 else "medium",
            ))

        malware_samples = getattr(domain_result, 'malware_samples', 0)
        if malware_samples > 0:
            mapping.tactics.append('command-and-control')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1071.001", technique_name="Web Protocols",
                tactic="command-and-control",
                reason=f"Domain associated with {malware_samples} malware samples",
                confidence="high",
            ))

        if getattr(domain_result, 'is_tor', False):
            mapping.tactics.append('defense-evasion')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1090.003", technique_name="Multi-hop Proxy (Tor)",
                tactic="defense-evasion", reason="Primary IP is Tor exit node",
                confidence="high",
            ))

        mapping.tactics = list(set(mapping.tactics))
        mapping.potential_groups = self._get_potential_groups(mapping.techniques)
        mapping.recommendations = self._get_mitigations(mapping.techniques)
        return mapping

    def map_investigation(self, ip: str, validation: dict, surface: dict,
                          osint: dict, correlation: dict) -> AttackMapping:
        """Map a full ML Threat Intel investigation result to ATT&CK."""
        mapping = AttackMapping(target=ip, scan_type="investigation")

        # Open ports from surface data
        ports = surface.get('ports', [])
        open_port_numbers = [p.get('port') for p in ports if p.get('port')]

        if open_port_numbers:
            mapping.tactics.append('reconnaissance')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1595", technique_name="Active Scanning",
                tactic="reconnaissance",
                reason=f"{len(open_port_numbers)} open ports on surface scan",
                confidence="medium",
            ))

        c2_ports = [p for p in open_port_numbers if p in self.C2_PORTS]
        if c2_ports:
            mapping.tactics.append('command-and-control')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1071", technique_name="Application Layer Protocol",
                tactic="command-and-control",
                reason=f"Suspicious C2 ports: {c2_ports}",
                confidence="high",
            ))

        # Lateral movement ports
        for port, tech_id, tech_name in [
            (22, "T1021.004", "SSH"),
            (3389, "T1021.001", "Remote Desktop Protocol"),
        ]:
            if port in open_port_numbers:
                mapping.tactics.append('lateral-movement')
                mapping.techniques.append(TechniqueMapping(
                    technique_id=tech_id, technique_name=tech_name,
                    tactic="lateral-movement",
                    reason=f"Port {port} open", confidence="low",
                ))

        if {445, 139}.intersection(set(open_port_numbers)):
            mapping.tactics.append('lateral-movement')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1021.002", technique_name="SMB/Windows Admin Shares",
                tactic="lateral-movement", reason="SMB ports open", confidence="low",
            ))

        # Vulnerabilities from surface
        vulns = surface.get('vulns', [])
        if vulns:
            mapping.tactics.append('initial-access')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1190", technique_name="Exploit Public-Facing Application",
                tactic="initial-access",
                reason=f"{len(vulns)} known CVEs detected",
                confidence="high" if len(vulns) >= 3 else "medium",
            ))

        # Threat intel from OSINT
        otx_pulses = osint.get('otx_pulses', [])
        if otx_pulses:
            mapping.tactics.append('resource-development')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1588", technique_name="Obtain Capabilities",
                tactic="resource-development",
                reason=f"IP found in {len(otx_pulses)} OTX threat pulses",
                confidence="medium",
            ))

        # Reputation-based mapping
        abuse_confidence = validation.get('abuse_confidence', 0)
        vt_ratio = validation.get('vt_detection_ratio', 0)

        if abuse_confidence >= 80 or vt_ratio > 0.3:
            mapping.tactics.append('initial-access')
            mapping.techniques.append(TechniqueMapping(
                technique_id="T1190", technique_name="Exploit Public-Facing Application",
                tactic="initial-access",
                reason=f"AbuseIPDB: {abuse_confidence}%, VT ratio: {vt_ratio:.1%}",
                confidence="high",
            ))

        mapping.tactics = list(set(mapping.tactics))
        mapping.potential_groups = self._get_potential_groups(mapping.techniques)
        mapping.recommendations = self._get_mitigations(mapping.techniques)
        return mapping

    def _get_potential_groups(self, techniques: list[TechniqueMapping]) -> list[str]:
        """Get potential APT groups based on techniques."""
        groups = set()
        for tech in techniques:
            parent_id = tech.technique_id.split('.')[0]
            if parent_id in self.APT_TECHNIQUE_MAPPING:
                groups.update(self.APT_TECHNIQUE_MAPPING[parent_id])
        return list(groups)

    def _get_mitigations(self, techniques: list[TechniqueMapping]) -> list[str]:
        """Get mitigation recommendations for detected techniques."""
        mitigations = set()
        mitigation_map = {
            "T1595": "M1056 - Pre-compromise: Network Monitoring",
            "T1071": "M1031 - Network Intrusion Prevention",
            "T1090": "M1037 - Filter Network Traffic",
            "T1566": "M1049 - Antivirus/Antimalware, M1054 - User Training",
            "T1190": "M1048 - Application Isolation, M1050 - Exploit Protection",
            "T1021": "M1032 - Multi-factor Authentication",
            "T1583": "M1056 - Pre-compromise: Threat Intelligence",
        }
        for tech in techniques:
            parent_id = tech.technique_id.split('.')[0]
            if parent_id in mitigation_map:
                mitigations.add(mitigation_map[parent_id])
        return list(mitigations)


def map_osint_to_attack(osint_result: Any, scan_type: str) -> AttackMapping:
    """Convenience function to map OSINT results to ATT&CK."""
    mapper = MITREAttackMapper()
    if scan_type == "ip":
        return mapper.map_ip_osint(osint_result)
    else:
        return mapper.map_domain_osint(osint_result)
