from dataclasses import dataclass


@dataclass
class RuleResult:

    eligible: bool

    reason: str = ""

    warning: str = ""

    extra_spread: float = 0.0
