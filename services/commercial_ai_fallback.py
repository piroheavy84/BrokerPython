import json
import os
import re

import pdfplumber
import requests


class CommercialAiFallback:
    """Completa le sole scontistiche commerciali sfuggite al parser deterministico.

    Il parser tradizionale resta autorevole. L'AI viene chiamata soltanto quando
    una pagina promozionale contiene una percentuale/bps associata a uno sconto
    che non compare tra le regole gia' estratte. Le regole AI vengono validate
    e marcate con origin=AI_FALLBACK; non sostituiscono mai regole deterministiche.
    """

    KEYWORDS = ("SCONT", "PROMOZ", "WHITE LABEL", "GREEN", "CONTO CORRENTE", "CCA")

    def enrich(self, pdf_path, commercial_by_page):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return commercial_by_page

        result = {
            int(page): {
                "rules": list(payload.get("rules", [])),
                "warnings": list(payload.get("warnings", [])),
            }
            for page, payload in (commercial_by_page or {}).items()
        }

        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not self._looks_like_discount_page(text):
                    continue

                current = result.setdefault(page_number, {"rules": [], "warnings": []})
                missing = self._missing_discount_values(text, current["rules"])
                if not missing:
                    continue

                try:
                    ai_rules = self._ask_openai(text, page_number, api_key)
                except Exception as exc:
                    current["warnings"].append(
                        f"Fallback AI scontistiche non riuscito a pag. {page_number}: {exc}"
                    )
                    continue

                added = 0
                for rule in ai_rules:
                    validated = self._validate_rule(rule, page_number)
                    if not validated:
                        continue
                    pct = round(float(validated.get("percent") or 0.0), 4)
                    if pct not in missing:
                        continue
                    if self._is_duplicate(validated, current["rules"]):
                        continue
                    current["rules"].append(validated)
                    added += 1

                if added == 0:
                    current["warnings"].append(
                        "Fallback AI attivato ma nessuna nuova scontistica validata "
                        f"a pag. {page_number}; valori non coperti: {sorted(missing)}"
                    )

        return result

    def _looks_like_discount_page(self, text):
        upper = self._norm(text)
        return any(token in upper for token in self.KEYWORDS) and ("%" in upper or "BPS" in upper)

    def _missing_discount_values(self, text, rules):
        candidates = set()
        for raw_line in str(text or "").splitlines():
            line = self._norm(raw_line)
            if not any(token in line for token in self.KEYWORDS):
                continue
            for value in re.findall(r"(\d+[,.]\d+)\s*%", line):
                candidates.add(round(self._pct(value), 4))
            for value in re.findall(r"(\d+)\s*BPS", line):
                candidates.add(round(int(value) / 100.0, 4))

        parsed = set()
        for rule in rules or []:
            if str(rule.get("rule_type") or "").upper() != "DISCOUNT":
                continue
            value = rule.get("percent")
            if value is None and rule.get("basis_points") is not None:
                value = float(rule["basis_points"]) / 100.0
            if value is not None:
                parsed.add(round(float(value), 4))
        return candidates - parsed

    def _ask_openai(self, text, page, api_key):
        prompt = """Sei il fallback documentale del motore mutui Kiron.
Analizza SOLO il testo della pagina riportato sotto. Estrai esclusivamente sconti/promozioni mutuo che modificano economicamente il prodotto e che sono esplicitamente presenti nel testo. Non inventare condizioni e non trasformare esempi numerici in regole.

Restituisci SOLO JSON valido nel formato:
{"rules":[{"rule_type":"DISCOUNT","discount_type":"CODICE_BREVE","name":"...","percent":0.25,"basis_points":25,"scope":"...","finalita":[],"classi_energetiche":[],"requirements":[{"code":"...","description":"..."}],"cumulative":false,"cumulative_with":[],"source_text":"frase del documento","confidence":0.0}]}

Regole:
- percent e' espresso in punti percentuali: -0,25% => 0.25; 20 bps => 0.20.
- source_text deve essere una breve porzione realmente presente nella pagina.
- se non c'e' uno sconto certo restituisci {"rules":[]}.
- non estrarre tassi di esempio, spread di esempio, retrocessioni, provvigioni o costi istruttoria.

PAGINA %d:
%s""" % (page, text[:14000])

        model = os.getenv("KIRON_OPENAI_MODEL", "gpt-5.6-luna")
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "store": False,
                "input": [{
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }],
            },
            timeout=90,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:250]}")
        payload = response.json()
        obj = self._extract_json(self._response_text(payload))
        rules = obj.get("rules") if isinstance(obj, dict) else []
        return rules if isinstance(rules, list) else []

    def _validate_rule(self, rule, page):
        if not isinstance(rule, dict):
            return None
        if str(rule.get("rule_type") or "").upper() != "DISCOUNT":
            return None
        try:
            percent = float(rule.get("percent"))
        except (TypeError, ValueError):
            bps = rule.get("basis_points")
            try:
                percent = float(bps) / 100.0
            except (TypeError, ValueError):
                return None
        if percent <= 0 or percent > 10:
            return None
        source = str(rule.get("source_text") or "").strip()
        name = str(rule.get("name") or "").strip()
        if not source or not name:
            return None

        clean = dict(rule)
        clean["rule_type"] = "DISCOUNT"
        clean["percent"] = round(percent, 4)
        clean["page"] = page
        clean["origin"] = "AI_FALLBACK"
        try:
            clean["confidence"] = max(0.0, min(1.0, float(clean.get("confidence", 0.0))))
        except (TypeError, ValueError):
            clean["confidence"] = 0.0
        return clean

    def _is_duplicate(self, candidate, rules):
        candidate_pct = round(float(candidate.get("percent") or 0.0), 4)
        candidate_source = self._norm(candidate.get("source_text"))
        for rule in rules or []:
            if str(rule.get("rule_type") or "").upper() != "DISCOUNT":
                continue
            try:
                pct = round(float(rule.get("percent") or 0.0), 4)
            except (TypeError, ValueError):
                continue
            if pct != candidate_pct:
                continue
            source = self._norm(rule.get("source_text"))
            if source and candidate_source and (source in candidate_source or candidate_source in source):
                return True
            if self._norm(rule.get("name")) == self._norm(candidate.get("name")):
                return True
        return False

    def _response_text(self, payload):
        direct = payload.get("output_text") if isinstance(payload, dict) else None
        if direct:
            return str(direct)
        chunks = []
        for item in (payload.get("output") or []) if isinstance(payload, dict) else []:
            for content in item.get("content") or []:
                text = content.get("text")
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks)

    def _extract_json(self, text):
        value = str(text or "").strip()
        if value.startswith("```"):
            value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
            value = re.sub(r"\s*```$", "", value)
        try:
            return json.loads(value)
        except Exception:
            start = value.find("{")
            end = value.rfind("}")
            if start >= 0 and end > start:
                return json.loads(value[start:end + 1])
            raise

    def _pct(self, value):
        return float(str(value).replace("%", "").replace(",", ".").strip())

    def _norm(self, value):
        text = re.sub(r"\s+", " ", str(value or "")).strip().upper()
        return text.replace("À", "A").replace("È", "E").replace("Ì", "I").replace("Ò", "O").replace("Ù", "U").replace("’", "'")
