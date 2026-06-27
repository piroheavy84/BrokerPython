from config.bank_memory_service import BankMemoryService


class BankEligibilityService:

    def __init__(self):

        self.memory_service = BankMemoryService()

    def _downgrade_to_yellow(
        self,
        semaforo
    ):

        if semaforo == "ROSSO":

            return "ROSSO"

        return "GIALLO"

    def _add_warning(
        self,
        warnings,
        message
    ):

        if message not in warnings:

            warnings.append(
                message
            )

    def _add_exclusion(
        self,
        motivi_esclusione,
        message
    ):

        if message not in motivi_esclusione:

            motivi_esclusione.append(
                message
            )

    def _has_rows(
        self,
        memory,
        key
    ):

        return len(
            memory.get(
                key,
                []
            )
        ) > 0

    def evaluate(
        self,
        banca,
        practice_data
    ):

        memory = self.memory_service.load_bank_memory(
            banca
        )

        warnings = []

        motivi_esclusione = []

        score = 100

        semaforo = "VERDE"

        eta_cliente = practice_data.get(
            "eta_cliente",
            None
        )

        durata = practice_data.get(
            "durata",
            0
        )

        ltv = practice_data.get(
            "ltv",
            0
        )

        finalita = str(
            practice_data.get(
                "finalita",
                ""
            )
        ).upper()

        classe_energetica = str(
            practice_data.get(
                "classe_energetica",
                ""
            )
        ).upper()

        is_autonomo = practice_data.get(
            "autonomo",
            False
        )

        is_dipendente = practice_data.get(
            "dipendente",
            False
        )

        is_pensionato = practice_data.get(
            "pensionato",
            False
        )

        redditi_esteri = practice_data.get(
            "redditi_esteri",
            False
        )

        ha_garante = practice_data.get(
            "garante",
            False
        )

        ha_coobbligato = practice_data.get(
            "coobbligato",
            False
        )

        eta_massima = memory.get(
            "eta_massima",
            None
        )

        if eta_cliente is not None and eta_massima is not None:

            eta_scadenza = eta_cliente + durata

            if eta_scadenza > eta_massima:

                semaforo = "ROSSO"

                message = (
                    f"Età a scadenza {eta_scadenza} superiore al limite banca {eta_massima}"
                )

                self._add_warning(
                    warnings,
                    message
                )

                self._add_exclusion(
                    motivi_esclusione,
                    message
                )

                score -= 40

        elif eta_cliente is not None and eta_massima is None:

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Limite età non presente nella memoria banca"
            )

            score -= 5

        ltv_massimo = memory.get(
            "ltv_massimo",
            None
        )

        if ltv_massimo is not None and ltv > ltv_massimo:

            semaforo = "ROSSO"

            message = (
                f"LTV {ltv:.2f}% superiore al limite banca {ltv_massimo}%"
            )

            self._add_warning(
                warnings,
                message
            )

            self._add_exclusion(
                motivi_esclusione,
                message
            )

            score -= 50

        elif ltv_massimo is None:

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Limite LTV non presente nella memoria banca"
            )

            score -= 5

        if finalita == "SURROGA" and memory.get(
            "surroga",
            True
        ) is False:

            semaforo = "ROSSO"

            message = "Surroga non ammessa"

            self._add_warning(
                warnings,
                message
            )

            self._add_exclusion(
                motivi_esclusione,
                message
            )

            score -= 35

        if finalita == "LIQUIDITA" and memory.get(
            "liquidita",
            True
        ) is False:

            semaforo = "ROSSO"

            message = "Liquidità non ammessa"

            self._add_warning(
                warnings,
                message
            )

            self._add_exclusion(
                motivi_esclusione,
                message
            )

            score -= 35

        if finalita == "CONSOLIDAMENTO" and memory.get(
            "consolidamento",
            True
        ) is False:

            semaforo = "ROSSO"

            message = "Consolidamento non ammesso"

            self._add_warning(
                warnings,
                message
            )

            self._add_exclusion(
                motivi_esclusione,
                message
            )

            score -= 35

        if is_autonomo and not self._has_rows(
            memory,
            "autonomi"
        ):

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Nessuna regola per autonomi confermata"
            )

            score -= 15

        if is_dipendente and not self._has_rows(
            memory,
            "dipendenti"
        ):

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Nessuna regola per dipendenti confermata"
            )

            score -= 5

        if is_pensionato and not self._has_rows(
            memory,
            "pensionati"
        ):

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Nessuna regola per pensionati confermata"
            )

            score -= 10

        if redditi_esteri and not self._has_rows(
            memory,
            "redditi_esteri"
        ):

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Nessuna regola redditi esteri confermata"
            )

            score -= 20

        if ha_garante and not self._has_rows(
            memory,
            "garanti"
        ):

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Nessuna regola garante confermata"
            )

            score -= 10

        if ha_coobbligato and not self._has_rows(
            memory,
            "coobbligati"
        ):

            semaforo = self._downgrade_to_yellow(
                semaforo
            )

            self._add_warning(
                warnings,
                "Nessuna regola coobbligato confermata"
            )

            score -= 10

        if classe_energetica in [
            "A4",
            "A3",
            "A2",
            "A1",
            "B"
        ]:

            if not self._has_rows(
                memory,
                "classe_energetica"
            ):

                semaforo = self._downgrade_to_yellow(
                    semaforo
                )

                self._add_warning(
                    warnings,
                    "Classe energetica green non confermata"
                )

                score -= 10

        if not self._has_rows(
            memory,
            "polizze"
        ):

            self._add_warning(
                warnings,
                "Nessuna informazione polizze presente"
            )

            score -= 3

        if not self._has_rows(
            memory,
            "istruttoria"
        ):

            self._add_warning(
                warnings,
                "Nessuna informazione istruttoria presente"
            )

            score -= 2

        if not self._has_rows(
            memory,
            "perizia"
        ):

            self._add_warning(
                warnings,
                "Nessuna informazione perizia presente"
            )

            score -= 2

        if self._has_rows(
            memory,
            "deroghe"
        ):

            self._add_warning(
                warnings,
                f"{len(memory.get('deroghe', []))} deroghe disponibili"
            )

            score += 3

        if score < 0:

            score = 0

        if score > 100:

            score = 100

        if semaforo == "ROSSO":

            score = min(
                score,
                49
            )

        if semaforo == "GIALLO":

            score = min(
                score,
                79
            )

        return {
            "semaforo": semaforo,
            "score": score,
            "warnings": warnings,
            "motivi_esclusione": motivi_esclusione,
            "memory_used": memory
        }