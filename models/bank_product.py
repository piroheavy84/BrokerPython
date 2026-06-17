from dataclasses import dataclass

@dataclass
class BankProduct:

    banca: str

    finalita: str

    tipo_tasso: str

    durata_min: int

    durata_max: int

    ltv_max: int

    spread: float

    promo: str = ""

    note: str = ""