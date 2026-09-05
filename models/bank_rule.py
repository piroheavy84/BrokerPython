from dataclasses import dataclass, field
from typing import Any

from models.rule_type import RuleType


@dataclass
class BankRule:

    type: RuleType

    title: str = ""

    description: str = ""

    parameters: dict[str, Any] = field(default_factory=dict)

    source_page: int = 0

    confidence: float = 1.0
