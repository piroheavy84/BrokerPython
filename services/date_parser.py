class DateParser:

    def parse(self, rule):

        risultato = {

            "tipo_listino":

                rule.get(

                    "tipo_listino",

                    ""

                ),

            "canalizzazione": {

                "dal":

                    rule.get(

                        "canalizzazione_da",

                        ""

                    ),

                "al":

                    rule.get(

                        "canalizzazione_a",

                        ""

                    )

            },

            "stipula_entro":

                rule.get(

                    "stipula_entro",

                    ""

                )

        }

        return risultato