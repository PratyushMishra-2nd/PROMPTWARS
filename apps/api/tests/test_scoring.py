"""Risk scoring formula + rulebook tests."""
from app import scoring


def test_label_buckets():
    assert scoring.label_for(10) == "Low"
    assert scoring.label_for(24) == "Low"
    assert scoring.label_for(25) == "Medium"
    assert scoring.label_for(49) == "Medium"
    assert scoring.label_for(50) == "High"
    assert scoring.label_for(74) == "High"
    assert scoring.label_for(75) == "Critical"
    assert scoring.label_for(100) == "Critical"


def test_final_score_components():
    r = scoring.final_score(llm_severity=80, rule_mod=20, benchmark_div=0.5)
    assert r["value"] == round(0.55 * 80 + 0.25 * 50 + 0.20 * 20, 1)
    assert r["components"] == {"llm": 80.0, "rule": 20.0, "benchmark": 50.0}


def test_final_score_no_benchmark():
    r = scoring.final_score(llm_severity=60, rule_mod=10, benchmark_div=None)
    assert r["components"]["benchmark"] == 0.0
    assert 0 <= r["value"] <= 100


def test_final_score_clamps():
    r = scoring.final_score(llm_severity=200, rule_mod=200, benchmark_div=2.0)
    assert r["value"] == 100.0
    r2 = scoring.final_score(llm_severity=-50, rule_mod=-50, benchmark_div=-1.0)
    assert r2["value"] == 0.0


def test_document_score_empty():
    assert scoring.document_score([]) == (0.0, "Low")


def test_document_score_critical_dominates():
    # one Critical clause cannot be diluted by many Lows — should stay at least High
    score, label = scoring.document_score([90, 5, 5, 5, 5, 5])
    assert label in ("High", "Critical")
    assert score >= 50


def test_document_score_all_critical():
    score, label = scoring.document_score([90, 85, 80, 75, 75])
    assert label == "Critical"


def test_rule_modifier_returns_zero_on_unknown_type():
    mod, reasons = scoring.rule_modifier("nonexistent_type", "any text", "employee")
    assert mod == 0.0
    assert reasons == []
