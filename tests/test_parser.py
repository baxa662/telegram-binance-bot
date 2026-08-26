from app.signal_parser import parse_signal


ICP = """
CryptoFrancoARG | Señales GRATIS:
🟢 $ICP – LONG
🟢 Entrada: 2.2766 – 2.2780
🎯 TP1: 2.2864
🎯 TP2: 2.2919
🎯 TP3: 2.3012
🔴 SL: 2.2669
⚡ Apalancamiento: x15 (Margen Aislado)
"""

ETH = """
Estoy mirando un short en $ETH con x10 de apalancamiento (Margen Aislado)
Mi entrada: 2273.9 – 2276.4
🎯 TP1: 2258.0
🎯 TP2: 2244.3
🎯 TP3: 2223.9
🔴 SL: 2294.1
"""


def test_icp():
    s = parse_signal(ICP)
    assert s is not None
    assert s.symbol == "ICPUSDT"
    assert s.direction == "LONG"
    assert s.leverage == 15


def test_eth():
    s = parse_signal(ETH)
    assert s is not None
    assert s.symbol == "ETHUSDT"
    assert s.direction == "SHORT"
    assert s.stop_loss == 2294.1
