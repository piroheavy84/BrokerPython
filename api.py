import json
import base64
import os
import re
import shutil
import requests
from datetime import date, datetime

from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.bank_memory_service import BankMemoryService
from config.italian_geography import REGIONI, PROVINCE

from models.broker_database import BrokerDatabase
from repositories.product_repository import ProductRepository

from services.practice_service import PracticeService
from services.rates_service import RatesService
from services.pdf_import_service import PdfImportService
from services.quote_pdf_service import QuotePdfService
from services.technical_report_service import TechnicalReportService
from services.pdf_preview_service import PdfPreviewService
from services.bank_memory_confirm_service import BankMemoryConfirmService
from services.bank_eligibility_service import BankEligibilityService
from services.commercial_discount_calculator import (
    calculate_commercial_discounts,
    has_cca_discount_policy,
)
from services.pdf_document_reader import PdfDocumentReader
from services.pdf_gap_analyzer_service import PdfGapAnalyzerService
from services.page_analyzer import PageAnalyzer

from domain.mortgage_practice import MortgagePractice

from models.customer import Customer
from models.property import Property
from models.mortgage import Mortgage


app = FastAPI(
    title="Kiron Broker Engine API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def discover_index_files():

    json_files = []

    if os.path.exists("output"):

        for filename in os.listdir("output"):

            if filename.endswith("_index.json"):

                json_files.append(
                    os.path.join(
                        "output",
                        filename
                    )
                )

    if len(json_files) == 0:

        json_files = [
            "output/chebanca_index.json"
        ]

    return json_files


db = BrokerDatabase()

db.load_many(
    discover_index_files()
)

repo = ProductRepository(db)

service = PracticeService(repo)

rates_service = RatesService()

pdf_import_service = PdfImportService()

quote_pdf_service = QuotePdfService()

technical_report_service = TechnicalReportService()

pdf_preview_service = PdfPreviewService()

bank_memory_confirm_service = BankMemoryConfirmService()

bank_memory_service = BankMemoryService()

bank_eligibility_service = BankEligibilityService()

pdf_gap_analyzer_service = PdfGapAnalyzerService()

page_analyzer = PageAnalyzer()


class SearchRequest(BaseModel):

    finalita: str

    # Serve anche alla sussistenza: se non è valorizzata o non distingue
    # prima/seconda casa, per default si applicano i parametri PRIMA_CASA.
    tipologia_immobile: str = ""

    tasso: str

    durata: int

    importo: float

    valore: float

    valore_perizia: float | None = None

    classe_energetica: str = ""

    # Polizze cliente / MetLife pagina 14.
    # Per Vita, Lavoro e Vita+Lavoro, se rateizzata=True la provvigione broker
    # si calcola sull'importo mutuo; se False si calcola sul premio inserito.
    polizza_vita_euro: float = 0
    polizza_vita_rateizzata: bool = False
    polizza_lavoro_euro: float = 0
    polizza_lavoro_rateizzata: bool = False
    polizza_vita_lavoro_euro: float = 0
    polizza_vita_lavoro_rateizzata: bool = False
    polizza_scoppio_incendio_euro: float = 0
    polizza_scoppio_incendio_compenso_euro: float = 0

    # Reddito netto mensile totale richiedenti.
    # Serve per le regole LTC/requisiti pagina 2.
    reddito_mensile: float = 0

    indice_mercato: float = 0

    data_rogito: str = ""

    # Dati reali della pratica usati per le verifiche banca-specifiche.
    richiedenti: list[dict] = []

    debiti: list[dict] = []

class ManualIrsRequest(BaseModel):

    text: str


class SussistenzaRequest(BaseModel):

    banca: str
    soglie: dict = {}
    incremento_oltre_5: dict = {}
    fonte: str = "MANUALE"
    tipo_geografia: str = "AREA"

    # Struttura evoluta per banche come ING:
    # Regione -> Metropoli/Grande Centro/Piccolo Centro ->
    # Prima Casa/Seconda Casa -> componenti 1..6 e 7+.
    struttura: str = "SEMPLICE"
    matrice: dict = {}
    dimensioni: dict = {}


class SussistenzaDeferredRequest(BaseModel):

    banca: str



class QuoteRequest(BaseModel):

    cliente: dict

    pratica: dict

    prodotti: list


class TechnicalReportRequest(BaseModel):

    pratica: dict

    prodotti: list

    migliore: dict | None = None


class PdfPreviewRequest(BaseModel):

    banca: str

    pdf_path: str


class DebugPdfRequest(BaseModel):

    banca: str

    pdf_path: str


class ConfirmPhrasesRequest(BaseModel):

    banca: str

    phrases: list


class ConfirmFieldsRequest(BaseModel):

    banca: str

    fields: dict


class ConfirmCategoryRequest(BaseModel):

    banca: str

    category: str

    phrases: list


def reload_database():

    global db
    global repo
    global service

    db = BrokerDatabase()

    db.load_many(
        discover_index_files()
    )

    repo = ProductRepository(
        db
    )

    service = PracticeService(
        repo
    )


def percent_to_float(value):

    if value is None:

        return 0.0

    return float(
        str(value)
        .replace("%", "")
        .replace(",", ".")
        .strip()
    )


def spread_to_float(spread):

    return percent_to_float(
        spread
    )


def euro_to_float(value):

    if value is None:

        return 0.0

    clean = (
        str(value)
        .replace("€", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )

    if clean == "":

        return 0.0

    return float(clean)


def slug(value):

    return str(value).lower().replace(" ", "_")


def load_bank_knowledge(banca):

    path = os.path.join(
        "output",
        f"{slug(banca)}_knowledge.json"
    )

    if not os.path.exists(path):

        return []

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def parse_istruttoria_from_text(text):

    result = {
        "percentuale": 0.0,
        "minimo": 0.0,
        "massimo": 0.0
    }

    percent_match = re.search(
        r"(\d+(?:[,.]\d+)?)\s*%",
        text
    )

    if percent_match:

        result["percentuale"] = percent_to_float(
            percent_match.group(1)
        )

    euro_values = re.findall(
        r"€\s*([\d.]+(?:,\d+)?)",
        text
    )

    if len(euro_values) >= 1:

        result["minimo"] = euro_to_float(
            euro_values[0]
        )

    if len(euro_values) >= 2:

        result["massimo"] = euro_to_float(
            euro_values[1]
        )

    return result


def get_istruttoria_rule(banca):

    knowledge = load_bank_knowledge(
        banca
    )

    for page in knowledge:

        page_number = page.get(
            "page",
            page.get("pagina", None)
        )

        for cost in page.get(
            "costs",
            []
        ):

            cost_type = str(
                cost.get(
                    "type",
                    ""
                )
            ).upper()

            cost_name = str(
                cost.get(
                    "cost",
                    ""
                )
            ).upper()

            rule_type = str(
                cost.get(
                    "rule_type",
                    ""
                )
            ).upper()

            is_istruttoria = (
                cost_type == "ISTRUTTORIA"
                or cost_name == "ISTRUTTORIA"
                or (rule_type == "COST_RULE" and cost_name == "ISTRUTTORIA")
            )

            if not is_istruttoria:
                continue

            source_text = cost.get(
                "source_text",
                ""
            )

            parsed = parse_istruttoria_from_text(
                source_text
            )

            calculation = cost.get(
                "calculation",
                {}
            )

            if isinstance(calculation, dict):

                if calculation.get("type") == "percent_of_financed_amount":
                    parsed["percentuale"] = float(
                        calculation.get(
                            "percent",
                            parsed.get("percentuale", 0.0)
                        ) or 0.0
                    )

                if calculation.get("type") == "fixed_amount":
                    parsed["fixed_amount"] = float(
                        calculation.get(
                            "amount",
                            0.0
                        ) or 0.0
                    )

            if cost.get("minimum_amount") is not None:
                parsed["minimo"] = float(cost.get("minimum_amount") or 0.0)

            if cost.get("maximum_amount") is not None:
                parsed["massimo"] = float(cost.get("maximum_amount") or 0.0)

            parsed["source_text"] = source_text
            parsed["pagina"] = page_number

            return parsed

    return None



def is_surroga_finalita(value):
    text = str(value or "").upper()
    return "SURROGA" in text


def is_enasarco_product(value):
    text = str(value or "").upper()
    return "ENASARCO" in text or "DISMISSIONI_ENASARCO" in text or "DISMISSIONI ENASARCO" in text


def calcola_istruttoria_detail(
    banca,
    importo
):

    # Se configurata manualmente per la banca, l'istruttoria manuale ha
    # priorità sulla lettura del PDF. Questo evita di trattare tutte le banche
    # allo stesso modo e rende esplicito il parametro in Gestione Banche.
    memory = bank_memory_service.load_bank_memory(banca)
    manual_percentuale = memory.get("istruttoria_percentuale")
    if manual_percentuale is not None:
        try:
            percentuale = float(manual_percentuale or 0.0)
            minimo = float(memory.get("istruttoria_minimo") or 0.0)
            massimo = float(memory.get("istruttoria_massimo") or 0.0)
            istruttoria = float(importo or 0.0) * percentuale / 100.0

            if minimo > 0 and istruttoria < minimo:
                istruttoria = minimo
            if massimo > 0 and istruttoria > massimo:
                istruttoria = massimo

            return {
                "importo": istruttoria,
                "percentuale": percentuale,
                "minimo": minimo,
                "massimo": massimo,
                "pagina": None,
                "source_text": "Parametro manuale Memoria Banca"
            }
        except Exception:
            pass

    rule = get_istruttoria_rule(
        banca
    )

    if rule is None:

        return {
            "importo": 0.0,
            "percentuale": 0.0,
            "minimo": 0.0,
            "massimo": 0.0,
            "pagina": None,
            "source_text": ""
        }

    if rule.get("fixed_amount") is not None:
        istruttoria = float(rule.get("fixed_amount") or 0.0)
    else:
        percentuale = rule.get(
            "percentuale",
            0.0
        )

        minimo = rule.get(
            "minimo",
            0.0
        )

        massimo = rule.get(
            "massimo",
            0.0
        )

        istruttoria = importo * percentuale / 100

        if minimo > 0 and istruttoria < minimo:

            istruttoria = minimo

        if massimo > 0 and istruttoria > massimo:

            istruttoria = massimo

    return {
        "importo": istruttoria,
        "percentuale": rule.get("percentuale", 0.0),
        "minimo": rule.get("minimo", 0.0),
        "massimo": rule.get("massimo", 0.0),
        "pagina": rule.get("pagina"),
        "source_text": rule.get("source_text", "")
    }


def calcola_istruttoria(
    banca,
    importo
):

    return calcola_istruttoria_detail(
        banca,
        importo
    ).get(
        "importo",
        0.0
    )



def get_bank_cost_parameters(banca):

    memory = bank_memory_service.load_bank_memory(banca)

    def to_float(value, default=0.0):
        try:
            if value in (None, ""):
                return default
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return default

    return {
        "perizia_euro": to_float(memory.get("perizia_euro"), 0.0),
        "imposta_sostitutiva_percentuale": to_float(
            memory.get(
                "imposta_sostitutiva_percentuale",
                memory.get("costi_avviamento_percentuale")
            ),
            0.25
        ),
        # Alias legacy mantenuto per compatibilità con pratiche/versioni precedenti.
        "costi_avviamento_percentuale": to_float(
            memory.get(
                "imposta_sostitutiva_percentuale",
                memory.get("costi_avviamento_percentuale")
            ),
            0.25
        ),
    }



def normalize_finalita_for_commission(value):

    text = str(value or "").upper()
    text = text.replace("MORTGAGEPURPOSE.", "")
    text = text.replace(" ", "_")
    text = text.replace("+", "_")
    text = text.replace("__", "_")

    if "ENASARCO" in text:
        return "DISMISSIONI_ENASARCO"
    if "SURROGA" in text:
        return "SURROGA"
    if "RIFINANZI" in text:
        return "RIFINANZIAMENTO"
    if "CONSOLID" in text:
        return "CONSOLIDAMENTO"
    if "LIQUID" in text:
        return "LIQUIDITA"
    if "SOSTITUZIONE" in text and "RISTRUT" in text:
        return "SOSTITUZIONE_RISTRUTTURAZIONE"
    if "ACQUISTO" in text and "RISTRUT" in text:
        return "ACQUISTO_RISTRUTTURAZIONE"
    if "ACQUISTO" in text and "SOSTITUZIONE" in text:
        return "ACQUISTO_SOSTITUZIONE"
    if "RISTRUT" in text:
        return "RISTRUTTURAZIONE"
    if "SOSTITUZIONE" in text:
        return "SOSTITUZIONE"
    if "ACQUISTO" in text:
        return "ACQUISTO"
    if "RISPARMIO" in text:
        return "RISPARMIO"

    return text


def get_retrocessione_rule(banca, finalita, prodotto=None):

    finalita_norm = normalize_finalita_for_commission(finalita)
    prodotto_text = str(prodotto or "").upper()

    # Pagina 13 CheBanca: tabella standard retrocessioni.
    # La logica resta normalizzata: il motore non dipende dalla dicitura Flutter.
    percentuale = 0.0
    descrizione = ""

    if "ENASARCO" in prodotto_text or finalita_norm == "DISMISSIONI_ENASARCO":
        percentuale = 1.00
        descrizione = "Prodotti per dismissioni Enasarco: retrocessione 1,00%"
    elif finalita_norm == "SURROGA":
        percentuale = 0.60
        descrizione = "Surroga: retrocessione 0,60%"
    elif finalita_norm == "RISPARMIO":
        percentuale = 0.20
        descrizione = "Risparmio: retrocessione 0,20%"
    elif finalita_norm in [
        "ACQUISTO",
        "ACQUISTO_RISTRUTTURAZIONE",
        "ACQUISTO_SOSTITUZIONE",
        "ACQUISTO_USO_UFFICIO",
    ]:
        percentuale = 1.50
        descrizione = "Acquisto / Acquisto+ristrutturazione / Acquisto+sostituzione: retrocessione 1,50%"
    elif finalita_norm in [
        "CONSOLIDAMENTO",
        "SOSTITUZIONE_RISTRUTTURAZIONE",
        "LIQUIDITA",
        "RIFINANZIAMENTO",
        "RISTRUTTURAZIONE",
    ]:
        percentuale = 1.00
        descrizione = "Consolidamento / Liquidità / Rifinanziamento / Ristrutturazione: retrocessione 1,00%"

    note = []
    if finalita_norm in [
        "RISTRUTTURAZIONE",
        "ACQUISTO_RISTRUTTURAZIONE",
        "SOSTITUZIONE_RISTRUTTURAZIONE",
    ]:
        note.append(
            "In caso di erogazione a tranches, le tranches successive alla prima devono essere erogate entro 24 mesi; oltre tale termine non generano provvigioni."
        )

    return {
        "percentuale": percentuale,
        "pagina": 13 if percentuale > 0 else None,
        "source_text": descrizione,
        "note": note,
        "provvigione_massima_percentuale": 3.0,
    }


def calcola_polizze_cliente_e_broker(request):

    importo_mutuo = float(getattr(request, "importo", 0) or 0)

    vita_premio = float(getattr(request, "polizza_vita_euro", 0) or 0)
    lavoro_premio = float(getattr(request, "polizza_lavoro_euro", 0) or 0)
    vita_lavoro_premio = float(getattr(request, "polizza_vita_lavoro_euro", 0) or 0)
    scoppio_premio = float(getattr(request, "polizza_scoppio_incendio_euro", 0) or 0)
    scoppio_compenso = float(getattr(request, "polizza_scoppio_incendio_compenso_euro", 0) or 0)

    vita_rateizzata = bool(getattr(request, "polizza_vita_rateizzata", False))
    lavoro_rateizzata = bool(getattr(request, "polizza_lavoro_rateizzata", False))
    vita_lavoro_rateizzata = bool(getattr(request, "polizza_vita_lavoro_rateizzata", False))

    # Pagina 14 CheBanca / MetLife:
    # Premio Unico Anticipato: provvigione 10% del premio unico.
    # Premio Rateale: provvigione su importo mutuo:
    # Vita 0,15%, Lavoro 0,05%, Vita+Lavoro 0,15%.
    if vita_rateizzata:
        vita_compenso = importo_mutuo * 0.15 / 100
        vita_percentuale = 0.15
        vita_base = "importo_mutuo"
    else:
        vita_compenso = vita_premio * 10 / 100
        vita_percentuale = 10.0
        vita_base = "premio_unico"

    if lavoro_rateizzata:
        lavoro_compenso = importo_mutuo * 0.05 / 100
        lavoro_percentuale = 0.05
        lavoro_base = "importo_mutuo"
    else:
        lavoro_compenso = lavoro_premio * 10 / 100
        lavoro_percentuale = 10.0
        lavoro_base = "premio_unico"

    if vita_lavoro_rateizzata:
        vita_lavoro_compenso = importo_mutuo * 0.15 / 100
        vita_lavoro_percentuale = 0.15
        vita_lavoro_base = "importo_mutuo"
    else:
        vita_lavoro_compenso = vita_lavoro_premio * 10 / 100
        vita_lavoro_percentuale = 10.0
        vita_lavoro_base = "premio_unico"

    totale_premi = vita_premio + lavoro_premio + vita_lavoro_premio + scoppio_premio
    totale_compensi = vita_compenso + lavoro_compenso + vita_lavoro_compenso + scoppio_compenso

    return {
        "polizza_vita_euro": vita_premio,
        "polizza_vita_rateizzata": vita_rateizzata,
        "polizza_vita_compenso_percentuale": vita_percentuale,
        "polizza_vita_compenso_base": vita_base,
        "polizza_vita_compenso_euro": vita_compenso,
        "polizza_lavoro_euro": lavoro_premio,
        "polizza_lavoro_rateizzata": lavoro_rateizzata,
        "polizza_lavoro_compenso_percentuale": lavoro_percentuale,
        "polizza_lavoro_compenso_base": lavoro_base,
        "polizza_lavoro_compenso_euro": lavoro_compenso,
        "polizza_vita_lavoro_euro": vita_lavoro_premio,
        "polizza_vita_lavoro_rateizzata": vita_lavoro_rateizzata,
        "polizza_vita_lavoro_compenso_percentuale": vita_lavoro_percentuale,
        "polizza_vita_lavoro_compenso_base": vita_lavoro_base,
        "polizza_vita_lavoro_compenso_euro": vita_lavoro_compenso,
        "polizza_scoppio_incendio_euro": scoppio_premio,
        "polizza_scoppio_incendio_compenso_euro": scoppio_compenso,
        "totale_polizze_cliente": totale_premi,
        "totale_compensi_polizze": totale_compensi,
        "polizze_rule_page": 14 if totale_premi > 0 or totale_compensi > 0 else None,
        "polizze_source_text": "Pagina 14: MetLife premio unico 10% del premio; premio rateale su importo mutuo: Vita 0,15%, Lavoro 0,05%, Vita+Lavoro 0,15%.",
    }

def calcola_costi_cliente(banca, importo, istruttoria_euro, polizze_cliente_e_broker=None):

    params = get_bank_cost_parameters(banca)

    perizia_euro = float(params.get("perizia_euro") or 0.0)
    imposta_sostitutiva_percentuale = float(
        params.get(
            "imposta_sostitutiva_percentuale",
            params.get("costi_avviamento_percentuale")
        ) or 0.0
    )
    imposta_sostitutiva_euro = (
        float(importo or 0.0) * imposta_sostitutiva_percentuale / 100
    )

    polizze_cliente_e_broker = polizze_cliente_e_broker or {}
    totale_polizze_cliente = float(polizze_cliente_e_broker.get("totale_polizze_cliente", 0.0) or 0.0)

    totale_costi_cliente = (
        float(istruttoria_euro or 0.0)
        + perizia_euro
        + imposta_sostitutiva_euro
        + totale_polizze_cliente
    )

    return {
        "perizia_euro": perizia_euro,
        "imposta_sostitutiva_percentuale": imposta_sostitutiva_percentuale,
        "imposta_sostitutiva_euro": imposta_sostitutiva_euro,
        # Alias legacy.
        "costi_avviamento_percentuale": imposta_sostitutiva_percentuale,
        "costi_avviamento_euro": imposta_sostitutiva_euro,
        "totale_polizze_cliente": totale_polizze_cliente,
        "totale_costi_cliente": totale_costi_cliente,
    }

def calcola_rata(
    importo,
    durata_anni,
    tasso_annuo
):

    mesi = durata_anni * 12

    if mesi <= 0:

        return 0

    tasso_mensile = tasso_annuo / 100 / 12

    if tasso_mensile == 0:

        return importo / mesi

    return importo * (
        tasso_mensile
        /
        (
            1
            -
            (
                1
                /
                ((1 + tasso_mensile) ** mesi)
            )
        )
    )


def trova_irs_per_durata(
    durata,
    eurirs
):

    if not eurirs:

        return 0

    migliore = None

    distanza_minima = 999

    for row in eurirs:

        descrizione = row.get(
            "descrizione",
            ""
        )

        anni = "".join(
            c for c in descrizione
            if c.isdigit()
        )

        if not anni:

            continue

        anni = int(
            anni
        )

        distanza = abs(
            anni - durata
        )

        if distanza < distanza_minima:

            distanza_minima = distanza

            migliore = row

    if migliore is None:

        return 0

    return float(
        migliore.get(
            "fixing_value",
            0
        )
    )


def trova_euribor(
    euribor
):

    if not euribor:

        return 0

    for row in euribor:

        descrizione = str(
            row.get(
                "descrizione",
                ""
            )
        ).lower()

        if "3 mesi" in descrizione:

            return float(
                row.get(
                    "fixing_value",
                    0
                )
            )

    return float(
        euribor[0].get(
            "fixing_value",
            0
        )
    )


def is_tasso_fisso(prodotto):

    # I prodotti speciali LTC vengono mostrati come "FISSO LTC95",
    # ma per il calcolo dell'indice devono ereditare il tasso base.
    tasso_base = getattr(prodotto, "tasso_base", None)

    if tasso_base:

        return str(tasso_base).upper() == "FISSO"

    tasso = str(
        prodotto.tasso
    ).upper()

    return tasso == "FISSO" or tasso.startswith("FISSO ")


def calcola_indice_automatico(
    prodotto,
    request
):

    rates = rates_service.get_rates()

    if is_tasso_fisso(prodotto):

        return trova_irs_per_durata(
            request.durata,
            rates.get(
                "eurirs",
                []
            )
        )

    return trova_euribor(
        rates.get(
            "euribor",
            []
        )
    )


def get_indice_riferimento(prodotto):

    if is_tasso_fisso(prodotto):

        return "IRS"

    return "EURIBOR 3 MESI / 360"


def _eta_anni(data_nascita):

    if not data_nascita:
        return None

    try:
        nascita = datetime.fromisoformat(
            str(data_nascita).replace("Z", "+00:00")
        ).date()
    except Exception:
        try:
            nascita = date.fromisoformat(str(data_nascita)[:10])
        except Exception:
            return None

    oggi = date.today()

    return oggi.year - nascita.year - (
        (oggi.month, oggi.day) < (nascita.month, nascita.day)
    )


def _verifica_parametri_manual_banca(
    banca,
    request,
    rata_mutuo
):

    memory = bank_memory_service.load_bank_memory(banca)

    motivi = []
    dettagli = {}

    # ETA: limite specifico della banca.
    eta_massima = memory.get("eta_massima_finanziabile")
    try:
        eta_massima = int(eta_massima) if eta_massima is not None else None
    except Exception:
        eta_massima = None

    eta_rows = []
    for richiedente in request.richiedenti or []:
        eta = _eta_anni(richiedente.get("data_nascita"))
        if eta is None:
            continue
        eta_scadenza = eta + int(request.durata or 0)
        nome = " ".join(x for x in [str(richiedente.get("nome", "")).strip(), str(richiedente.get("cognome", "")).strip()] if x).strip() or "Richiedente"
        ok = eta_massima is not None and eta_scadenza <= eta_massima
        eta_rows.append({"richiedente": nome, "eta_attuale": eta, "eta_scadenza": eta_scadenza, "eta_massima_banca": eta_massima, "ok": ok})
        if not ok:
            motivi.append(f"{nome}: età a fine mutuo {eta_scadenza} anni superiore al limite banca di {eta_massima} anni")

    if eta_massima is None:
        motivi.append("Età massima a fine mutuo non configurata nella Memoria Banca")
    dettagli["eta"] = {"eta_massima_banca": eta_massima, "richiedenti": eta_rows, "ok": eta_massima is not None and bool(eta_rows) and all(row["ok"] for row in eta_rows)}

    # ANNI IN ITALIA: per cittadini italiani il requisito è automaticamente soddisfatto.
    anni_minimi = memory.get("anni_residenza_italia_straniero")
    try:
        anni_minimi = int(anni_minimi) if anni_minimi is not None else None
    except Exception:
        anni_minimi = None
    residenza_rows = []
    for richiedente in request.richiedenti or []:
        naz = str(richiedente.get("nazionalita", "")).strip().lower()
        italiano = naz in {"italiana", "italiano", "italy", "italia"}
        try:
            anni = int(richiedente.get("anni_italia", richiedente.get("anniItalia", 0)) or 0)
        except Exception:
            anni = 0
        nome = " ".join(x for x in [str(richiedente.get("nome", "")).strip(), str(richiedente.get("cognome", "")).strip()] if x).strip() or "Richiedente"
        ok = italiano or (anni_minimi is not None and anni >= anni_minimi)
        residenza_rows.append({"richiedente": nome, "nazionalita": richiedente.get("nazionalita"), "anni_italia": anni, "minimo_banca": anni_minimi, "ok": ok})
        if not ok:
            motivi.append(f"{nome}: {anni} anni di residenza in Italia, minimo banca {anni_minimi}")
    if anni_minimi is None:
        motivi.append("Anni minimi di residenza in Italia per stranieri non configurati")
    dettagli["anni_italia"] = {"minimo_banca": anni_minimi, "richiedenti": residenza_rows, "ok": anni_minimi is not None and bool(residenza_rows) and all(r["ok"] for r in residenza_rows)}

    # RAPPORTO RATA/REDDITO + DEBITI: percentuale sempre /100.
    metodo = str(memory.get("calcolo_debito") or "").upper().strip()
    try:
        rapporto_raw = memory.get("rapporto_rata_reddito_percentuale")
        rapporto = float(rapporto_raw) if rapporto_raw is not None else None
    except Exception:
        rapporto = None

    reddito_totale = 0.0
    persone_a_carico_totali = 0
    aree = []
    for richiedente in request.richiedenti or []:
        try: reddito_totale += float(richiedente.get("reddito", 0) or 0)
        except Exception: pass
        try: persone_a_carico_totali += int(richiedente.get("persone_a_carico", richiedente.get("figli", 0)) or 0)
        except Exception: pass
        area = str(richiedente.get("area", "")).strip().lower()
        if area in {"nord", "centro", "sud"}: aree.append(area)

    rate_debiti = 0.0
    for debito in request.debiti or []:
        try: rate_debiti += float(debito.get("rata", 0) or 0)
        except Exception: pass

    if metodo == "RATA" and rapporto is not None:
        rata_massima_base = reddito_totale * rapporto / 100.0
        capacita_rata = rata_massima_base - rate_debiti
        descrizione = "Strada 1 - debiti sottratti dalla rata massima calcolata sul rapporto rata/reddito"
    elif metodo == "REDDITO" and rapporto is not None:
        reddito_netto_debiti = reddito_totale - rate_debiti
        capacita_rata = reddito_netto_debiti * rapporto / 100.0
        descrizione = "Strada 2 - rate debiti sottratte dal reddito prima del calcolo del rapporto rata/reddito"
    else:
        capacita_rata = None
        descrizione = "Metodo di calcolo debiti/rapporto rata reddito non configurato per la banca"

    margine = None if capacita_rata is None else capacita_rata - float(rata_mutuo or 0)
    debiti_ok = capacita_rata is not None and margine >= 0
    dettagli["debiti"] = {"metodo": metodo or None, "descrizione": descrizione, "rapporto_rata_reddito_percentuale": rapporto, "reddito_totale": round(reddito_totale, 2), "rate_debiti": round(rate_debiti, 2), "rata_mutuo": round(float(rata_mutuo or 0), 2), "rata_massima_disponibile": None if capacita_rata is None else round(capacita_rata, 2), "margine": None if margine is None else round(margine, 2), "ok": debiti_ok}
    dettagli["rapporto_rata_reddito"] = {
        "percentuale_banca": rapporto,
        "metodo": metodo or None,
        "reddito_totale": round(reddito_totale, 2),
        "rate_debiti": round(rate_debiti, 2),
        "rata_mutuo": round(float(rata_mutuo or 0), 2),
        "capacita_rata": None if capacita_rata is None else round(capacita_rata, 2),
        "margine": None if margine is None else round(margine, 2),
        "formula": (
            "reddito × percentuale / 100 - rate debiti"
            if metodo == "RATA"
            else "(reddito - rate debiti) × percentuale / 100"
            if metodo == "REDDITO"
            else None
        ),
        "ok": debiti_ok
    }
    if capacita_rata is None:
        motivi.append("Metodo calcolo debiti o rapporto rata/reddito non configurato nella memoria banca")
    elif not debiti_ok:
        motivi.append(f"Capacità rata € {capacita_rata:.2f} inferiore alla rata mutuo € {float(rata_mutuo or 0):.2f} (margine € {margine:.2f})")

    # SUSSISTENZA: reddito residuo effettivo dopo debiti e nuova rata.
    suss = memory.get("sussistenza") or {}
    suss_config = bool(suss.get("configurata"))
    componenti = max(1, len(request.richiedenti or []) + persone_a_carico_totali)
    tipo_geo = str(suss.get("tipo_geografia") or "AREA").upper()
    struttura_suss = str(suss.get("struttura") or "SEMPLICE").upper()

    richiedenti_geo = request.richiedenti or []
    geografia_completa = bool(richiedenti_geo) and all(
        str(r.get("area", "")).strip()
        and str(r.get("regione", "")).strip()
        and str(r.get("provincia", "")).strip()
        for r in richiedenti_geo
    )

    primo = richiedenti_geo[0] if richiedenti_geo else {}
    if tipo_geo == "PROVINCIA":
        geo_value = str(primo.get("provincia", "")).strip() or None
    elif tipo_geo == "REGIONE":
        geo_value = str(primo.get("regione", "")).strip() or None
    else:
        geo_value = (aree[0].capitalize() if aree else None)

    soglia = None
    soglia_base_5 = None
    incremento_applicato = 0.0
    tipo_centro = None
    destinazione_casa = None
    rows = {}

    if suss_config and geo_value and struttura_suss == "CENTRO_CASA":
        # Per questa struttura è obbligatorio scegliere la tipologia di centro.
        raw_center = str(
            primo.get("tipo_centro", primo.get("tipoCentro", ""))
        ).strip().upper().replace(" ", "_")

        aliases = {
            "METROPOLI": "METROPOLI",
            "GRANDE_CENTRO": "GRANDE_CENTRO",
            "GRANDE": "GRANDE_CENTRO",
            "PICCOLO_CENTRO": "PICCOLO_CENTRO",
            "PICCOLO": "PICCOLO_CENTRO",
        }
        tipo_centro = aliases.get(raw_center)

        # Se la pratica non distingue esplicitamente prima/seconda casa,
        # si applicano per default i parametri PRIMA_CASA come richiesto.
        tipologia = str(getattr(request, "tipologia_immobile", "") or "").upper()
        destinazione_casa = (
            "SECONDA_CASA"
            if tipologia == "SECONDA_CASA"
            else "PRIMA_CASA"
        )

        matrix = suss.get("matrice") or {}
        reg = (
            matrix.get(str(geo_value).upper())
            or matrix.get(str(geo_value))
            or {}
        )
        centers = reg.get(tipo_centro, {}) if tipo_centro else {}
        rows = centers.get(destinazione_casa, {}) if isinstance(centers, dict) else {}

        comp_key = "7+" if componenti >= 7 else str(componenti)
        try:
            if rows.get(comp_key) is not None:
                soglia = float(rows.get(comp_key))
        except Exception:
            soglia = None

    elif suss_config and geo_value:
        all_rows = suss.get("soglie") or {}
        rows = all_rows.get(geo_value) or all_rows.get(str(geo_value).lower()) or {}
        base_n = min(componenti, 5)

        try:
            soglia = float(rows.get(str(base_n)))

            if rows.get("5") is not None:
                soglia_base_5 = float(rows.get("5"))

            if componenti > 5:
                incs = suss.get("incremento_oltre_5") or {}
                incremento_applicato = float(
                    incs.get(geo_value, incs.get(str(geo_value).lower(), 0)) or 0
                )
                soglia += (componenti - 5) * incremento_applicato
        except Exception:
            soglia = None
            soglia_base_5 = None
            incremento_applicato = 0.0

    reddito_residuo = reddito_totale - rate_debiti - float(rata_mutuo or 0)

    centro_completo = (
        struttura_suss != "CENTRO_CASA"
        or tipo_centro is not None
    )

    suss_ok = (
        suss_config
        and geografia_completa
        and centro_completo
        and soglia is not None
        and reddito_residuo >= soglia
    )

    dettagli["sussistenza"] = {
        "configurata": suss_config,
        "geografia_pratica_completa": geografia_completa,
        "tipo_geografia": tipo_geo,
        "struttura": struttura_suss,
        "geografia": geo_value,
        "tipo_centro": tipo_centro,
        "destinazione_casa": destinazione_casa,
        "numero_richiedenti": len(request.richiedenti or []),
        "persone_a_carico": persone_a_carico_totali,
        "componenti_nucleo": componenti,
        "soglia_base_5": None if soglia_base_5 is None else round(soglia_base_5, 2),
        "incremento_oltre_5": round(incremento_applicato, 2),
        "numero_incrementi_oltre_5": max(0, componenti - 5),
        "soglia": None if soglia is None else round(soglia, 2),
        "reddito_totale": round(reddito_totale, 2),
        "rate_debiti": round(rate_debiti, 2),
        "rata_mutuo": round(float(rata_mutuo or 0), 2),
        "reddito_residuo": round(reddito_residuo, 2),
        "formula": "reddito totale - rate debiti - rata mutuo",
        "ok": suss_ok
    }

    if not suss_config:
        motivi.append("Sussistenza non configurata per la banca")
    elif not geografia_completa:
        motivi.append("Area geografica, Regione e Provincia devono essere compilate per tutti i richiedenti")
    elif geo_value is None:
        motivi.append(f"{tipo_geo.title()} del richiedente non disponibile per la sussistenza")
    elif struttura_suss == "CENTRO_CASA" and tipo_centro is None:
        motivi.append("Tipologia centro obbligatoria: Metropoli, Grande Centro o Piccolo Centro")
    elif soglia is None:
        if struttura_suss == "CENTRO_CASA":
            motivi.append(
                f"Soglia sussistenza non disponibile per {geo_value} / "
                f"{tipo_centro or '-'} / {destinazione_casa or 'PRIMA_CASA'} / "
                f"{componenti} componenti"
            )
        else:
            motivi.append(f"Soglia di sussistenza non disponibile per {tipo_geo.lower()} / componenti della pratica")
    elif not suss_ok:
        motivi.append(f"Reddito residuo € {reddito_residuo:.2f} inferiore alla sussistenza € {soglia:.2f}")

    return {"ok": len(motivi) == 0, "motivi": motivi, "dettagli": dettagli, "memory": {"calcolo_debito": metodo or None, "rapporto_rata_reddito_percentuale": rapporto, "eta_massima_finanziabile": eta_massima, "anni_residenza_italia_straniero": anni_minimi, "sussistenza_configurata": suss_config}}




def _collect_commercial_discount_rules(banca):
    rules = []
    for page in load_bank_knowledge(banca):
        if not isinstance(page, dict):
            continue
        page_number = page.get("page", page.get("pagina"))
        commercial_rows = (
            page.get("commercial_rules")
            or page.get("regole_commerciali")
            or []
        )
        for row in commercial_rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("rule_type") or "").upper() != "DISCOUNT":
                continue
            item = dict(row)
            item.setdefault("page", page_number)
            rules.append(item)
    return rules


def _commercial_summary(detail):
    rows = []
    for item in detail.get("sconti_applicati", []) or []:
        try:
            pct = float(item.get("percentuale") or 0.0)
        except Exception:
            pct = 0.0
        if pct <= 0:
            continue
        rows.append(f"{item.get('label') or 'Sconto'} -{pct:.2f}%")
    if not rows:
        return ""
    return "Sconti applicati: " + "; ".join(rows)

def prodotto_to_json(
    p,
    request,
    practice
):

    spread_originale = spread_to_float(
        p.spread
    )

    commercial_rules = _collect_commercial_discount_rules(p.banca)
    commercial_policy = has_cca_discount_policy(commercial_rules)

    # Il BrokerEngine può avere già applicato il solo Green commerciale.
    # Per una policy CCA cumulativa ripartiamo dallo spread precedente al Green,
    # così ogni sconto viene applicato una sola volta.
    commercial_base_spread = spread_originale
    if commercial_policy and getattr(p, "green_sconto", None):
        old_base = getattr(p, "spread_base", None)
        if old_base not in (None, ""):
            commercial_base_spread = spread_to_float(old_base)

    tasso_esplicito = getattr(
        p,
        "tasso_esplicito",
        False
    )

    tasso_finito_pdf = getattr(
        p,
        "tasso_finito_pdf",
        None
    )

    indice_riferimento = getattr(
        p,
        "indice_riferimento",
        None
    )

    if tasso_esplicito:
        indice = 0
        base_tasso_esplicito = percent_to_float(tasso_finito_pdf)
        spread = spread_originale
        tasso_finito = base_tasso_esplicito
    else:
        indice = calcola_indice_automatico(
            p,
            request
        )

        if indice == 0 and request.indice_mercato > 0:
            indice = request.indice_mercato

        spread = commercial_base_spread if commercial_policy else spread_originale
        tasso_finito = indice + spread
        indice_riferimento = get_indice_riferimento(p)

    commercial_discount_detail = {
        "spread_base": spread,
        "sconti_applicati": [],
        "sconto_totale_percentuale": 0.0,
        "spread_finale": spread,
        "reddito_residuo": None,
        "soglia_reddito_residuo": 1500.0,
    }

    if commercial_policy:
        # Prima passata: applica gli sconti non dipendenti dal residuo.
        stage_one = calculate_commercial_discounts(
            commercial_base_spread,
            commercial_rules,
            classe_energetica=request.classe_energetica,
            reddito_residuo=None,
            finalita=request.finalita,
        )

        if tasso_esplicito:
            tasso_finito = max(
                0.0,
                base_tasso_esplicito - stage_one.get("sconto_totale_percentuale", 0.0)
            )
            spread = max(
                0.0,
                spread_originale - stage_one.get("sconto_totale_percentuale", 0.0)
            )
        else:
            spread = stage_one.get("spread_finale", commercial_base_spread)
            tasso_finito = indice + spread

        rata_stage_one = calcola_rata(
            request.importo,
            request.durata,
            tasso_finito
        )
        verifica_stage_one = _verifica_parametri_manual_banca(
            p.banca,
            request,
            rata_stage_one
        )
        reddito_residuo = (
            verifica_stage_one
            .get("dettagli", {})
            .get("sussistenza", {})
            .get("reddito_residuo")
        )

        # Seconda passata: se dopo gli sconti base il residuo supera 1.500 euro,
        # entra anche la White Label/MRI -0,25.
        commercial_discount_detail = calculate_commercial_discounts(
            commercial_base_spread,
            commercial_rules,
            classe_energetica=request.classe_energetica,
            reddito_residuo=reddito_residuo,
            finalita=request.finalita,
        )

        if tasso_esplicito:
            total_discount = commercial_discount_detail.get(
                "sconto_totale_percentuale",
                0.0
            )
            tasso_finito = max(0.0, base_tasso_esplicito - total_discount)
            spread = max(0.0, spread_originale - total_discount)
        else:
            spread = commercial_discount_detail.get(
                "spread_finale",
                commercial_base_spread
            )
            tasso_finito = indice + spread

    rata = calcola_rata(
        request.importo,
        request.durata,
        tasso_finito
    )

    commercial_summary = _commercial_summary(commercial_discount_detail)

    if is_surroga_finalita(getattr(request, "finalita", "")) or is_surroga_finalita(getattr(p, "finalita", "")):
        istruttoria_detail = {
            "importo": 0.0,
            "percentuale": 0.0,
            "minimo": 0.0,
            "massimo": 0.0,
            "pagina": None,
            "source_text": "Surroga: istruttoria non prevista dal listino"
        }
    elif is_enasarco_product(getattr(request, "finalita", "")) or is_enasarco_product(getattr(p, "tasso", "")) or is_enasarco_product(getattr(p, "finalita", "")):
        enasarco_percentuale = 0.60
        enasarco_minimo = 500.0
        enasarco_massimo = 2500.0
        enasarco_importo = request.importo * enasarco_percentuale / 100
        if enasarco_importo < enasarco_minimo:
            enasarco_importo = enasarco_minimo
        if enasarco_importo > enasarco_massimo:
            enasarco_importo = enasarco_massimo
        istruttoria_detail = {
            "importo": enasarco_importo,
            "percentuale": enasarco_percentuale,
            "minimo": enasarco_minimo,
            "massimo": enasarco_massimo,
            "pagina": 9,
            "source_text": "Enasarco: istruttoria 0,60%, minimo € 500, massimo € 2.500"
        }
    else:
        istruttoria_detail = calcola_istruttoria_detail(
            p.banca,
            request.importo
        )

    istruttoria_euro = istruttoria_detail.get(
        "importo",
        0.0
    )

    polizze_detail = calcola_polizze_cliente_e_broker(request)

    costi_cliente = calcola_costi_cliente(
        p.banca,
        request.importo,
        istruttoria_euro,
        polizze_detail
    )

    retrocessione_detail = get_retrocessione_rule(
        p.banca,
        request.finalita,
        getattr(p, "tasso", "")
    )

    retrocessione_percentuale = retrocessione_detail.get(
        "percentuale",
        0.0
    )

    retrocessione_euro = request.importo * retrocessione_percentuale / 100
    totale_compensi_polizze = polizze_detail.get("totale_compensi_polizze", 0.0)

    # Il controllo LTV corretto viene già fatto a livello prodotto/listino
    # dal BrokerEngine. Non usiamo qui l'LTV generico della memoria banca,
    # perché può contenere valori letti da altre pagine/contesti e generare
    # falsi rossi, soprattutto sui prodotti LTC.
    eligibility = bank_eligibility_service.evaluate(
        p.banca,
        {
            "eta_cliente": None,
            "durata": request.durata,
            "ltv": 0,
            "finalita": request.finalita,
            "classe_energetica": request.classe_energetica,
            "autonomo": False,
            "dipendente": True,
            "pensionato": False,
            "redditi_esteri": False,
            "garante": False,
            "coobbligato": False
        }
    )
    warnings = list(
        eligibility.get(
            "warnings",
            []
        )
    )

    for warning in getattr(p, "warnings", []) or []:
        if warning not in warnings:
            warnings.append(warning)

    rule_checks = getattr(p, "rule_checks", []) or []

    motivi_esclusione = []

    semaforo = eligibility.get(
        "semaforo",
        "VERDE"
    )

    score = eligibility.get(
        "score",
        100
    )

    ltv_massimo_prodotto = percent_to_float(
        p.ltv
    )

    if (
        ltv_massimo_prodotto > 0
        and practice.ltv > ltv_massimo_prodotto
    ):

        messaggio = (
            f"LTV pratica {practice.ltv:.2f}% superiore "
            f"al massimo prodotto "
            f"{ltv_massimo_prodotto:.2f}%"
        )

        if messaggio not in warnings:

            warnings.append(
                messaggio
            )

        motivi_esclusione.append(
            messaggio
        )

        semaforo = "ROSSO"

        score -= 50

    for check in rule_checks:
        if isinstance(check, dict) and check.get("status") in ["ko", "missing_data", "invalid_data"]:
            semaforo = "ROSSO"
            message = check.get("message")
            if message and message not in motivi_esclusione:
                motivi_esclusione.append(message)
            score -= 30

    if score < 0:

        score = 0

    # Verifica definitiva: rapporto rata/reddito e sussistenza devono usare
    # la rata FINALE, dopo tutte le scontistiche commerciali.
    verifica_manual_banca = _verifica_parametri_manual_banca(
        p.banca,
        request,
        rata
    )

    final_residual = (
        verifica_manual_banca
        .get("dettagli", {})
        .get("sussistenza", {})
        .get("reddito_residuo")
    )
    if commercial_policy and final_residual is not None:
        commercial_discount_detail["reddito_residuo"] = final_residual

    for motivo in verifica_manual_banca.get("motivi", []):
        if motivo not in warnings:
            warnings.append(motivo)
        if motivo not in motivi_esclusione:
            motivi_esclusione.append(motivo)

    if not verifica_manual_banca.get("ok", True):
        semaforo = "ROSSO"
        score = max(0, score - 40)

    semaforo_verde = semaforo == "VERDE"

    return {
        "banca": p.banca,
        "prodotto": p.tasso,
        "listino": (
            f"LISTINO {p.tipo_listino} - Offerta {p.banca} "
            f"canalizzazioni dal {getattr(p, 'canalizzazione_da', '')} "
            f"al {getattr(p, 'canalizzazione_a', '')} "
            f"con stipule entro il {getattr(p, 'stipula_entro', '')}"
        ),
        "spread": spread,
        "spread_label": f"{spread:.2f}%",
        "sconti_applicati": commercial_discount_detail.get("sconti_applicati", []),
        "sconto_totale_percentuale": commercial_discount_detail.get("sconto_totale_percentuale", 0.0),
        "spread_base_commerciale": commercial_discount_detail.get("spread_base") if commercial_policy else None,
        "spread_finale": spread,
        "reddito_residuo_sconti": commercial_discount_detail.get("reddito_residuo"),
        "soglia_reddito_residuo_sconti": commercial_discount_detail.get("soglia_reddito_residuo", 1500.0),
        "indice": indice,
        "indice_riferimento": indice_riferimento,
        "tasso_esplicito": tasso_esplicito,
        "tasso_finito": tasso_finito,
        "tasso_finito_pdf": tasso_finito_pdf,
        "rata": rata,
        "importo_finanziato": request.importo,
        "ltv": practice.ltv,
        "ltv_massimo": p.ltv,
        "durata": p.durata,
        "pagina": p.pagina,
        "pdf": p.pdf,
        "retrocessione_percentuale": retrocessione_percentuale,
        "retrocessione_euro": retrocessione_euro,
        "retrocessione_rule_page": retrocessione_detail.get("pagina"),
        "retrocessione_source_text": retrocessione_detail.get("source_text", ""),
        "retrocessione_note": retrocessione_detail.get("note", []),
        "provvigione_massima_percentuale": retrocessione_detail.get("provvigione_massima_percentuale", 3.0),
        "provvigione_percentuale": 0.0,
        "provvigione_euro": 0.0,
        "totale_compensi_polizze": totale_compensi_polizze,
        "compenso_totale": retrocessione_euro + totale_compensi_polizze,
        "istruttoria_euro": istruttoria_euro,
        "istruttoria_percentuale": istruttoria_detail.get("percentuale", 0.0),
        "istruttoria_minimo": istruttoria_detail.get("minimo", 0.0),
        "istruttoria_massimo": istruttoria_detail.get("massimo", 0.0),
        "istruttoria_rule_page": istruttoria_detail.get("pagina"),
        "istruttoria_source_text": istruttoria_detail.get("source_text", ""),
        "perizia_euro": costi_cliente.get("perizia_euro", 0.0),
        "imposta_sostitutiva_percentuale": costi_cliente.get(
            "imposta_sostitutiva_percentuale",
            costi_cliente.get("costi_avviamento_percentuale", 0.25)
        ),
        "imposta_sostitutiva_euro": costi_cliente.get(
            "imposta_sostitutiva_euro",
            costi_cliente.get("costi_avviamento_euro", 0.0)
        ),
        # Alias legacy.
        "costi_avviamento_percentuale": costi_cliente.get("costi_avviamento_percentuale", 0.25),
        "costi_avviamento_euro": costi_cliente.get("costi_avviamento_euro", 0.0),
        "totale_costi_cliente": costi_cliente.get("totale_costi_cliente", 0.0),
        "polizza_vita_euro": polizze_detail.get("polizza_vita_euro", 0.0),
        "polizza_vita_rateizzata": polizze_detail.get("polizza_vita_rateizzata", False),
        "polizza_vita_compenso_percentuale": polizze_detail.get("polizza_vita_compenso_percentuale", 0.0),
        "polizza_vita_compenso_base": polizze_detail.get("polizza_vita_compenso_base", ""),
        "polizza_vita_compenso_euro": polizze_detail.get("polizza_vita_compenso_euro", 0.0),
        "polizza_lavoro_euro": polizze_detail.get("polizza_lavoro_euro", 0.0),
        "polizza_lavoro_rateizzata": polizze_detail.get("polizza_lavoro_rateizzata", False),
        "polizza_lavoro_compenso_percentuale": polizze_detail.get("polizza_lavoro_compenso_percentuale", 0.0),
        "polizza_lavoro_compenso_base": polizze_detail.get("polizza_lavoro_compenso_base", ""),
        "polizza_lavoro_compenso_euro": polizze_detail.get("polizza_lavoro_compenso_euro", 0.0),
        "polizza_vita_lavoro_euro": polizze_detail.get("polizza_vita_lavoro_euro", 0.0),
        "polizza_vita_lavoro_rateizzata": polizze_detail.get("polizza_vita_lavoro_rateizzata", False),
        "polizza_vita_lavoro_compenso_percentuale": polizze_detail.get("polizza_vita_lavoro_compenso_percentuale", 0.0),
        "polizza_vita_lavoro_compenso_base": polizze_detail.get("polizza_vita_lavoro_compenso_base", ""),
        "polizza_vita_lavoro_compenso_euro": polizze_detail.get("polizza_vita_lavoro_compenso_euro", 0.0),
        "polizza_scoppio_incendio_euro": polizze_detail.get("polizza_scoppio_incendio_euro", 0.0),
        "polizza_scoppio_incendio_compenso_euro": polizze_detail.get("polizza_scoppio_incendio_compenso_euro", 0.0),
        "totale_polizze_cliente": polizze_detail.get("totale_polizze_cliente", 0.0),
        "polizze_rule_page": polizze_detail.get("polizze_rule_page"),
        "polizze_source_text": polizze_detail.get("polizze_source_text", ""),
        "semaforo_verde": semaforo_verde,
        "semaforo": semaforo,
        "warnings": warnings,
        "motivi_esclusione": motivi_esclusione,
        "score": score,
        "memory_used": eligibility.get(
            "memory_used",
            {}
        ),
        "verifica_parametri_banca": verifica_manual_banca.get("dettagli", {}),
        "parametri_manual_banca": verifica_manual_banca.get("memory", {}),
        "prodotto_speciale": bool(commercial_policy) or getattr(p, "prodotto_speciale", False),
        "convenzione": getattr(p, "convenzione", None),
        "valore_perizia": getattr(p, "valore_perizia", None),
        "massimo_finanziabile_ltc": getattr(p, "massimo_finanziabile_ltc", None),
        "ltv_standard_base": getattr(p, "ltv_standard_base", None),
        "ltc_limite": getattr(p, "ltc_limite", None),
        "ltc_periodo": getattr(p, "ltc_periodo", None),
        "ltc_data_regola": getattr(p, "ltc_data_regola", None),
        "ltc_rule_page": getattr(p, "ltc_rule_page", None),
        "ltc_spread_bps": getattr(p, "ltc_spread_bps", None),
        "ltc_reddito_soglia": getattr(p, "ltc_reddito_soglia", None),
        "ltc_reddito_operatore": getattr(p, "ltc_reddito_operatore", None),
        "ltc_reddito_minimo": getattr(p, "ltc_reddito_minimo", None),
        "ltc_reddito_note": getattr(p, "ltc_reddito_note", None),
        "spread_base": (
            commercial_discount_detail.get("spread_base")
            if commercial_policy
            else getattr(p, "spread_base", None)
        ),
        "spread_delta": (
            -float(commercial_discount_detail.get("sconto_totale_percentuale", 0.0) or 0.0)
            if commercial_policy
            else getattr(p, "spread_delta", None)
        ),
        "motivo_prodotto_speciale": (
            commercial_summary
            if commercial_policy and commercial_summary
            else getattr(p, "motivo_prodotto_speciale", None)
        ),
        "promozione": getattr(p, "promozione", None),
        "green_tipo": getattr(p, "green_tipo", None),
        "green_sconto": getattr(p, "green_sconto", None),
        "green_sconto_bps": getattr(p, "green_sconto_bps", None),
        "green_tipo_label": getattr(p, "green_tipo_label", None),
        "green_finalita": getattr(p, "green_finalita", None),
        "green_classe_energetica": getattr(p, "green_classe_energetica", None),
        "green_limite_importo": getattr(p, "green_limite_importo", None),
        "green_limite_importo_applicato": getattr(p, "green_limite_importo_applicato", None),
        "green_note_applicazione": getattr(p, "green_note_applicazione", None),
        "green_requisiti": getattr(p, "green_requisiti", []),
        "green_rule_page": getattr(p, "green_rule_page", None),
        "pagina_regola_green": getattr(p, "pagina_regola_green", None),
        "tasso_base": getattr(p, "tasso_base", None),
        "pagina_prodotto_base": getattr(p, "pagina_prodotto_base", None),
        "pagina_regola_ltc": getattr(p, "pagina_regola_ltc", None),
        "pdf_pagine_riferimento": getattr(p, "pdf_pagine_riferimento", []),
        "applied_rules": getattr(p, "applied_rules", []),
        "rule_checks": getattr(p, "rule_checks", []),
    }


def block_to_text(
    blocco
):

    if isinstance(
        blocco,
        list
    ):

        return " ".join(
            str(row)
            for row in blocco
        )

    return str(
        blocco
    )


def read_pdf_debug_pages(
    pdf_path
):

    reader = PdfDocumentReader(
        pdf_path
    )

    documento = reader.read_document()

    pages = []

    for pagina in documento:

        page_number = pagina.get(
            "pagina"
        )

        blocchi = pagina.get(
            "blocchi",
            []
        )

        raw_text = "\n".join(
            block_to_text(
                blocco
            )
            for blocco in blocchi
        )

        model = page_analyzer.analyze(
            page_number,
            blocchi
        )

        analysis = pdf_preview_service.analyze_text(
            raw_text
        )

        pages.append(
            {
                "pagina": page_number,
                "numero_blocchi": len(
                    blocchi
                ),
                "header_count": len(
                    model.header
                ),
                "products_count": len(
                    model.products
                ),
                "info_count": len(
                    model.info
                ),
                "unknown_count": len(
                    model.unknown
                ),
                "raw_text_length": len(
                    raw_text
                ),
                "raw_text": raw_text,
                "blocchi": blocchi,
                "header_blocks": model.header,
                "product_blocks": model.products,
                "info_blocks": model.info,
                "unknown_blocks": model.unknown,
                "analysis": analysis
            }
        )

    return pages


@app.get("/health")
def health():

    return {
        "status": "OK",
        "prodotti": len(repo.all()),
        "version": "1.0.0"
    }


@app.get("/rates")
def rates():

    return rates_service.get_rates()


@app.post("/rates/irs/manual")
def update_manual_irs(
    request: ManualIrsRequest
):

    return rates_service.save_manual_irs(
        request.text
    )


@app.get("/banks")
def banks():

    items = []
    for bank in pdf_import_service.list_banks():
        item = dict(bank)
        banca = str(item.get("banca", ""))
        memory = bank_memory_service.load_bank_memory(banca) if banca else {}
        suss = memory.get("sussistenza") or {}
        item["sussistenza_configurata"] = bool(suss.get("configurata"))
        item["sussistenza_stato"] = suss.get("stato") or (
            "CONFIGURATA" if suss.get("configurata") else "MANCANTE"
        )
        item["sussistenza_fonte"] = suss.get("fonte")
        item["sussistenza_file_nome"] = suss.get("file_nome")
        items.append(item)

    return {
        "success": True,
        "banks": items
    }


@app.get("/banks/memory/{banca}")
def get_bank_memory(
    banca: str
):

    return {
        "success": True,
        "banca": banca,
        "memory": bank_memory_service.load_bank_memory(
            banca
        )
    }


@app.get("/banks/sussistenza/{banca}")
def get_bank_sussistenza(banca: str):
    memory = bank_memory_service.load_bank_memory(banca)
    return {
        "success": True,
        "banca": banca,
        "sussistenza": memory.get("sussistenza", {})
    }


@app.post("/banks/sussistenza")
def save_bank_sussistenza(request: SussistenzaRequest):
    memory = bank_memory_service.load_bank_memory(request.banca)
    tipo = str(request.tipo_geografia or "AREA").upper().strip()
    if tipo not in {"AREA", "REGIONE", "PROVINCIA"}:
        raise HTTPException(status_code=400, detail="Tipo geografia sussistenza non valido")

    struttura = str(request.struttura or "SEMPLICE").upper().strip()
    if struttura not in {"SEMPLICE", "CENTRO_CASA"}:
        raise HTTPException(status_code=400, detail="Struttura sussistenza non valida")

    normalized = {}
    for geo, rows in (request.soglie or {}).items():
        key = str(geo).strip()
        if not key or not isinstance(rows, dict):
            continue
        normalized[key] = {}
        for n, value in rows.items():
            try:
                number = float(value)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Soglia non valida: {geo} / {n}")
            if number < 0:
                raise HTTPException(status_code=400, detail="Le soglie di sussistenza non possono essere negative")
            normalized[key][str(n)] = number

    increments = {}
    for geo, value in (request.incremento_oltre_5 or {}).items():
        try:
            increments[str(geo).strip()] = float(value or 0)
        except Exception:
            increments[str(geo).strip()] = 0.0

    matrix = {}
    if struttura == "CENTRO_CASA":
        if tipo != "REGIONE":
            raise HTTPException(
                status_code=400,
                detail="La struttura CENTRO_CASA richiede tipo_geografia REGIONE",
            )

        valid_centers = {"METROPOLI", "GRANDE_CENTRO", "PICCOLO_CENTRO"}
        valid_houses = {"PRIMA_CASA", "SECONDA_CASA"}

        for regione, centers in (request.matrice or {}).items():
            if not isinstance(centers, dict):
                continue
            reg_key = str(regione).strip().upper()
            matrix[reg_key] = {}

            for centro, houses in centers.items():
                centro_key = str(centro).strip().upper().replace(" ", "_")
                if centro_key not in valid_centers or not isinstance(houses, dict):
                    continue
                matrix[reg_key][centro_key] = {}

                for casa, rows in houses.items():
                    casa_key = str(casa).strip().upper().replace(" ", "_")
                    if casa_key not in valid_houses or not isinstance(rows, dict):
                        continue

                    clean_rows = {}
                    for raw_n, raw_value in rows.items():
                        n = str(raw_n).strip().upper().replace("≥", "").replace(">=", "")
                        if n in {"7", "7+", "+7"}:
                            n = "7+"
                        if n not in {"1", "2", "3", "4", "5", "6", "7+"}:
                            continue
                        try:
                            value = float(raw_value)
                        except Exception:
                            continue
                        if value >= 0:
                            clean_rows[n] = value

                    if clean_rows:
                        matrix[reg_key][centro_key][casa_key] = clean_rows

        matrix = {
            r: c for r, c in matrix.items()
            if any(houses for houses in c.values())
        }
        if not matrix:
            raise HTTPException(
                status_code=400,
                detail="Matrice Metropoli/Grande Centro/Piccolo Centro non valida",
            )

    previous = memory.get("sussistenza") or {}
    memory["sussistenza"] = {
        "configurata": True,
        "stato": "CONFIGURATA",
        "fonte": request.fonte or "MANUALE",
        "file_nome": previous.get("file_nome"),
        "file_path": previous.get("file_path"),
        "tipo_geografia": tipo,
        "struttura": struttura,
        "dimensioni": request.dimensioni or {},
        "soglie": normalized,
        "incremento_oltre_5": increments,
        "matrice": matrix,
        "interpretazione_proposta": previous.get("interpretazione_proposta"),
    }
    bank_memory_service.save_bank_memory(request.banca, memory)
    return {"success": True, "banca": request.banca, "sussistenza": memory["sussistenza"]}


@app.post("/banks/sussistenza/upload")
async def upload_bank_sussistenza_file(
    banca: str = Form(...),
    file: UploadFile = File(...)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    allowed = {".xlsx", ".xls", ".csv", ".pdf"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Formato non supportato. Usa Excel (.xlsx/.xls), CSV o PDF."
        )

    safe_bank = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in banca.strip()
    ).strip("_") or "banca"

    folder = os.path.join("input", "sussistenza", safe_bank)
    os.makedirs(folder, exist_ok=True)

    safe_name = os.path.basename(file.filename or f"sussistenza{ext}")
    file_path = os.path.join(folder, safe_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    memory = bank_memory_service.load_bank_memory(banca)
    current = memory.get("sussistenza") or {}
    memory["sussistenza"] = {
        "configurata": False,
        "stato": "FILE_CARICATO_DA_ELABORARE",
        "fonte": "FILE",
        "file_nome": safe_name,
        "file_path": file_path,
        "tipo_geografia": current.get("tipo_geografia", "AREA"),
        "soglie": current.get("soglie") or {"nord": {}, "centro": {}, "sud": {}},
        "incremento_oltre_5": current.get("incremento_oltre_5") or {
            "nord": 0.0, "centro": 0.0, "sud": 0.0
        },
        "interpretazione_proposta": None,
    }
    bank_memory_service.save_bank_memory(banca, memory)

    return {
        "success": True,
        "banca": banca,
        "file_nome": safe_name,
        "file_path": file_path,
        "stato": "FILE_CARICATO_DA_ELABORARE",
        "message": "File caricato e associato alla banca. Configurazione da completare.",
    }



def _norm_geo(value):
    import unicodedata
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return value


def _num_cell(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("€", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _read_sussistenza_rows(path):
    ext = os.path.splitext(path)[1].lower()
    tables = []
    if ext in {".xlsx", ".xls", ".csv"}:
        import pandas as pd
        if ext == ".csv":
            frames = {"CSV": pd.read_csv(path, header=None, sep=None, engine="python")}
        else:
            frames = pd.read_excel(path, sheet_name=None, header=None)
        for sheet, df in frames.items():
            rows = []
            for row in df.fillna("").values.tolist():
                vals = [str(v).strip() if not isinstance(v, (int, float)) else v for v in row]
                if any(str(v).strip() for v in vals):
                    rows.append(vals)
            if rows:
                tables.append({"source": sheet, "rows": rows})
    elif ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page_no, page in enumerate(pdf.pages, 1):
                found = page.extract_tables() or []
                for idx, table in enumerate(found, 1):
                    rows = [["" if v is None else str(v).strip() for v in row] for row in table]
                    if rows:
                        tables.append({"source": f"Pagina {page_no} tabella {idx}", "rows": rows})
    return tables


def _match_geo_label(value):
    n = _norm_geo(value)
    area_alias = {"nord":"Nord", "centro":"Centro", "sud":"Sud", "sud isole":"Sud", "isole":"Sud"}
    if n in area_alias:
        return "AREA", area_alias[n]
    for r in REGIONI:
        if n == _norm_geo(r):
            return "REGIONE", r
    province_alias = {"citta metropolitana di cagliari":"Cagliari", "citta metropolitana di sassari":"Sassari"}
    if n in province_alias:
        return "PROVINCIA", province_alias[n]
    for p in PROVINCE:
        if n == _norm_geo(p):
            return "PROVINCIA", p
    return None, None


def _interpret_sussistenza_tables(tables):
    best = None
    for table in tables:
        rows = table["rows"]
        # Orientation A: geography in header columns, component count in first column.
        for hi, header in enumerate(rows[:12]):
            geo_cols = []
            modes = []
            for ci, cell in enumerate(header):
                mode, label = _match_geo_label(cell)
                if mode:
                    geo_cols.append((ci, label)); modes.append(mode)
            if len(geo_cols) >= 2 and len(set(modes)) == 1:
                mode = modes[0]; soglie={label:{} for _,label in geo_cols}; matched=0
                for row in rows[hi+1:hi+12]:
                    if not row: continue
                    comp = _num_cell(row[0])
                    if comp is None or int(comp) not in {1,2,3,4,5}: continue
                    comp=str(int(comp)); anyv=False
                    for ci,label in geo_cols:
                        if ci < len(row):
                            v=_num_cell(row[ci])
                            if v is not None:
                                soglie[label][comp]=v; anyv=True
                    if anyv: matched += 1
                if matched >= 3:
                    candidate={"tipo_geografia":mode,"soglie":soglie,"incremento_oltre_5":{},"confidence":min(0.98,0.65+matched*0.06),"source":table['source'],"warnings":[]}
                    if best is None or candidate['confidence']>best['confidence']: best=candidate
        # Orientation B: component numbers in header, geography labels in first column.
        for hi, header in enumerate(rows[:12]):
            comp_cols=[]
            for ci,cell in enumerate(header):
                v=_num_cell(cell)
                if v is not None and int(v) in {1,2,3,4,5}: comp_cols.append((ci,str(int(v))))
            if len(comp_cols)>=3:
                soglie={}; mode=None; matched=0
                for row in rows[hi+1:]:
                    if not row: continue
                    m,label=_match_geo_label(row[0])
                    if not m: continue
                    if mode and m!=mode: continue
                    mode=m; vals={}
                    for ci,comp in comp_cols:
                        if ci < len(row):
                            v=_num_cell(row[ci])
                            if v is not None: vals[comp]=v
                    if len(vals)>=3:
                        soglie[label]=vals; matched+=1
                if mode and matched>=2:
                    candidate={"tipo_geografia":mode,"soglie":soglie,"incremento_oltre_5":{},"confidence":min(0.96,0.62+matched*0.05),"source":table['source'],"warnings":[]}
                    if best is None or candidate['confidence']>best['confidence']: best=candidate
    if best is None:
        return {"success":False,"confidence":0.0,"warnings":["Struttura della tabella non riconosciuta automaticamente."],"tipo_geografia":None,"soglie":{},"incremento_oltre_5":{}}
    # Search any two-row table for increments over 5.
    for table in tables:
        rows=table['rows']
        for i,row in enumerate(rows[:-1]):
            labels=[]
            for ci,cell in enumerate(row):
                mode,label=_match_geo_label(cell)
                if mode==best['tipo_geografia']: labels.append((ci,label))
            if len(labels)>=2:
                nextrow=rows[i+1]
                vals={}
                for ci,label in labels:
                    if ci < len(nextrow):
                        v=_num_cell(nextrow[ci])
                        if v is not None: vals[label]=v
                # do not mistake main first component row as increment; favor source containing 'oltre' nearby
                context=' '.join(str(x) for r in rows[max(0,i-2):i+1] for x in r).lower()
                if len(vals)>=2 and ('oltre' in context or 'aggiunt' in context or 'piu di 5' in context or 'più di 5' in context):
                    best['incremento_oltre_5']=vals
                    break
    if not best['incremento_oltre_5']:
        best['warnings'].append("Incremento oltre 5 componenti non rilevato: verificare manualmente se previsto.")
    best['success']=True
    return best


def _extract_json_object(text):
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\\s*", "", text)
        text = re.sub(r"\\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def _openai_response_text(data):
    if data.get("output_text"):
        return data["output_text"]
    chunks = []
    for item in data.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                chunks.append(content.get("text", ""))
    return "\\n".join(chunks)


def _validate_ai_sussistenza(obj):
    if not isinstance(obj, dict):
        return None

    tipo = str(obj.get("tipo_geografia") or "").upper()
    if tipo not in {"AREA", "REGIONE", "PROVINCIA"}:
        return None

    struttura = str(obj.get("struttura") or "SEMPLICE").upper()

    if struttura == "CENTRO_CASA":
        if tipo != "REGIONE":
            return None

        raw_matrix = obj.get("matrice")
        if not isinstance(raw_matrix, dict) or not raw_matrix:
            return None

        valid_centers = {"METROPOLI", "GRANDE_CENTRO", "PICCOLO_CENTRO"}
        valid_houses = {"PRIMA_CASA", "SECONDA_CASA"}
        matrix = {}

        for regione, centers in raw_matrix.items():
            if not isinstance(centers, dict):
                continue
            reg_key = str(regione).strip().upper()
            matrix[reg_key] = {}

            for centro, houses in centers.items():
                centro_key = str(centro).strip().upper().replace(" ", "_")
                if centro_key not in valid_centers or not isinstance(houses, dict):
                    continue
                matrix[reg_key][centro_key] = {}

                for casa, values in houses.items():
                    casa_key = str(casa).strip().upper().replace(" ", "_")
                    if casa_key not in valid_houses or not isinstance(values, dict):
                        continue

                    clean = {}
                    for raw_n in ["1", "2", "3", "4", "5", "6", "7+"]:
                        value = values.get(raw_n)
                        if value is None and raw_n == "7+":
                            value = values.get("7", values.get(">=7", values.get("≥7")))
                        v = _num_cell(value)
                        if v is not None:
                            clean[raw_n] = v

                    if clean:
                        matrix[reg_key][centro_key][casa_key] = clean

        matrix = {
            r: c for r, c in matrix.items()
            if any(houses for houses in c.values())
        }
        if not matrix:
            return None

        return {
            "success": True,
            "tipo_geografia": "REGIONE",
            "struttura": "CENTRO_CASA",
            "dimensioni": {
                "tipo_centro": ["METROPOLI", "GRANDE_CENTRO", "PICCOLO_CENTRO"],
                "destinazione_casa": ["PRIMA_CASA", "SECONDA_CASA"],
                "componenti": ["1", "2", "3", "4", "5", "6", "7+"],
            },
            "matrice": matrix,
            "soglie": {},
            "incremento_oltre_5": {},
            "confidence": float(obj.get("confidence") or 0.85),
            "source": "OPENAI_FILE_INTERPRETER",
            "metodo": "AI",
            "warnings": [str(x) for x in (obj.get("warnings") or [])],
        }

    # Legacy/simple structure.
    raw = obj.get("soglie")
    if not isinstance(raw, dict) or not raw:
        return None

    soglie = {}
    for label, values in raw.items():
        if not isinstance(values, dict):
            continue
        clean = {}
        for n in range(1, 6):
            v = _num_cell(values.get(str(n), values.get(n)))
            if v is not None:
                clean[str(n)] = v
        if len(clean) >= 3:
            soglie[str(label).strip()] = clean

    if not soglie:
        return None

    inc = {}
    for label, value in (obj.get("incremento_oltre_5") or {}).items():
        v = _num_cell(value)
        if v is not None:
            inc[str(label).strip()] = v

    return {
        "success": True,
        "tipo_geografia": tipo,
        "struttura": "SEMPLICE",
        "dimensioni": {},
        "matrice": {},
        "soglie": soglie,
        "incremento_oltre_5": inc,
        "confidence": float(obj.get("confidence") or 0.85),
        "source": "OPENAI_FILE_INTERPRETER",
        "metodo": "AI",
        "warnings": [str(x) for x in (obj.get("warnings") or [])],
    }


def _interpret_sussistenza_with_openai(path):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "confidence": 0.0,
            "warnings": [
                "Parser tradizionale non sufficiente e OPENAI_API_KEY non configurata. "
                "Configura la chiave API sul backend per attivare il fallback AI."
            ],
            "tipo_geografia": None,
            "soglie": {},
            "incremento_oltre_5": {},
            "metodo": "AI_NON_CONFIGURATA",
        }

    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext)
    if not mime:
        return {"success": False, "warnings": ["Fallback AI previsto per PDF/immagini."], "tipo_geografia": None, "soglie": {}, "incremento_oltre_5": {}, "confidence": 0.0}

    with open(path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")

    prompt = """Sei l'interprete documentale di Kiron. Analizza ESCLUSIVAMENTE il file allegato e individua le soglie di sussistenza per mutui senza eliminare dimensioni della tabella.

Puoi incontrare due strutture.

A) SEMPLICE: geografia AREA/REGIONE/PROVINCIA con soglie per componenti 1-5 ed eventuale incremento oltre 5.

B) CENTRO_CASA: tipica di tabelle come ING, dove per ogni REGIONE esistono una o più categorie tra METROPOLI, GRANDE_CENTRO, PICCOLO_CENTRO e, per ciascuna, PRIMA_CASA e SECONDA_CASA. In questo caso devi estrarre TUTTE le serie presenti e i componenti 1,2,3,4,5,6,7+ (≥7). Non scegliere una sola colonna e non trasformare 6/7+ in un incremento oltre 5.

Restituisci SOLO JSON valido.

Per struttura semplice:
{"tipo_geografia":"AREA|REGIONE|PROVINCIA","struttura":"SEMPLICE","soglie":{"etichetta":{"1":numero,"2":numero,"3":numero,"4":numero,"5":numero}},"incremento_oltre_5":{"etichetta":numero},"confidence":0.0,"warnings":[]}

Per struttura CENTRO_CASA:
{"tipo_geografia":"REGIONE","struttura":"CENTRO_CASA","matrice":{"REGIONE":{"METROPOLI":{"PRIMA_CASA":{"1":numero,"2":numero,"3":numero,"4":numero,"5":numero,"6":numero,"7+":numero},"SECONDA_CASA":{...}},"GRANDE_CENTRO":{...},"PICCOLO_CENTRO":{...}}},"confidence":0.0,"warnings":[]}

Se una categoria non è disponibile per una regione, omettila. Non inventare valori. I numeri devono essere numeri JSON, non stringhe."""

    content = [{"type": "input_text", "text": prompt}]
    if ext == ".pdf":
        content.append({
            "type": "input_file",
            "filename": os.path.basename(path),
            "file_data": f"data:{mime};base64,{encoded}",
        })
    else:
        content.append({
            "type": "input_image",
            "image_url": f"data:{mime};base64,{encoded}",
            "detail": "high",
        })

    model = os.getenv("KIRON_OPENAI_MODEL", "gpt-5.6-luna")
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "store": False,
                "input": [{"role": "user", "content": content}],
            },
            timeout=120,
        )
        if response.status_code >= 400:
            return {"success": False, "confidence": 0.0, "warnings": [f"Fallback AI non riuscito ({response.status_code}): {response.text[:300]}"], "tipo_geografia": None, "soglie": {}, "incremento_oltre_5": {}, "metodo": "AI_ERRORE"}
        obj = _extract_json_object(_openai_response_text(response.json()))
        validated = _validate_ai_sussistenza(obj)
        if validated:
            return validated
        return {"success": False, "confidence": 0.0, "warnings": ["L'AI ha risposto ma non ha prodotto una tabella di sussistenza valida."], "tipo_geografia": None, "soglie": {}, "incremento_oltre_5": {}, "metodo": "AI_NON_VALIDATA"}
    except Exception as exc:
        return {"success": False, "confidence": 0.0, "warnings": [f"Errore fallback AI: {exc}"], "tipo_geografia": None, "soglie": {}, "incremento_oltre_5": {}, "metodo": "AI_ERRORE"}


@app.post("/banks/sussistenza/analyze/{banca}")
def analyze_bank_sussistenza(banca: str):
    memory = bank_memory_service.load_bank_memory(banca)
    current = memory.get("sussistenza") or {}
    path = current.get("file_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Nessun file sussistenza caricato per questa banca")
    try:
        tables = _read_sussistenza_rows(path)
        proposal = _interpret_sussistenza_tables(tables)
        if not proposal.get("success"):
            proposal = _interpret_sussistenza_with_openai(path)
    except Exception as exc:
        proposal = _interpret_sussistenza_with_openai(path)
        if not proposal.get("success"):
            proposal.setdefault("warnings", []).insert(0, f"Parser tradizionale: {exc}")
    current["interpretazione_proposta"] = proposal
    current["stato"] = "INTERPRETAZIONE_PROPOSTA" if proposal.get("success") else "FILE_DA_VERIFICARE_MANUALMENTE"
    current["configurata"] = False
    memory["sussistenza"] = current
    bank_memory_service.save_bank_memory(banca, memory)
    return {"success": bool(proposal.get("success")), "banca": banca, "interpretazione": proposal}


@app.post("/banks/sussistenza/defer")
def defer_bank_sussistenza(request: SussistenzaDeferredRequest):
    memory = bank_memory_service.load_bank_memory(request.banca)
    current = memory.get("sussistenza") or {}
    current["configurata"] = False
    current["stato"] = (
        "FILE_CARICATO_DA_ELABORARE"
        if current.get("file_nome")
        else "DA_CARICARE"
    )
    memory["sussistenza"] = current
    bank_memory_service.save_bank_memory(request.banca, memory)

    return {
        "success": True,
        "banca": request.banca,
        "sussistenza": current,
    }


@app.post("/banks/verify-import")
def verify_bank_import(
    request: DebugPdfRequest
):

    pages = read_pdf_debug_pages(
        request.pdf_path
    )

    gaps = pdf_gap_analyzer_service.analyze_pages(
        pages
    )

    preview = pdf_preview_service.preview_pdf(
        banca=request.banca,
        pdf_path=request.pdf_path
    )

    memory = bank_memory_service.load_bank_memory(
        request.banca
    )

    confirmed_phrases = set(
        str(row).strip()
        for row in memory.get("frasi_confermate", [])
        if str(row).strip()
    )

    confirmed_by_category = set()
    for category in [
        "autonomi",
        "redditi_esteri",
        "garanti",
        "polizze",
        "deroghe",
        "classe_energetica"
    ]:
        confirmed_by_category.update(
            str(row).strip()
            for row in memory.get(category, [])
            if str(row).strip()
        )

    unresolved = []
    for row in gaps.get("all_sentences", []):
        sentence = str(row.get("sentence", "")).strip()
        if not sentence:
            continue
        if sentence in confirmed_phrases or sentence in confirmed_by_category:
            continue
        unresolved.append(row)

    page_audit = []
    covered_pages = 0
    suspicious_pages = 0

    for page in pages:
        classified_count = (
            page.get("header_count", 0)
            + page.get("products_count", 0)
            + page.get("info_count", 0)
        )
        unknown_count = page.get("unknown_count", 0)
        raw_length = page.get("raw_text_length", 0)
        covered = classified_count > 0 or raw_length < 40
        suspicious = (
            raw_length >= 40
            and (not covered or unknown_count > classified_count)
        )

        if covered:
            covered_pages += 1
        if suspicious:
            suspicious_pages += 1

        page_audit.append({
            "pagina": page.get("pagina"),
            "covered": covered,
            "suspicious": suspicious,
            "header_count": page.get("header_count", 0),
            "products_count": page.get("products_count", 0),
            "info_count": page.get("info_count", 0),
            "unknown_count": unknown_count,
            "raw_text_length": raw_length,
            "text_preview": str(page.get("raw_text", ""))[:600]
        })

    total_pages = len(pages)
    coverage_percent = round(
        (covered_pages / total_pages * 100) if total_pages else 0,
        1
    )

    changes = preview.get("changes", [])
    status = "OK"
    if suspicious_pages > 0 or unresolved:
        status = "ATTENZIONE"
    if coverage_percent < 70:
        status = "ERRORE"

    return {
        "success": True,
        "banca": request.banca,
        "pdf_path": request.pdf_path,
        "status": status,
        "summary": {
            "numero_pagine": total_pages,
            "pagine_coperte": covered_pages,
            "copertura_percentuale": coverage_percent,
            "pagine_sospette": suspicious_pages,
            "modifiche_rilevate": len(changes),
            "frasi_non_risolte": len(unresolved)
        },
        "changes": changes,
        "detected": preview.get("detected", {}),
        "memory": memory,
        "new_phrases": preview.get("new_phrases", []),
        "unresolved": unresolved,
        "page_audit": page_audit,
        "technical_pages": pages
    }


@app.post("/banks/memory/confirm-phrases")
def confirm_phrases(
    request: ConfirmPhrasesRequest
):

    return bank_memory_confirm_service.confirm_phrases(
        banca=request.banca,
        phrases=request.phrases
    )


@app.post("/banks/memory/confirm-fields")
def confirm_fields(
    request: ConfirmFieldsRequest
):

    return bank_memory_confirm_service.confirm_fields(
        banca=request.banca,
        fields=request.fields
    )


@app.post("/banks/memory/confirm-category")
def confirm_category(
    request: ConfirmCategoryRequest
):

    return bank_memory_confirm_service.confirm_category(
        banca=request.banca,
        category=request.category,
        phrases=request.phrases
    )


@app.post("/banks/import-pdf")
async def import_bank_pdf(
    banca: str = Form(...),
    tasso_esplicito: bool = Form(...),
    perizia_euro: float = Form(0.0),
    imposta_sostitutiva_percentuale: float = Form(0.25),
    istruttoria_percentuale: float = Form(...),
    istruttoria_minimo: float = Form(0.0),
    istruttoria_massimo: float = Form(0.0),
    calcolo_debito: str = Form(...),
    rapporto_rata_reddito_percentuale: float = Form(35.0),
    eta_massima_finanziabile: int = Form(80),
    anni_residenza_italia_straniero: int = Form(...),
    file: UploadFile = File(...)
):

    os.makedirs(
        "input",
        exist_ok=True
    )

    file_path = os.path.join(
        "input",
        file.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    memory = bank_memory_service.load_bank_memory(banca)
    memory["perizia_euro"] = float(perizia_euro or 0.0)
    imposta_pct = float(
        imposta_sostitutiva_percentuale
        if imposta_sostitutiva_percentuale is not None
        else 0.25
    )
    memory["imposta_sostitutiva_percentuale"] = imposta_pct
    # Alias legacy per compatibilità.
    memory["costi_avviamento_percentuale"] = imposta_pct

    memory["istruttoria_percentuale"] = float(istruttoria_percentuale)
    memory["istruttoria_minimo"] = float(istruttoria_minimo or 0.0)
    memory["istruttoria_massimo"] = float(istruttoria_massimo or 0.0)
    if memory["istruttoria_percentuale"] < 0:
        raise HTTPException(status_code=400, detail="Istruttoria percentuale non valida")
    if memory["istruttoria_minimo"] < 0 or memory["istruttoria_massimo"] < 0:
        raise HTTPException(status_code=400, detail="Minimo/massimo istruttoria non validi")
    if (
        memory["istruttoria_massimo"] > 0
        and memory["istruttoria_minimo"] > memory["istruttoria_massimo"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Il minimo istruttoria non può superare il massimo"
        )
    memory["tasso_esplicito"] = bool(tasso_esplicito)
    metodo_debito = str(calcolo_debito or "").upper().strip()
    if metodo_debito not in {"RATA", "REDDITO"}:
        raise HTTPException(
            status_code=400,
            detail="calcolo_debito deve essere RATA oppure REDDITO"
        )
    memory["calcolo_debito"] = metodo_debito
    memory["rapporto_rata_reddito_percentuale"] = float(
        rapporto_rata_reddito_percentuale
    )
    memory["eta_massima_finanziabile"] = int(eta_massima_finanziabile)
    memory["anni_residenza_italia_straniero"] = int(anni_residenza_italia_straniero)
    if memory["anni_residenza_italia_straniero"] < 0:
        raise HTTPException(status_code=400, detail="Gli anni di residenza minima non possono essere negativi")
    bank_memory_service.save_bank_memory(banca, memory)

    result = pdf_import_service.import_pdf(
        banca=banca,
        pdf_path=file_path,
        pdf_name=file.filename,
        tasso_esplicito=tasso_esplicito
    )

    reload_database()

    result["perizia_euro"] = float(perizia_euro or 0.0)
    result["imposta_sostitutiva_percentuale"] = imposta_pct
    result["costi_avviamento_percentuale"] = imposta_pct
    result["istruttoria_percentuale"] = float(istruttoria_percentuale)
    result["istruttoria_minimo"] = float(istruttoria_minimo or 0.0)
    result["istruttoria_massimo"] = float(istruttoria_massimo or 0.0)
    result["calcolo_debito"] = metodo_debito
    result["rapporto_rata_reddito_percentuale"] = float(
        rapporto_rata_reddito_percentuale
    )
    result["eta_massima_finanziabile"] = int(eta_massima_finanziabile)
    result["anni_residenza_italia_straniero"] = int(anni_residenza_italia_straniero)
    result["sussistenza_configurata"] = bool((memory.get("sussistenza") or {}).get("configurata"))

    return result


@app.get("/pdf/{pdf_name}")
def get_pdf(
    pdf_name: str
):

    file_path = os.path.join(
        "input",
        pdf_name
    )

    if not os.path.exists(
        file_path
    ):

        raise HTTPException(
            status_code=404,
            detail="PDF non trovato"
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=pdf_name
    )


@app.post("/quotes/pdf")
def create_quote_pdf(
    request: QuoteRequest
):

    return quote_pdf_service.create_quote_pdf(
        {
            "cliente": request.cliente,
            "pratica": request.pratica,
            "prodotti": request.prodotti
        }
    )


@app.post("/reports/technical-pdf")
def create_technical_report_pdf(
    request: TechnicalReportRequest
):

    return technical_report_service.create_report_pdf(
        {
            "pratica": request.pratica,
            "prodotti": request.prodotti,
            "migliore": request.migliore,
        }
    )


@app.get("/quotes")
def list_quotes():

    return {
        "success": True,
        "quotes": quote_pdf_service.list_quotes()
    }


@app.get("/clients")
def list_clients():

    return {
        "success": True,
        "clients": quote_pdf_service.list_clients()
    }


@app.get("/quotes/{filename}")
def get_quote_pdf(
    filename: str
):

    file_path = os.path.join(
        "quotes",
        filename
    )

    if not os.path.exists(
        file_path
    ):

        raise HTTPException(
            status_code=404,
            detail="Preventivo non trovato"
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


@app.post("/search")
def search(
    request: SearchRequest
):

    reload_database()

    customer = Customer(
        nome="API",
        cognome="CLIENT",
        eta=40,
        reddito=request.reddito_mensile
    )

    property = Property(
        valore=request.valore,
        regione="",
        provincia=""
    )

    mortgage = Mortgage(
        importo=request.importo,
        durata=request.durata,
        finalita=request.finalita,
        tasso=request.tasso,
        data_rogito=request.data_rogito,
        valore_perizia=request.valore_perizia,
        classe_energetica=request.classe_energetica
    )

    practice = MortgagePractice(
        customer,
        property,
        mortgage
    )

    result = service.search(
        practice
    )

    if not result["success"]:

        return result

    response = result["response"]

    prodotti = []

    for p in response.risultati:

        prodotti.append(
            prodotto_to_json(
                p,
                request,
                practice
            )
        )

    prodotti = sorted(
        prodotti,
        key=lambda x: (
            -x.get(
                "score",
                0
            ),
            x.get(
                "rata",
                0
            )
        )
    )

    migliore = None

    for prodotto in prodotti:
        if prodotto.get("semaforo") != "ROSSO":
            migliore = prodotto
            break

    return {
        "success": True,
        "numero_prodotti": len(prodotti),
        "ltv": practice.ltv,
        "migliore": migliore,
        "prodotti": prodotti
    }
