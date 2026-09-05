from datetime import datetime

from models.search_result import SearchResult
from models.broker_response import BrokerResponse

from services.ranking_service import RankingService
from services.rule_engine import RuleEngine
from services.finalita_normalizer import FinalitaNormalizer


class BrokerEngine:

    def __init__(self):
        self.finalita_normalizer = FinalitaNormalizer()

    def search(self, rules, richiesta, knowledge=None):

        product_rules = rules

        if isinstance(rules, dict):
            product_rules = (
                rules.get("products")
                or rules.get("rules")
                or rules.get("product_rules")
                or []
            )
            knowledge = knowledge or rules.get("knowledge")

        rule_engine = RuleEngine()
        has_ltc = bool(knowledge) and rule_engine.has_ltc_rules(knowledge)

        candidate_rules = []

        for rule in product_rules:

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
                # Se la pratica supera l'LTV standard, tengo comunque una copia
                # solo come candidata LTC. Il RuleEngine la trasformerà in prodotto
                # LTC se valore perizia e massimo finanziabile lo consentono.
                if has_ltc and self._is_ltc_candidate_rule(rule, richiesta, rule_engine):
                    ltc_candidate = dict(rule)
                    ltc_candidate["_ltc_only_candidate"] = True
                    candidate_rules.append(ltc_candidate)
                continue

            candidate_rules.append(rule)

        candidate_rules = self._filter_by_rogito_best_listino(
            candidate_rules,
            richiesta,
        )

        candidate_rules = self._filter_by_ltv_band(
            candidate_rules,
            richiesta,
        )

        if knowledge:
            candidate_rules = rule_engine.apply(
                candidate_rules,
                richiesta,
                knowledge,
            )

        risultati = []

        for rule in candidate_rules:

            tipo_tasso = self._get_tipo_tasso(rule)

            extra = self._extract_extra_fields(rule)

            result = SearchResult(
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
                extra=extra,
            )

            risultati.append(result)

        return BrokerResponse(
            richiesta,
            RankingService().sort(risultati)
        )

    def _extract_extra_fields(self, rule):
        extra_keys = [
            "prodotto_speciale",
            "convenzione",
            "valore_perizia",
            "massimo_finanziabile_ltc",
            "ltv_standard_base",
            "ltc_limite",
            "ltc_periodo",
            "ltc_data_regola",
            "ltc_rule_page",
            "ltc_spread_bps",
            "ltc_reddito_soglia",
            "ltc_reddito_operatore",
            "ltc_reddito_minimo",
            "ltc_reddito_note",
            "spread_base",
            "spread_delta",
            "motivo_prodotto_speciale",
            "tasso_base",
            "pagina_prodotto_base",
            "pagina_regola_ltc",
            "pdf_pagine_riferimento",
            "promozione",
            "green_tipo",
            "green_sconto",
            "green_sconto_bps",
            "green_tipo_label",
            "green_finalita",
            "green_classe_energetica",
            "green_limite_importo",
            "green_limite_importo_applicato",
            "green_note_applicazione",
            "green_requisiti",
            "green_rule_page",
            "pagina_regola_green",
            "applied_rules",
            "rule_checks",
            "warnings",
        ]

        return {
            key: rule.get(key)
            for key in extra_keys
            if key in rule
        }

    def _is_ltc_candidate_rule(self, rule, richiesta, rule_engine):
        # Uso come base solo la fascia massima standard disponibile, normalmente 80.
        try:
            base_ltv = float(rule.get("ltv_max", 0) or 0)
        except Exception:
            return False

        if base_ltv <= 0:
            return False

        return rule_engine.is_ltc_eligible(
            richiesta,
            base_ltv_percent=base_ltv,
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

    def _filter_by_rogito_best_listino(self, rules, richiesta):
        """
        Se è presente la data rogito:
        - usa il listino valido più vicino alla data rogito;
        - se la data rogito è oltre tutti i listini disponibili,
          usa comunque l'ultimo listino disponibile.
        """

        if not rules:
            return rules

        data_rogito_raw = getattr(richiesta, "data_rogito", None)

        if not data_rogito_raw:
            return rules

        data_rogito = self._parse_date(data_rogito_raw)

        if data_rogito is None:
            return rules

        dated_rules = []

        for rule in rules:
            stipula_entro = self._parse_date(
                rule.get("stipula_entro", "")
            )

            if stipula_entro is not None:
                dated_rules.append((rule, stipula_entro))

        if not dated_rules:
            return rules

        valid_dates = sorted(
            {
                stipula_entro
                for _, stipula_entro in dated_rules
                if stipula_entro >= data_rogito
            }
        )

        if valid_dates:
            selected_date = valid_dates[0]
        else:
            selected_date = max(
                stipula_entro
                for _, stipula_entro in dated_rules
            )

        return [
            rule
            for rule, stipula_entro in dated_rules
            if stipula_entro == selected_date
        ]

    def _filter_by_ltv_band(self, rules, richiesta):
        """
        Sceglie una sola fascia LTV per ogni gruppo prodotto/durata.
        I candidati solo-LTC vengono mantenuti separatamente, perché servono
        per generare il prodotto LTC anche quando la pratica supera LTV 80.
        """

        if not rules:
            return rules

        standard_rules = [
            rule for rule in rules
            if not rule.get("_ltc_only_candidate", False)
        ]

        ltc_only_rules = [
            rule for rule in rules
            if rule.get("_ltc_only_candidate", False)
        ]

        grouped = {}

        for rule in standard_rules:
            key = self._ltv_group_key(rule)
            grouped.setdefault(key, []).append(rule)

        selected = []
        pratica_ltv = float(getattr(richiesta, "ltv", 0) or 0)

        for group_rules in grouped.values():
            ltv_values = sorted(
                {
                    int(rule.get("ltv_max"))
                    for rule in group_rules
                    if rule.get("ltv_max") is not None
                }
            )

            if not ltv_values:
                continue

            compatible_values = [
                value
                for value in ltv_values
                if pratica_ltv <= value
            ]

            if not compatible_values:
                continue

            selected_ltv = min(compatible_values)

            for rule in group_rules:
                if int(rule.get("ltv_max")) == selected_ltv:
                    selected.append(rule)

        # Per i candidati LTC sopra LTV standard tengo una sola fascia per gruppo:
        # la fascia massima disponibile, che sarà usata come LTV standard base.
        ltc_grouped = {}

        for rule in ltc_only_rules:
            key = self._ltv_group_key(rule)
            ltc_grouped.setdefault(key, []).append(rule)

        for group_rules in ltc_grouped.values():
            max_ltv = max(
                int(rule.get("ltv_max", 0) or 0)
                for rule in group_rules
            )
            for rule in group_rules:
                if int(rule.get("ltv_max", 0) or 0) == max_ltv:
                    selected.append(rule)
                    break

        return selected

    def _ltv_group_key(self, rule):
        return (
            rule.get("banca", ""),
            rule.get("pdf", ""),
            rule.get("pagina", ""),
            rule.get("tipo_listino", ""),
            rule.get("canalizzazione_da", ""),
            rule.get("canalizzazione_a", ""),
            rule.get("stipula_entro", ""),
            self._get_tipo_tasso(rule),
            rule.get("durata_min", ""),
            rule.get("durata_max", ""),
        )

    def _parse_date(self, value):

        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        text = str(value).strip()

        if not text:
            return None

        if "T" in text:
            text = text.split("T")[0]

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d/%m/%y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass

        return None

    def _match_finalita(self, rule, richiesta):
        return self.finalita_normalizer.match(
            getattr(richiesta, "finalita", ""),
            rule.get("finalita", []),
        )

    def _get_tipo_tasso(self, rule):

        if isinstance(rule["tasso"], dict):
            return rule["tasso"].get("tipo", "")

        return rule["tasso"]

    def _match_tasso(self, tipo_tasso_prodotto, tipo_tasso_richiesto):

        prodotto = str(tipo_tasso_prodotto).upper()
        richiesto = str(tipo_tasso_richiesto).upper()

        if richiesto == "FISSO":
            return prodotto == "FISSO" or prodotto.startswith("FISSO ") or prodotto.startswith("TF ")

        if richiesto == "VARIABILE":
            return not (prodotto == "FISSO" or prodotto.startswith("FISSO ") or prodotto.startswith("TF "))

        return prodotto == richiesto
