"""Version-compare tests."""
from app import store, compare


def _mk_clause(cid: str, ctype: str, text: str, score: float):
    return store.Clause(
        id=cid, type=ctype, text=text, page_number=1,
        risk_score=score, risk_label="High" if score >= 50 else "Low",
    )


def test_compare_detects_added_removed_changed():
    a1 = store.Analysis(
        id="a1", filename="v1", contract_type="employment", perspective="employee",
        overall_score=50, overall_label="High",
        clauses=[
            _mk_clause("c1", "non_compete", "no competing for 12 months", 50),
            _mk_clause("c2", "ip_assignment", "you assign all inventions", 60),
        ],
    )
    a2 = store.Analysis(
        id="a2", filename="v2", contract_type="employment", perspective="employee",
        overall_score=70, overall_label="High",
        clauses=[
            # non_compete changed (longer)
            _mk_clause("c1n", "non_compete", "no competing for 24 months worldwide", 80),
            # ip_assignment unchanged
            _mk_clause("c2n", "ip_assignment", "you assign all inventions", 60),
            # new clause added
            _mk_clause("c3n", "arbitration", "binding arbitration with class waiver", 70),
        ],
    )
    store.ANALYSES["a1"] = a1
    store.ANALYSES["a2"] = a2
    try:
        r = compare.compare("a1", "a2")
        assert r["summary"]["added"] == 1
        assert r["summary"]["removed"] == 0
        assert r["summary"]["changed"] >= 1
        assert r["verdict"] == "worse"
        assert r["overall_delta"] == 20.0
    finally:
        store.ANALYSES.pop("a1", None)
        store.ANALYSES.pop("a2", None)


def test_compare_missing_analysis():
    r = compare.compare("missing-a", "missing-b")
    assert r.get("error")
