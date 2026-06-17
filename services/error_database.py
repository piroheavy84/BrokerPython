import json
import os


class ErrorDatabase:

    def save(self, errors, filename):

        os.makedirs("output", exist_ok=True)

        with open(

            filename,

            "w",

            encoding="utf-8"

        ) as f:

            json.dump(

                errors,

                f,

                indent=4,

                ensure_ascii=False

            )

        return len(errors)