class SearchResult:

    def __init__(
        self,
        banca,
        tipo_listino,
        finalita,
        tasso,
        durata,
        ltv,
        spread,
        pagina,
        pdf,
        score=0,
        tasso_esplicito=False,
        indice_riferimento=None,
        tasso_finito_pdf=None,
        canalizzazione_da="",
        canalizzazione_a="",
        stipula_entro="",
        condition=None
    ):

        self.banca = banca
        self.tipo_listino = tipo_listino
        self.finalita = finalita
        self.tasso = tasso
        self.durata = durata
        self.ltv = ltv
        self.spread = spread
        self.pagina = pagina
        self.pdf = pdf
        self.score = score
        self.tasso_esplicito = tasso_esplicito
        self.indice_riferimento = indice_riferimento
        self.tasso_finito_pdf = tasso_finito_pdf
        self.canalizzazione_da = canalizzazione_da
        self.canalizzazione_a = canalizzazione_a
        self.stipula_entro = stipula_entro
        self.condition = condition

    def __repr__(self):

        return (
            f"{self.banca} "
            f"{self.tasso} "
            f"{self.spread}"
        )
