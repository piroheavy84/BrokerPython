import argparse
import json

from services.import_diagnostic_service import ImportDiagnosticService


def main():
    parser = argparse.ArgumentParser(description="Riepilogo compatto import banca Kiron")
    parser.add_argument("banca", help="Nome banca, es. ING")
    args = parser.parse_args()

    result = ImportDiagnosticService().build(args.banca)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
