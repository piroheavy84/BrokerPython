import json
import os


class JsonDatabase:

    def save(self, rules, filename):

        os.makedirs("output", exist_ok=True)

        with open(

            filename,

            "w",

            encoding="utf-8"

        ) as f:

            json.dump(

                rules,

                f,

                indent=4,

                ensure_ascii=False

            )

        return len(rules)