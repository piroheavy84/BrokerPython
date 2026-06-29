from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageKnowledge:

    page: int = 0

    header: dict[str, Any] = field(
        default_factory=dict
    )

    products: list[dict[str, Any]] = field(
        default_factory=list
    )

    costs: list[dict[str, Any]] = field(
        default_factory=list
    )

    conditions: list[dict[str, Any]] = field(
        default_factory=list
    )

    exceptions: list[dict[str, Any]] = field(
        default_factory=list
    )

    notes: list[str] = field(
        default_factory=list
    )

    raw_text: str = ""

    def to_dict(self):

        return {
            "page": self.page,
            "header": self.header,
            "products": self.products,
            "costs": self.costs,
            "conditions": self.conditions,
            "exceptions": self.exceptions,
            "notes": self.notes,
            "raw_text": self.raw_text
        }
