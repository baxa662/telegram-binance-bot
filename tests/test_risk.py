from app.models import Signal
from app.risk_manager import calculate_trade_plan


def test_risk_plan():
    s = Signal("ICPUSDT", "LONG", 2.2766, 2.2780, [2.2864, 2.2919, 2.3012], 2.2669, 15)
    plan = calculate_trade_plan(s, 1000, 1.0, 15, 25.0)
    assert plan.quantity > 0
    assert plan.margin_required <= 250.0001


def test_plan_uses_max_margin_when_risk_limit_is_ignored():
    s = Signal("ICPUSDT", "LONG", 2.2766, 2.2780, [2.2864, 2.2919, 2.3012], 2.2669, 15)
    plan = calculate_trade_plan(s, 1000, 1.0, 15, 15.0, ignore_risk_percent=True)
    assert plan.margin_required == 150.0
