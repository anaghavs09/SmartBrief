import os
import requests
import smtplib
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from timezonefinder import TimezoneFinder
import pytz

from database import (
    get_all_subscribers,
    update_last_sent_date
)

# --------------------------------------------------
# ENV
# --------------------------------------------------

load_dotenv()

SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# --------------------------------------------------
# GEMINI (STABLE API)
# --------------------------------------------------

import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# --------------------------------------------------
# TIMEZONE
# --------------------------------------------------

tf = TimezoneFinder()

def should_send_now(lat, lon, last_sent_date):
    """
    Send only if:
    - Local time is between 5–7 PM
    - Email not already sent today
    """
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    if not tz_name:
        return False

    tz = pytz.timezone(tz_name)
    local_time = datetime.now(pytz.utc).astimezone(tz)

    # 5–7 PM window
    if not (17 <= local_time.hour < 19):
        return False

    # Already sent today?
    if last_sent_date == local_time.date().isoformat():
        return False

    return True


# --------------------------------------------------
# WEATHER
# --------------------------------------------------

def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "apparent_temperature_max,apparent_temperature_min,"
        "sunrise,sunset,precipitation_sum,cloudcover_mean"
        "&timezone=auto"
    )

    data = requests.get(url, timeout=10).json()
    daily = data["daily"]

    feels_like = (
        daily["apparent_temperature_max"][0] +
        daily["apparent_temperature_min"][0]
    ) / 2

    return {
        "min": daily["temperature_2m_min"][0],
        "max": daily["temperature_2m_max"][0],
        "feels_like": round(feels_like, 1),
        "sunrise": daily["sunrise"][0].split("T")[1],
        "sunset": daily["sunset"][0].split("T")[1],
        "cloudcover": daily["cloudcover_mean"][0],
        "precipitation": daily["precipitation_sum"][0]
    }


# --------------------------------------------------
# NEWS
# --------------------------------------------------

def fetch_news(country="us", limit=4):
    url = (
        "https://newsapi.org/v2/top-headlines"
        f"?country={country}&pageSize={limit}"
        f"&apiKey={NEWS_API_KEY}"
    )

    data = requests.get(url, timeout=10).json()
    articles = data.get("articles", [])

    return [
        f"{a['title']} – {a['description']}"
        for a in articles
        if a.get("title") and a.get("description")
    ]


# --------------------------------------------------
# AI EMAIL
# --------------------------------------------------

def generate_email(weather, location, news):
    today = datetime.now().strftime("%A, %B %d")

    news_text = "\n".join(news) if news else "No major headlines today."

    prompt = f"""
Create a calm, premium HTML email.

Use only HTML tags like <p>, <b>, <ul>, <li>.

Structure:
1) Warm greeting
2) <b>Weather Snapshot</b>
3) 2–3 sentence weather summary
4) <b>Top News</b>

Location: {location}
Date: {today}

Weather:
Min: {weather['min']}°C
Max: {weather['max']}°C
Feels Like: {weather['feels_like']}°C
Sunrise: {weather['sunrise']}
Sunset: {weather['sunset']}
Cloud Cover: {weather['cloudcover']}%
Precipitation: {weather['precipitation']} mm

News:
{news_text}
"""

    response = model.generate_content(prompt)
    return response.text


# --------------------------------------------------
# EMAIL SENDER
# --------------------------------------------------

def send_email(to_email, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    full_html = f"""
    <html>
    <body style="font-family:Arial;background:#f4f4f4;padding:20px">
      <div style="max-width:600px;margin:auto;background:white;border-radius:10px">
        <div style="background:#5f6cff;color:white;padding:20px;text-align:center">
          <h2>🌇 SmartBrief</h2>
          <p>Your Evening Digest</p>
        </div>
        <div style="padding:25px">
          {html_body}
        </div>
        <div style="text-align:center;font-size:12px;color:#999;padding:10px">
          Powered by AI
        </div>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(full_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    print("\n🚀 SmartBrief Digest Started\n")

    subscribers = get_all_subscribers()
    print(f"👥 Subscribers found: {len(subscribers)}")

    for sub in subscribers:
        (
            sub_id,
            email,
            lat,
            lon,
            location,
            last_sent_date
        ) = sub

        if not should_send_now(lat, lon, last_sent_date):
            print(f"⏭ Skipping {email}")
            continue

        print(f"📧 Sending to {email} ({location})")

        weather = fetch_weather(lat, lon)
        news = fetch_news()

        html = generate_email(weather, location, news)

        subject = f"🌇 SmartBrief — {datetime.now().strftime('%A')}"

        send_email(email, subject, html)

        update_last_sent_date(sub_id, date.today().isoformat())

        print("   ✅ Sent")

    print("\n✅ Digest run complete\n")


if __name__ == "__main__":
    main()
