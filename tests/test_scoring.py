from rfp.services.scoring_service import calculate_absolute_score


def test_weighted_score_is_0_to_100_scale():
    criteria = [
        {"criterion_id": 1, "weight": 60, "max_score": 10},
        {"criterion_id": 2, "weight": 40, "max_score": 10},
    ]
    scores = [{"criterion_id": 1, "score": 8}, {"criterion_id": 2, "score": 5}]
    assert calculate_absolute_score(scores, criteria) == 68.0


def test_weighted_score_rejects_invalid_active_total():
    criteria = [{"criterion_id": 1, "weight": 50, "max_score": 10}]
    try:
        calculate_absolute_score([], criteria)
    except ValueError as exc:
        assert "100%" in str(exc)
    else:
        raise AssertionError("Expected invalid weight total to fail")
