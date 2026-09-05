import json
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


class QuotePdfService:

    QUOTES_DIR = Path("quotes")
    REGISTRY_FILE = QUOTES_DIR / "quotes_registry.json"
    CLIENTS_FILE = QUOTES_DIR / "clients_registry.json"

    NAVY = colors.HexColor("#082971")
    NAVY_DARK = colors.HexColor("#151C2C")
    BLUE = colors.HexColor("#2A67A5")
    LIGHT_BLUE = colors.HexColor("#EAF5FC")
    VERY_LIGHT_BLUE = colors.HexColor("#F5FAFE")
    BORDER = colors.HexColor("#C7DCEB")
    TEXT = colors.HexColor("#253247")
    MUTED = colors.HexColor("#65758A")
    WHITE = colors.white

    PAGE_MARGIN = 38
    FOOTER_H = 82

    def __init__(self):
        self.QUOTES_DIR.mkdir(exist_ok=True)
        self.logo_path = Path(__file__).resolve().parent.parent / "assets" / "kiron_logo.png"

    def _load_json(self, path):
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_json(self, path, data):
        path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

    def list_quotes(self):
        registry = self._load_json(self.REGISTRY_FILE)
        return sorted(
            registry,
            key=lambda x: x.get("created_at_sort", ""),
            reverse=True,
        )

    def list_clients(self):
        clients = self._load_json(self.CLIENTS_FILE)
        return sorted(
            clients,
            key=lambda x: x.get("last_updated_sort", ""),
            reverse=True,
        )

    def _update_clients_registry(self, quote_item):
        clients = self._load_json(self.CLIENTS_FILE)
        cliente = quote_item.get("cliente", "").strip() or "Cliente senza nome"
        clients = [
            c for c in clients
            if c.get("cliente", "").lower() != cliente.lower()
        ]
        clients.append({
            "cliente": cliente,
            "ultimo_preventivo": quote_item.get("filename", ""),
            "ultimo_preventivo_numero": quote_item.get("quote_number", ""),
            "ultimo_preventivo_data": quote_item.get("created_at", ""),
            "last_updated_sort": quote_item.get("created_at_sort", ""),
            "importo": quote_item.get("importo", 0),
            "durata": quote_item.get("durata", ""),
            "prodotti": quote_item.get("prodotti", 0),
        })
        self._save_json(self.CLIENTS_FILE, clients)

    def _next_quote_number(self, now):
        year = now.year
        max_seq = 0
        for item in self._load_json(self.REGISTRY_FILE):
            try:
                item_year = int(item.get("quote_year", 0) or 0)
                seq = int(item.get("quote_seq", 0) or 0)
            except Exception:
                continue
            if item_year == year:
                max_seq = max(max_seq, seq)
        seq = max_seq + 1
        return f"{year}-{seq:03d}", seq

    def _euro(self, value):
        try:
            return (
                f"€ {float(value):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except Exception:
            return "€ 0,00"

    def _percent(self, value):
        try:
            return f"{float(value):.2f}%".replace(".", ",")
        except Exception:
            return "0,00%"

    def _safe_float(self, value, default=0.0):
        try:
            return float(value or 0)
        except Exception:
            return default

    def _wrap(self, c, text, x, y, width, font="Helvetica", size=9.5, leading=13, color=None):
        c.setFont(font, size)
        c.setFillColor(color or self.TEXT)
        words = str(text or "").split()
        line = ""
        while words:
            candidate = (line + " " + words[0]).strip()
            if c.stringWidth(candidate, font, size) <= width:
                line = candidate
                words.pop(0)
            else:
                if line:
                    c.drawString(x, y, line)
                    y -= leading
                    line = ""
                else:
                    word = words.pop(0)
                    c.drawString(x, y, word)
                    y -= leading
        if line:
            c.drawString(x, y, line)
            y -= leading
        return y

    def _draw_round_box(self, c, x, y, w, h, fill, stroke=None, radius=10):
        c.setFillColor(fill)
        c.setStrokeColor(stroke or fill)
        c.roundRect(x, y, w, h, radius, fill=1, stroke=1)

    def _draw_header(self, c, width, height, quote_number=None, page_num=None):
        top = height - 38

        if self.logo_path.exists():
            try:
                img = ImageReader(str(self.logo_path))
                c.drawImage(
                    img,
                    self.PAGE_MARGIN,
                    top - 34,
                    width=128,
                    height=32,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        x_sep = 178
        c.setStrokeColor(self.NAVY)
        c.setLineWidth(1)
        c.line(x_sep, top - 38, x_sep, top + 1)

        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(194, top - 7, "KIRON MILANO")
        c.setFont("Helvetica", 8.5)
        c.drawString(194, top - 20, "Viale Brenta 6 - 20123 Milano (MI)")

        right_x = 360
        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_x, top - 8, "MUTUI - PRESTITI - ASSICURAZIONI")
        c.setFont("Helvetica-Oblique", 8.5)
        c.setFillColor(self.BLUE)
        c.drawString(right_x, top - 23, "Le persone al centro delle tue scelte")

        if quote_number:
            c.setFont("Helvetica", 7.5)
            c.setFillColor(self.MUTED)
            label = f"Preventivo {quote_number}"
            if page_num:
                label += f" - pag. {page_num}"
            c.drawRightString(width - self.PAGE_MARGIN, top - 38, label)

        c.setStrokeColor(self.BORDER)
        c.setLineWidth(0.7)
        c.line(self.PAGE_MARGIN, top - 47, width - self.PAGE_MARGIN, top - 47)
        return top - 61

    def _draw_footer(self, c, width, quote_number):
        y0 = 18
        c.setFillColor(self.NAVY)
        c.rect(0, 0, width, self.FOOTER_H, fill=1, stroke=0)

        c.setFillColor(self.WHITE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(38, y0 + 45, "RICCARDO PIRINI")
        c.setFont("Helvetica", 7.5)
        c.drawString(38, y0 + 33, "Consulente del Credito e Assicurativo")
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(38, y0 + 20, "349 8174222")
        c.setFont("Helvetica", 7.5)
        c.drawString(38, y0 + 9, "riccardo.pirini@kiron.it")

        c.setStrokeColor(colors.HexColor("#5A86B4"))
        c.line(250, y0 + 8, 250, y0 + 54)

        c.setFont("Helvetica-Bold", 8.2)
        c.drawString(266, y0 + 45, "AGENZIA KIRON MILANO")
        c.setFont("Helvetica", 7.2)
        c.drawString(266, y0 + 33, "Viale Brenta 6 - 20123 Milano (MI)")
        c.drawString(266, y0 + 21, "02 82877580 - k0278@kiron.it")
        c.drawString(266, y0 + 9, "www.kiron.it")

        c.setFont("Helvetica", 6.2)
        c.drawRightString(
            width - 38,
            y0 + 45,
            "Kiron Partner S.p.A.",
        )
        c.drawRightString(
            width - 38,
            y0 + 33,
            "Società di Mediazione Creditizia",
        )
        c.drawRightString(
            width - 38,
            y0 + 21,
            "Iscrizione Elenco OAM n. M39",
        )
        c.drawRightString(
            width - 38,
            y0 + 9,
            f"Preventivo n. {quote_number}",
        )

    def _new_page(self, c, width, height, quote_number, page_num):
        if page_num > 1:
            c.showPage()
        y = self._draw_header(c, width, height, quote_number, page_num)
        self._draw_footer(c, width, quote_number)
        return y

    def _draw_intro(self, c, y, width):
        x = self.PAGE_MARGIN
        w = width - 2 * self.PAGE_MARGIN
        h = 88
        self._draw_round_box(c, x, y - h, w, h, self.VERY_LIGHT_BLUE, self.BORDER, 12)

        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x + 18, y - 28, "PREVENTIVO MUTUO")
        c.setFont("Helvetica", 11.5)
        c.drawString(x + 18, y - 47, "Una proposta costruita sui dati della tua pratica")

        self._wrap(
            c,
            "Ti presentiamo le soluzioni selezionate per accompagnarti nella scelta del mutuo, con una lettura chiara dei principali parametri economici e dei costi.",
            x + 18,
            y - 65,
            w - 36,
            size=8.8,
            leading=11,
            color=self.TEXT,
        )
        return y - h - 14

    def _draw_meta_and_practice(self, c, y, width, quote_number, now, cliente, pratica):
        x = self.PAGE_MARGIN
        gap = 10
        total_w = width - 2 * x
        left_w = 168
        right_w = total_w - left_w - gap
        h = 132

        self._draw_round_box(c, x, y - h, left_w, h, self.LIGHT_BLUE, self.BORDER, 10)
        self._draw_round_box(c, x + left_w + gap, y - h, right_w, h, colors.white, self.BORDER, 10)

        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 14, y - 25, f"Preventivo n. {quote_number}")
        c.setFont("Helvetica", 9)
        c.setFillColor(self.TEXT)
        c.drawString(x + 14, y - 42, f"Data: {now.strftime('%d/%m/%Y')}")

        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(self.NAVY)
        c.drawString(x + 14, y - 69, "CLIENTE")
        c.setFont("Helvetica", 9)
        c.setFillColor(self.TEXT)
        nome = f"{cliente.get('nome', '')} {cliente.get('cognome', '')}".strip() or "-"
        c.drawString(x + 14, y - 86, nome)

        rx = x + left_w + gap + 14
        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(rx, y - 24, "DATI PRATICA")

        finalita = pratica.get("finalita_label") or pratica.get("finalita", "")
        rows = [
            ("Finalità", str(finalita).replace("_", " ").title()),
            ("Valore immobile", self._euro(pratica.get("valore_immobile", 0))),
            ("Importo mutuo", self._euro(pratica.get("importo", 0))),
            ("Durata", f"{pratica.get('durata', '')} anni"),
            ("LTV", self._percent(pratica.get("ltv", 0))),
        ]
        yy = y - 45
        for label, value in rows:
            c.setFont("Helvetica", 8.5)
            c.setFillColor(self.MUTED)
            c.drawString(rx, yy, f"{label}:")
            c.setFont("Helvetica-Bold", 8.2)
            c.setFillColor(self.TEXT)
            c.drawRightString(x + total_w - 14, yy, value)
            yy -= 17

        return y - h - 14

    def _policy_lines(self, prodotto):
        lines = []
        policies = [
            ("Vita", "polizza_vita_euro"),
            ("Lavoro", "polizza_lavoro_euro"),
            ("Vita + Lavoro", "polizza_vita_lavoro_euro"),
            ("Scoppio e Incendio", "polizza_scoppio_incendio_euro"),
        ]
        for label, key in policies:
            value = self._safe_float(prodotto.get(key, 0))
            if value > 0:
                lines.append((f"Polizza {label}", self._euro(value)))
        return lines

    def _total_quote_cost(self, prodotto):
        explicit = prodotto.get("totale_costi_preventivo_cliente")
        if explicit is not None:
            return self._safe_float(explicit)

        imposta = self._safe_float(
            prodotto.get(
                "imposta_sostitutiva_euro",
                prodotto.get("costi_avviamento_euro", 0),
            )
        )
        polizze = self._safe_float(prodotto.get("totale_polizze_cliente", 0))
        if polizze <= 0:
            polizze = sum(
                self._safe_float(prodotto.get(k, 0))
                for k in [
                    "polizza_vita_euro",
                    "polizza_lavoro_euro",
                    "polizza_vita_lavoro_euro",
                    "polizza_scoppio_incendio_euro",
                ]
            )

        return (
            self._safe_float(prodotto.get("istruttoria_euro", 0))
            + imposta
            + self._safe_float(prodotto.get("perizia_euro", 0))
            + polizze
            + self._safe_float(prodotto.get("provvigione_euro", 0))
        )

    def _product_costs(self, prodotto):
        imposta_euro = self._safe_float(
            prodotto.get(
                "imposta_sostitutiva_euro",
                prodotto.get("costi_avviamento_euro", 0),
            )
        )
        compensi = self._safe_float(prodotto.get("provvigione_euro", 0))

        rows = [
            ("Istruttoria", self._euro(prodotto.get("istruttoria_euro", 0))),
            ("Imposta sostitutiva", self._euro(imposta_euro)),
            ("Perizia", self._euro(prodotto.get("perizia_euro", 0))),
        ]

        policy_lines = self._policy_lines(prodotto)
        if policy_lines:
            rows.extend(policy_lines)
        else:
            rows.append(("Polizze", "Non previste"))

        rows.append(("Compensi KIRON", self._euro(compensi)))
        return rows

    def _draw_product_card(self, c, y, width, index, prodotto):
        x = self.PAGE_MARGIN
        w = width - 2 * x
        h = 205

        self._draw_round_box(c, x, y - h, w, h, colors.white, self.BORDER, 10)

        # Header prodotto
        c.setFillColor(self.LIGHT_BLUE)
        c.roundRect(x, y - 38, w, 38, 10, fill=1, stroke=0)
        c.rect(x, y - 38, w, 9, fill=1, stroke=0)

        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(x + 14, y - 23, f"PRODOTTO n. {index}")

        c.setFont("Helvetica", 7.4)
        c.setFillColor(self.MUTED)
        c.drawRightString(
            x + w - 14,
            y - 23,
            "Soluzione selezionata sulla base dei dati della pratica",
        )

        # Colonna sinistra: tasso e rata
        hero_y = y - 57
        c.setFont("Helvetica", 7.2)
        c.setFillColor(self.MUTED)
        c.drawString(x + 16, hero_y, "Tasso finito")
        c.drawString(x + 168, hero_y, "Rata mensile")

        c.setFont("Helvetica-Bold", 16.5)
        c.setFillColor(self.NAVY)
        c.drawString(
            x + 16,
            hero_y - 21,
            self._percent(prodotto.get("tasso_finito", 0)),
        )
        c.drawString(
            x + 168,
            hero_y - 21,
            self._euro(prodotto.get("rata", 0)),
        )

        # Separatore verticale
        split_x = x + 315
        c.setStrokeColor(self.BORDER)
        c.setLineWidth(0.7)
        c.line(split_x, y - 48, split_x, y - h + 28)

        # Colonna destra: costi
        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 8.4)
        c.drawString(split_x + 16, hero_y, "COSTI E CONDIZIONI")

        yy = hero_y - 16
        costs = self._product_costs(prodotto)
        for label, value in costs:
            c.setFont("Helvetica", 7.2)
            c.setFillColor(self.TEXT)
            c.drawString(split_x + 16, yy, label)
            c.setFont("Helvetica-Bold", 7.2)
            c.drawRightString(x + w - 16, yy, value)
            yy -= 12.5

        # Totale costi sempre sotto le voci, senza sovrapposizioni
        total_box_h = 25
        total_box_y = y - h + 34
        c.setFillColor(self.NAVY)
        c.roundRect(
            split_x + 12,
            total_box_y,
            w - (split_x - x) - 24,
            total_box_h,
            6,
            fill=1,
            stroke=0,
        )
        c.setFillColor(self.WHITE)
        c.setFont("Helvetica-Bold", 7.8)
        c.drawString(split_x + 23, total_box_y + 8.5, "TOTALE COSTI")
        c.setFont("Helvetica-Bold", 9.1)
        c.drawRightString(
            x + w - 18,
            total_box_y + 8.5,
            self._euro(self._total_quote_cost(prodotto)),
        )

        # Nota prodotto, più piccola e contenuta a sinistra
        self._wrap(
            c,
            "I valori esposti sono riferiti alla simulazione selezionata e possono variare in fase di delibera.",
            x + 16,
            y - h + 22,
            275,
            size=6.4,
            leading=8,
            color=self.MUTED,
        )

        return y - h - 10

    def _draw_closing(self, c, y, width):
        x = self.PAGE_MARGIN
        w = width - 2 * x
        h = 74
        self._draw_round_box(c, x, y - h, w, h, self.VERY_LIGHT_BLUE, self.BORDER, 10)

        c.setFillColor(self.NAVY)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x + 15, y - 24, "IL TUO CONSULENTE KIRON")
        self._wrap(
            c,
            "Ti accompagnerò nella lettura delle soluzioni e nei passaggi successivi, per chiarire condizioni, costi e documentazione necessaria fino alla scelta definitiva.",
            x + 15,
            y - 42,
            w - 30,
            size=8.6,
            leading=11,
            color=self.TEXT,
        )
        return y - h - 10

    def create_quote_pdf(self, data):
        now = datetime.now()
        quote_number, quote_seq = self._next_quote_number(now)

        filename = (
            f"preventivo_{now.year}_{quote_seq:03d}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        path = self.QUOTES_DIR / filename

        cliente = data.get("cliente", {}) or {}
        pratica = data.get("pratica", {}) or {}
        prodotti = data.get("prodotti", []) or []

        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4

        page_num = 1
        y = self._new_page(c, width, height, quote_number, page_num)
        y = self._draw_intro(c, y, width)
        y = self._draw_meta_and_practice(
            c,
            y,
            width,
            quote_number,
            now,
            cliente,
            pratica,
        )

        # Due prodotti per pagina: 1-2 sulla prima, 3-4 sulla seconda,
        # 5-6 sulla terza, e così via.
        for index, prodotto in enumerate(prodotti, start=1):
            position_in_page = (index - 1) % 2

            if index > 1 and position_in_page == 0:
                page_num += 1
                y = self._new_page(c, width, height, quote_number, page_num)
                c.setFillColor(self.NAVY)
                c.setFont("Helvetica-Bold", 12)
                c.drawString(self.PAGE_MARGIN, y, "SOLUZIONI SELEZIONATE")
                y -= 20

            y = self._draw_product_card(c, y, width, index, prodotto)


        c.save()

        quote_item = {
            "filename": filename,
            "quote_number": quote_number,
            "quote_year": now.year,
            "quote_seq": quote_seq,
            "created_at": now.strftime("%d/%m/%Y %H:%M"),
            "created_at_sort": now.strftime("%Y%m%d%H%M%S"),
            "cliente": f"{cliente.get('nome', '')} {cliente.get('cognome', '')}".strip(),
            "importo": pratica.get("importo", 0),
            "durata": pratica.get("durata", ""),
            "prodotti": len(prodotti),
            "path": str(path),
        }

        registry = self._load_json(self.REGISTRY_FILE)
        registry.append(quote_item)
        self._save_json(self.REGISTRY_FILE, registry)
        self._update_clients_registry(quote_item)

        return {
            "success": True,
            "filename": filename,
            "quote_number": quote_number,
            "path": str(path),
        }
