import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import pytz
from timezonefinder import TimezoneFinder
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import get_all_subscribers

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# Initialize Gemini - UPDATED API
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

tf = TimezoneFinder()


# ----------------------------
# TIME CHECK 5–7 PM LOCAL
# ----------------------------
def should_send_now(lat, lon, last_sent_date):
    """Check if it's 5-7 PM in subscriber's local timezone"""
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    if not tz_name:
        return False

    local_tz = pytz.timezone(tz_name)
    local_time = datetime.now(pytz.utc).astimezone(local_tz)

    # Only send once per day
    today_str = local_time.strftime("%Y-%m-%d")
    if last_sent_date == today_str:
        return False

    # 17–19 hours = 5–7 PM
    return 17 <= local_time.hour < 19


# ----------------------------
# FETCH WEATHER
# ----------------------------
def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "apparent_temperature_max,apparent_temperature_min,"
        "sunrise,sunset,precipitation_sum,uv_index_max,cloudcover_mean"
        "&timezone=auto"
    )
    data = requests.get(url).json()
    current = data.get("current_weather", {})
    daily = data.get("daily", {})

    feels_like = (
        daily.get("apparent_temperature_max", [current.get("temperature")])[0] +
        daily.get("apparent_temperature_min", [current.get("temperature")])[0]
    ) / 2

    return {
        "temp": current.get("temperature"),
        "windspeed": current.get("windspeed"),
        "winddir": current.get("winddirection"),
        "max": daily.get("temperature_2m_max", [0])[0],
        "min": daily.get("temperature_2m_min", [0])[0],
        "feels_like": round(feels_like, 1),
        "sunrise": daily.get("sunrise", ["00:00"])[0].split("T")[1],
        "sunset": daily.get("sunset", ["00:00"])[0].split("T")[1],
        "cloudcover": daily.get("cloudcover_mean", [0])[0],
        "precipitation": daily.get("precipitation_sum", [0])[0],
        "uv_index": daily.get("uv_index_max", [0])[0]
    }


# ----------------------------
# FETCH NEWS
# ----------------------------
def fetch_news(country="us", max_articles=5):
    url = f"https://newsapi.org/v2/top-headlines?country={country}&pageSize={max_articles}&apiKey={NEWS_API_KEY}"
    data = requests.get(url).json()
    articles = data.get("articles", [])
    news_list = []
    for a in articles:
        title = a.get("title")
        desc = a.get("description")
        if title and desc:
            news_list.append(f"{title} - {desc}")
    return news_list


# ----------------------------
# AI MESSAGE - FIXED GEMINI API
# ----------------------------
def ai_message(weather, location, news_list):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = "\n".join(news_list) if news_list else "No major news today."

    prompt = f"""
You are a calm, premium AI evening assistant.

Generate a clean, readable HTML email.

STRUCTURE EXACTLY AS BELOW:

1) A warm Good Evening greeting
2) A bold "Weather Snapshot" section with bullet points:
   - Min
   - Max
   - Feels Like
   - Sunrise
   - Sunset
3) A 2–3 line short weather summary
4) A bold "Top News" section with bullet points (1–2 sentences each)

Keep spacing clean. Use proper HTML tags only (<b>, <ul>, <li>, <p>).

Location: {location}
Date: {today}

Weather details:
Min: {weather['min']}°C
Max: {weather['max']}°C
Feels Like: {weather['feels_like']}°C
Sunrise: {weather['sunrise']}
Sunset: {weather['sunset']}
Wind: {weather['windspeed']} km/h
Cloud cover: {weather['cloudcover']}%
Precipitation: {weather['precipitation']} mm

News:
{news_text}
"""

    # FIXED: Use new Gemini API
    response = model.generate_content(prompt)
    return response.text


# ----------------------------
# SEND EMAIL
# ----------------------------
def send_email(to_email, subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    full_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
      <div style="max-width:600px;margin:auto;background:white;border-radius:12px;overflow:hidden;">
        <div style="background:#6b73ff;color:white;padding:20px;text-align:center;">
          <h1 style="margin:0;">🌙 SmartBrief</h1>
          <p style="margin:5px 0 0;">Your AI Evening Briefing</p>
        </div>

        <div style="padding:25px;color:#333;line-height:1.6;">
          {html_content}
        </div>

        <div style="background:#fafafa;padding:15px;text-align:center;font-size:12px;color:#888;">
          Powered by Gemini AI
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
# MAIN
# ----------------------------
def main():
    print("\n🚀 SmartBrief Digest Starting\n")
    subscribers = get_all_subscribers()

    # Print DB for debugging
    print("📋 Subscribers in DB:")
    for sub in subscribers:
        print(sub)

    print(f"\n📊 Active subscribers found: {len(subscribers)}\n")

    if not subscribers:
        print("⚠️  No subscribers found in database!")
        print("💡 Make sure you've subscribed via http://localhost:8080\n")
        return

    sent_count = 0
    skipped_count = 0

    for sub in subscribers:
        # FIXED: Unpack 7 values (added last_sent)
        id_, email, lat, lon, location_name, subscribed_at, last_sent = sub
        
        # For now, send to everyone (skip time check for testing)
        # if not should_send_now(lat, lon, last_sent):
        #     print(f"⏭️ Skipping {email} ({location_name}) — not 5–7 PM local or already sent today")
        #     skipped_count += 1
        #     continue

        print(f"📧 Sending to {email} ({location_name})")

        try:
            weather = fetch_weather(lat, lon)
            news = fetch_news("us")
            message = ai_message(weather, location_name, news)
            subject = f"🌙 SmartBrief — {datetime.now().strftime('%A, %B %d')}"

            send_email(email, subject, message)
            
            # Update last_sent_date in database
            from database import update_last_sent
            update_last_sent(id_)
            
            sent_count += 1
            print("   ✅ Sent\n")
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")

    print("="*60)
    print(f"🎉 Distribution Complete!")
    print(f"   ✅ Sent: {sent_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()