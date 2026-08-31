# Telegram -> Binance USD-M Futures Bot

Bot Python para Coolify que:

- Lee un canal de Telegram usando tu sesion de usuario (Telethon).
- Parsea señales LONG/SHORT como los ejemplos de CryptoFrancoARG.
- Modos: `MONITOR`, `PAPER`, `TESTNET`, `PRODUCTION`.
- Espera a que el mark price toque el rango de entrada antes de abrir.
- Calcula cantidad por riesgo, con limite de margen y leverage.
- Configura margen aislado y leverage.
- En TESTNET/PRODUCTION abre MARKET, coloca SL y TPs parciales.
- Mueve SL a break-even despues de TP1 y a TP1 despues de TP2.
- Guarda estado en SQLite para sobrevivir redeploys.
- Comandos Telegram: `/help`, `/status`, `/balance`, `/positions`, `/signals`, `/lastsignal`, `/trades`, `/pause`, `/resume`, `/exec_signal`, `/breakeven SYMBOL`, `/close SYMBOL`, `/cancel`.

## 1. Coolify

Usa Dockerfile. Monta almacenamiento persistente:

- Source: el path/volume que prefieras en tu host.
- Destination: `/app/data`

No necesitas dominio para este worker.

## 2. Variables de entorno

Copia `.env.example` a las Environment Variables de Coolify.

### Telegram

- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`: my.telegram.org/apps.
- `TELEGRAM_SOURCE_CHANNEL_ID`: ID del canal que lees.
- `TELEGRAM_BOT_TOKEN`: bot creado con BotFather.
- `TELEGRAM_ADMIN_CHAT_ID`: tu chat ID privado.

### Sesion Telethon

Desde la terminal del contenedor:

```bash
python /app/scripts/create_telegram_session.py
```

La sesion se guarda como `/app/data/telegram.session`.

## 3. Modos

### MONITOR

```env
TRADING_MODE=MONITOR
```

Solo lee, parsea, guarda y notifica. No crea trades.

### PAPER

```env
TRADING_MODE=PAPER
```

Crea trades virtuales y usa el mark price real para simular TP/SL. Si no hay credenciales de Binance para leer balance, usa un balance virtual de 1000 USDT para calculo de riesgo.

### TESTNET

```env
TRADING_MODE=TESTNET
BINANCE_TESTNET_API_KEY=...
BINANCE_TESTNET_API_SECRET=...
```

Envia ordenes reales al entorno Binance USD-M Futures Testnet (`https://testnet.binancefuture.com`), sin fondos reales.

### PRODUCTION

Por seguridad, elegir `PRODUCTION` no basta. Se requieren ambas variables:

```env
TRADING_MODE=PRODUCTION
ENABLE_PRODUCTION_TRADING=true
PRODUCTION_CONFIRMATION=I_UNDERSTAND_LIVE_TRADING
```

Sin esas dos, el bot arranca pero bloquea cualquier orden live.

## 4. API key Binance

Para produccion:

- habilita Futures en la API key;
- no habilites retiros;
- usa whitelist de IP si tu IP de salida es estable;
- prueba antes con TESTNET.

## 5. Flujo de entrada

El bot usa `ENTRY_STRATEGY=MARKET_IF_IN_RANGE`.

Cuando recibe una señal, crea `PENDING_ENTRY`. Cada pocos segundos consulta mark price. Solo abre cuando el precio esta dentro del rango (con tolerancia configurable). Si no toca el rango antes de `SIGNAL_EXPIRY_MINUTES`, expira.

Para cargar una señal manualmente desde el chat administrador, envia `/exec_signal` y, cuando el bot lo solicite, pega el texto completo. Se usa el mismo parser y flujo de ejecucion que para las señales del canal. Si el formato no es valido puedes corregirlo y reenviarlo, o salir con `/cancel`.

## 6. Riesgo

```env
RISK_PERCENT=1.0
MAX_LEVERAGE=15
MAX_MARGIN_PERCENT=25
MAX_OPEN_TRADES=3
```

La cantidad se limita por:

1. riesgo hasta SL;
2. margen maximo permitido.

Se usa el menor de ambos tamaños.

## 7. Take profits y SL

Por defecto:

```env
TP_ALLOCATIONS=0.33,0.33,0.34
MOVE_SL_TO_BREAKEVEN_AFTER_TP1=true
MOVE_SL_TO_TP1_AFTER_TP2=true
```

Para Binance, los TPs usan `TAKE_PROFIT_MARKET` reduce-only. El SL usa `STOP_MARKET` con `closePosition=true`.

## 8. Deploy

```bash
git add .
git commit -m "complete trading bot"
git push
```

Coolify construye el Dockerfile y ejecuta `python main.py`.

## 9. Verificacion recomendada

Orden recomendado:

1. `MONITOR` por unas horas/dias.
2. `PAPER` y comparar señales vs ejecuciones virtuales.
3. `TESTNET` y verificar ordenes/TP/SL/movimientos.
4. `PRODUCTION` solo despues de revisar logs y con riesgo pequeno.

## Notas importantes

- El proyecto asume Binance USD-M Futures en **One-way Mode**. No esta diseñado para Hedge Mode.
- Una API key de TESTNET es distinta de la de produccion.
- Si el proveedor de señales cambia el formato, actualiza `app/signal_parser.py` y sus tests.
- No subas `.env`, `telegram.session` ni API secrets a Git.
- Un bot automatico puede ejecutar operaciones incorrectas por cambios de formato, retrasos, API errors, liquidez o slippage. TESTNET/PAPER no garantizan el mismo comportamiento que produccion.
