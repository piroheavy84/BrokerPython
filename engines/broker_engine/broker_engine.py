from models.search_result import SearchResult
from models.broker_response import BrokerResponse

from services.ranking_service import RankingService


class BrokerEngine:

    def search(
        self,
        rules,
        richiesta
    ):

        risultati = []

        for rule in rules:

            if not self._match_finalita(
                rule,
                richiesta
            ):

                continue

            tipo_tasso = self._get_tipo_tasso(
                rule
            )

            if not self._match_tasso(
                tipo_tasso,
                richiesta.tasso
            ):

                continue

            if richiesta.durata < rule["durata_min"]:

                continue

            if richiesta.durata > rule["durata_max"]:

                continue

            if richiesta.ltv > rule["ltv_max"]:

                continue

            risultati.append(
                SearchResult(
                    banca=rule["banca"],
                    tipo_listino=rule["tipo_listino"],
                    finalita=rule["finalita"],
                    tasso=tipo_tasso,
                    durata=f'{rule["durata_min"]}-{rule["durata_max"]}',
                    ltv=rule["ltv_max"],
                    spread=rule["spread"],
                    pagina=rule["pagina"],
                    pdf=rule["pdf"],
                    tasso_esplicito=rule.get(
                        "tasso_esplicito",
                        False
                    ),
                    indice_riferimento=rule.get(
                        "indice_riferimento",
                        None
                    ),
                    tasso_finito_pdf=rule.get(
                        "tasso_finito_pdf",
                        None
                    )
                )
            )

        ranking = RankingService()

        risultati = ranking.sort(
            risultati
        )

        return BrokerResponse(
            richiesta,
            risultati
        )

    def _match_finalita(
        self,
        rule,
        richiesta
    ):

        for finalita in rule["finalita"]:

            if richiesta.finalita in finalita:

                return True

        return False

    def _get_tipo_tasso(
        self,
        rule
    ):

        if isinstance(
            rule["tasso"],
            dict
        ):

            return rule["tasso"].get(
                "tipo",
                ""
            )

        return rule["tasso"]

    def _match_tasso(
        self,
        tipo_tasso_prodotto,
        tipo_tasso_richiesto
    ):

        prodotto = str(
            tipo_tasso_prodotto
        ).upper()

        richiesto = str(
            tipo_tasso_richiesto
        ).upper()

        if richiesto == "FISSO":

            return prodotto == "FISSO"

        if richiesto == "VARIABILE":

            return prodotto != "FISSO"

        return prodotto == richiesto
