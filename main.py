import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --------------------
# Load environment variables
# --------------------
load_dotenv()

# Gemini AI configuration
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

# --------------------
# Fetch location & weather
# --------------------
def fetch_location():
    data = requests.get("https://ipinfo.io/json").json()
    lat, lon = data["loc"].split(",")
    location = f"{data.get('city')}, {data.get('region')}, {data.get('country')}"
    return float(lat), float(lon), location

def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,precipitation_sum,uv_index_max,cloudcover_mean"
        "&timezone=auto"
    )
    data = requests.get(url).json()
    current = data.get("current_weather", {})
    daily = data.get("daily", {})

    feels_like = (daily.get("apparent_temperature_max", [current.get("temperature")])[0] +
                  daily.get("apparent_temperature_min", [current.get("temperature")])[0]) / 2

    return {
        "temp": current.get("temperature"),
        "windspeed": current.get("windspeed"),
        "winddir": current.get("winddirection"),
        "max": daily["temperature_2m_max"][0],
        "min": daily["temperature_2m_min"][0],
        "feels_like": round(feels_like, 1),
        "sunrise": daily["sunrise"][0].split("T")[1],
        "sunset": daily["sunset"][0].split("T")[1],
        "cloudcover": daily.get("cloudcover_mean", [0])[0],
        "precipitation": daily.get("precipitation_sum", [0])[0],
        "uv_index": daily.get("uv_index_max", [0])[0]
    }

# --------------------
# Fetch top news
# --------------------
def fetch_news(country="us", max_articles=5):
    url = f"https://newsapi.org/v2/top-headlines?country={country}&pageSize={max_articles}&apiKey={os.environ['NEWS_API_KEY']}"
    data = requests.get(url).json()
    articles = data.get("articles", [])
    news_list = []
    for article in articles:
        title = article.get("title")
        desc = article.get("description")
        if title and desc:
            news_list.append(f"{title} - {desc}")
    return news_list

# --------------------
# Generate AI Good Morning Message
# --------------------
def ai_morning_message(weather, location, news_list):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = "\n".join(news_list) if news_list else "No major news today."

    prompt = f"""
You are a friendly AI morning assistant.

Create a **short, cheerful Good Morning message** for {location} for {today}.

1. Start with a **weather snapshot** section as bullet points:
- Min
- Max
- Feels Like
- Sunrise
- Sunset

2. Then give a 2–3 line summary of today’s weather including highs, lows, wind, cloud cover, precipitation, sunrise/sunset.

3. Include top news headlines from the list below in bullet points, 1–2 sentences each.

Weather details:
Current: {weather['temp']}°C, Wind: {weather['windspeed']} km/h from {weather['winddir']}°, Cloud cover: {weather['cloudcover']}%, Precipitation: {weather['precipitation']} mm, UV index: {weather['uv_index']}

News to summarize:
{news_text}

Format the message with proper line breaks, bullets, and bolds. Use HTML formatting so it looks readable in an email.
"""
    response = model.generate_content(prompt)
    return response.text

# --------------------
# Send Email
# --------------------
def send_email(subject, html_content):
    EMAIL = os.environ["SENDER_EMAIL"]
    PASSWORD = os.environ["SENDER_PASSWORD"]
    RECEIVER = os.environ.get("RECEIVER_EMAIL", EMAIL)

    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL
    msg["To"] = RECEIVER
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, RECEIVER, msg.as_string())

# --------------------
# MAIN
# --------------------
def main():
    lat, lon, location = fetch_location()
    weather = fetch_weather(lat, lon)
    news = fetch_news("us")

    message_html = ai_morning_message(weather, location, news)

    print("\n☀️ FirstLight — AI Good Morning Briefing\n")
    print(message_html)  # Terminal preview

    send_email(f"Good Morning — {location} | {datetime.now().strftime('%d %B %Y')}", message_html)
    print("\n✅ Email sent successfully!")

if __name__ == "__main__":
    main()
