from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Signal:
    symbol: str
    direction: str
    entry_min: float
    entry_max: float
    take_profits: List[float]
    stop_loss: float
    leverage: int
    margin_type: str = "ISOLATED"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TradePlan:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profits: List[float]
    leverage: int
    quantity: float
    risk_percent: float
    risk_amount: float
    notional: float
    margin_required: float

    def to_dict(self) -> dict:
        return asdict(self)
