from rfp.services.ranking_service import rank_suppliers


def test_ranking_uses_ppi_then_date_then_experience_then_name():
    suppliers = [
        {"supplier_name": "Zeta", "ppi": 95, "submission_date": "2026-10-02", "experience_rating": 8},
        {"supplier_name": "Beta", "ppi": 95, "submission_date": "2026-10-01", "experience_rating": 5},
        {"supplier_name": "Alpha", "ppi": 95, "submission_date": "2026-10-01", "experience_rating": 9},
        {"supplier_name": "Gamma", "ppi": 95, "submission_date": "2026-10-01", "experience_rating": 9},
    ]
    ranked = rank_suppliers(suppliers)
    assert [x["supplier_name"] for x in ranked] == ["Alpha", "Gamma", "Beta", "Zeta"]
    assert [x["rank"] for x in ranked] == [1, 2, 3, 4]
