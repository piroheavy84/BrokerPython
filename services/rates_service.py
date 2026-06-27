import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class RatesService:

    EURIBOR_URL = "https://www.euribor-rates.eu/it/tassi-euribor-aggiornati/"

    DATA_DIR = Path("data")
    RATES_FILE = DATA_DIR / "rates.json"

    def __init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)

    def _fetch_text(self, url):
        try:
            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept-Language": "it-IT,it;q=0.9",
                },
            )

            if response.status_code != 200:
                return ""

            soup = BeautifulSoup(response.text, "html.parser")

            return soup.get_text("\n", strip=True)

        except Exception:
            return ""

    def _percent_to_float(self, value):
        return float(
            value
            .replace("%", "")
            .replace(",", ".")
            .strip()
        )

    def get_euribor(self):
        text = self._fetch_text(self.EURIBOR_URL)

        rows = []

        pattern = re.compile(
            r"(Euribor\s+(?:1\s+settimana|1\s+mese|3\s+mesi|6\s+mesi|12\s+mesi))\s+(-?\d+,\d+)\s*%",
            re.IGNORECASE,
        )

        seen = set()

        for match in pattern.finditer(text):
            descrizione = match.group(1).strip()
            fixing = match.group(2).strip()

            if descrizione in seen:
                continue

            seen.add(descrizione)

            rows.append(
                {
                    "descrizione": descrizione,
                    "fixing": fixing + "%",
                    "fixing_value": self._percent_to_float(fixing),
                    "data_fixing": datetime.now().strftime("%d/%m/%Y"),
                    "fonte": "euribor-rates.eu",
                }
            )

        return rows

    def parse_irs_text(self, text):
        rows = []

        clean = text.replace("\t", " ")
        clean = re.sub(r"\s+", " ", clean)

        patterns = [
            re.compile(
                r"(IRS\s*\d+\s*A)\s+(-?\d+[,.]\d+)\s*%\s+(\d{2}/\d{2}/\d{4})",
                re.IGNORECASE,
            ),
            re.compile(
                r"(IRS\s*\d+\s*anni)\s+(-?\d+[,.]\d+)\s*%\s+(\d{2}/\d{2}/\d{4})",
                re.IGNORECASE,
            ),
            re.compile(
                r"IRS\s*(\d+)\s*A\s+(-?\d+[,.]\d+)\s*%",
                re.IGNORECASE,
            ),
            re.compile(
                r"IRS\s*(\d+)\s*anni\s+(-?\d+[,.]\d+)\s*%",
                re.IGNORECASE,
            ),
        ]

        found = {}

        for pattern in patterns:
            for match in pattern.finditer(clean):
                if len(match.groups()) >= 3 and "IRS" in match.group(1).upper():
                    descrizione_raw = match.group(1)
                    fixing_raw = match.group(2)
                    data_raw = match.group(3)

                    anni_match = re.search(r"(\d+)", descrizione_raw)

                    if not anni_match:
                        continue

                    anni = int(anni_match.group(1))

                    found[anni] = {
                        "fixing": fixing_raw,
                        "data_fixing": data_raw,
                    }

                else:
                    anni = int(match.group(1))
                    fixing_raw = match.group(2)

                    found[anni] = {
                        "fixing": fixing_raw,
                        "data_fixing": datetime.now().strftime("%d/%m/%Y"),
                    }

        for anni in sorted(found.keys()):
            fixing = found[anni]["fixing"].replace(".", ",")
            value = self._percent_to_float(fixing)

            rows.append(
                {
                    "descrizione": f"IRS {anni}A",
                    "fixing": fixing + "%",
                    "fixing_value": value,
                    "data_fixing": found[anni]["data_fixing"],
                    "fonte": "manuale Sole24Ore",
                }
            )

        return rows

    def load_saved_rates(self):
        if not self.RATES_FILE.exists():
            return {
                "eurirs": [],
                "eurirs_last_updated": None,
            }

        return json.loads(
            self.RATES_FILE.read_text(
                encoding="utf-8",
            )
        )

    def save_manual_irs(self, text):
        eurirs = self.parse_irs_text(text)

        data = self.load_saved_rates()

        data["eurirs"] = eurirs
        data["eurirs_last_updated"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        self.RATES_FILE.write_text(
            json.dumps(
                data,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return data

    def get_rates(self):
        euribor = self.get_euribor()
        saved = self.load_saved_rates()

        return {
            "success": True,
            "euribor": euribor,
            "eurirs": saved.get("eurirs", []),
            "eurirs_last_updated": saved.get("eurirs_last_updated"),
            "status": {
                "euribor_rows": len(euribor),
                "eurirs_rows": len(saved.get("eurirs", [])),
            },
        }