import json
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class QuotePdfService:

    QUOTES_DIR = Path("quotes")

    REGISTRY_FILE = QUOTES_DIR / "quotes_registry.json"

    CLIENTS_FILE = QUOTES_DIR / "clients_registry.json"

    def __init__(self):

        self.QUOTES_DIR.mkdir(
            exist_ok=True
        )

    def _load_json(
        self,
        path
    ):

        if not path.exists():

            return []

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def _save_json(
        self,
        path,
        data
    ):

        path.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    def list_quotes(
        self
    ):

        registry = self._load_json(
            self.REGISTRY_FILE
        )

        return sorted(
            registry,
            key=lambda x: x.get(
                "created_at_sort",
                ""
            ),
            reverse=True
        )

    def list_clients(
        self
    ):

        clients = self._load_json(
            self.CLIENTS_FILE
        )

        return sorted(
            clients,
            key=lambda x: x.get(
                "last_updated_sort",
                ""
            ),
            reverse=True
        )

    def _update_clients_registry(
        self,
        quote_item
    ):

        clients = self._load_json(
            self.CLIENTS_FILE
        )

        cliente = quote_item.get(
            "cliente",
            ""
        ).strip()

        if cliente == "":

            cliente = "Cliente senza nome"

        clients = [
            c
            for c in clients
            if c.get(
                "cliente",
                ""
            ).lower()
            != cliente.lower()
        ]

        clients.append(
            {
                "cliente": cliente,
                "ultimo_preventivo": quote_item.get(
                    "filename",
                    ""
                ),
                "ultimo_preventivo_data": quote_item.get(
                    "created_at",
                    ""
                ),
                "last_updated_sort": quote_item.get(
                    "created_at_sort",
                    ""
                ),
                "importo": quote_item.get(
                    "importo",
                    0
                ),
                "durata": quote_item.get(
                    "durata",
                    ""
                ),
                "prodotti": quote_item.get(
                    "prodotti",
                    0
                )
            }
        )

        self._save_json(
            self.CLIENTS_FILE,
            clients
        )

    def _euro(
        self,
        value
    ):

        try:

            return f"€ {float(value):,.2f}" \
                .replace(",", "X") \
                .replace(".", ",") \
                .replace("X", ".")

        except Exception:

            return "€ 0,00"

    def _percent(
        self,
        value
    ):

        try:

            return f"{float(value):.2f}%" \
                .replace(".", ",")

        except Exception:

            return "0,00%"

    def _score(
        self,
        value
    ):

        try:

            return int(
                round(
                    float(
                        value
                    )
                )
            )

        except Exception:

            return 0

    def _semaforo_label(
        self,
        prodotto
    ):

        semaforo = str(
            prodotto.get(
                "semaforo",
                ""
            )
        ).upper()

        if semaforo == "ROSSO":

            return "ROSSO"

        if semaforo == "GIALLO":

            return "GIALLO"

        if prodotto.get(
            "semaforo_verde",
            True
        ) is False:

            return "ROSSO"

        return "VERDE"

    def _ensure_space(
        self,
        c,
        y,
        height,
        needed=80
    ):

        if y < needed:

            c.showPage()

            return height - 50

        return y

    def _draw_confronto_prodotti(
        self,
        c,
        y,
        height,
        prodotti
    ):

        if len(prodotti) < 2:

            return y

        prodotti_ordinati = sorted(
            prodotti,
            key=lambda p: (
                -self._score(
                    p.get(
                        "score",
                        0
                    )
                ),
                float(
                    p.get(
                        "rata",
                        0
                    )
                )
            )
        )

        rata_migliore = float(
            prodotti_ordinati[0].get(
                "rata",
                0
            )
        )

        y = self._ensure_space(
            c,
            y,
            height,
            150
        )

        c.setFont(
            "Helvetica-Bold",
            13
        )

        c.drawString(
            40,
            y,
            "CONFRONTO PRODOTTI"
        )

        y -= 24

        c.setFont(
            "Helvetica-Bold",
            8
        )

        c.drawString(
            40,
            y,
            "Banca"
        )

        c.drawString(
            135,
            y,
            "Rata"
        )

        c.drawString(
            200,
            y,
            "Diff."
        )

        c.drawString(
            260,
            y,
            "Tasso"
        )

        c.drawString(
            315,
            y,
            "Spread"
        )

        c.drawString(
            375,
            y,
            "Costi"
        )

        c.drawString(
            445,
            y,
            "Semaforo"
        )

        c.drawString(
            515,
            y,
            "Score"
        )

        y -= 12

        c.line(
            40,
            y,
            555,
            y
        )

        y -= 16

        c.setFont(
            "Helvetica",
            8
        )

        for prodotto in prodotti_ordinati:

            y = self._ensure_space(
                c,
                y,
                height,
                70
            )

            rata = float(
                prodotto.get(
                    "rata",
                    0
                )
            )

            diff = rata - rata_migliore

            banca = str(
                prodotto.get(
                    "banca",
                    ""
                )
            )[:18]

            semaforo = self._semaforo_label(
                prodotto
            )

            score = self._score(
                prodotto.get(
                    "score",
                    0
                )
            )

            c.drawString(
                40,
                y,
                banca
            )

            c.drawString(
                135,
                y,
                self._euro(
                    rata
                )
            )

            c.drawString(
                200,
                y,
                self._euro(
                    diff
                )
            )

            c.drawString(
                260,
                y,
                self._percent(
                    prodotto.get(
                        "tasso_finito",
                        0
                    )
                )
            )

            c.drawString(
                315,
                y,
                self._percent(
                    prodotto.get(
                        "spread",
                        0
                    )
                )
            )

            c.drawString(
                375,
                y,
                self._euro(
                    prodotto.get(
                        "totale_costi_compensi",
                        0
                    )
                )
            )

            c.drawString(
                445,
                y,
                semaforo
            )

            c.drawString(
                515,
                y,
                f"{score}/100"
            )

            y -= 16

        y -= 20

        return y

    def create_quote_pdf(
        self,
        data
    ):

        now = datetime.now()

        filename = (
            f"preventivo_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        path = self.QUOTES_DIR / filename

        cliente = data.get(
            "cliente",
            {}
        )

        pratica = data.get(
            "pratica",
            {}
        )

        prodotti = data.get(
            "prodotti",
            []
        )

        c = canvas.Canvas(
            str(path),
            pagesize=A4
        )

        width, height = A4

        y = height - 50

        c.setFont(
            "Helvetica-Bold",
            18
        )

        c.drawString(
            40,
            y,
            "KIRON BROKER ENGINE - PREVENTIVO MUTUO"
        )

        y -= 35

        c.setFont(
            "Helvetica",
            10
        )

        c.drawString(
            40,
            y,
            f"Data preventivo: {now.strftime('%d/%m/%Y %H:%M')}"
        )

        y -= 30

        c.setFont(
            "Helvetica-Bold",
            13
        )

        c.drawString(
            40,
            y,
            "DATI CLIENTE"
        )

        y -= 20

        c.setFont(
            "Helvetica",
            10
        )

        c.drawString(
            40,
            y,
            f"Cliente: {cliente.get('nome', '')} {cliente.get('cognome', '')}"
        )

        y -= 16

        c.drawString(
            40,
            y,
            f"Reddito: {self._euro(cliente.get('reddito', 0))}"
        )

        y -= 30

        c.setFont(
            "Helvetica-Bold",
            13
        )

        c.drawString(
            40,
            y,
            "DATI PRATICA"
        )

        y -= 20

        c.setFont(
            "Helvetica",
            10
        )

        c.drawString(
            40,
            y,
            f"Finalità: {pratica.get('finalita', '')}"
        )

        y -= 16

        c.drawString(
            40,
            y,
            f"Importo mutuo: {self._euro(pratica.get('importo', 0))}"
        )

        y -= 16

        c.drawString(
            40,
            y,
            f"Valore immobile: {self._euro(pratica.get('valore_immobile', 0))}"
        )

        y -= 16

        c.drawString(
            40,
            y,
            f"Durata: {pratica.get('durata', '')} anni"
        )

        y -= 16

        c.drawString(
            40,
            y,
            f"LTV: {self._percent(pratica.get('ltv', 0))}"
        )

        y -= 35

        y = self._draw_confronto_prodotti(
            c,
            y,
            height,
            prodotti
        )

        c.setFont(
            "Helvetica-Bold",
            13
        )

        c.drawString(
            40,
            y,
            "PRODOTTI SELEZIONATI"
        )

        y -= 25

        for index, prodotto in enumerate(
            prodotti,
            start=1
        ):

            if y < 150:

                c.showPage()

                y = height - 50

            c.setFont(
                "Helvetica-Bold",
                11
            )

            c.drawString(
                40,
                y,
                f"{index}. {prodotto.get('banca', '')} - {prodotto.get('prodotto', '')}"
            )

            y -= 18

            semaforo = self._semaforo_label(
                prodotto
            )

            score = self._score(
                prodotto.get(
                    "score",
                    0
                )
            )

            warning_text = ""

            warnings = prodotto.get(
                "warnings",
                []
            )

            if len(warnings) > 0:

                warning_text = " | ".join(
                    str(warning)
                    for warning in warnings
                )

            c.setFont(
                "Helvetica",
                10
            )

            rows = [
                f"Semaforo: {semaforo}",
                f"Score banca: {score}/100",
                f"Listino: {prodotto.get('listino', '')}",
                f"Importo finanziato: {self._euro(prodotto.get('importo_finanziato', 0))}",
                f"Rata mensile: {self._euro(prodotto.get('rata', 0))}",
                f"Tasso finito: {self._percent(prodotto.get('tasso_finito', 0))}",
                f"Spread: {self._percent(prodotto.get('spread', 0))}",
                f"Indice: {self._percent(prodotto.get('indice', 0))} {prodotto.get('indice_riferimento', '')}",
                f"Istruttoria: {self._euro(prodotto.get('istruttoria_euro', 0))}",
                f"Perizia: {self._euro(prodotto.get('perizia_euro', 0))}",
                f"Retrocessione: {self._euro(prodotto.get('retrocessione_euro', 0))}",
                f"Provvigione: {self._euro(prodotto.get('provvigione_euro', 0))}",
                f"Totale costi/compensi: {self._euro(prodotto.get('totale_costi_compensi', 0))}",
                f"PDF banca: {prodotto.get('pdf', '')} - pagina {prodotto.get('pagina', '')}"
            ]

            for row in rows:

                y = self._ensure_space(
                    c,
                    y,
                    height,
                    90
                )

                c.drawString(
                    55,
                    y,
                    row
                )

                y -= 15

            if warning_text != "":

                y = self._ensure_space(
                    c,
                    y,
                    height,
                    90
                )

                c.setFont(
                    "Helvetica-Bold",
                    10
                )

                c.drawString(
                    55,
                    y,
                    "ATTENZIONE / MOTIVAZIONI:"
                )

                y -= 15

                c.setFont(
                    "Helvetica",
                    9
                )

                for warning in warnings:

                    y = self._ensure_space(
                        c,
                        y,
                        height,
                        70
                    )

                    c.drawString(
                        65,
                        y,
                        f"- {str(warning)[:95]}"
                    )

                    y -= 14

            motivi_esclusione = prodotto.get(
                "motivi_esclusione",
                []
            )

            if len(motivi_esclusione) > 0:

                y = self._ensure_space(
                    c,
                    y,
                    height,
                    90
                )

                c.setFont(
                    "Helvetica-Bold",
                    10
                )

                c.drawString(
                    55,
                    y,
                    "MOTIVI DI ESCLUSIONE:"
                )

                y -= 15

                c.setFont(
                    "Helvetica",
                    9
                )

                for motivo in motivi_esclusione:

                    y = self._ensure_space(
                        c,
                        y,
                        height,
                        70
                    )

                    c.drawString(
                        65,
                        y,
                        f"- {str(motivo)[:95]}"
                    )

                    y -= 14

            y -= 15

        c.save()

        quote_item = {
            "filename": filename,
            "created_at": now.strftime("%d/%m/%Y %H:%M"),
            "created_at_sort": now.strftime("%Y%m%d%H%M%S"),
            "cliente": f"{cliente.get('nome', '')} {cliente.get('cognome', '')}".strip(),
            "importo": pratica.get(
                "importo",
                0
            ),
            "durata": pratica.get(
                "durata",
                ""
            ),
            "prodotti": len(
                prodotti
            ),
            "path": str(
                path
            )
        }

        registry = self._load_json(
            self.REGISTRY_FILE
        )

        registry.append(
            quote_item
        )

        self._save_json(
            self.REGISTRY_FILE,
            registry
        )

        self._update_clients_registry(
            quote_item
        )

        return {
            "success": True,
            "filename": filename,
            "path": str(
                path
            )
        }