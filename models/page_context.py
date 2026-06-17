from dataclasses import dataclass, field


@dataclass
class PageContext:

    banca: str = ""

    versione: str = ""

    pagina: int = 0

    finalita: str = ""

    tipo_tasso: str = ""

    promo: str = ""

    validita: str = ""

    canalizzazione: str = ""

    caricamento: str = ""

    stipula: str = ""

    note: list = field(default_factory=list)

    warning: list = field(default_factory=list)

    tabella: list = field(default_factory=list)