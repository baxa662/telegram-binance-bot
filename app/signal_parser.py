import re
from typing import Optional


def _normalize_text(text: str) -> str:
    return (
        text.replace("–", "-")
        .replace("—", "-")
        .replace("\u00a0", " ")
        .strip()
    )


def _extract_symbol(text: str) -> Optional[str]:
    patterns = [
        r"\$([A-Z0-9]{2,15})\s*-\s*(?:LONG|SHORT)",
        r"(?:long|short)\s+en\s+\$([A-Z0-9]{2,15})",
        r"\$([A-Z0-9]{2,15})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).upper()

    return None


def _extract_direction(text: str) -> Optional[str]:
    if re.search(r"\bLONG\b", text, re.IGNORECASE):
        return "LONG"

    if re.search(r"\bSHORT\b", text, re.IGNORECASE):
        return "SHORT"

    return None


def _extract_entry(text: str):
    patterns = [
        r"(?:Entrada|Mi entrada)\s*:\s*([\d.]+)\s*-\s*([\d.]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value_1 = float(match.group(1))
            value_2 = float(match.group(2))

            return (
                min(value_1, value_2),
                max(value_1, value_2)
            )

    return None


def _extract_take_profits(text: str):
    matches = re.findall(
        r"TP\d+\s*:\s*([\d.]+)",
        text,
        re.IGNORECASE
    )

    return [float(value) for value in matches]


def _extract_stop_loss(text: str) -> Optional[float]:
    match = re.search(
        r"\bSL\s*:\s*([\d.]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return float(match.group(1))

    return None


def _extract_leverage(text: str) -> Optional[int]:
    patterns = [
        r"Apalancamiento\s*:\s*x(\d+)",
        r"con\s+x(\d+)\s+de\s+apalancamiento",
        r"\bx(\d+)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return int(match.group(1))

    return None


def _extract_margin_type(text: str) -> str:
    if re.search(
        r"Margen\s+Aislado",
        text,
        re.IGNORECASE
    ):
        return "ISOLATED"

    if re.search(
        r"Margen\s+Cruzado",
        text,
        re.IGNORECASE
    ):
        return "CROSSED"

    return "UNKNOWN"


def _validate_signal(signal: dict) -> bool:
    required_fields = [
        signal["symbol"],
        signal["direction"],
        signal["entry_min"],
        signal["entry_max"],
        signal["take_profits"],
        signal["stop_loss"],
        signal["leverage"],
    ]

    if not all(required_fields):
        return False

    if signal["direction"] == "LONG":
        if signal["stop_loss"] >= signal["entry_min"]:
            return False

    if signal["direction"] == "SHORT":
        if signal["stop_loss"] <= signal["entry_max"]:
            return False

    return True


def parse_signal(text: str) -> Optional[dict]:
    text = _normalize_text(text)

    entry = _extract_entry(text)

    if entry is None:
        return None

    signal = {
        "symbol": _extract_symbol(text),
        "direction": _extract_direction(text),
        "entry_min": entry[0],
        "entry_max": entry[1],
        "take_profits": _extract_take_profits(text),
        "stop_loss": _extract_stop_loss(text),
        "leverage": _extract_leverage(text),
        "margin_type": _extract_margin_type(text),
    }

    if not _validate_signal(signal):
        return None

    signal["symbol"] = f'{signal["symbol"]}USDT'

    return signal