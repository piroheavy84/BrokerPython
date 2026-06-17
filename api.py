from fastapi import FastAPI
from pydantic import BaseModel

from models.broker_database import BrokerDatabase
from repositories.product_repository import ProductRepository

from services.practice_service import PracticeService

from domain.mortgage_practice import MortgagePractice

from models.customer import Customer
from models.property import Property
from models.mortgage import Mortgage


app = FastAPI(
    title="Kiron Broker Engine API"
)


# ==========================================
# CARICAMENTO DATABASE
# ==========================================

db = BrokerDatabase()

db.load_many(

    [

        "output/chebanca_index.json"

    ]

)

repo = ProductRepository(db)

service = PracticeService(repo)


# ==========================================
# REQUEST MODEL
# ==========================================

class SearchRequest(BaseModel):

    finalita: str

    tasso: str

    durata: int

    importo: float

    valore: float


# ==========================================
# SEARCH
# ==========================================

@app.post("/search")

def search(request: SearchRequest):

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

    # --------------------------

    if not result["success"]:

        return result

    response = result["response"]

    migliore = None

    if response.migliore:

        migliore = {

            "banca": response.migliore.banca,

            "listino": response.migliore.tipo_listino,

            "spread": response.migliore.spread,

            "durata": response.migliore.durata,

            "ltv": response.migliore.ltv,

            "pagina": response.migliore.pagina,

            "pdf": response.migliore.pdf

        }

    prodotti = []

    for p in response.risultati:

        prodotti.append(

            {

                "banca": p.banca,

                "listino": p.tipo_listino,

                "spread": p.spread,

                "durata": p.durata,

                "ltv": p.ltv,

                "pagina": p.pagina,

                "pdf": p.pdf

            }

        )

    return {

        "success": True,

        "numero_prodotti": response.numero_prodotti,

        "ltv": practice.ltv,

        "migliore": migliore,

        "prodotti": prodotti

    }