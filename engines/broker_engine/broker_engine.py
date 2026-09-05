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
            product_rules = rules.get("products") or rules.get("rules") or rules.get("product_rules") or []
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
            if richiesta.durata < rule["durata_min"] or richiesta.durata > rule["durata_max"]:
                continue
            if richiesta.ltv > rule["ltv_max"]:
                if has_ltc and self._is_ltc_candidate_rule(rule, richiesta, rule_engine):
                    ltc_candidate = dict(rule)
                    ltc_candidate["_ltc_only_candidate"] = True
                    candidate_rules.append(ltc_candidate)
                continue
            candidate_rules.append(rule)

        candidate_rules = self._filter_preferred_listino(candidate_rules)
        candidate_rules = self._filter_by_rogito_best_listino(candidate_rules, richiesta)
        candidate_rules = self._filter_by_ltv_band(candidate_rules, richiesta)

        if knowledge:
            candidate_rules = rule_engine.apply(candidate_rules, richiesta, knowledge)
            candidate_rules = self._decorate_commercial_promotions(
                candidate_rules,
                richiesta,
                knowledge,
            )

        risultati = []
        for rule in candidate_rules:
            tipo_tasso = self._get_tipo_tasso(rule)
            extra = self._extract_extra_fields(rule)
            result = SearchResult(
                banca=rule["banca"], tipo_listino=rule["tipo_listino"], finalita=rule["finalita"],
                tasso=tipo_tasso, durata=f'{rule["durata_min"]}-{rule["durata_max"]}',
                ltv=rule["ltv_max"], spread=rule["spread"], pagina=rule["pagina"], pdf=rule["pdf"],
                tasso_esplicito=rule.get("tasso_esplicito", False),
                indice_riferimento=rule.get("indice_riferimento", None),
                tasso_finito_pdf=rule.get("tasso_finito_pdf", None),
                canalizzazione_da=rule.get("canalizzazione_da", ""),
                canalizzazione_a=rule.get("canalizzazione_a", ""),
                stipula_entro=rule.get("stipula_entro", ""),
                condition=rule.get("condition", None), extra=extra,
            )
            risultati.append(result)
        return BrokerResponse(richiesta, RankingService().sort(risultati))

    def _filter_preferred_listino(self, rules):
        """Se per una banca esistono regole IN VIGORE, non propone il MAGAZZINO.

        La scelta è per banca, così un listino storico di una banca non influenza
        i risultati delle altre. I documenti legacy senza classificazione restano
        invariati.
        """
        if not rules:
            return rules
        by_bank = {}
        for rule in rules:
            by_bank.setdefault(str(rule.get("banca") or ""), []).append(rule)
        selected = []
        for bank_rules in by_bank.values():
            active = [r for r in bank_rules if str(r.get("tipo_listino") or "").strip().upper() == "IN VIGORE"]
            if active:
                selected.extend(active)
            else:
                selected.extend(bank_rules)
        return selected

    def _extract_extra_fields(self, rule):
        extra_keys = ["prodotto_speciale", "convenzione", "valore_perizia", "massimo_finanziabile_ltc",
            "ltv_standard_base", "ltc_limite", "ltc_periodo", "ltc_data_regola", "ltc_rule_page",
            "ltc_spread_bps", "ltc_reddito_soglia", "ltc_reddito_operatore", "ltc_reddito_minimo",
            "ltc_reddito_note", "spread_base", "spread_delta", "motivo_prodotto_speciale", "tasso_base",
            "pagina_prodotto_base", "pagina_regola_ltc", "pdf_pagine_riferimento", "promozione", "green_tipo",
            "green_sconto", "green_sconto_bps", "green_tipo_label", "green_finalita", "green_classe_energetica",
            "green_limite_importo", "green_limite_importo_applicato", "green_note_applicazione", "green_requisiti",
            "green_rule_page", "pagina_regola_green", "applied_rules", "rule_checks", "warnings"]
        return {key: rule.get(key) for key in extra_keys if key in rule}

    def _decorate_commercial_promotions(self, rules, richiesta, knowledge):
        if not rules or not knowledge:
            return rules

        by_bank = {}
        for page in knowledge:
            if not isinstance(page, dict):
                continue
            bank = str(page.get("banca") or "").strip()
            if not bank:
                # Le knowledge precedenti non avevano banca. Le ignoriamo per
                # evitare che una promozione venga applicata all'istituto errato.
                continue
            for commercial in page.get("commercial_rules") or []:
                if str(commercial.get("rule_type") or "").upper() != "DISCOUNT":
                    continue
                item = dict(commercial)
                item.setdefault("page", page.get("page"))
                by_bank.setdefault(bank.lower(), []).append(item)

        decorated = []
        for original in rules:
            rule = dict(original)
            discounts = by_bank.get(str(rule.get("banca") or "").strip().lower(), [])
            if not discounts:
                decorated.append(rule)
                continue

            relevant = [d for d in discounts if self._commercial_finalita_matches(d, richiesta)]
            if not relevant:
                decorated.append(rule)
                continue

            applied_green = None
            for discount in relevant:
                if str(discount.get("discount_type") or "").upper() != "GREEN":
                    continue
                if discount.get("automatic") is not True:
                    continue
                if not self._commercial_energy_matches(discount, richiesta):
                    continue
                if str(rule.get("promozione") or "").upper() == "GREEN" or rule.get("green_sconto"):
                    # Green già gestito dal RuleEngine (es. CheBanca): non duplicare.
                    applied_green = discount
                    break
                try:
                    percent = float(discount.get("percent") or 0.0)
                except (TypeError, ValueError):
                    percent = 0.0
                if percent <= 0:
                    continue

                base_value = self._rate_value(
                    rule.get("tasso_finito_pdf") if rule.get("tasso_esplicito") else rule.get("spread")
                )
                if base_value is None:
                    continue
                discounted = max(0.0, base_value - percent)

                if rule.get("tasso_esplicito"):
                    rule["spread_base"] = rule.get("tasso_finito_pdf") or rule.get("spread")
                    rule["tasso_finito_pdf"] = self._rate_label(discounted)
                    rule["spread"] = self._rate_label(discounted)
                else:
                    rule["spread_base"] = rule.get("spread")
                    rule["spread"] = self._rate_label(discounted)

                rule["spread_delta"] = -percent
                rule["prodotto_speciale"] = True
                rule["promozione"] = "GREEN"
                rule["green_tipo"] = "COMMERCIAL_RULE"
                rule["green_tipo_label"] = "Sconto Green automatico da regola commerciale"
                rule["green_sconto"] = percent
                rule["green_sconto_bps"] = discount.get("basis_points") or round(percent * 100)
                rule["green_finalita"] = getattr(richiesta, "finalita", "")
                rule["green_classe_energetica"] = getattr(richiesta, "classe_energetica", "")
                rule["green_rule_page"] = discount.get("page")
                rule["pagina_regola_green"] = discount.get("page")
                applied_green = discount
                break

            summary = self._commercial_summary(relevant, applied_green)
            if summary:
                existing_note = str(rule.get("motivo_prodotto_speciale") or "").strip()
                rule["motivo_prodotto_speciale"] = (
                    f"{existing_note} | {summary}" if existing_note else summary
                )
                rule["prodotto_speciale"] = True
                if not rule.get("promozione"):
                    rule["promozione"] = "COMMERCIAL_RULES"

            decorated.append(rule)
        return decorated

    def _commercial_finalita_matches(self, discount, richiesta):
        finalita = discount.get("finalita")
        if not finalita:
            return True
        try:
            return self.finalita_normalizer.match(
                getattr(richiesta, "finalita", ""),
                finalita,
            )
        except Exception:
            requested = str(getattr(richiesta, "finalita", "") or "").upper()
            values = finalita if isinstance(finalita, list) else [finalita]
            return any(str(value or "").upper() in requested for value in values)

    def _commercial_energy_matches(self, discount, richiesta):
        allowed = [self._energy_norm(v) for v in (discount.get("classi_energetiche") or [])]
        if not allowed:
            return True
        requested = self._energy_norm(getattr(richiesta, "classe_energetica", ""))
        if not requested:
            return False
        if requested in allowed:
            return True
        if "A_SUPERIORE" in allowed and requested.startswith("A"):
            return True
        return False

    def _commercial_summary(self, discounts, applied_green):
        rows = []
        for discount in discounts:
            name = str(discount.get("name") or discount.get("discount_type") or "Sconto").strip()
            try:
                percent = float(discount.get("percent") or 0.0)
            except (TypeError, ValueError):
                percent = 0.0
            if percent <= 0:
                continue
            status = " applicato automaticamente" if discount is applied_green else " da verificare"
            rows.append(f"{name} -{percent:.2f}%{status}")
        if not rows:
            return ""
        return "Scontistiche commerciali: " + "; ".join(rows)

    def _rate_value(self, value):
        try:
            return float(str(value).replace("%", "").replace(",", ".").strip())
        except (TypeError, ValueError):
            return None

    def _rate_label(self, value):
        return f"{float(value):.2f}%".replace(".", ",")

    def _energy_norm(self, value):
        text = str(value or "").strip().upper().replace(" ", "_")
        text = text.replace("+", "_SUPERIORE")
        return text

    def _is_ltc_candidate_rule(self, rule, richiesta, rule_engine):
        try:
            base_ltv = float(rule.get("ltv_max", 0) or 0)
        except Exception:
            return False
        if base_ltv <= 0:
            return False
        return rule_engine.is_ltc_eligible(richiesta, base_ltv_percent=base_ltv)

    def _is_valid_product_rule(self, rule):
        invalid_tassi = ["", "IN CORSO", "MAGAZZINO", "LISTINO"]
        tipo_tasso = self._get_tipo_tasso(rule)
        if str(tipo_tasso).upper() in invalid_tassi or not rule.get("spread") or not rule.get("finalita"):
            return False
        if rule.get("durata_min") is None or rule.get("durata_max") is None or rule.get("ltv_max") is None:
            return False
        return True

    def _filter_by_rogito_best_listino(self, rules, richiesta):
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
            stipula_entro = self._parse_date(rule.get("stipula_entro", ""))
            if stipula_entro is not None:
                dated_rules.append((rule, stipula_entro))
        if not dated_rules:
            return rules
        valid_dates = sorted({d for _, d in dated_rules if d >= data_rogito})
        selected_date = valid_dates[0] if valid_dates else max(d for _, d in dated_rules)
        return [rule for rule, d in dated_rules if d == selected_date]

    def _filter_by_ltv_band(self, rules, richiesta):
        if not rules:
            return rules
        standard_rules = [r for r in rules if not r.get("_ltc_only_candidate", False)]
        ltc_only_rules = [r for r in rules if r.get("_ltc_only_candidate", False)]
        grouped = {}
        for rule in standard_rules:
            grouped.setdefault(self._ltv_group_key(rule), []).append(rule)
        selected = []
        pratica_ltv = float(getattr(richiesta, "ltv", 0) or 0)
        for group_rules in grouped.values():
            ltv_values = sorted({int(r.get("ltv_max")) for r in group_rules if r.get("ltv_max") is not None})
            compatible = [v for v in ltv_values if pratica_ltv <= v]
            if not compatible:
                continue
            selected_ltv = min(compatible)
            selected.extend(r for r in group_rules if int(r.get("ltv_max")) == selected_ltv)
        ltc_grouped = {}
        for rule in ltc_only_rules:
            ltc_grouped.setdefault(self._ltv_group_key(rule), []).append(rule)
        for group_rules in ltc_grouped.values():
            max_ltv = max(int(r.get("ltv_max", 0) or 0) for r in group_rules)
            for rule in group_rules:
                if int(rule.get("ltv_max", 0) or 0) == max_ltv:
                    selected.append(rule)
                    break
        return selected

    def _ltv_group_key(self, rule):
        return (rule.get("banca", ""), rule.get("pdf", ""), rule.get("pagina", ""), rule.get("tipo_listino", ""),
            rule.get("canalizzazione_da", ""), rule.get("canalizzazione_a", ""), rule.get("stipula_entro", ""),
            self._get_tipo_tasso(rule), rule.get("durata_min", ""), rule.get("durata_max", ""))

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
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"]:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        return None

    def _match_finalita(self, rule, richiesta):
        return self.finalita_normalizer.match(getattr(richiesta, "finalita", ""), rule.get("finalita", []))

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
