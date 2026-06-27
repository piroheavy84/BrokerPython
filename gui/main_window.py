import tkinter as tk
from tkinter import ttk


class MainWindow:

    def __init__(self):

        self.root = tk.Tk()

        self.root.title("Kiron Broker Engine")

        self.root.geometry("1400x800")

        self.build_ui()

    def build_ui(self):

        titolo = tk.Label(

            self.root,

            text="KIRON BROKER ENGINE",

            font=("Arial", 20, "bold")

        )

        titolo.pack(pady=10)

        container = tk.Frame(self.root)

        container.pack(

            fill="both",

            expand=True,

            padx=20,

            pady=20

        )

        # -------------------------

        left = tk.Frame(container)

        left.pack(

            side="left",

            fill="y",

            padx=10

        )

        # -------------------------

        right = tk.Frame(container)

        right.pack(

            side="right",

            fill="both",

            expand=True,

            padx=10

        )

        # =====================================

        tk.Label(

            left,

            text="DATI MUTUO",

            font=("Arial", 14, "bold")

        ).pack(anchor="w", pady=10)

        # =====================================

        tk.Label(left, text="Finalità").pack(anchor="w")

        self.finalita = ttk.Combobox(

            left,

            values=[

                "ACQUISTO",

                "SURROGA",

                "LIQUIDITA"

            ],

            width=25

        )

        self.finalita.pack()

        # =====================================

        tk.Label(left, text="Tasso").pack(anchor="w")

        self.tasso = ttk.Combobox(

            left,

            values=[

                "FISSO",

                "VARIABILE",

                "RATA PROTETTA"

            ],

            width=25

        )

        self.tasso.pack()

        # =====================================

        tk.Label(left, text="Durata").pack(anchor="w")

        self.durata = tk.Entry(left)

        self.durata.pack()

        # =====================================

        tk.Label(left, text="Importo mutuo").pack(anchor="w")

        self.importo = tk.Entry(left)

        self.importo.pack()

        # =====================================

        tk.Label(left, text="Valore immobile").pack(anchor="w")

        self.valore = tk.Entry(left)

        self.valore.pack()

        # =====================================

        cerca = tk.Button(

            left,

            text="CERCA",

            width=20

        )

        cerca.pack(

            pady=30

        )

        # =====================================

        tk.Label(

            right,

            text="RISULTATI",

            font=("Arial", 14, "bold")

        ).pack(anchor="w")

        self.result = tk.Text(

            right,

            height=35,

            width=90

        )

        self.result.pack(

            fill="both",

            expand=True

        )

    def run(self):

        self.root.mainloop()


if __name__ == "__main__":

    app = MainWindow()

    app.run()