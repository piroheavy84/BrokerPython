from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExtractedRuleConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class ExtractedRuleSource:
    document: str
    page: int | None = None
    section: str | None = None
    original_text: str | None = None


@dataclass(frozen=True)
class ExtractedRule:
    type: str
    title: str
    conditions: list[dict[str, Any]] = field(default_factory=list)
    effects: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: ExtractedRuleConfidence = ExtractedRuleConfidence.LOW
    source: ExtractedRuleSource | None = None

    def is_valid(self) -> bool:
        return bool(self.type and self.title)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "conditions": self.conditions,
            "effects": self.effects,
            "notes": self.notes,
            "confidence": self.confidence.value,
            "source": {
                "document": self.source.document,
                "page": self.source.page,
                "section": self.source.section,
                "original_text": self.source.original_text,
            }
            if self.source
            else None,
        }
