import pytest
from datetime import datetime, timedelta
from backend.date_parser import DateParserTool

def test_workshop_relative_offset():
    fixed_workshop_date = datetime(2026, 11, 10, 9, 0)
    parser = DateParserTool(target_workshop_date=fixed_workshop_date)

    # Test "3 days before workshop"
    res1 = parser.parse("finalize headcount 3 days before workshop")
    assert "2026-11-07" in res1["date"]
    assert res1["source"] == "workshop_milestone_offset"

    # Test "48 hours prior"
    res2 = parser.parse("run AV test 48 hours prior")
    assert "2026-11-08" in res2["date"]

    # Test "T-5 days"
    res3 = parser.parse("send prerequisite email T-5 days")
    assert "2026-11-05" in res3["date"]

def test_natural_language_dates():
    parser = DateParserTool()
    
    # Test "tomorrow"
    res = parser.parse("review the slide deck tomorrow at 5pm")
    assert res["formatted"] is not None
    assert "Tomorrow" in res["relative"] or "Today" in res["relative"]

    # Test "in 3 days"
    res2 = parser.parse("print badges in 3 days")
    assert res2["iso"] is not None

def test_contextual_fallback():
    parser = DateParserTool()
    # Catering task without explicit date should infer 3 days before workshop
    res = parser.parse("order vegan catering", context_hint="GreenLeaf Catering headcount")
    assert res["source"] == "contextual_inference"
    assert "3 business days prior" in res["reason"]

if __name__ == "__main__":
    pytest.main(["-v", __file__])
