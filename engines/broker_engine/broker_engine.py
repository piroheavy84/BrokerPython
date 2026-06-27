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

            # ---------------------
            # FINALITA
            # ---------------------

            ok = False

            for f in rule["finalita"]:

                if richiesta.finalita in f:

                    ok = True

                    break

            if not ok:

                continue

            # ---------------------
            # TASSO
            # ---------------------

            if isinstance(
                rule["tasso"],
                dict
            ):

                tipo_tasso = rule["tasso"].get(
                    "tipo",
                    ""
                )

            else:

                tipo_tasso = rule["tasso"]

            if tipo_tasso != richiesta.tasso:

                continue

            # ---------------------
            # DURATA
            # ---------------------

            if richiesta.durata < rule["durata_min"]:

                continue

            if richiesta.durata > rule["durata_max"]:

                continue

            # ---------------------
            # LTV
            # ---------------------

            if richiesta.ltv > rule["ltv_max"]:

                continue

            # ---------------------
            # NUOVI CAMPI TASSO
            # ---------------------

            tasso_esplicito = rule.get(
                "tasso_esplicito",
                False
            )

            indice_riferimento = rule.get(
                "indice_riferimento",
                None
            )

            tasso_finito_pdf = rule.get(
                "tasso_finito_pdf",
                None
            )

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
                    tasso_esplicito=tasso_esplicito,
                    indice_riferimento=indice_riferimento,
                    tasso_finito_pdf=tasso_finito_pdf
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