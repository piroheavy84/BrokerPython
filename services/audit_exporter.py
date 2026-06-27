import os


class AuditExporter:

    def save(

        self,

        pagina,

        blocchi,

        rules

    ):

        os.makedirs(

            "audit",

            exist_ok=True

        )

        filename = f"audit/pagina_{pagina}.txt"

        with open(

            filename,

            "w",

            encoding="utf-8"

        ) as f:

            f.write("\n")

            f.write("====================================\n")

            f.write(

                f"PAGINA {pagina}\n"

            )

            f.write("====================================\n\n")

            f.write(

                f"Blocchi letti: {len(blocchi)}\n"

            )

            f.write(

                f"Regole create: {len(rules)}\n\n"

            )

            f.write("------------------------------------\n")

            f.write("BLOCCHI\n")

            f.write("------------------------------------\n\n")

            for i, blocco in enumerate(

                blocchi,

                start=1

            ):

                f.write(

                    f"\nBLOCCO {i}\n\n"

                )

                for riga in blocco:

                    f.write(

                        riga + "\n"

                    )

            f.write("\n")

            f.write("------------------------------------\n")

            f.write("REGOLE\n")

            f.write("------------------------------------\n\n")

            for rule in rules:

                f.write(

                    str(rule)

                )

                f.write("\n\n")