class AuditEngine:

    def audit_page(

        self,

        pagina,

        blocchi,

        rules

    ):

        print()

        print("====================================")

        print(

            "AUDIT PAGINA",

            pagina

        )

        print("====================================")

        print()

        print(

            "Blocchi letti:",

            len(blocchi)

        )

        print(

            "Regole create:",

            len(rules)

        )

        print()

        print("------------------------------------")

        print("BLOCCHI")

        print("------------------------------------")

        print()

        for i, blocco in enumerate(

            blocchi,

            start=1

        ):

            print()

            print(

                "BLOCCO",

                i

            )

            print()

            for riga in blocco:

                print(riga)

        print()

        print("------------------------------------")

        print("FINE AUDIT")

        print("------------------------------------")