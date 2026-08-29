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

APT = """
SEÑAL VIP
$ALGO - LONG 📈

Plan de Comercio:
• Entrada: 0.091961 – 0.092290
• Stop Loss: 0.089824

Take Profits:
• TP1: 0.093934
• TP2: 0.095250
• TP3: 0.097223

Apalancamiento sugerido: x5 (Margen Aislado)

Justificación:
La estructura de 1h mantiene un sesgo claramente alcista, con el precio operando por encima de la MA99 (0.092601), lo que valida la tendencia de fondo y respalda la continuidad del movimiento.
El RSI en 1h (~47.8) se encuentra por debajo de niveles de sobrecompra, lo que deja margen para una nueva extensión alcista antes de que aparezca una presión bajista significativa.
La zona de entrada entre 0.091961 y 0.092290 coincide con un área técnica donde los compradores siguen defendiendo el precio, ofreciendo una relación riesgo/beneficio favorable con Stop Loss bien definido en 0.089824.
La volatilidad medida por el ATR (~0.001644) muestra un mercado activo en 1h, aumentando las probabilidades de que el precio alcance los objetivos si el impulso alcista se mantiene.
TP1 busca capturar el primer movimiento hacia 0.093934, mientras que TP2 y TP3 apuntan a una extensión de la tendencia hacia 0.095250 y 0.097223, permitiendo gestionar la posición de forma escalonada.

⚠️ Mientras el precio permanezca por encima de 0.089824, el escenario LONG continúa siendo válido.

Sesgo: Alcista con potencial de continuidad si se mantiene el soporte de la zona de entrada.

This message was sent automatically with n8n
"""

MAGMA_SHORT = """
**Setup short — $MAGMA / USDT (15m)**

** • Entrada (limit sell):** 0,5300 – 0,5350
Zona de reintento hacia el máximo reciente (0,53883).
** • Stop Loss:** 0,5500
Por encima del máximo local, con margen amplio dado lo errático que viene siendo este token.
** • TP1 (parcial ~40-50%):** 0,50470
Zona de la MA(7), casi coincidente con la MA(99) (0,50302) — doble soporte ahí.
** • TP2:** 0,47354
MA(25).
** • TP3 (runner):** 0,41137
Mínimo del ciclo reciente, si hay reversión más profunda.

**R/B:** con entrada en 0,5320 y SL en 0,5500, riesgo ~0,013 contra ~0,027 hasta TP1 → aprox 1:2, razonable.
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


def test_apt_with_expanded_stop_loss_label():
    s = parse_signal(APT)
    assert s is not None
    assert s.symbol == "ALGOUSDT"
    assert s.direction == "LONG"
    assert (s.entry_min, s.entry_max) == (0.091961, 0.092290)
    assert s.stop_loss == 0.089824
    assert s.take_profits == [0.093934, 0.095250, 0.097223]
    assert s.leverage == 5
    assert s.margin_type == "ISOLATED"


def test_magma_short_setup():
    s = parse_signal(MAGMA_SHORT)
    assert s is not None
    assert s.symbol == "MAGMAUSDT"
    assert s.direction == "SHORT"
    assert (s.entry_min, s.entry_max) == (0.5300, 0.5350)
    assert s.stop_loss == 0.5500
    assert s.take_profits == [0.50470, 0.47354, 0.41137]
    assert s.leverage == 1
