class BrokerIndex:

    def build(self, rules):

        index = {}

        for rule in rules:

            finalita_list = rule.get(

                "finalita",

                []

            )

            if isinstance(

                finalita_list,

                str

            ):

                finalita_list = [

                    finalita_list

                ]

            for finalita in finalita_list:

                chiave = (

                    finalita,

                    rule.get(

                        "tasso",

                        ""

                    )

                )

                if chiave not in index:

                    index[chiave] = []

                index[chiave].append(

                    rule

                )

        return index