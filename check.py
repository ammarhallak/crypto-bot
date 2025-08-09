import requests

# حط التوكن تبع البوت
BOT_TOKEN = "8357040231:AAHMHvKZIWSiqsHCIuguJsJB-MzKsJmWaQg"
CHAT_ID = "687892495"  # مثلا 123456789 أو @ammar_alhallak

message = "✅ اختبار البوت: البوت شغال تمام؟"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": message
}

res = requests.post(url, data=payload)
print(res.json())
