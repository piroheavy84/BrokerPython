from models.broker_database import BrokerDatabase
from models.mortgage_case import MortgageCase

from repositories.product_repository import ProductRepository

from engines.broker_engine.broker_engine import BrokerEngine

from services.result_formatter import ResultFormatter


# ==========================================
# CARICAMENTO DATABASE
# ==========================================

db = BrokerDatabase()

db.load_many(

    [

        "output/chebanca_index.json"

        # In futuro:
        # "output/intesa_index.json",
        # "output/bper_index.json",
        # "output/bpm_index.json",
        # "output/mps_index.json",
        # "output/credit_agricole_index.json"

    ]

)

repo = ProductRepository(db)


# ==========================================
# PRATICA CLIENTE
# ==========================================

pratica = MortgageCase(

    nome="Mario Rossi",

    eta=38,

    reddito=42000,

    importo_mutuo=170000,

    valore_immobile=250000,

    finalita="ACQUISTO",

    tasso="FISSO",

    durata=23,

    regione="Lombardia",

    provincia="Milano",

    prima_casa=True,

    consap=False,

    under36=False

)


# ==========================================
# RICERCA
# ==========================================

engine = BrokerEngine()

response = engine.search(

    repo.all(),

    pratica

)


# ==========================================
# STAMPA RISULTATI
# ==========================================

formatter = ResultFormatter()

formatter.print(

    response.risultati

)

print()

print("=" * 50)

print("RIEPILOGO RICERCA")

print("=" * 50)

print()

print("Cliente        :", pratica.nome)

print("Età            :", pratica.eta)

print("Reddito        :", pratica.reddito)

print("Importo mutuo  :", pratica.importo_mutuo)

print("Valore immobile:", pratica.valore_immobile)

print("LTV calcolato  :", round(pratica.ltv, 2), "%")

print("Finalità       :", pratica.finalita)

print("Tasso          :", pratica.tasso)

print("Durata         :", pratica.durata)

print()

print("Prodotti trovati:", response.numero_prodotti)

print()

if response.migliore:

    print("🏆 MIGLIORE OFFERTA")

    print()

    print("Banca      :", response.migliore.banca)

    print("Listino    :", response.migliore.tipo_listino)

    print("Spread     :", response.migliore.spread)

    print("Durata     :", response.migliore.durata)

    print("LTV <=     :", response.migliore.ltv)

    print("Pagina PDF :", response.migliore.pagina)

    print("File PDF   :", response.migliore.pdf)

print()

print("Database contiene", db.count(), "prodotti")