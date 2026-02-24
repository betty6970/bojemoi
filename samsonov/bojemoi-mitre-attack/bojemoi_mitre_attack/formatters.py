"""Formatters for ATT&CK mapping output (text, markdown, Navigator JSON)."""

from typing import Any
from bojemoi_mitre_attack.models import AttackMapping, TechniqueMapping


def format_attack_mapping_text(mapping: AttackMapping) -> str:
    """Format ATT&CK mapping as plain text."""
    lines = []
    lines.append("=" * 60)
    lines.append("MITRE ATT&CK MAPPING")
    lines.append("=" * 60)
    lines.append(f"Target: {mapping.target}")
    lines.append(f"Type: {mapping.scan_type.upper()}")
    lines.append("")

    lines.append(f"TACTICS IDENTIFIED: {len(mapping.tactics)}")
    for tactic in mapping.tactics:
        lines.append(f"  - {tactic.replace('-', ' ').title()}")
    lines.append("")

    lines.append(f"TECHNIQUES DETECTED: {len(mapping.techniques)}")
    lines.append("-" * 60)

    techniques_by_tactic: dict[str, list[TechniqueMapping]] = {}
    for tech in mapping.techniques:
        techniques_by_tactic.setdefault(tech.tactic, []).append(tech)

    for tactic, techniques in techniques_by_tactic.items():
        lines.append(f"\n{tactic.replace('-', ' ').upper()}")
        for tech in techniques:
            confidence_marker = {'high': '[!!!]', 'medium': '[!!]', 'low': '[!]'}.get(tech.confidence, '[-]')
            lines.append(f"  {confidence_marker} {tech.technique_id} - {tech.technique_name}")
            lines.append(f"      Reason: {tech.reason}")
            lines.append(f"      Confidence: {tech.confidence.upper()}")

    if mapping.potential_groups:
        lines.append("")
        lines.append("POTENTIAL APT GROUPS")
        lines.append("-" * 60)
        for group in mapping.potential_groups:
            lines.append(f"  - {group}")

    if mapping.recommendations:
        lines.append("")
        lines.append("MITIGATION RECOMMENDATIONS")
        lines.append("-" * 60)
        for rec in mapping.recommendations:
            lines.append(f"  - {rec}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_attack_mapping_markdown(mapping: AttackMapping) -> str:
    """Format ATT&CK mapping as Markdown."""
    lines = []
    lines.append(f"# MITRE ATT&CK Mapping - `{mapping.target}`")
    lines.append("")

    high_conf = sum(1 for t in mapping.techniques if t.confidence == 'high')
    lines.append(f"**Tactics:** {len(mapping.tactics)} | **Techniques:** {len(mapping.techniques)} | **High Confidence:** {high_conf}")
    lines.append("")

    if mapping.tactics:
        lines.append("## Tactics Identified")
        for tactic in mapping.tactics:
            lines.append(f"- {tactic.replace('-', ' ').title()}")
        lines.append("")

    lines.append("## Techniques Detected")

    techniques_by_tactic: dict[str, list[TechniqueMapping]] = {}
    for tech in mapping.techniques:
        techniques_by_tactic.setdefault(tech.tactic, []).append(tech)

    for tactic, techniques in techniques_by_tactic.items():
        lines.append(f"\n### {tactic.replace('-', ' ').title()}")
        for tech in techniques:
            lines.append(f"\n**{tech.technique_id}** - {tech.technique_name}")
            lines.append(f"- *Reason:* {tech.reason}")
            lines.append(f"- *Confidence:* `{tech.confidence.upper()}`")

    if mapping.potential_groups:
        lines.append("")
        lines.append("## Potential Threat Actors")
        for group in mapping.potential_groups:
            lines.append(f"- {group}")

    if mapping.recommendations:
        lines.append("")
        lines.append("## Mitigation Recommendations")
        for rec in mapping.recommendations:
            lines.append(f"- {rec}")

    return "\n".join(lines)


def export_to_navigator(mapping: AttackMapping) -> dict[str, Any]:
    """Export mapping to ATT&CK Navigator layer JSON format."""
    layer = {
        "name": f"Bojemoi - {mapping.target}",
        "versions": {"attack": "14", "navigator": "4.9.1", "layer": "4.5"},
        "domain": "enterprise-attack",
        "description": f"ATT&CK mapping for {mapping.target} ({mapping.scan_type})",
        "filters": {"platforms": ["windows", "linux", "macos", "network"]},
        "sorting": 0,
        "layout": {
            "layout": "side",
            "aggregateFunction": "average",
            "showID": True,
            "showName": True,
        },
        "hideDisabled": False,
        "techniques": [],
    }

    for tech in mapping.techniques:
        confidence_score = {'high': 100, 'medium': 50, 'low': 25}.get(tech.confidence, 25)
        color = {'high': '#ff6666', 'medium': '#ffcc66', 'low': '#99ccff'}.get(tech.confidence, '#cccccc')

        layer['techniques'].append({
            "techniqueID": tech.technique_id,
            "tactic": tech.tactic,
            "color": color,
            "comment": tech.reason,
            "enabled": True,
            "score": confidence_score,
            "metadata": [
                {"name": "Confidence", "value": tech.confidence},
                {"name": "Reason", "value": tech.reason},
            ],
        })

    return layer
