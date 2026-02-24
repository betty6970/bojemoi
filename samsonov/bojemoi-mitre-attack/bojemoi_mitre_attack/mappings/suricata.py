"""Suricata alert category -> MITRE ATT&CK technique mapping."""

from typing import Optional
from bojemoi_mitre_attack.models import TechniqueMapping

# Emerging Threats / Suricata alert categories -> ATT&CK (technique_id, name, tactic)
SURICATA_CATEGORY_MAPPING = {
    # Initial Access
    "web-application-attack": ("T1190", "Exploit Public-Facing Application", "initial-access"),
    "web-application-activity": ("T1190", "Exploit Public-Facing Application", "initial-access"),
    "attempted-user": ("T1078", "Valid Accounts", "initial-access"),

    # Reconnaissance
    "attempted-recon": ("T1595", "Active Scanning", "reconnaissance"),
    "successful-recon-limited": ("T1595.002", "Vulnerability Scanning", "reconnaissance"),
    "successful-recon-largescale": ("T1595.001", "Scanning IP Blocks", "reconnaissance"),
    "network-scan": ("T1046", "Network Service Discovery", "discovery"),
    "misc-activity": ("T1046", "Network Service Discovery", "discovery"),

    # Command and Control
    "trojan-activity": ("T1071", "Application Layer Protocol", "command-and-control"),
    "bad-unknown": ("T1071", "Application Layer Protocol", "command-and-control"),
    "potentially-bad-traffic": ("T1071", "Application Layer Protocol", "command-and-control"),
    "command-and-control": ("T1071", "Application Layer Protocol", "command-and-control"),
    "misc-attack": ("T1071", "Application Layer Protocol", "command-and-control"),

    # Credential Access
    "default-login-attempt": ("T1110", "Brute Force", "credential-access"),
    "credential-theft": ("T1003", "OS Credential Dumping", "credential-access"),
    "unsuccessful-user": ("T1110.001", "Password Guessing", "credential-access"),

    # Privilege Escalation
    "attempted-admin": ("T1078", "Valid Accounts", "privilege-escalation"),
    "successful-admin": ("T1078", "Valid Accounts", "privilege-escalation"),

    # Execution
    "shellcode-detect": ("T1059", "Command and Scripting Interpreter", "execution"),
    "rpc-portmap-decode": ("T1059", "Command and Scripting Interpreter", "execution"),
    "string-detect": ("T1059", "Command and Scripting Interpreter", "execution"),

    # Exfiltration
    "policy-violation": ("T1048", "Exfiltration Over Alternative Protocol", "exfiltration"),
    "suspicious-filename-detect": ("T1048", "Exfiltration Over Alternative Protocol", "exfiltration"),
    "suspicious-login": ("T1048", "Exfiltration Over Alternative Protocol", "exfiltration"),

    # Defense Evasion
    "protocol-command-decode": ("T1001", "Data Obfuscation", "defense-evasion"),
    "not-suspicious": ("T1001", "Data Obfuscation", "defense-evasion"),

    # Impact
    "attempted-dos": ("T1498", "Network Denial of Service", "impact"),
    "denial-of-service": ("T1498", "Network Denial of Service", "impact"),

    # Lateral Movement
    "icmp-event": ("T1018", "Remote System Discovery", "discovery"),
    "system-call-detect": ("T1059", "Command and Scripting Interpreter", "execution"),

    # Malware
    "kickass-porn": ("T1189", "Drive-by Compromise", "initial-access"),
    "exploit-kit": ("T1189", "Drive-by Compromise", "initial-access"),
    "malware-cnc": ("T1071", "Application Layer Protocol", "command-and-control"),
    "malware-other": ("T1204", "User Execution", "execution"),
}


def map_suricata_alert(category: str, signature: str = "",
                       severity: int = 3) -> Optional[TechniqueMapping]:
    """
    Map a Suricata alert to an ATT&CK technique.

    Args:
        category: Suricata alert category (e.g. 'web-application-attack')
        signature: Alert signature text for additional context
        severity: Alert severity (1=high, 2=medium, 3=low)

    Returns:
        TechniqueMapping or None if no mapping found
    """
    cat_lower = category.lower().strip()

    mapping = SURICATA_CATEGORY_MAPPING.get(cat_lower)
    if not mapping:
        return None

    technique_id, technique_name, tactic = mapping

    # Map Suricata severity (1=high, 2=medium, 3=low) to confidence
    confidence_map = {1: "high", 2: "medium", 3: "low"}
    confidence = confidence_map.get(severity, "low")

    reason = f"Suricata alert: {signature}" if signature else f"Suricata category: {category}"

    return TechniqueMapping(
        technique_id=technique_id,
        technique_name=technique_name,
        tactic=tactic,
        reason=reason,
        confidence=confidence,
    )
