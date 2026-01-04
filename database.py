import sqlite3
import time
from datetime import datetime

DB_PATH = "subscribers.db"

# ----------------------------
# Database connection
# ----------------------------
def get_connection():
    """Get SQLite connection with WAL mode"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")  # Enable WAL for concurrency
    return conn


# ----------------------------
# Initialize DB
# ----------------------------
def init_db():
    """Initialize subscribers table"""
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
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized!")


# ----------------------------
# Add subscriber
# ----------------------------
def add_subscriber(email, latitude, longitude, location_name=None):
    """Add a new subscriber"""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO subscribers (email, latitude, longitude, location_name)
                VALUES (?, ?, ?, ?)
            """, (email, latitude, longitude, location_name))

            conn.commit()
            conn.close()
            return True, "Subscribed successfully!"

        except sqlite3.IntegrityError:
            if conn:
                conn.close()
            return False, "Email already subscribed!"

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                retry_count += 1
                if conn:
                    conn.close()
                time.sleep(0.1)  # wait 100ms
                if retry_count >= max_retries:
                    return False, "Database busy, try again later"
            else:
                if conn:
                    conn.close()
                return False, f"Error: {str(e)}"

        except Exception as e:
            if conn:
                conn.close()
            return False, f"Error: {str(e)}"

    return False, "Failed after retries"


# ----------------------------
# Get all active subscribers
# ----------------------------
def get_all_subscribers():
    """Return all active subscribers with last_sent_date"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, email, latitude, longitude, location_name, subscribed_at, last_sent_date
            FROM subscribers
            WHERE is_active = 1
        """)

        subscribers = cursor.fetchall()
        conn.close()
        return subscribers
    except Exception as e:
        print(f"❌ Error fetching subscribers: {e}")
        return []


# ----------------------------
# Unsubscribe
# ----------------------------
def unsubscribe(email):
    """Deactivate subscriber"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE subscribers
            SET is_active = 0
            WHERE email = ?
        """, (email,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error unsubscribing: {e}")
        return False


# ----------------------------
# Update last sent date
# ----------------------------
def update_last_sent(subscriber_id):
    """Update last_sent_date to today"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE subscribers
            SET last_sent_date = ?
            WHERE id = ?
        """, (today, subscriber_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error updating last_sent_date: {e}")
        return False


# ----------------------------
# For debugging
# ----------------------------
if __name__ == "__main__":
    init_db()
    print("✅ DB ready")
