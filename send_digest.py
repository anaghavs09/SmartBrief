import os
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from dotenv import load_dotenv
from timezonefinder import TimezoneFinder
import pytz

from database import get_all_subscribers, update_last_sent_date

# ----------------------------
# Load env
# ----------------------------
load_dotenv()

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not all([SENDER_EMAIL, SENDER_PASSWORD, NEWS_API_KEY, GEMINI_API_KEY]):
    raise RuntimeError("📌 Missing required environment variables!")

# ----------------------------
# Gemini / Google GenAI
# ----------------------------
from google.genai import Client

client = Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "models/gemini-2.5-flash"

# ----------------------------
# Timezone finder
# ----------------------------
tf = TimezoneFinder()

def should_send_now(lat, lon, last_sent_date):
    """
    Only send if local time is between 17:00–18:59
    and email has NOT been sent today.
    """
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    if not tz_name:
        return False

    local_tz = pytz.timezone(tz_name)
    local_time = datetime.now(pytz.utc).astimezone(local_tz)

    # Only once per day
    today_local = local_time.date().isoformat()
    if last_sent_date == today_local:
        return False

    # Only between 5–7 PM
    return 17 <= local_time.hour < 19

# ----------------------------
# Weather
# ----------------------------
def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "apparent_temperature_max,apparent_temperature_min,"
        "sunrise,sunset,precipitation_sum,cloudcover_mean"
        "&timezone=auto"
    )
    r = requests.get(url, timeout=10).json()
    current = r.get("current_weather", {})
    daily = r.get("daily", {})

    feels_like = (
        daily.get("apparent_temperature_max", [current.get("temperature")])[0] +
        daily.get("apparent_temperature_min", [current.get("temperature")])[0]
    ) / 2

    return {
        "min": daily["temperature_2m_min"][0],
        "max": daily["temperature_2m_max"][0],
        "feels_like": round(feels_like, 1),
        "sunrise": daily["sunrise"][0].split("T")[1],
        "sunset": daily["sunset"][0].split("T")[1],
        "cloudcover": daily.get("cloudcover_mean", [0])[0],
        "precipitation": daily.get("precipitation_sum", [0])[0]
    }

# ----------------------------
# News
# ----------------------------
def fetch_news(country="us", max_articles=5):
    url = (
        "https://newsapi.org/v2/top-headlines"
        f"?country={country}&pageSize={max_articles}"
        f"&apiKey={NEWS_API_KEY}"
    )
    r = requests.get(url, timeout=10).json()
    return [
        f"{a['title']} – {a['description']}"
        for a in r.get("articles", [])
        if a.get("title") and a.get("description")
    ]

# ----------------------------
# Build email content using AI
# ----------------------------
def ai_morning_message(weather, location, news_list):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = "\n".join(news_list) if news_list else "No major news today."

    prompt = f"""
You are an AI that writes clean, friendly HTML email content.

Generate HTML for an evening briefing.

1) Warm hello
2) Weather snapshot (Min, Max, Feels Like, Sunrise, Sunset) as bullet list
3) Short 2–3 sentence weather summary
4) Top news in bullet points (1–2 sentences each)

Location: {location}
Date: {today}

Weather:
Min: {weather['min']}°C
Max: {weather['max']}°C
Feels Like: {weather['feels_like']}°C
Sunrise: {weather['sunrise']}
Sunset: {weather['sunset']}
Cloud cover: {weather['cloudcover']}%
Precipitation: {weather['precipitation']} mm

News:
{news_text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text

# ----------------------------
# Send email
# ----------------------------
def send_email(to_email, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    full_html = f"""
    <html>
    <body style="font-family:Arial;background:#f5f5f5;padding:20px">
      <div style="max-width:600px;margin:auto;background:white;border-radius:10px;overflow:hidden;">
        <div style="background:#4a90e2;color:white;text-align:center;padding:20px;">
          <h2>🌇 SmartBrief Evening</h2>
        </div>
        <div style="padding:25px;color:#333;line-height:1.6;">
          {html_body}
        </div>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(full_html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

# ----------------------------
# MAIN PROGRAM
# ----------------------------
def main():
    print("\n🚀 SmartBrief Digest Starting\n")
    subscribers = get_all_subscribers()
    print(f"📊 {len(subscribers)} subscribers found\n")

    for sub in subscribers:
        (
            sub_id,
            email,
            lat,
            lon,
            location_name,
            last_sent_date
        ) = sub

        # Check if it's within allowed time and not already sent today
        if not should_send_now(lat, lon, last_sent_date):
            print(f"⏭ Skipping {email}")
            continue

        print(f"📧 Sending to {email} ({location_name})")

        weather = fetch_weather(lat, lon)
        news = fetch_news("us")

        html = ai_morning_message(weather, location_name, news)
        subject = f"🌆 SmartBrief — {datetime.now().strftime('%A, %b %d')}"

        send_email(email, subject, html)

        # Update last sent date in DB
        today_iso = datetime.now(pytz.utc).astimezone(pytz.timezone(tf.timezone_at(lat=lat, lng=lon))).date().isoformat()
        update_last_sent_date(sub_id, today_iso)

        print("   ✅ Sent\n")

    print("🎉 All done!\n")

if __name__ == "__main__":
    main()
