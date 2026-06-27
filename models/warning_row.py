from dataclasses import dataclass

@dataclass
class WarningRow:

    pagina: int

    riga: int

    testo: str

    motivo: str