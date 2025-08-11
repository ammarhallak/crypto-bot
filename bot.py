# bot.py
import json
import logging
import asyncio
from aiohttp import ClientSession
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# load config
with open("bot_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
CHAT_ID = config["CHAT_ID"]

notified_coins = set()
muted = False
app = None

async def send_notification(message: str):
    global muted
    if muted:
        logging.info("🔕 التنبيهات موقوفة، لن يتم الإرسال.")
        return
    try:
        await app.bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"فشل في إرسال الرسالة: {e}")

async def fetch_top_coins(session: ClientSession):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false"
    }
    async with session.get(url, params=params, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.json()

async def check_crypto(context: ContextTypes.DEFAULT_TYPE):
    """دالة تعمل من خلال JobQueue كل دقيقة — غير متزامنة بالكامل."""
    global notified_coins
    try:
        async with ClientSession() as session:
            data = await fetch_top_coins(session)

            for coin in data:
                # مثال فلترة: قيمة سوقية أقل من 1 مليون تتجاهل
                if not coin.get("market_cap") or coin["market_cap"] < 1_000_000:
                    continue

                coin_id = coin["id"]
                if coin_id in notified_coins:
                    continue

                name = coin["name"]
                symbol = coin["symbol"].upper()
                price = coin.get("current_price", 0.0)
                market_cap = coin.get("market_cap", 0)
                volume = coin.get("total_volume", 0)
                change = coin.get("price_change_percentage_24h", 0.0)

                message = (
                    f"🚨 عملة جديدة ظهرت في السوق!\n\n"
                    f"💰 الاسم: {name} ({symbol})\n"
                    f"📊 السعر: ${price:,.6f}\n"
                    f"💸 القيمة السوقية: ${market_cap:,.0f}\n"
                    f"📈 الحجم خلال 24 ساعة: ${volume:,.0f}\n"
                    f"📉 التغيير 24 ساعة: {change:.2f}%\n"
                    f"🌐 المصدر: CoinGecko"
                )

                # نرسل الإشعار
                await send_notification(message)
                notified_coins.add(coin_id)

    except Exception as e:
        logging.error(f"حدث خطأ أثناء فحص العملات: {e}")

# Handlers
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

async def main():
    global app
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))

    # جدولة باستخدام JobQueue المدمج (يعمل ضمن نفس ال-event loop)
    # run_repeating(callback, interval_seconds, first=delay_seconds)
    app.job_queue.run_repeating(check_crypto, interval=60, first=5)

    # تشغيل الـ bot (غير حاجز للـ loop لأن هذا يعيد التحكم بشكل آمن)
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("بوت توقف يدويًا.")
