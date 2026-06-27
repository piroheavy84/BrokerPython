class ResultFormatter:

    def print(self, risultati):

        print()

        print("=" * 50)
        print("KIRON BROKER ENGINE")
        print("=" * 50)

        print()

        if len(risultati) == 0:

            print("Nessun prodotto trovato.")

            return

        migliore = risultati[0]

        print("🏆 MIGLIORE OFFERTA")

        print()

        print("Banca      :", migliore.banca)

        print("Listino    :", migliore.tipo_listino)

        print("Tasso      :", migliore.tasso)

        print("Durata     :", migliore.durata)

        print("LTV <=     :", migliore.ltv)

        print("Spread     :", migliore.spread)

        print("PDF        :", migliore.pdf)

        print("Pagina     :", migliore.pagina)

        print()

        print("-" * 50)

        print()

        if len(risultati) > 1:

            print("ALTRE SOLUZIONI")

            print()

            for r in risultati[1:]:

                print(

                    f"{r.banca} | "

                    f"{r.tipo_listino} | "

                    f"{r.tasso} | "

                    f"{r.spread}"

                )

            print()