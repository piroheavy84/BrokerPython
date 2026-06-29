import json
import os
import re
import shutil

from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.bank_memory_service import BankMemoryService

from models.broker_database import BrokerDatabase
from repositories.product_repository import ProductRepository

from services.practice_service import PracticeService
from services.rates_service import RatesService
from services.pdf_import_service import PdfImportService
from services.quote_pdf_service import QuotePdfService
from services.pdf_preview_service import PdfPreviewService
from services.bank_memory_confirm_service import BankMemoryConfirmService
from services.bank_eligibility_service import BankEligibilityService
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

pdf_preview_service = PdfPreviewService()

bank_memory_confirm_service = BankMemoryConfirmService()

bank_memory_service = BankMemoryService()

bank_eligibility_service = BankEligibilityService()

pdf_gap_analyzer_service = PdfGapAnalyzerService()

page_analyzer = PageAnalyzer()


class SearchRequest(BaseModel):

    finalita: str

    tasso: str

    durata: int

    importo: float

    valore: float

    indice_mercato: float = 0


class ManualIrsRequest(BaseModel):

    text: str


class QuoteRequest(BaseModel):

    cliente: dict

    pratica: dict

    prodotti: list


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

        for cost in page.get(
            "costs",
            []
        ):

            if str(
                cost.get(
                    "type",
                    ""
                )
            ).upper() == "ISTRUTTORIA":

                source_text = cost.get(
                    "source_text",
                    ""
                )

                return parse_istruttoria_from_text(
                    source_text
                )

    return None


def calcola_istruttoria(
    banca,
    importo
):

    rule = get_istruttoria_rule(
        banca
    )

    if rule is None:

        return 0.0

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

    return istruttoria


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

    return str(
        prodotto.tasso
    ).upper() == "FISSO"


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

    return "EURIBOR"


def prodotto_to_json(
    p,
    request,
    practice
):

    spread = spread_to_float(
        p.spread
    )

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

        tasso_finito = percent_to_float(
            tasso_finito_pdf
        )

    else:

        indice = calcola_indice_automatico(
            p,
            request
        )

        if indice == 0 and request.indice_mercato > 0:

            indice = request.indice_mercato

        tasso_finito = indice + spread

        indice_riferimento = get_indice_riferimento(
            p
        )

    rata = calcola_rata(
        request.importo,
        request.durata,
        tasso_finito
    )

    istruttoria_euro = calcola_istruttoria(
        p.banca,
        request.importo
    )

    eligibility = bank_eligibility_service.evaluate(
        p.banca,
        {
            "eta_cliente": practice.customer.eta,
            "durata": request.durata,
            "ltv": practice.ltv,
            "finalita": request.finalita,
            "classe_energetica": "",
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

    if score < 0:

        score = 0

    semaforo_verde = semaforo == "VERDE"

    return {
        "banca": p.banca,
        "prodotto": f"{p.tasso} {p.tipo_listino}",
        "listino": p.tipo_listino,
        "spread": spread,
        "spread_label": p.spread,
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
        "retrocessione_euro": 0,
        "istruttoria_euro": istruttoria_euro,
        "perizia_euro": 0,
        "semaforo_verde": semaforo_verde,
        "semaforo": semaforo,
        "warnings": warnings,
        "motivi_esclusione": motivi_esclusione,
        "score": score,
        "memory_used": eligibility.get(
            "memory_used",
            {}
        )
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

    return {
        "success": True,
        "banks": pdf_import_service.list_banks()
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


@app.post("/banks/preview-pdf")
def preview_pdf(
    request: PdfPreviewRequest
):

    return pdf_preview_service.preview_pdf(
        banca=request.banca,
        pdf_path=request.pdf_path
    )


@app.post("/banks/debug-pdf")
def debug_pdf(
    request: DebugPdfRequest
):

    pages = read_pdf_debug_pages(
        request.pdf_path
    )

    return {
        "success": True,
        "banca": request.banca,
        "numero_pagine": len(
            pages
        ),
        "pages": pages
    }


@app.post("/banks/debug-gaps")
def debug_gaps(
    request: DebugPdfRequest
):

    pages = read_pdf_debug_pages(
        request.pdf_path
    )

    gaps = pdf_gap_analyzer_service.analyze_pages(
        pages
    )

    return {
        "success": True,
        "banca": request.banca,
        "numero_pagine": len(
            pages
        ),
        "pages": pages,
        "gaps": gaps
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

    result = pdf_import_service.import_pdf(
        banca=banca,
        pdf_path=file_path,
        pdf_name=file.filename,
        tasso_esplicito=tasso_esplicito
    )

    reload_database()

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
        reddito=40000
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
        tasso=request.tasso
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

    if len(prodotti) > 0:

        migliore = prodotti[0]

    return {
        "success": True,
        "numero_prodotti": len(prodotti),
        "ltv": practice.ltv,
        "migliore": migliore,
        "prodotti": prodotti
    }
