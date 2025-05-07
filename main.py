import websocket
import json
import os
import requests
from datetime import datetime, timezone

WEBHOOK_URL = os.getenv("Trump_Alert")
SYMBOL = "TRUMP-USD"
BREAKOUT = 10.95
BREAKDOWN = 10.85
RESET_DELTA = 0.03
REQUIRED_PROFIT = 0.0437  # ≈ 4.37%
MAX_TRADES_PER_DAY = 3

# State trackers
ALERTED = {"long": False, "short": False}
trade_count = 0
current_day = datetime.utcnow().date()

def reset_trade_counter():
    global trade_count, current_day
    today = datetime.utcnow().date()
    if today != current_day:
        trade_count = 0
        current_day = today
        print("🔄 New day detected. Trade counter reset.")

def send_alert(message):
    if not WEBHOOK_URL:
        print("❌ Webhook not set.")
        return
    try:
        res = requests.post(WEBHOOK_URL, json={"content": message})
        if res.status_code in [200, 204]:
            print("✅ Alert sent.")
        else:
            print(f"❌ Discord error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")

def on_message(ws, msg):
    global ALERTED, trade_count
    try:
        reset_trade_counter()
        data = json.loads(msg)
        if data.get("type") != "ticker":
            return

        price = float(data["price"])
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"💹 {now} | Price: ${price:.4f} | Trades today: {trade_count}")

        if trade_count >= MAX_TRADES_PER_DAY:
            print("🚫 Max trades hit for today.")
            return

        # LONG condition
        if price >= BREAKOUT and not ALERTED["long"]:
            tp1 = round(price * (1 + REQUIRED_PROFIT), 4)
            send_alert(f"🚀 **LONG ENTRY** | {now}\nEntry: ${price:.4f}\nTarget: ${tp1}")
            ALERTED["long"] = True
            ALERTED["short"] = False
            trade_count += 1

        # SHORT condition
        elif price <= BREAKDOWN and not ALERTED["short"]:
            tp2 = round(price * (1 - REQUIRED_PROFIT), 4)
            send_alert(f"🔻 **SHORT ENTRY** | {now}\nEntry: ${price:.4f}\nTarget: ${tp2}")
            ALERTED["short"] = True
            ALERTED["long"] = False
            trade_count += 1

        # Reset logic
        if ALERTED["long"] and price < BREAKOUT - RESET_DELTA:
            ALERTED["long"] = False
        if ALERTED["short"] and price > BREAKDOWN + RESET_DELTA:
            ALERTED["short"] = False

    except Exception as e:
        print(f"❌ Error: {e}")

def on_open(ws):
    print(f"[{datetime.now()}] ✅ Connected to Coinbase.")
    ws.send(json.dumps({
        "type": "subscribe",
        "channels": [{"name": "ticker", "product_ids": [SYMBOL]}]
    }))

def on_close(ws, code, reason):
    print(f"🔌 Closed: {code} | Reason: {reason}")

def on_error(ws, error):
    print(f"❌ WebSocket error: {error}")

if __name__ == "__main__":
    print(f"[{datetime.now()}] 🚀 Starting TRUMP/USD Scalper (Max 3 Trades/day)...")
    ws = websocket.WebSocketApp(
        "wss://ws-feed.exchange.coinbase.com",
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error
    )
    ws.run_forever()
