import json
import logging
import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

with open("bot_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
CHAT_ID = config["CHAT_ID"]

notified_coins = set()
scheduler = AsyncIOScheduler()
app = None
muted = False

async def send_notification(message):
    global muted
    if muted:
        logging.info("🔕 التنبيهات موقوفة، لن يتم الإرسال.")
        return
    try:
        await app.bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"فشل في إرسال الرسالة: {e}")

def check_crypto():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        for coin in data:
            if not coin.get("market_cap") or coin["market_cap"] < 1_000_000:
                continue

            coin_id = coin["id"]
            if coin_id in notified_coins:
                continue

            name = coin["name"]
            symbol = coin["symbol"].upper()
            price = coin["current_price"]
            market_cap = coin["market_cap"]
            volume = coin["total_volume"]
            change = coin["price_change_percentage_24h"]

            message = (
                f"🚨 عملة جديدة ظهرت في السوق!\n\n"
                f"💰 الاسم: {name} ({symbol})\n"
                f"📊 السعر: ${price:,.6f}\n"
                f"💸 القيمة السوقية: ${market_cap:,.0f}\n"
                f"📈 الحجم خلال 24 ساعة: ${volume:,.0f}\n"
                f"📉 التغيير 24 ساعة: {change:.2f}%\n"
                f"🌐 المنصة: CoinGecko"
            )

            asyncio.run_coroutine_threadsafe(send_notification(message), app.loop)
            notified_coins.add(coin_id)

    except Exception as e:
        logging.error(f"حدث خطأ أثناء جلب البيانات: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 بوت مراقبة العملات شغّال!")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global muted
    muted = True
    await update.message.reply_text("🔕 تم إيقاف التنبيهات. استخدم /unmute لتفعيلها.")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global muted
    muted = False
    await update.message.reply_text("🔔 تم تفعيل التنبيهات.")

async def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_crypto, "interval", minutes=1)
        scheduler.start()
        logging.info("✅ الجدولة شغّالة...")

def main():
    global app
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))

    loop = asyncio.get_event_loop()

    loop.create_task(start_scheduler())
    loop.create_task(app.run_polling())

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logging.info("بوت توقف يدويًا.")

if __name__ == "__main__":
    main()
