from services.finalita_parser import FinalitaParser
from services.tasso_parser import TassoParser
from services.date_parser import DateParser


class RuleCleaner:

    def __init__(self):

        self.finalita_parser = FinalitaParser()

        self.tasso_parser = TassoParser()

        self.date_parser = DateParser()

    def clean(self, rule):

        nuovo = rule.copy()

        # -------------------
        # FINALITA
        # -------------------

        nuovo["finalita"] = self.finalita_parser.parse(

            nuovo.get(

                "finalita",

                ""

            )

        )

        # -------------------
        # TASSO
        # -------------------

        nuovo["tasso"] = self.tasso_parser.parse(

            nuovo.get(

                "tasso",

                ""

            )

        )

        # -------------------
        # DATE
        # -------------------

        nuovo["date"] = self.date_parser.parse(

            nuovo

        )

        return nuovo