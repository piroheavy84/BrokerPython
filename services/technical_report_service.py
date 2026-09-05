from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


class TechnicalReportService:
    REPORTS_DIR = Path("quotes")

    def __init__(self):
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_report_pdf(self, payload):
        now = datetime.now()
        filename = f"report_tecnico_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        path = self.REPORTS_DIR / filename

        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        margin_x = 1.5 * cm
        y = height - 1.5 * cm

        def line(text, size=9, bold=False, gap=0.42 * cm):
            nonlocal y
            if y < 1.8 * cm:
                c.showPage()
                y = height - 1.5 * cm
            font = "Helvetica-Bold" if bold else "Helvetica"
            c.setFont(font, size)
            c.drawString(margin_x, y, self._safe(text))
            y -= gap

        def wrap_line(label, value, size=8):
            text = f"{label}: {value}"
            max_len = 112
            while len(text) > max_len:
                line(text[:max_len], size=size)
                text = text[max_len:]
            line(text, size=size)

        pratica = payload.get("pratica", {}) or {}
        prodotti = payload.get("prodotti", []) or []
        migliore = payload.get("migliore")

        line("REPORT TECNICO RISULTATI RICERCA", size=15, bold=True, gap=0.65 * cm)
        line(f"Data report: {now.strftime('%d/%m/%Y %H:%M')}", size=9)
        line("", gap=0.25 * cm)

        line("DATI PRATICA", size=11, bold=True)
        for key in [
            "finalita", "tipologia_immobile", "tipo_tasso", "durata", "importo",
            "valore_immobile", "valore_perizia", "classe_energetica", "data_rogito", "ltv"
        ]:
            if key in pratica:
                wrap_line(key, pratica.get(key, ""), size=8)
        line("", gap=0.25 * cm)

        if migliore:
            line("MIGLIORE OFFERTA", size=11, bold=True)
            self._draw_product(line, wrap_line, migliore, 0)
            line("", gap=0.25 * cm)

        self._draw_variant_summary(line, wrap_line, prodotti)
        line("", gap=0.25 * cm)

        line(f"TUTTI I RISULTATI / SCENARI ({len(prodotti)})", size=11, bold=True)
        for index, prodotto in enumerate(prodotti, start=1):
            self._draw_product(line, wrap_line, prodotto, index)
            line("-" * 105, size=7, gap=0.28 * cm)

        c.save()

        return {
            "success": True,
            "filename": filename,
            "path": str(path),
        }

    def _draw_variant_summary(self, line, wrap_line, prodotti):
        groups = self._group_products(prodotti)

        line("RIEPILOGO PRODOTTI E VARIANTI", size=11, bold=True)

        if not groups:
            line("Nessun prodotto presente.", size=8)
            return

        for index, group in enumerate(groups, start=1):
            sample = group["sample"]
            base_name = group["base_name"]
            pagina = sample.get("pagina", "")
            pdf_pages = sample.get("pdf_pagine_riferimento", []) or []
            page_info = f"pag. prodotto {pagina}"
            if pdf_pages:
                page_info += f"; riferimenti {', '.join(str(x) for x in pdf_pages)}"

            line(
                f"{index}) {sample.get('banca', '')} - {base_name} ({len(group['items'])} scenari) - {page_info}",
                size=9,
                bold=True,
                gap=0.38 * cm,
            )

            for item in group["items"]:
                variant_name = self._variant_name(item)
                parts = [
                    f"{variant_name}",
                    f"spread {self._percent(item.get('spread'))}",
                    f"tasso {self._percent(item.get('tasso_finito'))}",
                    f"rata {self._money(item.get('rata'))}",
                ]

                extras = []
                if item.get("spread_base") not in (None, ""):
                    extras.append(f"base {self._percent(item.get('spread_base'))}")
                if item.get("green_spread_delta") not in (None, ""):
                    extras.append(f"green {self._percent(item.get('green_spread_delta'))}")
                if item.get("spread_delta") not in (None, ""):
                    extras.append(f"delta {self._percent(item.get('spread_delta'))}")
                if item.get("massimo_finanziabile_ltc") not in (None, ""):
                    extras.append(f"max LTC {self._money(item.get('massimo_finanziabile_ltc'))}")

                suffix = f" ({'; '.join(extras)})" if extras else ""
                line("   - " + " | ".join(parts) + suffix, size=7, gap=0.30 * cm)

            line("", gap=0.15 * cm)

    def _group_products(self, prodotti):
        grouped = {}
        order = []

        for p in prodotti:
            base_name = self._base_product_name(p)
            key = (
                p.get("banca", ""),
                p.get("pdf", ""),
                p.get("pagina", ""),
                p.get("listino", ""),
                base_name,
                p.get("durata", ""),
                p.get("ltv_massimo", ""),
            )

            if key not in grouped:
                grouped[key] = {
                    "base_name": base_name,
                    "sample": p,
                    "items": [],
                }
                order.append(key)

            grouped[key]["items"].append(p)

        return [grouped[key] for key in order]

    def _base_product_name(self, p):
        raw = str(p.get("prodotto_base") or p.get("prodotto") or "").strip()
        upper = raw.upper()
        for suffix in [" GREEN + LTC95", " LTC95 + GREEN", " GREEN", " LTC95", " LTC90", " LTC97"]:
            if upper.endswith(suffix):
                return raw[: -len(suffix)].strip()
        return raw

    def _variant_name(self, p):
        names = []

        promozione = str(p.get("promozione") or "").strip()
        convenzione = str(p.get("convenzione") or "").strip()
        tipo_green = str(p.get("tipo_green") or "").strip()

        if promozione:
            if tipo_green:
                names.append(f"{promozione} {tipo_green}")
            else:
                names.append(promozione)

        if convenzione:
            names.append(convenzione)

        if not names:
            return "STANDARD"

        return " + ".join(names)

    def _draw_product(self, line, wrap_line, p, index):
        title_index = f"{index}) " if index else ""
        line(
            f"{title_index}{p.get('banca', '')} - {p.get('prodotto', '')} - {p.get('semaforo', '')} - Score {p.get('score', '')}",
            size=10,
            bold=True,
            gap=0.45 * cm,
        )

        warnings = p.get("warnings", []) or []
        if warnings:
            line("Motivazioni / attenzioni:", size=8, bold=True)
            for warning in warnings:
                wrap_line(" -", warning, size=7)

        fields = [
            ("Prodotto", p.get("prodotto", "")),
            ("Prodotto base", p.get("prodotto_base", "")),
            ("Variante", self._variant_name(p)),
            ("Listino", p.get("listino", "")),
            ("Promozione", p.get("promozione", "")),
            ("Convenzione", p.get("convenzione", "")),
            ("Tipo Green", p.get("tipo_green", "")),
            ("Finalità Green", p.get("finalita_green", "")),
            ("Importo finanziato", self._money(p.get("importo_finanziato"))),
            ("LTV pratica", self._percent(p.get("ltv"))),
            ("LTV massimo", self._percent(p.get("ltv_massimo"))),
            ("Valore perizia", self._money(p.get("valore_perizia"))),
            ("Massimo finanziabile LTC", self._money(p.get("massimo_finanziabile_ltc"))),
            ("Spread", self._percent(p.get("spread"))),
            ("Spread base", self._percent(p.get("spread_base"))),
            ("Maggiorazione", self._percent(p.get("spread_delta"))),
            ("Sconto Green", self._percent(p.get("green_spread_delta"))),
            ("Indice", self._percent(p.get("indice"))),
            ("Indice riferimento", p.get("indice_riferimento", "")),
            ("Tasso finito", self._percent(p.get("tasso_finito"))),
            ("Rata", self._money(p.get("rata"))),
            ("PDF", p.get("pdf", "")),
            ("Pagina prodotto", p.get("pagina", "")),
            ("Pagine riferimento", ", ".join(str(x) for x in (p.get("pdf_pagine_riferimento", []) or []))),
        ]

        for label, value in fields:
            if value not in (None, "", "EUR 0.00", "0.00%"):
                wrap_line(label, value, size=8)

        line("COSTI CLIENTE", size=9, bold=True, gap=0.35 * cm)
        cost_fields = [
            ("Istruttoria", self._money(p.get("istruttoria_euro"))),
            ("Istruttoria %", self._percent(p.get("istruttoria_percentuale"))),
            ("Istruttoria minimo", self._money(p.get("istruttoria_minimo"))),
            ("Istruttoria massimo", self._money(p.get("istruttoria_massimo"))),
            ("Pagina regola istruttoria", p.get("istruttoria_rule_page", "")),
            ("Regola istruttoria", p.get("istruttoria_source_text", "")),
            ("Perizia", self._money(p.get("perizia_euro"))),
            ("Imposta sostitutiva %", self._percent(p.get("costi_avviamento_percentuale"))),
            ("Imposta sostitutiva", self._money(p.get("costi_avviamento_euro"))),
            ("Polizza Vita", self._money(p.get("polizza_vita_euro"))),
            ("Polizza Lavoro", self._money(p.get("polizza_lavoro_euro"))),
            ("Polizza Vita + Lavoro", self._money(p.get("polizza_vita_lavoro_euro"))),
            ("Polizza Scoppio e Incendio", self._money(p.get("polizza_scoppio_incendio_euro"))),
            ("Totale polizze cliente", self._money(p.get("totale_polizze_cliente"))),
            ("Totale costi cliente", self._money(p.get("totale_costi_cliente"))),
        ]
        for label, value in cost_fields:
            if value not in (None, "", "EUR 0.00", "0.00%"):
                wrap_line(label, value, size=8)

        has_compensi = any([
            p.get("retrocessione_percentuale"),
            p.get("retrocessione_euro"),
            p.get("provvigione_percentuale"),
            p.get("provvigione_euro"),
            p.get("totale_compensi_polizze"),
            p.get("compenso_totale"),
        ])
        if has_compensi:
            line("COMPENSI BROKER", size=9, bold=True, gap=0.35 * cm)
            compensation_fields = [
                ("Retrocessione %", self._percent(p.get("retrocessione_percentuale"))),
                ("Retrocessione", self._money(p.get("retrocessione_euro"))),
                ("Provvigione %", self._percent(p.get("provvigione_percentuale"))),
                ("Provvigione", self._money(p.get("provvigione_euro"))),
                ("Compenso Polizza Vita", self._money(p.get("polizza_vita_compenso_euro"))),
                ("Compenso Polizza Lavoro", self._money(p.get("polizza_lavoro_compenso_euro"))),
                ("Compenso Polizza Vita + Lavoro", self._money(p.get("polizza_vita_lavoro_compenso_euro"))),
                ("Compenso Scoppio e Incendio", self._money(p.get("polizza_scoppio_incendio_compenso_euro"))),
                ("Totale compensi polizze", self._money(p.get("totale_compensi_polizze"))),
                ("Riferimento polizze", p.get("polizze_rule_page", "")),
                ("Compenso totale", self._money(p.get("compenso_totale"))),
            ]
            for label, value in compensation_fields:
                if value not in (None, "", "EUR 0.00", "0.00%"):
                    wrap_line(label, value, size=8)

    def _safe(self, value):
        text = str(value)
        replacements = {
            "€": "EUR",
            "–": "-",
            "—": "-",
            "“": '"',
            "”": '"',
            "’": "'",
            "à": "a'",
            "è": "e'",
            "é": "e'",
            "ì": "i'",
            "ò": "o'",
            "ù": "u'",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _money(self, value):
        if value in (None, ""):
            return ""
        try:
            return f"EUR {float(value):.2f}"
        except Exception:
            return str(value)

    def _percent(self, value):
        if value in (None, ""):
            return ""
        try:
            return f"{float(value):.2f}%"
        except Exception:
            return str(value)
