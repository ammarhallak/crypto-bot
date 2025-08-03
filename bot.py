import asyncio
import logging
import requests
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# تطبيق fix لبيئات مثل VS Code
nest_asyncio.apply()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = "8357040231:AAEiTt3fYdDzlP7APdzIVxjRwLa4hnoOgQM"
CHAT_ID = "687892495"

# متغيرات مراقبة
known_coin_ids = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! البوت بدأ المراقبة.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("الأوامر:\n/start - بدء البوت\n/help - المساعدة")

def fetch_coins_list():
    url = "https://api.coingecko.com/api/v3/coins/list"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def fetch_coin_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "1h,24h,7d"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

async def monitor(app):
    global known_coin_ids
    try:
        coins_list = fetch_coins_list()
        known_coin_ids = set(coin['id'] for coin in coins_list)
        logger.info(f"تم جلب قائمة {len(known_coin_ids)} عملة.")
    except Exception as e:
        logger.error(f"خطأ بجلب قائمة العملات: {e}")
        return

    while True:
        try:
            data = fetch_coin_data()
            logger.info(f"تم جلب بيانات {len(data)} عملة في الجولة الحالية.")

            # تحقق من عملات جديدة
            new_coins = []
            for coin in data:
                if coin['id'] not in known_coin_ids:
                    new_coins.append(coin)
                    known_coin_ids.add(coin['id'])

            if new_coins:
                for coin in new_coins:
                    text = (f"🚀 عملة جديدة على السوق:\n"
                            f"اسم: {coin['name']} ({coin['symbol'].upper()})\n"
                            f"السعر: ${coin['current_price']}\n"
                            f"القيمة السوقية: ${coin['market_cap']:,}")
                    await app.bot.send_message(chat_id=CHAT_ID, text=text)
            else:
                logger.info("لا توجد عملات جديدة في الجولة الحالية.")

            # تحقق عملات ضاربة (مثال: زيادة سعر 10% بالساعة الماضية)
            hot_coins = [c for c in data if c.get("price_change_percentage_1h_in_currency") and c["price_change_percentage_1h_in_currency"] > 10]
            for coin in hot_coins:
                text = (f"🔥 عملة ضاربة:\n"
                        f"اسم: {coin['name']} ({coin['symbol'].upper()})\n"
                        f"زيادة 1 ساعة: {coin['price_change_percentage_1h_in_currency']:.2f}%\n"
                        f"السعر: ${coin['current_price']}\n"
                        f"القيمة السوقية: ${coin['market_cap']:,}")
                await app.bot.send_message(chat_id=CHAT_ID, text=text)

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error: {http_err}")
        except Exception as e:
            logger.error(f"خطأ أثناء المراقبة: {e}")

        logger.info("انتظار 60 ثانية قبل الجولة القادمة...")
        await asyncio.sleep(60)  # تأخير 60 ثانية لتجنب حظر API

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # ابدأ المراقبة بشكل غير متزامن (background)
    asyncio.create_task(monitor(app))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

