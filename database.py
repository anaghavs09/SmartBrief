import sqlite3
import time

DB_PATH = "subscribers.db"


# --------------------------------------------------
# CONNECTION
# --------------------------------------------------

def get_connection():
    """Get database connection with timeout"""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10.0,
        check_same_thread=False
    )
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# --------------------------------------------------
# INIT
# --------------------------------------------------

def init_db():
    """Initialize the database"""
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

            )
    """)


    conn.commit()
    conn.close()
    print("✅ Database initialized!")


# --------------------------------------------------
# ADD SUBSCRIBER
# --------------------------------------------------

def add_subscriber(email, latitude, longitude, location_name=None):
    max_retries = 3

    for _ in range(max_retries):
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
            conn.close()
            return False, "Email already subscribed!"

        except sqlite3.OperationalError as e:
            conn.close()
            if "locked" in str(e).lower():
                time.sleep(0.1)
            else:
                return False, str(e)

        except Exception as e:
            conn.close()
            return False, str(e)

    return False, "Database busy, try again"


# --------------------------------------------------
# READ SUBSCRIBERS (USED BY DIGEST)
# --------------------------------------------------

def get_all_subscribers():
    """Return active subscribers with last_sent_date"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                email,
                latitude,
                longitude,
                location_name,
                last_sent_date
            FROM subscribers
            WHERE is_active = 1
        """)

        rows = cursor.fetchall()
        conn.close()
        return rows

    except Exception as e:
        print(f"❌ Error fetching subscribers: {e}")
        return []


# --------------------------------------------------
# UPDATE LAST SENT DATE
# --------------------------------------------------

def update_last_sent_date(subscriber_id, sent_date):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE subscribers
            SET last_sent_date = ?
            WHERE id = ?
        """, (sent_date, subscriber_id))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"❌ Failed updating last_sent_date: {e}")


# --------------------------------------------------
# UNSUBSCRIBE
# --------------------------------------------------

def unsubscribe(email):
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
        print(f"❌ Unsubscribe failed: {e}")
        return False


# --------------------------------------------------
# RUN DIRECTLY
# --------------------------------------------------

if __name__ == "__main__":
    init_db()
