import pytest
from datetime import datetime, timedelta
from backend.priority_classifier import PriorityClassifierTool

def test_priority_classifier_keywords():
    classifier = PriorityClassifierTool()

    # Urgent keyword
    res1 = classifier.classify("URGENT: confirm catering with caterer immediately")
    assert res1["priority"] == "Urgent"
    assert res1["score"] >= 75

    # Low priority keyword
    res2 = classifier.classify("Optional nice to have attendee stickers")
    assert res2["priority"] == "Low"
    assert res2["score"] <= 35

def test_priority_classifier_domain_impact():
    classifier = PriorityClassifierTool()

    # Safety critical allergy
    res = classifier.classify("Verify nut-free food boxes for severe airborne peanut allergy", category="Catering")
    assert res["priority"] in ["High", "Urgent"]
    assert "dietary/allergy compliance" in res["reason"]

    # Technical AV equipment
    res_av = classifier.classify("Perform dual 4K projector dry run in room 302", category="Venue & AV")
    assert res_av["priority"] in ["High", "Urgent"]

def test_priority_classifier_deadline_proximity():
    classifier = PriorityClassifierTool()
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    res = classifier.classify("Order supplies", due_date_str=tomorrow_str)
    assert res["score"] > 50

if __name__ == "__main__":
    pytest.main(["-v", __file__])
