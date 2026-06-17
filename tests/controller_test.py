from models.broker_database import BrokerDatabase
from repositories.product_repository import ProductRepository

from controllers.broker_controller import BrokerController

from domain.mortgage_practice import MortgagePractice

from models.customer import Customer
from models.property import Property
from models.mortgage import Mortgage


db = BrokerDatabase()

db.load_many(

    [

        "output/chebanca_index.json"

    ]

)

repo = ProductRepository(db)

controller = BrokerController(repo)

cliente = Customer(

    nome="Mario",

    cognome="Rossi",

    eta=38,

    reddito=42000

)

immobile = Property(

    valore=250000,

    regione="Lombardia",

    provincia="Milano"

)

mutuo = Mortgage(

    importo=170000,

    durata=23,

    finalita="ACQUISTO",

    tasso="FISSO"

)

practice = MortgagePractice(

    cliente,

    immobile,

    mutuo

)

result = controller.search(

    practice

)

print(result)