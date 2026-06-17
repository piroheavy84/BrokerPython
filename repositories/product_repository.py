class ProductRepository:

    def __init__(

        self,

        database

    ):

        self.database = database

    def all(self):

        return self.database.get_all()

    def by_bank(

        self,

        banca

    ):

        risultati = []

        for r in self.database.get_all():

            if r["banca"] == banca:

                risultati.append(r)

        return risultati

    def count(self):

        return len(

            self.database.get_all()

        )