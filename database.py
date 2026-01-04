import os
import sqlite3
import time
from datetime import datetime, timedelta
import requests
import pytz
from timezonefinder import TimezoneFinder
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# -----------------------------
# Database functions
# -----------------------------

def get_connection():
    conn = sqlite3.connect('subscribers.db', timeout=10.0, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    """Initialize the database and ensure last_sent_date exists"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_name TEXT,
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            last_sent_date TEXT
        )
    """)
    conn.commit()

    # Add last_sent_date column if it does not exist
    try:
        cursor.execute("ALTER TABLE subscribers ADD COLUMN last_sent_date TEXT")
        conn.commit()
        print("✅ Added last_sent_date column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.close()

def get_all_subscribers():
    """Get all active subscribers"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, email, latitude, longitude, location_name, last_sent_date
            FROM subscribers
            WHERE is_active = 1
        """)
        subscribers = cursor.fetchall()
        return subscribers
    except Exception as e:
        print(f"❌ Error fetching subscribers: {e}")
        return []
    finally:
        conn.close()

def update_last_sent(subscriber_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("UPDATE subscribers SET last_sent_date=? WHERE id=?", (today, subscriber_id))
    conn.commit()
    conn.close()

# -----------------------------
# Timezone and scheduling
# -----------------------------

tf = TimezoneFinder()

def should_send_now(lat, lon):
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    if not tz_name:
        return False
    local_tz = pytz.timezone(tz_name)
    local_time = datetime.now(pytz.utc).astimezone(local_tz)
    return 17 <= local_time.hour < 19  # 5 PM to 7 PM local time

# -----------------------------
# Fetch weather & news
# -----------------------------

def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current_weather=true&daily=temperature_2m_max,temperature_2m_min,"
        "apparent_temperature_max,apparent_temperature_min,sunrise,sunset,"
        "precipitation_sum,uv_index_max,cloudcover_mean&timezone=auto"
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
        "max": daily.get("temperature_2m_max", [current.get("temperature")])[0],
        "min": daily.get("temperature_2m_min", [current.get("temperature")])[0],
        "feels_like": round(feels_like, 1),
        "sunrise": daily.get("sunrise", ["00:00"])[0].split("T")[1],
        "sunset": daily.get("sunset", ["00:00"])[0].split("T")[1],
        "cloudcover": daily.get("cloudcover_mean", [0])[0],
        "precipitation": daily.get("precipitation_sum", [0])[0],
        "uv_index": daily.get("uv_index_max", [0])[0]
    }

def fetch_news(country="us", max_articles=5):
    url = f"https://newsapi.org/v2/top-headlines?country={country}&pageSize={max_articles}&apiKey={NEWS_API_KEY}"
    data = requests.get(url).json()
    articles = data.get("articles", [])
    news_list = []
    for article in articles:
        title = article.get("title")
        desc = article.get("description")
        if title and desc:
            news_list.append(f"{title} - {desc}")
    return news_list

# -----------------------------
# AI message
# -----------------------------

try:
    import google.generativeai as genai
    genai.api_key = GEMINI_API_KEY
except Exception as e:
    print(f"⚠️ Could not load Gemini AI: {e}")
    genai = None

def ai_message(weather, location, news_list):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = "\n".join(news_list) if news_list else "No major news today."
    prompt = f"""
Generate an HTML morning briefing for location {location} on {today}.
Weather: Min {weather['min']}°C, Max {weather['max']}°C, Feels Like {weather['feels_like']}°C,
Sunrise {weather['sunrise']}, Sunset {weather['sunset']}, Wind {weather['windspeed']} km/h,
Cloud cover {weather['cloudcover']}%, Precipitation {weather['precipitation']} mm.

News:
{news_text}
"""
    if genai:
        response = genai.generate_text(model="gemini-pro", prompt=prompt)
        return response.text
    else:
        return f"<p>{prompt}</p>"

# -----------------------------
# Email
# -----------------------------

def send_email(to_email, subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    full_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        {html_content}
      </body>
    </html>
    """

    msg.attach(MIMEText(full_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

# -----------------------------
# Main
# -----------------------------

def main():
    print("\n🚀 SmartBrief Digest Starting\n")
    subscribers = get_all_subscribers()
    
    # Print all subscribers
    print("📋 Subscribers in DB:")
    for sub in subscribers:
        print(sub)
    print(f"📊 Total: {len(subscribers)}\n")

    for sub in subscribers:
        id_, email, lat, lon, location_name, last_sent = sub

        # Skip if already sent today
        today = datetime.now().strftime("%Y-%m-%d")
        if last_sent == today:
            print(f"⏭️ Already sent to {email} today")
            continue

        if not should_send_now(lat, lon):
            print(f"⏭️ Skipping {email} (not 5–7 PM local)")
            continue

        print(f"📧 Sending to {email} ({location_name})")

        weather = fetch_weather(lat, lon)
        news = fetch_news()
        message = ai_message(weather, location_name, news)
        subject = f"🌅 SmartBrief Digest — {datetime.now().strftime('%A, %b %d')}"

        send_email(email, subject, message)
        update_last_sent(id_)
        print("   ✅ Sent\n")

    print("🎉 All done!\n")

if __name__ == "__main__":
    init_db()
    main()
