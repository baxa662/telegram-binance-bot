# Guía completa de instalación y uso — Telegram Binance Bot

Esta guía asume que vas a usar el proyecto completo que ya te pasé:

[Descargar proyecto completo](sandbox:/mnt/data/telegram-binance-bot-completo.zip)

El bot soporta estos modos:

- `MONITOR`
- `PAPER`
- `TESTNET`
- `PRODUCTION`

Y trabaja con **Binance USD-M Futures** en modo **One-way**.

---

# 1. Estructura del proyecto

Tu repositorio debe quedar así:

```text
telegram-binance-bot/
├── app/
│   ├── binance_api.py
│   ├── bot_commands.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── notifier.py
│   ├── risk_manager.py
│   ├── signal_parser.py
│   ├── telegram_reader.py
│   └── trade_engine.py
│
├── scripts/
│   ├── create_telegram_session.py
│   └── smoke_test.py
│
├── tests/
│   ├── test_parser.py
│   └── test_risk.py
│
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# 2. Dockerfile

Ruta:

```text
/Dockerfile
```

Debe quedar así:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY scripts/ /app/scripts/

RUN mkdir -p /app/data

CMD ["python", "main.py"]
```

---

# 3. requirements.txt

Ruta:

```text
/requirements.txt
```

Usa el que viene dentro del ZIP.

No necesitas instalar paquetes manualmente dentro del contenedor; Coolify los instala durante el build.

---

# 4. Crear repositorio en GitHub

Sube todo el proyecto.

Desde tu PC:

```bash
git init
git add .
git commit -m "initial telegram binance bot"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/telegram-binance-bot.git
git push -u origin main
```

No subas nunca:

```text
.env
telegram.session
bot.db
API keys
```

El `.gitignore` del proyecto ya está preparado para eso.

---

# 5. Crear aplicación en Coolify

En Coolify:

```text
Projects
→ tu proyecto
→ New Resource
→ Application
→ Git Repository with GitHub App
```

Selecciona:

```text
Repository:
telegram-binance-bot
```

Branch:

```text
main
```

Build Pack:

```text
Dockerfile
```

Base Directory:

```text
/
```

Dockerfile:

```text
/Dockerfile
```

No necesitas dominio para el bot.

Es un worker permanente, no una página web.

---

# 6. Persistent Storage

En la aplicación de Coolify entra a:

```text
Persistent Storage
```

Configura:

```text
Source:
/var/lib/coolify/telegram-binance-bot
```

Destination:

```text
/app/data
```

Puedes usar otra ruta en `Source`.

Lo importante es que el destino sea:

```text
/app/data
```

Ahí se guardarán:

```text
/app/data/bot.db
/app/data/telegram.session
```

---

# 7. Variables de entorno completas

En Coolify entra a:

```text
Environment Variables
```

Copia estas variables.

## Aplicación

```env
APP_ENV=production
LOG_LEVEL=INFO
DATABASE_PATH=/app/data/bot.db
```

---

## Modo de trading

Para empezar:

```env
TRADING_MODE=MONITOR
BOT_PAUSED=false
```

Valores disponibles:

```text
MONITOR
PAPER
TESTNET
PRODUCTION
```

---

## Seguridad para Production

Inicialmente:

```env
ENABLE_PRODUCTION_TRADING=false
PRODUCTION_CONFIRMATION=
```

Para producción real tendrás que cambiar explícitamente a:

```env
ENABLE_PRODUCTION_TRADING=true
PRODUCTION_CONFIRMATION=I_UNDERSTAND_LIVE_TRADING
```

No actives esto todavía.

---

# 8. Telegram — cuenta que lee las señales

Necesitas:

```env
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
```

Se obtienen en:

```text
my.telegram.org/apps
```

Usa la cuenta de Telegram que tiene acceso al canal de señales.

También configura:

```env
TELEGRAM_SOURCE_CHANNEL_ID=-100XXXXXXXXXX
TELEGRAM_SESSION_PATH=/app/data/telegram
```

Ejemplo:

```env
TELEGRAM_SOURCE_CHANNEL_ID=-1001234567890
```

---

# 9. Telegram — bot de control

Crea un bot con BotFather.

Necesitas:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=
```

Ejemplo:

```env
TELEGRAM_BOT_TOKEN=123456789:AAxxxxxxxxxxxxxxxx
TELEGRAM_ADMIN_CHAT_ID=5010783172
```

No compartas el token.

---

# 10. Binance Production

Configura:

```env
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

La API key debería tener:

```text
Futures habilitado
Retiros deshabilitados
Whitelist de IP si es posible
```

Tu bot enviará las solicitudes desde la IP pública del servidor donde corre Coolify.

Puedes verla desde el contenedor con:

```bash
curl -4 https://api.ipify.org
```

---

# 11. Binance Testnet

Para Testnet:

```env
BINANCE_TESTNET_API_KEY=
BINANCE_TESTNET_API_SECRET=
```

Estas claves son distintas a las de producción.

---

# 12. Configuración Binance general

```env
BINANCE_RECV_WINDOW=5000
BINANCE_TIMEOUT_SECONDS=10
```

Normalmente no necesitas modificar estos valores.

---

# 13. Configuración de riesgo

Configuración recomendada inicial:

```env
RISK_PERCENT=1.0
MAX_LEVERAGE=15
MAX_MARGIN_PERCENT=25
MAX_OPEN_TRADES=3
ALLOW_MULTIPLE_POSITIONS_PER_SYMBOL=false
```

## RISK_PERCENT

```env
RISK_PERCENT=1.0
```

Significa:

```text
Riesgar máximo 1% del balance por operación.
```

Si tienes:

```text
1000 USDT
```

el riesgo máximo aproximado hasta SL será:

```text
10 USDT
```

---

## MAX_LEVERAGE

```env
MAX_LEVERAGE=15
```

Aunque una señal diga:

```text
x25
```

el bot no usará más de:

```text
x15
```

---

## MAX_MARGIN_PERCENT

```env
MAX_MARGIN_PERCENT=25
```

Nunca utilizará más de aproximadamente el 25% del balance disponible como margen para una sola operación.

---

## MAX_OPEN_TRADES

```env
MAX_OPEN_TRADES=3
```

Máximo:

```text
3 operaciones simultáneas
```

---

## Múltiples operaciones del mismo par

Recomendado:

```env
ALLOW_MULTIPLE_POSITIONS_PER_SYMBOL=false
```

Así evita abrir:

```text
BTCUSDT LONG
BTCUSDT LONG
BTCUSDT LONG
```

por señales repetidas.

---

# 14. Configuración de entrada

```env
ENTRY_STRATEGY=MARKET_IF_IN_RANGE
SIGNAL_EXPIRY_MINUTES=120
ENTRY_RANGE_TOLERANCE_PERCENT=0.10
```

El comportamiento es:

```text
Llega señal
↓
se guarda como pendiente
↓
bot consulta precio
↓
¿precio entra al rango?
├── No → esperar
└── Sí → ejecutar
```

---

## SIGNAL_EXPIRY_MINUTES

```env
SIGNAL_EXPIRY_MINUTES=120
```

Después de 120 minutos, si nunca tocó la entrada, la señal expira.

---

# 15. Distribución de TP

Actualmente:

```env
TP_ALLOCATIONS=0.33,0.33,0.34
```

Eso significa:

```text
TP1 = 33%
TP2 = 33%
TP3 = 34%
```

Ejemplo con:

```text
100 ICP
```

resultado:

```text
TP1 → 33 ICP
TP2 → 33 ICP
TP3 → restante ≈ 34 ICP
```

Si prefieres:

```text
40% / 30% / 30%
```

usa:

```env
TP_ALLOCATIONS=0.40,0.30,0.30
```

Si prefieres:

```text
50% / 30% / 20%
```

usa:

```env
TP_ALLOCATIONS=0.50,0.30,0.20
```

Los valores deben sumar aproximadamente:

```text
1.0
```

---

# 16. Movimiento automático del Stop Loss

Configuración recomendada:

```env
MOVE_SL_TO_BREAKEVEN_AFTER_TP1=true
MOVE_SL_TO_TP1_AFTER_TP2=true
```

El comportamiento será:

```text
Entrada
↓
TP1
├── cerrar primera parte
└── mover SL → Entry / Break Even

TP2
├── cerrar segunda parte
└── mover SL → TP1

TP3
└── cerrar posición restante
```

---

# 17. Polling

```env
POSITION_POLL_SECONDS=5
PENDING_ENTRY_POLL_SECONDS=3
```

Eso significa:

```text
Cada 3 segundos:
revisar señales esperando entrada.

Cada 5 segundos:
revisar posiciones abiertas.
```

Puedes dejar estos valores.

---

# 18. Comandos manuales

```env
ALLOW_MANUAL_CLOSE=true
ALLOW_MANUAL_BREAKEVEN=true
```

Permiten usar:

```text
/close
/breakeven
```

desde Telegram.

---

# 19. Variables completas listas para copiar

Para empezar en MONITOR:

```env
APP_ENV=production
LOG_LEVEL=INFO
DATABASE_PATH=/app/data/bot.db

TRADING_MODE=MONITOR
BOT_PAUSED=false

ENABLE_PRODUCTION_TRADING=false
PRODUCTION_CONFIRMATION=

TELEGRAM_API_ID=TU_API_ID
TELEGRAM_API_HASH=TU_API_HASH
TELEGRAM_SOURCE_CHANNEL_ID=-100XXXXXXXXXX
TELEGRAM_SESSION_PATH=/app/data/telegram

TELEGRAM_BOT_TOKEN=TU_BOT_TOKEN
TELEGRAM_ADMIN_CHAT_ID=TU_CHAT_ID

BINANCE_API_KEY=TU_BINANCE_API_KEY
BINANCE_API_SECRET=TU_BINANCE_SECRET

BINANCE_TESTNET_API_KEY=
BINANCE_TESTNET_API_SECRET=

BINANCE_RECV_WINDOW=5000
BINANCE_TIMEOUT_SECONDS=10

RISK_PERCENT=1.0
MAX_LEVERAGE=15
MAX_MARGIN_PERCENT=25
MAX_OPEN_TRADES=3
ALLOW_MULTIPLE_POSITIONS_PER_SYMBOL=false

ENTRY_STRATEGY=MARKET_IF_IN_RANGE
SIGNAL_EXPIRY_MINUTES=120
ENTRY_RANGE_TOLERANCE_PERCENT=0.10

TP_ALLOCATIONS=0.33,0.33,0.34

MOVE_SL_TO_BREAKEVEN_AFTER_TP1=true
MOVE_SL_TO_TP1_AFTER_TP2=true

POSITION_POLL_SECONDS=5
PENDING_ENTRY_POLL_SECONDS=3

ALLOW_MANUAL_CLOSE=true
ALLOW_MANUAL_BREAKEVEN=true
```

---

# 20. Generar la sesión de Telegram

Después del primer deploy, entra a:

```text
Coolify
→ Application
→ Terminal
```

Ejecuta:

```bash
python /app/scripts/create_telegram_session.py
```

Telegram te pedirá:

```text
Phone number
```

ponlo con código internacional:

```text
+52XXXXXXXXXX
```

Después:

```text
Telegram code
```

y si tienes 2FA:

```text
Password
```

Al terminar debe generarse:

```text
/app/data/telegram.session
```

Comprueba:

```bash
ls -lah /app/data
```

Deberías ver:

```text
telegram.session
bot.db
```

---

# 21. Si aparece error de sesión Telethon

Si aparece:

```text
ValueError: too many values to unpack (expected 5)
```

haz backup:

```bash
mv /app/data/telegram.session /app/data/telegram.session.backup
```

Luego genera otra sesión:

```bash
python /app/scripts/create_telegram_session.py
```

No borres:

```text
bot.db
```

---

# 22. Probar la sesión de Telegram

Ejecuta:

```bash
python - <<'PY'
import asyncio
import os
from telethon import TelegramClient

async def main():
    client = TelegramClient(
        "/app/data/telegram",
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"]
    )

    await client.connect()

    print(
        "Autorizado:",
        await client.is_user_authorized()
    )

    me = await client.get_me()

    print(
        "Usuario:",
        me.username or me.first_name
    )

    await client.disconnect()

asyncio.run(main())
PY
```

Debe salir:

```text
Autorizado: True
Usuario: ...
```

---

# 23. Modo MONITOR

Usa:

```env
TRADING_MODE=MONITOR
```

En este modo:

```text
Lee Telegram ✅
Parsea señales ✅
Guarda señales ✅
Notifica ✅
Consulta Binance ✅
Abre operaciones ❌
```

Es el modo recomendado para empezar.

---

# 24. Modo PAPER

Cambia:

```env
TRADING_MODE=PAPER
```

En PAPER:

```text
Lee señal
↓
espera rango de entrada
↓
crea trade virtual
↓
consulta precio real Binance
↓
simula TP / SL
↓
simula movimiento SL
↓
notifica
```

No manda órdenes reales.

---

# 25. Modo TESTNET

Configura:

```env
TRADING_MODE=TESTNET
```

Y:

```env
BINANCE_TESTNET_API_KEY=...
BINANCE_TESTNET_API_SECRET=...
```

En este modo sí se mandan órdenes, pero a Binance Futures Testnet.

Flujo:

```text
Señal
↓
entrada
↓
orden MARKET Testnet
↓
STOP MARKET
↓
TP1
TP2
TP3
↓
gestión automática SL
```

No utiliza fondos reales.

---

# 26. Modo PRODUCTION

Solo después de probar TESTNET.

Configura:

```env
TRADING_MODE=PRODUCTION
```

Pero esto solo no habilita operaciones reales.

También necesitas:

```env
ENABLE_PRODUCTION_TRADING=true
PRODUCTION_CONFIRMATION=I_UNDERSTAND_LIVE_TRADING
```

Configuración completa:

```env
TRADING_MODE=PRODUCTION
ENABLE_PRODUCTION_TRADING=true
PRODUCTION_CONFIRMATION=I_UNDERSTAND_LIVE_TRADING
```

Si falta cualquiera de las dos últimas, las operaciones reales quedan bloqueadas.

---

# 27. Comandos disponibles en Telegram

Solo funciona desde:

```text
TELEGRAM_ADMIN_CHAT_ID
```

## Estado

```text
/status
```

Muestra:

```text
Modo
Pausado o activo
Estado de producción
Canal configurado
```

---

## Balance

```text
/balance
```

Consulta balance USDT Futures.

---

## Posiciones

```text
/positions
```

En producción/testnet:

```text
Posiciones reales Binance
```

En PAPER:

```text
Paper trades abiertos
```

---

## Última señal

```text
/lastsignal
```

---

## Últimas señales

```text
/signals
```

Muestra las últimas 5.

---

## Últimos trades

```text
/trades
```

Muestra los últimos 10.

Ejemplo:

```text
#25 [PAPER] ICPUSDT LONG - OPEN
#24 [PAPER] ETHUSDT SHORT - CLOSED
```

---

# 28. Pausar nuevas operaciones

```text
/pause
```

Importante:

```text
NO cierra operaciones existentes.
```

Solo evita nuevas entradas.

Las posiciones que ya están abiertas siguen siendo gestionadas.

---

# 29. Reanudar

```text
/resume
```

---

# 30. Mover manualmente SL a Break Even

Ejemplo:

```text
/breakeven BTCUSDT
```

Solo funciona si:

```env
ALLOW_MANUAL_BREAKEVEN=true
```

---

# 31. Cerrar manualmente una posición

Ejemplo:

```text
/close BTCUSDT
```

Solo funciona si:

```env
ALLOW_MANUAL_CLOSE=true
```

Ten cuidado con este comando en `PRODUCTION`.

---

# 32. Flujo completo de una señal

Una señal:

```text
🟢 $ICP – LONG

Entrada: 2.2766 – 2.2780

TP1: 2.2864
TP2: 2.2919
TP3: 2.3012

SL: 2.2669

Apalancamiento: x15
```

se convierte en:

```text
ICPUSDT
LONG

Entry Min:
2.2766

Entry Max:
2.2780

SL:
2.2669

TP1:
2.2864

TP2:
2.2919

TP3:
2.3012

Leverage:
15
```

Después:

```text
Señal recibida
↓
validación parser
↓
guardar SQLite
↓
comprobar operación duplicada
↓
comprobar límite posiciones
↓
comprobar símbolo
↓
consultar precio Binance
↓
esperar entrada
↓
calcular riesgo
↓
calcular cantidad
↓
normalizar stepSize/tickSize
↓
abrir operación
↓
crear SL
↓
crear TP1
↓
crear TP2
↓
crear TP3
↓
notificar
```

---

# 33. Gestión después de abrir

Ejemplo:

```text
ICPUSDT LONG
100 ICP
```

Distribución:

```text
TP1:
33 ICP

TP2:
33 ICP

TP3:
34 ICP
```

Cuando llega TP1:

```text
Cerrar 33%
↓
SL → Break Even
```

Cuando llega TP2:

```text
Cerrar 33%
↓
SL → TP1
```

Cuando llega TP3:

```text
Cerrar restante
↓
Trade terminado
```

---

# 34. Base SQLite

La base está en:

```text
/app/data/bot.db
```

Puedes comprobar tablas desde terminal:

```bash
python - <<'PY'
import sqlite3

conn = sqlite3.connect("/app/data/bot.db")

for row in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
):
    print(row)

conn.close()
PY
```

---

# 35. Ver últimas señales desde terminal

```bash
python - <<'PY'
import sqlite3

conn = sqlite3.connect("/app/data/bot.db")

for row in conn.execute(
    """
    SELECT *
    FROM signals
    ORDER BY id DESC
    LIMIT 10
    """
):
    print(row)

conn.close()
PY
```

---

# 36. Ver IP pública del bot

Desde terminal Coolify:

```bash
curl -4 https://api.ipify.org
```

Binance verá esa IP.

Si usas whitelist:

```text
Binance API Management
→ Restrict access to trusted IPs
```

agrega esa IP.

---

# 37. Logs

En Coolify:

```text
Application
→ Logs
```

Al arrancar deberías ver aproximadamente:

```text
Crypto Signal Bot iniciado
Base de datos inicializada
Bot de comandos iniciado
Telegram conectado
Escuchando canal...
```

---

# 38. Error 409 Telegram

Si ves:

```text
telegram.error.Conflict:
terminated by other getUpdates request
```

significa que hay dos procesos usando el mismo bot.

No ejecutes manualmente:

```text
getUpdates
```

mientras el bot esté corriendo.

También revisa que no tengas dos instancias del mismo bot desplegadas.

---

# 39. Error Binance -2015

Si ves:

```text
Invalid API-key, IP, or permissions for action
```

revisa:

```text
API Key correcta
API Secret correcto
Futures habilitado
IP whitelist
IP pública correcta
```

Obtén la IP:

```bash
curl -4 https://api.ipify.org
```

---

# 40. Orden recomendado para ponerlo en funcionamiento

Hazlo exactamente en este orden:

```text
1. MONITOR
2. PAPER
3. TESTNET
4. PRODUCTION
```

No recomiendo saltarte etapas.

---

# 41. Configuración recomendada para empezar

Yo usaría:

```env
TRADING_MODE=PAPER

RISK_PERCENT=1.0
MAX_LEVERAGE=15
MAX_MARGIN_PERCENT=25
MAX_OPEN_TRADES=3

TP_ALLOCATIONS=0.40,0.30,0.30

MOVE_SL_TO_BREAKEVEN_AFTER_TP1=true
MOVE_SL_TO_TP1_AFTER_TP2=true

ALLOW_MULTIPLE_POSITIONS_PER_SYMBOL=false

SIGNAL_EXPIRY_MINUTES=120
```

Con esta distribución:

```text
TP1 → 40%
TP2 → 30%
TP3 → 30%
```

---

# 42. Checklist antes de PRODUCTION

Antes de activar dinero real:

- [ ] MONITOR funcionando varias horas/días.
- [ ] Parser interpretando correctamente las señales.
- [ ] PAPER funcionando.
- [ ] TP1 funciona.
- [ ] TP2 funciona.
- [ ] TP3 funciona.
- [ ] SL funciona.
- [ ] Break Even funciona.
- [ ] Movimiento SL a TP1 funciona.
- [ ] `/pause` funciona.
- [ ] `/resume` funciona.
- [ ] `/close BTCUSDT` funciona.
- [ ] `/breakeven BTCUSDT` funciona.
- [ ] TESTNET probado.
- [ ] Reinicio de Coolify probado con operaciones abiertas.
- [ ] SQLite persiste después del redeploy.
- [ ] `telegram.session` persiste.
- [ ] Binance IP whitelist configurada.
- [ ] Binance withdrawals deshabilitados.
- [ ] Riesgo configurado bajo.
- [ ] One-way Mode activo en Binance Futures.

Después de todo eso:

```env
TRADING_MODE=PRODUCTION
ENABLE_PRODUCTION_TRADING=true
PRODUCTION_CONFIRMATION=I_UNDERSTAND_LIVE_TRADING
```

Y para las primeras operaciones reales conviene usar:

```env
RISK_PERCENT=0.25
```

o:

```env
RISK_PERCENT=0.50
```

antes de subirlo al 1%.