from models.search_result import SearchResult
from models.broker_response import BrokerResponse

from services.ranking_service import RankingService


class BrokerEngine:

    def search(self, rules, richiesta):

        risultati = []

        for rule in rules:

            if not self._is_valid_product_rule(rule):
                continue

            if not self._match_finalita(rule, richiesta):
                continue

            tipo_tasso = self._get_tipo_tasso(rule)

            if not self._match_tasso(tipo_tasso, richiesta.tasso):
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
                    tasso_esplicito=rule.get("tasso_esplicito", False),
                    indice_riferimento=rule.get("indice_riferimento", None),
                    tasso_finito_pdf=rule.get("tasso_finito_pdf", None),
                    canalizzazione_da=rule.get("canalizzazione_da", ""),
                    canalizzazione_a=rule.get("canalizzazione_a", ""),
                    stipula_entro=rule.get("stipula_entro", ""),
                    condition=rule.get("condition", None),
                )
            )

        return BrokerResponse(
            richiesta,
            RankingService().sort(risultati)
        )

    def _is_valid_product_rule(self, rule):

        invalid_tassi = ["", "IN CORSO", "MAGAZZINO", "LISTINO"]

        tipo_tasso = self._get_tipo_tasso(rule)

        if str(tipo_tasso).upper() in invalid_tassi:
            return False

        if not rule.get("spread"):
            return False

        if not rule.get("finalita"):
            return False

        if rule.get("durata_min") is None:
            return False

        if rule.get("durata_max") is None:
            return False

        if rule.get("ltv_max") is None:
            return False

        return True

    def _match_finalita(self, rule, richiesta):

        richiesta_finalita = str(richiesta.finalita).upper()

        for finalita in rule["finalita"]:

            if richiesta_finalita in str(finalita).upper():
                return True

        return False

    def _get_tipo_tasso(self, rule):

        if isinstance(rule["tasso"], dict):
            return rule["tasso"].get("tipo", "")

        return rule["tasso"]

    def _match_tasso(self, tipo_tasso_prodotto, tipo_tasso_richiesto):

        prodotto = str(tipo_tasso_prodotto).upper()
        richiesto = str(tipo_tasso_richiesto).upper()

        if richiesto == "FISSO":
            return prodotto == "FISSO"

        if richiesto == "VARIABILE":
            return prodotto != "FISSO"

        return prodotto == richiesto
