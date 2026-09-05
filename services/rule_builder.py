import re

from services.header_parser import HeaderParser


class RuleBuilder:

    def __init__(self):

        self.header_parser = HeaderParser()
        self.rule_id = 1
        self.last_finalita = ""

    def build(self, header, blocco):

        rules = []
        header_info = self.header_parser.parse(header)

        enasarco_rules = self._build_enasarco_rules_if_present(header_info, blocco)
        if enasarco_rules:
            return enasarco_rules

        finalita = self.last_finalita
        current_tasso = ""
        pending_rows = []
        pending_direct = None
        colonne_ltv = [50, 60, 70, 80]
        last_durata_min = None

        for riga in blocco:

            clean = str(riga).strip()
            upper = clean.upper().strip()

            if clean == "":
                continue

            if self._is_finalita_row(upper):
                # Le intestazioni possono essere spezzate su più righe:
                # GRUPPO 1: ...
                # GRUPPO 2: ...
                # Se sono righe consecutive prima della tabella, le unisco.
                if (
                    finalita
                    and current_tasso == ""
                    and len(pending_rows) == 0
                    and pending_direct is None
                    and upper.startswith("GRUPPO")
                ):
                    finalita = f"{finalita} - {clean}"
                else:
                    finalita = clean

                self.last_finalita = finalita
                current_tasso = ""
                pending_rows = []
                pending_direct = None
                last_durata_min = None
                continue

            # Se la riga precedente era un CAP spezzato e questa contiene solo lo spread,
            # chiude la regola diretta del CAP.
            if pending_direct is not None:
                direct_spread = self._extract_single_percentage_without_duration(clean)
                if direct_spread is not None:
                    rules.append(
                        self._build_rule(
                            header_info=header_info,
                            finalita=finalita,
                            tasso=pending_direct["tasso"],
                            durata_min=10,
                            durata_max=30,
                            ltv_max=80,
                            spread=direct_spread,
                            condition=pending_direct.get("condition"),
                        )
                    )
                    pending_direct = None
                    current_tasso = ""
                    last_durata_min = None
                    continue

            detected_tasso = self._detect_tasso(upper)
            row_data = self._extract_table_row(clean)

            if detected_tasso is not None:

                # Le tabelle CheBanca spesso hanno la prima riga della sezione PRIMA
                # del nome tasso, e la seconda riga assieme al nome tasso.
                # Esempio: "10-20 anni ..." poi "VARIABILE* 21-25 anni ...".
                # Quindi le righe in pending appartengono al tasso appena trovato.
                if len(pending_rows) > 0:
                    rules.extend(
                        self._flush_pending_rows(
                            header_info=header_info,
                            finalita=finalita,
                            tasso=detected_tasso,
                            pending_rows=pending_rows,
                            colonne_ltv=colonne_ltv,
                        )
                    )
                    pending_rows = []

                current_tasso = detected_tasso
                last_durata_min = None

                if row_data is not None:
                    rules.extend(
                        self._build_rules_from_row(
                            header_info=header_info,
                            finalita=finalita,
                            tasso=current_tasso,
                            durata_min=row_data["durata_min"],
                            durata_max=row_data["durata_max"],
                            spread=row_data["spread"],
                            colonne_ltv=colonne_ltv,
                            row_text=row_data.get("source_text"),
                        )
                    )
                    last_durata_min = row_data["durata_min"]
                    continue

                if detected_tasso == "VARIABILE CON CAP":
                    direct_rule = self._build_direct_rate_rule(
                        header_info=header_info,
                        finalita=finalita,
                        tasso=current_tasso,
                        riga=clean,
                        condition=self._extract_cap_rule(clean),
                    )

                    if direct_rule is not None:
                        rules.append(direct_rule)
                        current_tasso = ""
                        last_durata_min = None
                    else:
                        pending_direct = {
                            "tasso": current_tasso,
                            "condition": self._extract_cap_rule(clean),
                        }
                        current_tasso = ""
                        last_durata_min = None

                continue

            if row_data is None:
                continue

            # Se la durata riparte da 10/16 dopo una sezione già letta,
            # è quasi certamente la prima riga della sezione successiva.
            # La teniamo in sospeso finché arriva il prossimo nome tasso.
            if (
                current_tasso != ""
                and last_durata_min is not None
                and row_data["durata_min"] < last_durata_min
            ):
                pending_rows = [row_data]
                current_tasso = ""
                last_durata_min = None
                continue

            if current_tasso == "":
                pending_rows.append(row_data)
                continue

            rules.extend(
                self._build_rules_from_row(
                    header_info=header_info,
                    finalita=finalita,
                    tasso=current_tasso,
                    durata_min=row_data["durata_min"],
                    durata_max=row_data["durata_max"],
                    spread=row_data["spread"],
                    colonne_ltv=colonne_ltv,
                    row_text=row_data.get("source_text"),
                )
            )
            last_durata_min = row_data["durata_min"]

        # A fine blocco NON assegniamo pending_rows al vecchio tasso: nelle tabelle
        # estratte dal PDF, una pending row può essere la prima riga del blocco successivo.
        return rules

    def _flush_pending_rows(
        self,
        header_info,
        finalita,
        tasso,
        pending_rows,
        colonne_ltv,
    ):

        rules = []

        for row_data in pending_rows:
            rules.extend(
                self._build_rules_from_row(
                    header_info=header_info,
                    finalita=finalita,
                    tasso=tasso,
                    durata_min=row_data["durata_min"],
                    durata_max=row_data["durata_max"],
                    spread=row_data["spread"],
                    colonne_ltv=colonne_ltv,
                    row_text=row_data.get("source_text"),
                )
            )

        return rules

    def _build_enasarco_rules_if_present(self, header_info, blocco):

        text = "\n".join(str(x) for x in blocco)
        upper = text.upper()

        # Enasarco va trattato come prodotto SOLO nella pagina/blocco del listino
        # vero: deve contenere i prodotti TF/TV Enasarco e la logica di prezzo
        # di aggiudicazione/perizia. Le pagine di retrocessioni citano
        # "prodotti per dismissioni enasarco" ma NON sono listini prodotto.
        is_real_enasarco_product = (
            "PRODOTTI PER DISMISSIONI ENASARCO" in upper
            and ("TF ENASARCO" in upper or "TV ENASARCO" in upper)
            and (
                "PREZZO DI AGGIUDICAZIONE" in upper
                or "PERIZIA ZERO" in upper
            )
        )

        if not is_real_enasarco_product:
            return []

        percentages = re.findall(r"\d+(?:,\d+)?%", text)
        spread_tf = "2,30%"
        spread_tv = "2,30%"

        if len(percentages) >= 2:
            # Nel PDF CheBanca pagina Enasarco la riga è:
            # Spread 2,30% 2,30%.
            spread_tf = percentages[0]
            spread_tv = percentages[1]
        elif len(percentages) == 1:
            spread_tf = percentages[0]
            spread_tv = percentages[0]

        rules = []
        finalita = "DISMISSIONI ENASARCO"

        base = {
            "header_info": header_info,
            "finalita": finalita,
            "durata_min": 1,
            "durata_max": 30,
            "ltv_max": 80,
        }

        rule_tf = self._build_rule(
            tasso="FISSO ENASARCO",
            spread=spread_tf,
            **base,
        )
        rule_tf["condition"] = {
            "type": "ENASARCO",
            "source_text": "Prodotto TF Enasarco: spread dedicato, durata fino a 30 anni, perizia zero",
            "max_price_percent": 110,
            "max_ltv_perizia": 80,
            "perizia_zero": True,
            "istruttoria_percentuale": 0.60,
            "istruttoria_minimo": 500,
            "istruttoria_massimo": 2500,
        }
        rule_tf["source_text"] = "TF Enasarco - Spread " + str(spread_tf)
        rules.append(rule_tf)

        rule_tv = self._build_rule(
            tasso="VARIABILE ENASARCO",
            spread=spread_tv,
            **base,
        )
        rule_tv["condition"] = {
            "type": "ENASARCO",
            "source_text": "Prodotto TV Enasarco: spread dedicato, durata fino a 30 anni, perizia zero",
            "max_price_percent": 110,
            "max_ltv_perizia": 80,
            "perizia_zero": True,
            "istruttoria_percentuale": 0.60,
            "istruttoria_minimo": 500,
            "istruttoria_massimo": 2500,
        }
        rule_tv["source_text"] = "TV Enasarco - Spread " + str(spread_tv)
        rules.append(rule_tv)

        return rules

    def _is_finalita_row(self, upper):

        if upper.startswith("FINALITA"):
            return True

        if upper.startswith("FINALITÀ"):
            return True

        # Anche GRUPPO 2 può non ripetere la parola FINALITÀ.
        if upper.startswith("GRUPPO"):
            return True

        if upper.startswith("SURROGA"):
            return True

        return False

    def _detect_tasso(self, upper):

        normalized = upper.replace("*", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if normalized == "FISSO" or normalized.startswith("FISSO "):
            return "FISSO"

        if "VARIABILE" in normalized and "FLOOR" in normalized:
            return "VARIABILE CON FLOOR"

        if "VARIABILE" in normalized and "CAP" in normalized:
            return "VARIABILE CON CAP"

        if "RATA PROTETTA" in normalized:
            return "RATA PROTETTA"

        if normalized == "VARIABILE" or normalized.startswith("VARIABILE "):
            return "VARIABILE"

        return None

    def _extract_table_row(self, riga):

        durata = re.search(
            r"(\d+)\s*[-–]\s*(\d+)",
            riga,
        )

        spread = re.findall(
            r"\d+,\d+%",
            riga,
        )

        if durata is None or len(spread) == 0:
            return None

        return {
            "durata_min": int(durata.group(1)),
            "durata_max": int(durata.group(2)),
            "spread": spread,
            "source_text": riga,
        }

    def _extract_single_percentage_without_duration(self, riga):

        if re.search(r"\d+\s*[-–]\s*\d+", riga):
            return None

        percentages = re.findall(r"\d+,\d+%", riga)

        if len(percentages) == 1:
            return percentages[0]

        return None

    def _build_direct_rate_rule(
        self,
        header_info,
        finalita,
        tasso,
        riga,
        condition=None,
        source_text=None,
    ):

        if re.search(r"\d+\s*[-–]\s*\d+", riga):
            return None

        percentages = re.findall(
            r"\d+,\d+%",
            riga,
        )

        # Per il CAP la prima percentuale può essere il cap, non lo spread.
        # Se c'è una sola percentuale aspettiamo la riga successiva.
        if tasso == "VARIABILE CON CAP" and len(percentages) < 2:
            return None

        if len(percentages) == 0:
            return None

        spread = percentages[-1]

        if tasso == "VARIABILE CON CAP":
            condition = condition or self._extract_cap_rule(riga)

        return self._build_rule(
            header_info=header_info,
            finalita=finalita,
            tasso=tasso,
            durata_min=10,
            durata_max=30,
            ltv_max=80,
            spread=spread,
            condition=condition,
        )

    def _extract_cap_rule(self, riga):

        percentages = re.findall(
            r"\d+,\d+%",
            riga,
        )

        condition = {
            "type": "CAP",
            "source_text": "",
        }

        if len(percentages) >= 1:
            condition["cap"] = percentages[0]

        return condition


    def _finalita_for_row(self, finalita, row_text):

        upper = str(row_text or "").upper()
        upper = upper.replace("À", "A").replace("’", "'")

        # Alcune tabelle hanno righe valide solo per una sotto-finalità.
        # Esempio pagina Liquidità / Consolidamento:
        # "26 - 30 anni ... disponibile solo per finalità liquidità".
        # In quel caso la riga non deve essere disponibile per Consolidamento.
        if "DISPONIBILE SOLO" in upper and "LIQUID" in upper:
            return "LIQUIDITA"

        return finalita

    def _build_rules_from_row(
        self,
        header_info,
        finalita,
        tasso,
        durata_min,
        durata_max,
        spread,
        colonne_ltv,
        row_text=None,
    ):

        rules = []
        finalita = self._finalita_for_row(finalita, row_text)

        if len(spread) >= 4:

            selected = spread[-4:]

            for i in range(4):

                rules.append(
                    self._build_rule(
                        header_info=header_info,
                        finalita=finalita,
                        tasso=tasso,
                        durata_min=durata_min,
                        durata_max=durata_max,
                        ltv_max=colonne_ltv[i],
                        spread=selected[i],
                        source_text=row_text,
                    )
                )

        elif len(spread) == 1:

            rules.append(
                self._build_rule(
                    header_info=header_info,
                    finalita=finalita,
                    tasso=tasso,
                    durata_min=durata_min,
                    durata_max=durata_max,
                    ltv_max=80,
                    spread=spread[0],
                    source_text=row_text,
                )
            )

        return rules

    def _build_rule(
        self,
        header_info,
        finalita,
        tasso,
        durata_min,
        durata_max,
        ltv_max,
        spread,
        condition=None,
        source_text=None,
    ):

        rule = {
            "id": self.rule_id,
            "tipo_listino": header_info.get("tipo_listino", ""),
            "canalizzazione_da": header_info.get("canalizzazione_da", ""),
            "canalizzazione_a": header_info.get("canalizzazione_a", ""),
            "stipula_entro": header_info.get("stipula_entro", ""),
            "finalita": finalita,
            "tasso": tasso,
            "durata_min": durata_min,
            "durata_max": durata_max,
            "ltv_max": ltv_max,
            "spread": spread,
            "source_text": source_text or "",
        }

        if condition is not None:
            rule["condition"] = condition

        self.rule_id += 1

        return rule
