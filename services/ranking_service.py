class RankingService:

    def score(self, prodotto):

        score = 0

        # -------------------
        # Listino
        # -------------------

        if prodotto.tipo_listino == "IN CORSO":

            score += 100

        elif prodotto.tipo_listino == "MAGAZZINO":

            score += 50

        # -------------------
        # Spread
        # -------------------

        spread = float(

            prodotto.spread

            .replace("%", "")

            .replace(",", ".")

        )

        score += int(

            (1 - spread) * 100

        )

        # -------------------
        # LTV
        # -------------------

        if prodotto.ltv == 70:

            score += 10

        elif prodotto.ltv == 80:

            score += 5

        return score

    def sort(self, risultati):

        risultati.sort(

            key=lambda x:

                self.score(x),

            reverse=True

        )

        return risultati