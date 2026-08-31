from __future__ import annotations

import re
from typing import Optional

try:
    from app.models import Signal
except ModuleNotFoundError:  # pragma: no cover - compatibility for direct script execution
    from models import Signal


def _normalize_text(text: str) -> str:
    return (
        text.replace("**", "")
        .replace("•", "")
        .replace("–", "-")
        .replace("—", "-")
        .replace("\u00a0", " ")
        .replace(",", ".")
        .replace("/ USDT", " USDT")
        .strip()
    )


def _extract_symbol(text: str) -> Optional[str]:
    patterns = [
        r"\$([A-Z0-9]{2,15})\s*(?:/\s*USDT|\s*-\s*(?:LONG|SHORT)|\s*\(.*?\))",
        r"\$([A-Z0-9]{2,15})\s*-\s*(?:LONG|SHORT)",
        r"(?:long|short)\s+en\s+\$([A-Z0-9]{2,15})",
        r"\$([A-Z0-9]{2,15})\s*/\s*USDT",
        r"\$([A-Z0-9]{2,15})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            symbol = match.group(1).upper()
            return symbol if symbol.endswith("USDT") else f"{symbol}USDT"
    return None


def _extract_direction(text: str) -> Optional[str]:
    if re.search(r"\bLONG\b", text, re.IGNORECASE):
        return "LONG"
    if re.search(r"\bSHORT\b", text, re.IGNORECASE):
        return "SHORT"
    return None


def _extract_entry(text: str) -> Optional[tuple[float, float]]:
    patterns = [
        r"(?:Entrada|Mi entrada|Entrada\s*\([^)]*\))\s*:\s*([\d.]+)\s*-\s*([\d.]+)",
        r"(?:Entrada|Mi entrada|Entrada\s*\([^)]*\))\s*:\s*([\d.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        a = float(match.group(1))
        b = float(match.group(2)) if match.lastindex and match.lastindex >= 2 else a
        return min(a, b), max(a, b)
    return None


def _extract_take_profits(text: str) -> list[float]:
    pairs = re.findall(r"TP\s*(\d+)\s*(?:\([^)]*\))?\s*:\s*([\d.]+)", text, re.IGNORECASE)
    pairs.sort(key=lambda item: int(item[0]))
    return [float(value) for _, value in pairs]


def _extract_stop_loss(text: str) -> Optional[float]:
    match = re.search(r"\b(?:SL|Stop\s+Loss)\s*(?:\*\*)?\s*:\s*([\d.]+)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _extract_leverage(text: str) -> Optional[int]:
    patterns = [
        r"Apalancamiento\s*:\s*x\s*(\d+)",
        r"con\s+x\s*(\d+)\s+de\s+apalancamiento",
        r"\bx\s*(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 3


def _extract_margin_type(text: str) -> str:
    if re.search(r"Margen\s+Aislado", text, re.IGNORECASE):
        return "ISOLATED"
    if re.search(r"Margen\s+Cruzado", text, re.IGNORECASE):
        return "CROSSED"
    return "ISOLATED"


def _validate(signal: Signal) -> bool:
    if not signal.symbol or not signal.direction:
        return False
    if not signal.take_profits or signal.stop_loss <= 0 or signal.leverage <= 0:
        return False
    if signal.entry_min <= 0 or signal.entry_max <= 0:
        return False
    if signal.direction == "LONG":
        if signal.stop_loss >= signal.entry_min:
            return False
        if any(tp <= signal.entry_min for tp in signal.take_profits):
            return False
    if signal.direction == "SHORT":
        if signal.stop_loss <= signal.entry_max:
            return False
        if any(tp >= signal.entry_max for tp in signal.take_profits):
            return False
    return True


def parse_signal(text: str) -> Optional[Signal]:
    text = _normalize_text(text)
    entry = _extract_entry(text)
    if entry is None:
        return None

    symbol = _extract_symbol(text)
    direction = _extract_direction(text)
    stop_loss = _extract_stop_loss(text)
    leverage = _extract_leverage(text)
    tps = _extract_take_profits(text)
    if not all([symbol, direction, stop_loss]) or not tps:
        return None
    if leverage <= 0:
        leverage = 1

    signal = Signal(
        symbol=symbol,
        direction=direction,
        entry_min=entry[0],
        entry_max=entry[1],
        take_profits=tps,
        stop_loss=stop_loss,
        leverage=leverage,
        margin_type=_extract_margin_type(text),
    )
    return signal if _validate(signal) else None
