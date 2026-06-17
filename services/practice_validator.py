class PracticeValidator:

    def validate(

        self,

        practice

    ):

        errors = []

        if practice.customer.eta < 18:

            errors.append(

                "Cliente minorenne"

            )

        if practice.property.valore <= 0:

            errors.append(

                "Valore immobile non valido"

            )

        if practice.mortgage.importo <= 0:

            errors.append(

                "Importo mutuo non valido"

            )

        return errors