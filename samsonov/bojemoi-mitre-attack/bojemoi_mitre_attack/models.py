"""Data models for MITRE ATT&CK mappings."""

import json
from dataclasses import dataclass, field, asdict


@dataclass
class TechniqueMapping:
    """A technique detected from OSINT data."""
    technique_id: str
    technique_name: str
    tactic: str
    reason: str
    confidence: str = "low"  # low, medium, high

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AttackMapping:
    """Complete ATT&CK mapping result."""
    target: str
    scan_type: str
    tactics: list[str] = field(default_factory=list)
    techniques: list[TechniqueMapping] = field(default_factory=list)
    potential_groups: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = asdict(self)
        result['techniques'] = [t.to_dict() if isinstance(t, TechniqueMapping) else t for t in self.techniques]
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
