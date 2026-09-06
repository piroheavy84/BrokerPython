from repositories.product_repository import ProductRepository


class _Db:
    def __init__(self, rules):
        self.rules = rules

    def get_all(self):
        return self.rules


def test_preserves_fixed_renegotiable_variants_from_legacy_dict():
    rules = [
        {"banca": "TEST", "tasso": {"tipo": "FISSO", "descrizione": "FISSO"}},
        {"banca": "TEST", "tasso": {"tipo": "FISSO", "descrizione": "FISSO 5 RINEGOZIABILE"}},
        {"banca": "TEST", "tasso": {"tipo": "FISSO", "descrizione": "FISSO 10 RINEGOZIABILE"}},
    ]
    loaded = ProductRepository(_Db(rules)).all()
    assert [r["tasso"]["tipo"] for r in loaded] == [
        "FISSO",
        "FISSO 5 RINEGOZIABILE",
        "FISSO 10 RINEGOZIABILE",
    ]


def test_structured_string_rate_is_left_unchanged():
    rules = [
        {"banca": "TEST", "tasso": "FISSO 5 RINEGOZIABILE"},
        {"banca": "TEST", "tasso": "FISSO 10 RINEGOZIABILE"},
    ]
    loaded = ProductRepository(_Db(rules)).all()
    assert [r["tasso"] for r in loaded] == [
        "FISSO 5 RINEGOZIABILE",
        "FISSO 10 RINEGOZIABILE",
    ]
