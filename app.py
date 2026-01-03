from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ----------------------------
# Environment & API Safeguards
# ----------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# Optional: initialize Gemini only if API key is set
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
    else:
        model = None
        print("⚠️ GEMINI_API_KEY not set. AI features will be disabled.")
except Exception as e:
    model = None
    print(f"⚠️ Failed to initialize Gemini API: {e}")

# ----------------------------
# Database Initialization
# ----------------------------

try:
    from database import init_db, add_subscriber, unsubscribe, get_all_subscribers
    init_db()
except Exception as e:
    print(f"⚠️ Database failed to initialize: {e}")
    add_subscriber = unsubscribe = get_all_subscribers = lambda *a, **k: []

# ----------------------------
# Routes
# ----------------------------

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>Error loading page</h1><p>{e}</p>", 500

@app.route('/test')
def test():
    return "<h1>✅ Flask is running on Render!</h1>"

# Example API route
@app.route('/api/subscribers', methods=['GET'])
def list_subscribers():
    try:
        subscribers = get_all_subscribers()
        return jsonify({"subscribers": subscribers, "total": len(subscribers)})
    except Exception as e:
        return jsonify({"subscribers": [], "total": 0, "error": str(e)}), 500

# ----------------------------
# Start server
# ----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
