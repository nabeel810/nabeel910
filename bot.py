import time
import requests
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import sqlite3

TOKEN = "8469297826:AAH6onC_4Pdmqej7ZoSNV-1cPjhr-VeVjpE"
CHAT_ID = "6557169034"

ASSETS = {
    "XAUUSD": {"name": "الذهب", "ticker": "GC=F", "htf": "1h", "ltf": "15m", "type": "fast"},
    "GBPUSD": {"name": "الباوند / دولار", "ticker": "GBPUSD=X", "htf": "1h", "ltf": "15m", "type": "fast"},
    "NZDUSD": {"name": "النيوزيلندي / دولار", "ticker": "NZDUSD=X", "htf": "1h", "ltf": "15m", "type": "fast"},
    "EURUSD": {"name": "اليورو / دولار", "ticker": "EURUSD=X", "htf": "1h", "ltf": "5m", "type": "slow"},
    "AUDUSD": {"name": "الدولار الأسترالي", "ticker": "AUDUSD=X", "htf": "1h", "ltf": "5m", "type": "slow"},
    "USDJPY": {"name": "الدولار / الين", "ticker": "USDJPY=X", "htf": "1h", "ltf": "5m", "type": "slow"},
}

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        print("✅ تم إرسال الرسالة بنجاح.")
    except Exception as e:
        print(f"خطأ: {e}")

def main():
    print("🚀 بدء تشغيل البوت وإرسال رسالة الشروط...")
    
    # رسالة فورية توضح شروط الدخول ونسبة الثقة
    intro_msg = (
        f"🤖 *رسالة اختبار نظام التداول الآلي (ICT/SMC)*\n"
        f"------------------------------------\n"
        f"✅ *البوت يعمل الآن بنجاح تام ومستعد لمراقبة السوق على مدار الساعة.*\n\n"
        f"📌 *شروط ونسب الثقة لكي يعطي البوت الصفقة:*\n\n"
        f"1️⃣ **فلتر الجلسات (Sessions):**\n"
        f"• يجب أن يكون السوق في أوقات السيولة الحقيقية (جلسة لندن أو جلسة نيويورك).\n\n"
        f"2️⃣ **تحديد الاتجاه العام (HTF - فريم الساعة):**\n"
        f"• يتم فحص مؤشر `EMA 200`. السعر فوق المتوسط = اتجاه صاعد، وتحته = اتجاه هابط.\n\n"
        f"3️⃣ **قوة الزخم (مؤشر ADX):**\n"
        f"• يجب أن تكون قراءة `ADX > 20` لضمان وجود اتجاه حقيقي وليس تداولات عرضية ضعيفة.\n\n"
        f"4️⃣ **تأكيد هيكل السوق (BOS - فريم الـ 15د أو 5د):**\n"
        f"• يجب أن تحدث شمعة تأكيد تخترق قمة سابقة (في الصعود) أو قاع سابق (في الهبوط).\n\n"
        f"🎯 *نسبة الثقة في الإشارة:*\n"
        f"• البوت يطبق دمج الإطار الزمني العالي مع الفريم الصغير (Multi-Timeframe Analysis) مع حساب نقاط وقف خسارة وأهداف (TP1 / TP2) ذكية ديناميكياً لضمان أعلى جودة ودقة للصفقات.\n"
        f"------------------------------------"
    )
    
    send_telegram_message(intro_msg)

if __name__ == "__main__":
    main()
