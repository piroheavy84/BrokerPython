class RuleEngine:
    """
    Motore universale per applicare regole lette dal knowledge.json.

    Questa versione aggiunge il primo caso reale:
    - prodotto/convenzione LTC letta dal PDF;
    - calcolo massimo finanziabile da valore perizia;
    - creazione di un prodotto aggiuntivo separato, senza modificare quello base.

    Regola LTC:
        massimo_finanziabile = min(
            valore_perizia * ltv_standard_prodotto,
            valore_immobile * limite_ltc
        )
    """

    def apply(self, prodotti, pratica, knowledge):
        rules = self._collect_rules(knowledge)
        risultati = []

        for prodotto in prodotti:
            keep_base = not prodotto.get("_ltc_only_candidate", False)

            if keep_base:
                enriched = dict(prodotto)
                enriched.setdefault("warnings", [])
                enriched.setdefault("applied_rules", [])

                for rule in rules:
                    if not self._rule_matches(rule, enriched, pratica):
                        continue
                    enriched = self._apply_rule(rule, enriched, pratica)

                enriched = self._apply_surroga_minimum(enriched, pratica)
                risultati.append(enriched)
                green_clones = self._build_green_clones(enriched, pratica, rules)
                risultati.extend([self._apply_surroga_minimum(clone, pratica) for clone in green_clones])

            ltc_clones = self._build_ltc_clones(prodotto, pratica, rules)
            for ltc_clone in ltc_clones:
                ltc_clone = self._apply_surroga_minimum(ltc_clone, pratica)
                risultati.append(ltc_clone)
                green_ltc_clones = self._build_green_clones(ltc_clone, pratica, rules)
                risultati.extend([self._apply_surroga_minimum(clone, pratica) for clone in green_ltc_clones])

        return risultati

    def _collect_rules(self, knowledge):
        rules = []

        if isinstance(knowledge, dict):
            pages = knowledge.get("pages", [])
            if not pages and "conditions" in knowledge:
                pages = [knowledge]
        elif isinstance(knowledge, list):
            pages = knowledge
        else:
            pages = []

        for page in pages:
            if isinstance(page, dict) and page.get("raw_text"):
                rules.append({
                    "rule_type": "page_raw_text",
                    "page": page.get("page"),
                    "header": page.get("header", {}),
                    "raw_text": page.get("raw_text", ""),
                    "source_text": page.get("raw_text", ""),
                })

            for condition in page.get("conditions", []):
                if isinstance(condition, dict):
                    condition = dict(condition)
                    condition.setdefault("page", page.get("page"))
                    condition.setdefault("header", page.get("header", {}))
                    rules.append(condition)

        return rules

    # ------------------------------------------------------------------
    # LTC
    # ------------------------------------------------------------------

    def has_ltc_rules(self, knowledge):
        rules = self._collect_rules(knowledge)
        return self._get_ltc_limit(rules) is not None

    def is_ltc_eligible(self, pratica, base_ltv_percent=80, ltc_limit=None):
        valore = self._to_float(self._get_pratica_value(pratica, "valore"))
        perizia = self._to_float(self._get_pratica_value(pratica, "valore_perizia"))
        importo = self._to_float(self._get_pratica_value(pratica, "importo"))

        if not valore or not perizia or not importo:
            return False

        if perizia <= valore:
            return False

        if ltc_limit is None:
            ltc_limit = 95

        massimo = self._ltc_massimo_finanziabile(
            valore=valore,
            perizia=perizia,
            base_ltv_percent=base_ltv_percent,
            ltc_limit=ltc_limit,
        )

        return importo <= massimo

    def _build_ltc_clones(self, prodotto, pratica, rules):
        campaigns = self._get_ltc_campaigns(rules)
        if not campaigns:
            return []

        valore = self._to_float(self._get_pratica_value(pratica, "valore"))
        perizia = self._to_float(self._get_pratica_value(pratica, "valore_perizia"))
        importo = self._to_float(self._get_pratica_value(pratica, "importo"))

        if not valore or not perizia or not importo:
            return []

        if perizia <= valore:
            return []

        base_ltv = self._to_float(prodotto.get("ltv_max"))
        if not base_ltv:
            return []

        tipo_tasso = self._get_tipo_tasso(prodotto)
        base_spread = self._parse_percent(prodotto.get("spread", 0))
        if base_spread is None:
            return []

        clones = []

        for campaign in campaigns:
            ltc_limit = campaign.get("ltc_limit") or self._get_ltc_limit(rules)
            if ltc_limit is None:
                continue

            massimo_ltc = self._ltc_massimo_finanziabile(
                valore=valore,
                perizia=perizia,
                base_ltv_percent=base_ltv,
                ltc_limit=ltc_limit,
            )

            # Se il prodotto LTC non è finanziariamente raggiungibile, non lo mostro.
            # I requisiti reddituali invece non nascondono il prodotto: lo rendono rosso.
            if importo > massimo_ltc:
                continue

            spread_delta = campaign.get("spread_delta")
            if spread_delta is None:
                spread_delta = self._get_ltc_spread_delta(rules)
            if spread_delta is None:
                spread_delta = 0.0

            convenzione = f"LTC{int(ltc_limit)}"

            clone = dict(prodotto)
            clone.pop("_ltc_only_candidate", None)
            clone.setdefault("warnings", [])
            clone.setdefault("applied_rules", [])
            clone.setdefault("rule_checks", [])

            # Mantengo il tipo tasso base per i calcoli (FISSO => IRS, VARIABILE => EURIBOR),
            # ma mostro il prodotto come variante LTC.
            clone["tasso_base"] = tipo_tasso
            clone["tasso"] = self._set_tipo_tasso(
                clone.get("tasso"),
                f"{tipo_tasso} {convenzione}"
            )
            clone["ltv_max"] = int(ltc_limit)
            clone["spread_base"] = self._format_percent(base_spread)
            clone["spread_delta"] = float(spread_delta)
            clone["spread"] = self._format_percent(base_spread + float(spread_delta))
            clone["prodotto_speciale"] = True
            clone["convenzione"] = convenzione
            clone["valore_perizia"] = perizia
            clone["massimo_finanziabile_ltc"] = massimo_ltc
            clone["ltv_standard_base"] = base_ltv
            clone["ltc_limite"] = int(ltc_limit)
            clone["ltc_periodo"] = campaign.get("period_label")
            clone["ltc_data_regola"] = campaign.get("date_label")
            clone["ltc_rule_page"] = campaign.get("page")
            clone["ltc_spread_bps"] = campaign.get("basis_points")
            clone["motivo_prodotto_speciale"] = (
                f"{convenzione} attivo: perizia superiore al valore immobile"
            )
            clone["pagina_prodotto_base"] = prodotto.get("pagina")
            clone["pagina_regola_ltc"] = campaign.get("page") or self._get_ltc_rule_page(rules)
            clone["pdf_pagine_riferimento"] = self._merge_pages(
                prodotto.get("pagina"),
                clone.get("pagina_regola_ltc"),
            )

            self._apply_ltc_income_check(clone, pratica, campaign, importo)

            clone["applied_rules"].append({
                "rule_type": "extended_financing_ltc",
                "convention": convenzione,
                "period": campaign.get("period_label"),
                "ltc_limit": int(ltc_limit),
                "standard_ltv": base_ltv,
                "spread_delta": float(spread_delta),
                "basis_points": campaign.get("basis_points"),
                "massimo_finanziabile_ltc": massimo_ltc,
            })

            clones.append(clone)

        return clones

    def _apply_ltc_income_check(self, clone, pratica, campaign, importo):
        requirement = self._select_ltc_income_requirement(campaign, importo)
        if not requirement:
            clone["ltc_reddito_note"] = "Nessun requisito reddituale specifico letto: applicati requisiti più recenti se disponibili."
            return

        minimum_income = requirement.get("minimum_monthly_income")
        threshold = requirement.get("threshold")
        operator = requirement.get("operator")

        clone["ltc_reddito_soglia"] = threshold
        clone["ltc_reddito_operatore"] = operator
        clone["ltc_reddito_minimo"] = minimum_income

        actual_income = self._to_float(
            self._get_pratica_value(
                pratica,
                "reddito_mensile",
                "redditoMensile",
                "reddito",
            )
        )

        check = {
            "type": "ltc_income_requirement",
            "period": campaign.get("period_label"),
            "loan_amount": importo,
            "operator": operator,
            "threshold": threshold,
            "minimum_monthly_income": minimum_income,
            "actual_monthly_income": actual_income,
            "source_text": requirement.get("source_text", ""),
        }

        if actual_income is None:
            check["status"] = "missing_data"
            check["message"] = f"Reddito mensile minimo richiesto per {campaign.get('period_label')}: € {minimum_income}"
            clone["warnings"].append(check["message"])
        elif actual_income < float(minimum_income):
            check["status"] = "ko"
            check["message"] = (
                f"Reddito insufficiente per {campaign.get('period_label')}: "
                f"richiesti € {minimum_income}, dichiarati € {actual_income:.2f}"
            )
            clone["warnings"].append(check["message"])
        else:
            check["status"] = "ok"
            check["message"] = (
                f"Reddito sufficiente per {campaign.get('period_label')}: "
                f"richiesti € {minimum_income}, dichiarati € {actual_income:.2f}"
            )

        clone.setdefault("rule_checks", []).append(check)

    def _select_ltc_income_requirement(self, campaign, importo):
        requirements = campaign.get("income_requirements") or []
        for req in requirements:
            operator = req.get("operator")
            threshold = self._to_float(req.get("threshold"))
            if threshold is None:
                continue
            if operator == "<=" and importo <= threshold:
                return req
            if operator == ">" and importo > threshold:
                return req
            if operator == ">=" and importo >= threshold:
                return req
            if operator == "<" and importo < threshold:
                return req
        return None

    def _get_ltc_campaigns(self, rules):
        raw_pages = []
        for rule in rules:
            header = rule.get("header", {}) or {}
            page = rule.get("page")
            source_text = rule.get("source_text", "")
            raw_text = rule.get("raw_text", "")
            if source_text:
                raw_pages.append((page, header, source_text))
            if raw_text:
                raw_pages.append((page, header, raw_text))

        # Recupero il raw_text dalle condizioni quando il builder lo mette solo a livello pagina.
        # Nei knowledge.json attuali le condizioni hanno page/header/source_text; se manca raw_text,
        # ricostruisco dalle frasi source_text della stessa pagina.
        by_page = {}
        for rule in rules:
            page = rule.get("page")
            if page is None:
                continue
            by_page.setdefault(page, {"header": rule.get("header", {}) or {}, "texts": []})
            if rule.get("source_text"):
                by_page[page]["texts"].append(str(rule.get("source_text")))

        for page, data in by_page.items():
            if data["texts"]:
                raw_pages.append((page, data["header"], "\n".join(data["texts"])))

        campaigns = []
        seen = set()

        for page, header, text in raw_pages:
            campaigns.extend(
                self._parse_ltc_campaigns_from_text(
                    text=text,
                    page=page,
                    header=header,
                    seen=seen,
                )
            )

        if not campaigns:
            ltc_limit = self._get_ltc_limit(rules)
            if ltc_limit is not None:
                campaigns.append({
                    "ltc_limit": ltc_limit,
                    "period_label": f"LTC{int(ltc_limit)}",
                    "date_label": "",
                    "page": self._get_ltc_rule_page(rules),
                    "spread_delta": self._get_ltc_spread_delta(rules) or 0.0,
                    "basis_points": int(round((self._get_ltc_spread_delta(rules) or 0.0) * 100)),
                    "income_requirements": [],
                })

        self._inherit_missing_ltc_requirements(campaigns)
        return campaigns

    def _parse_ltc_campaigns_from_text(self, text, page, header, seen):
        import re

        normalized = re.sub(r"\s+", " ", str(text)).strip()
        if "LTC" not in normalized.upper():
            return []

        pattern = re.compile(
            r"LTC\s*(\d+)\s+PER\s+PRATICHE\s+CARICATE\s+(DAL|FINO\s+AL)\s+(\d{2}/\d{2}/\d{4})",
            re.IGNORECASE,
        )

        matches = list(pattern.finditer(normalized))
        campaigns = []

        for i, match in enumerate(matches):
            prefix = normalized[max(0, match.start() - 60):match.start()].upper()
            # Evito di trasformare il titolo generale/listino in una campagna LTC separata.
            # Le campagne operative sono i blocchi "Mutuo PLUS - LTC ... PER PRATICHE...".
            if "LISTINO" in prefix:
                continue

            ltc_limit = int(match.group(1))
            direction = re.sub(r"\s+", " ", match.group(2).upper()).strip()
            date_value = match.group(3)
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
            block = normalized[start:end]

            key = (page, ltc_limit, direction, date_value)
            if key in seen:
                continue
            seen.add(key)

            bps = self._parse_bps(block)
            spread_delta = None if bps is None else float(bps) / 100

            period_label = f"LTC{ltc_limit} - pratiche caricate {direction.lower()} {date_value}"

            campaigns.append({
                "ltc_limit": ltc_limit,
                "period_label": period_label,
                "date_label": f"{direction} {date_value}",
                "direction": direction,
                "date": date_value,
                "page": page,
                "header": header,
                "spread_delta": spread_delta,
                "basis_points": bps,
                "income_requirements": self._parse_income_requirements(block),
                "source_text": block,
            })

        return campaigns

    def _inherit_missing_ltc_requirements(self, campaigns):
        # Se una campagna LTC non ha requisiti propri, eredita quelli più recenti disponibili.
        # Nel PDF CheBanca 11/05/2026 eredita i requisiti della campagna 01/05/2026.
        nearest_requirements = None
        nearest_bps = None
        nearest_delta = None

        for campaign in campaigns:
            if campaign.get("income_requirements"):
                nearest_requirements = campaign.get("income_requirements")
            elif nearest_requirements:
                campaign["income_requirements"] = nearest_requirements
                campaign["inherited_requirements"] = True

            if campaign.get("basis_points") is not None:
                nearest_bps = campaign.get("basis_points")
                nearest_delta = campaign.get("spread_delta")
            elif nearest_bps is not None:
                campaign["basis_points"] = nearest_bps
                campaign["spread_delta"] = nearest_delta
                campaign["inherited_spread_modifier"] = True

        # Secondo passaggio all'indietro: serve quando nel testo la campagna senza requisiti
        # appare prima di quella da cui deve ereditare.
        nearest_requirements = None
        nearest_bps = None
        nearest_delta = None
        for campaign in reversed(campaigns):
            if campaign.get("income_requirements"):
                nearest_requirements = campaign.get("income_requirements")
            elif nearest_requirements:
                campaign["income_requirements"] = nearest_requirements
                campaign["inherited_requirements"] = True

            if campaign.get("basis_points") is not None:
                nearest_bps = campaign.get("basis_points")
                nearest_delta = campaign.get("spread_delta")
            elif nearest_bps is not None:
                campaign["basis_points"] = nearest_bps
                campaign["spread_delta"] = nearest_delta
                campaign["inherited_spread_modifier"] = True

    def _parse_bps(self, text):
        import re
        match = re.search(r"\+\s*(\d+)\s*bps", str(text), flags=re.IGNORECASE)
        if not match:
            return None
        return int(match.group(1))

    def _parse_income_requirements(self, text):
        import re
        normalized = re.sub(r"\s+", " ", str(text)).strip()
        results = []

        pattern = re.compile(
            r"mutuo\s*(<=|>=|>|<)\s*([\d\.]+)\s*€?.{0,160}?reddito\s+da\s+lavoro\s+mensile\s+netto\s*:\s*([\d\.]+)",
            re.IGNORECASE,
        )

        for match in pattern.finditer(normalized):
            operator = match.group(1)
            threshold = self._parse_euro_number(match.group(2))
            minimum_income = self._parse_euro_number(match.group(3))
            if threshold is None or minimum_income is None:
                continue
            results.append({
                "operator": operator,
                "threshold": threshold,
                "minimum_monthly_income": minimum_income,
                "source_text": match.group(0),
            })

        return results

    def _parse_euro_number(self, value):
        try:
            return float(str(value).replace(".", "").replace(",", "."))
        except Exception:
            return None

    def _ltc_massimo_finanziabile(
        self,
        valore,
        perizia,
        base_ltv_percent,
        ltc_limit,
    ):
        massimo_da_perizia = perizia * float(base_ltv_percent) / 100
        massimo_da_valore = valore * float(ltc_limit) / 100
        return min(massimo_da_perizia, massimo_da_valore)

    def _get_ltc_limit(self, rules):
        candidates = []

        for rule in rules:
            value = None

            if rule.get("rule_type") == "convention_ltc":
                value = rule.get("ltc")

            trigger = rule.get("trigger", {}) or {}
            if value is None:
                value = trigger.get("ltc")

            if value is not None:
                try:
                    candidates.append(float(value))
                except Exception:
                    pass

        if not candidates:
            return None

        return max(candidates)


    def _get_ltc_rule_page(self, rules):
        for rule in rules:
            if rule.get("rule_type") == "convention_ltc":
                return rule.get("page")
            trigger = rule.get("trigger", {}) or {}
            if trigger.get("convention") == "LTC" and trigger.get("ltc") is not None:
                return rule.get("page")
        return None

    def _merge_pages(self, *pages):
        result = []
        for page in pages:
            if page is None or page == "":
                continue
            try:
                page = int(page)
            except Exception:
                pass
            if page not in result:
                result.append(page)
        return result

    def _get_ltc_spread_delta(self, rules):
        # Preferisco il modificatore esplicito per canale indiretto.
        generic = None

        for rule in rules:
            if rule.get("rule_type") != "spread_modifier":
                continue

            effect = rule.get("effect", {}) or {}
            delta = effect.get("spread_delta")
            if delta is None:
                continue

            trigger = rule.get("trigger", {}) or {}
            channel = str(trigger.get("channel", "")).lower()

            try:
                delta = float(delta)
            except Exception:
                continue

            if "indiretto" in channel:
                return delta

            if generic is None:
                generic = delta

        return generic


    # ------------------------------------------------------------------
    # GREEN PROMOTION
    # ------------------------------------------------------------------

    def _build_green_clones(self, prodotto, pratica, rules):
        green_rules = [
            rule for rule in rules
            if rule.get("rule_type") == "green_promotion"
        ]
        if not green_rules:
            return []

        clones = []
        for rule in green_rules:
            if not self._green_rule_matches(rule, prodotto, pratica):
                continue

            effect = rule.get("effect", {}) or {}
            spread_delta = self._to_float(effect.get("spread_delta"))
            if spread_delta is None:
                continue

            # Le promozioni potenziali non modificano il tasso subito: creano una card informativa.
            application = rule.get("application", "immediate")
            if application != "immediate":
                clone = dict(prodotto)
                clone.setdefault("warnings", [])
                clone.setdefault("applied_rules", [])
                clone.setdefault("rule_checks", [])
                clone["prodotto_speciale"] = True
                green_info = self._green_display_info(rule, pratica)
                clone["promozione"] = "GREEN"
                clone["green_tipo"] = application
                clone["green_tipo_label"] = green_info.get("tipo_label")
                clone["green_finalita"] = green_info.get("finalita")
                clone["green_classe_energetica"] = green_info.get("classe_energetica")
                clone["green_limite_importo"] = green_info.get("limite_importo")
                clone["green_limite_importo_applicato"] = green_info.get("limite_importo_applicato")
                clone["green_note_applicazione"] = green_info.get("note_applicazione")
                clone["green_requisiti"] = green_info.get("requisiti")
                clone["green_rule_page"] = rule.get("page")
                clone["pagina_regola_green"] = rule.get("page")
                clone["motivo_prodotto_speciale"] = "Promozione Green potenziale: verificare requisiti APE a fine lavori"
                clone["warnings"].append("Promozione Green potenziale: sconto applicabile solo al rispetto dei requisiti APE/fine lavori")
                clone["rule_checks"].append({
                    "type": "green_promotion",
                    "status": "manual_check",
                    "message": "Verificare requisiti Green: nuovo APE entro 30 mesi, miglioramento energetico e assenza rate insolute",
                    "source_text": rule.get("source_text", ""),
                })
                clone["applied_rules"].append(rule)
                clones.append(clone)
                continue

            base_spread = self._parse_percent(prodotto.get("spread", 0))
            if base_spread is None:
                continue

            final_spread = base_spread + float(spread_delta)
            if final_spread < 0:
                final_spread = 0.0

            tipo_tasso = self._get_tipo_tasso(prodotto)
            tasso_base = prodotto.get("tasso_base") or tipo_tasso
            prodotto_label = str(tipo_tasso)
            if "GREEN" not in prodotto_label.upper():
                prodotto_label = f"{prodotto_label} GREEN"

            clone = dict(prodotto)
            clone.setdefault("warnings", [])
            clone.setdefault("applied_rules", [])
            clone.setdefault("rule_checks", [])

            clone["tasso_base"] = tasso_base
            clone["tasso"] = self._set_tipo_tasso(clone.get("tasso"), prodotto_label)
            clone["spread_base"] = self._format_percent(base_spread)
            clone["spread_delta"] = float(spread_delta)
            clone["spread"] = self._format_percent(final_spread)
            clone["prodotto_speciale"] = True
            green_info = self._green_display_info(rule, pratica)
            clone["promozione"] = "GREEN"
            clone["green_tipo"] = application
            clone["green_tipo_label"] = green_info.get("tipo_label")
            clone["green_finalita"] = green_info.get("finalita")
            clone["green_classe_energetica"] = green_info.get("classe_energetica")
            clone["green_limite_importo"] = green_info.get("limite_importo")
            clone["green_limite_importo_applicato"] = green_info.get("limite_importo_applicato")
            clone["green_note_applicazione"] = green_info.get("note_applicazione")
            clone["green_requisiti"] = green_info.get("requisiti")
            clone["green_sconto"] = abs(float(spread_delta))
            clone["green_sconto_bps"] = abs(int(round(float(spread_delta) * 100)))
            clone["green_rule_page"] = rule.get("page")
            clone["pagina_regola_green"] = rule.get("page")
            clone["pagina_prodotto_base"] = prodotto.get("pagina")
            clone["pdf_pagine_riferimento"] = self._merge_pages(
                prodotto.get("pagina"),
                rule.get("page"),
            )
            clone["motivo_prodotto_speciale"] = "Promozione Green applicata: classe energetica A/B"
            clone["applied_rules"].append({
                "rule_type": "green_promotion",
                "application": application,
                "spread_delta": float(spread_delta),
                "page": rule.get("page"),
            })
            clone["rule_checks"].append({
                "type": "green_promotion",
                "status": "ok",
                "message": "Promozione Green applicata: classe energetica A/B",
                "source_text": rule.get("source_text", ""),
            })
            clones.append(clone)

        return clones

    def _green_rule_matches(self, rule, prodotto, pratica):
        trigger = rule.get("trigger", {}) or {}
        finalita = self._normalize_for_match(
            self._get_pratica_value(pratica, "finalita")
        )
        energy_class = self._normalize_energy_class(
            self._get_pratica_value(
                pratica,
                "classe_energetica",
                "classeEnergetica",
                "energy_class",
            )
        )

        finalita_options = trigger.get("finalita_in") or []
        if finalita_options and not self._match_any_text(finalita, finalita_options):
            return False

        # Green potenziale: NON vale per Acquisto semplice.
        # Vale solo per finalità che includono ristrutturazione.
        application = rule.get("application", "immediate")
        if application != "immediate" and not self._green_limit_250k_applies(finalita):
            return False

        allowed = trigger.get("energy_class_in") or []
        if allowed and energy_class not in [self._normalize_energy_class(x) for x in allowed]:
            return False

        not_allowed = trigger.get("energy_class_not_in") or []
        if not_allowed and energy_class in [self._normalize_energy_class(x) for x in not_allowed]:
            return False

        # Regola Green: Acquisto semplice in classe A/B senza limite 250k.
        # Tutte le finalità con ristrutturazione sono escluse dalla scontistica
        # se l'importo mutuo è >= 250.000.
        if self._green_limit_250k_applies(finalita):
            importo = self._to_float(
                self._get_pratica_value(
                    pratica,
                    "importo",
                    "importo_finanziato",
                    "importoRichiesto",
                )
            )
            if importo is not None and importo >= 250000:
                return False

        return True

    def _green_display_info(self, rule, pratica):
        finalita_raw = self._get_pratica_value(pratica, "finalita") or ""
        finalita = self._normalize_for_match(finalita_raw)
        energy_class = self._normalize_energy_class(
            self._get_pratica_value(
                pratica,
                "classe_energetica",
                "classeEnergetica",
                "energy_class",
            )
        )
        application = rule.get("application", "immediate")
        limit_applies = self._green_limit_250k_applies(finalita)

        if application == "immediate":
            tipo_label = "Green immediata"
            if self._is_green_simple_purchase(finalita):
                note = "Classe energetica A/B: sconto Green applicato anche per Acquisto semplice, senza limite 250.000 €."
            else:
                note = "Classe energetica A/B: sconto Green applicato per finalità con ristrutturazione, se importo inferiore a 250.000 €."
            requisiti = []
        else:
            tipo_label = "Green potenziale a fine lavori"
            note = "Classe energetica inferiore ad A/B: sconto potenziale solo per finalità con ristrutturazione e requisiti APE/fine lavori."
            requisiti = [
                "nuovo APE entro 30 mesi dalla stipula",
                "classe A/B oppure miglioramento di almeno 2 classi",
                "oppure EP gl,nren inferiore almeno del 30%",
                "nessuna rata insoluta al momento del nuovo APE",
            ]

        return {
            "tipo_label": tipo_label,
            "finalita": str(finalita_raw),
            "classe_energetica": energy_class,
            "limite_importo": 250000 if limit_applies else None,
            "limite_importo_applicato": limit_applies,
            "note_applicazione": note,
            "requisiti": requisiti,
        }

    def _green_limit_250k_applies(self, finalita):
        text = self._normalize_for_match(finalita)
        return "RISTRUTTURAZIONE" in text

    def _is_green_simple_purchase(self, finalita):
        text = self._normalize_for_match(finalita)
        if "ACQUISTO" not in text:
            return False
        if "RISTRUTTURAZIONE" in text:
            return False
        if "SOSTITUZIONE" in text:
            return False
        return True

    def _match_any_text(self, actual, expected_values):
        actual = self._normalize_for_match(actual)
        for value in expected_values:
            expected = self._normalize_for_match(value)
            if expected and (expected in actual or actual in expected):
                return True
        return False

    def _normalize_energy_class(self, value):
        if value is None:
            return ""
        text = str(value).upper().strip().replace(" ", "")

        # Le classi A1/A2/A3/A4 sono tutte classe A ai fini Green.
        # Manteniamo B come B; C, D, E... restano classi inferiori.
        if text.startswith("A"):
            return "A"
        if text.startswith("B"):
            return "B"

        return text

    def _normalize_for_match(self, value):
        if value is None:
            return ""
        return str(value).upper().replace("À", "A").replace("È", "E").strip()

    # ------------------------------------------------------------------
    # Regole base già presenti
    # ------------------------------------------------------------------

    def _rule_matches(self, rule, prodotto, pratica):
        trigger = rule.get("trigger", {}) or {}

        if not self._match_channel(trigger, pratica):
            return False

        if not self._match_loan_amount(trigger, pratica):
            return False

        return True

    def _match_channel(self, trigger, pratica):
        expected = trigger.get("channel")
        if not expected:
            return True

        actual = self._get_pratica_value(pratica, "channel", "canale")

        # Nel progetto Kiron assumiamo canale indiretto se non arriva ancora
        # un campo esplicito dalla pratica.
        if actual is None and str(expected).lower() == "indiretto":
            return True

        if actual is None:
            return False

        return str(expected).upper() in str(actual).upper()

    def _match_loan_amount(self, trigger, pratica):
        condition = trigger.get("loan_amount")
        if not condition:
            return True

        amount = self._get_pratica_value(
            pratica,
            "importo",
            "importo_finanziato",
            "importoRichiesto",
        )

        if amount is None:
            return False

        try:
            amount = float(amount)
            value = float(condition.get("value"))
        except Exception:
            return False

        operator = condition.get("operator")

        if operator == "<=":
            return amount <= value
        if operator == ">=":
            return amount >= value
        if operator == ">":
            return amount > value
        if operator == "<":
            return amount < value
        if operator == "==":
            return amount == value

        return False

    def _apply_rule(self, rule, prodotto, pratica):
        rule_type = rule.get("rule_type")

        # I requisiti reddituali letti nelle pagine LTC non vanno applicati ai prodotti base.
        # Vengono valutati solo sui cloni LTC, con il periodo corretto.
        if rule_type == "income_requirement":
            return prodotto

        if rule_type == "minimum_availability":
            return self._apply_minimum_availability(rule, prodotto)

        if rule_type in ["convention_ltc", "platform_selection", "product_condition"]:
            prodotto["applied_rules"].append(rule)
            return prodotto

        # I modificatori spread LTC vengono applicati solo ai cloni LTC,
        # non ai prodotti base.
        return prodotto

    def _apply_income_requirement(self, rule, prodotto, pratica):
        requirement = rule.get("requirement", {}) or {}
        minimum_income = requirement.get("minimum_monthly_income")

        if minimum_income is None:
            return prodotto

        actual_income = self._get_pratica_value(
            pratica,
            "reddito_mensile",
            "redditoMensile",
            "reddito",
        )

        warning = {
            "type": "income_requirement",
            "minimum_monthly_income": minimum_income,
            "source_text": rule.get("source_text", ""),
        }

        if actual_income is None:
            warning["status"] = "missing_data"
            warning["message"] = (
                f"Reddito mensile minimo richiesto: € {minimum_income}"
            )
            prodotto["warnings"].append(warning["message"])
            prodotto.setdefault("rule_checks", []).append(warning)
            prodotto["applied_rules"].append(rule)
            return prodotto

        try:
            if float(actual_income) < float(minimum_income):
                warning["status"] = "ko"
                warning["actual_monthly_income"] = actual_income
                warning["message"] = (
                    f"Reddito mensile insufficiente: richiesti € {minimum_income}"
                )
                prodotto["warnings"].append(warning["message"])
            else:
                warning["status"] = "ok"
                warning["actual_monthly_income"] = actual_income
        except Exception:
            warning["status"] = "invalid_data"
            warning["message"] = (
                f"Reddito mensile minimo richiesto: € {minimum_income}"
            )
            prodotto["warnings"].append(warning["message"])

        prodotto.setdefault("rule_checks", []).append(warning)
        prodotto["applied_rules"].append(rule)
        return prodotto

    def _apply_minimum_availability(self, rule, prodotto):
        message = "Verificare disponibilità minima: saldo prezzo + spese su conto corrente"
        prodotto.setdefault("warnings", []).append(message)
        prodotto.setdefault("rule_checks", []).append({
            "type": "minimum_availability",
            "status": "manual_check",
            "message": message,
            "source_text": rule.get("source_text", ""),
        })
        prodotto.setdefault("applied_rules", []).append(rule)
        return prodotto


    # ------------------------------------------------------------------
    # Surroga
    # ------------------------------------------------------------------

    def _apply_surroga_minimum(self, prodotto, pratica):
        if not self._is_surroga_context(prodotto, pratica):
            return prodotto

        importo = self._to_float(self._get_pratica_value(pratica, "importo"))
        minimo = 75000.0

        prodotto.setdefault("warnings", [])
        prodotto.setdefault("rule_checks", [])

        check = {
            "type": "surroga_minimum_amount",
            "minimum_amount": minimo,
            "actual_amount": importo,
            "source_text": "FINALITA’ SURROGA – Importo min 75.000€",
        }

        if not importo:
            check["status"] = "missing_data"
            check["message"] = "Surroga: importo minimo richiesto € 75.000"
            prodotto["warnings"].append(check["message"])
        elif importo < minimo:
            check["status"] = "ko"
            check["message"] = (
                f"Surroga non conforme: importo minimo € {minimo:,.0f}, "
                f"importo pratica € {importo:,.0f}"
            ).replace(",", ".")
            prodotto["warnings"].append(check["message"])
        else:
            check["status"] = "ok"
            check["message"] = "Surroga: importo minimo € 75.000 rispettato"

        prodotto["rule_checks"].append(check)
        return prodotto

    def _is_surroga_context(self, prodotto, pratica):
        values = []
        for key in ["finalita", "finalita_normalizzata", "finalita_norm"]:
            value = prodotto.get(key) if isinstance(prodotto, dict) else None
            if isinstance(value, list):
                values.extend(value)
            elif value is not None:
                values.append(value)

        for attr in ["finalita", "finalita_normalizzata", "finalita_norm"]:
            value = self._get_pratica_value(pratica, attr)
            if value is not None:
                values.append(value)

        text = " ".join(str(v).upper() for v in values)
        return "SURROGA" in text

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_tipo_tasso(self, rule):
        tasso = rule.get("tasso", "")
        if isinstance(tasso, dict):
            return tasso.get("tipo", "")
        return tasso

    def _set_tipo_tasso(self, original, new_value):
        if isinstance(original, dict):
            updated = dict(original)
            updated["tipo"] = new_value
            updated["descrizione"] = new_value
            return updated
        return new_value

    def _get_pratica_value(self, pratica, *names):
        for name in names:
            if isinstance(pratica, dict) and name in pratica:
                return pratica.get(name)

            if hasattr(pratica, name):
                return getattr(pratica, name)

            mortgage = getattr(pratica, "mortgage", None)
            if mortgage is not None and hasattr(mortgage, name):
                return getattr(mortgage, name)

            property_obj = getattr(pratica, "property", None)
            if property_obj is not None and hasattr(property_obj, name):
                return getattr(property_obj, name)

            customer_obj = getattr(pratica, "customer", None)
            if customer_obj is not None and hasattr(customer_obj, name):
                return getattr(customer_obj, name)

        return None

    def _parse_percent(self, value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).replace("%", "").replace(",", ".").strip()

        try:
            return float(text)
        except Exception:
            return None

    def _format_percent(self, value):
        return f"{float(value):.2f}%".replace(".", ",")

    def _to_float(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            try:
                return float(str(value).replace(".", "").replace(",", "."))
            except Exception:
                return None
