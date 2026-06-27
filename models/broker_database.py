import json


class BrokerDatabase:

    def __init__(self):

        self.rules = []

    # --------------------------

    def load(self, file):

        with open(

            file,

            encoding="utf-8"

        ) as f:

            self.rules.extend(

                json.load(f)

            )

    # --------------------------

    def load_many(

        self,

        files

    ):

        for file in files:

            self.load(file)

    # --------------------------

    def get_all(self):

        return self.rules

    # --------------------------

    def count(self):

        return len(

            self.rules

        )