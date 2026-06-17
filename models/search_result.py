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

        score=0

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

    def __repr__(self):

        return (

            f"{self.banca} "

            f"{self.tasso} "

            f"{self.spread}"

        )