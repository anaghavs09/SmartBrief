import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_subscribers_from_sheets():
    """Read subscribers from Google Sheets via CSV export"""
    try:
        sheet_id = "1J6KhlvuDZ0JZs24TzFPaVhyUD_Sjo-wfPyRcyAtgKoA"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        
        response = requests.get(csv_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch sheet: {response.status_code}")
            return []
        
        lines = response.text.strip().split('\n')
        
        if len(lines) <= 1:
            print("⚠️ No subscribers in sheet")
            return []
        
        subscribers = []
        for i, line in enumerate(lines[1:], start=2):  # Row 2+ (skip header)
            try:
                # Handle CSV with potential commas in fields
                import csv
                import io
                reader = csv.reader(io.StringIO(line))
                parts = next(reader)
                
                if len(parts) >= 4 and parts[0].strip():
                    email = parts[0].strip()
                    latitude = float(parts[1])
                    longitude = float(parts[2])
                    location = parts[3].strip()
                    subscribed_date = parts[4].strip() if len(parts) > 4 else ''
                    last_sent = parts[5].strip() if len(parts) > 5 else None
                    
                    subscribers.append((
                        i-1,  # Row number as ID
                        email,
                        latitude,
                        longitude,
                        location,
                        subscribed_date,
                        last_sent if last_sent else None
                    ))
            except Exception as e:
                print(f"⚠️ Skipping row {i}: {e}")
                continue
        
        return subscribers
        
    except Exception as e:
        print(f"❌ Error reading sheets: {e}")
        return []


def update_last_sent_in_sheets(row_number, date_str):
    """Update last sent date in Google Sheets"""
    try:
        # This requires Google Sheets API with write permissions
        # For now, we'll skip updating (will handle duplicates by checking date)
        pass
    except Exception as e:
        print(f"⚠️ Could not update sheet: {e}")


if __name__ == "__main__":
    print("Testing Google Sheets connection...\n")
    subs = get_subscribers_from_sheets()
    print(f"✅ Found {len(subs)} subscribers:\n")
    for s in subs:
        print(f"  Row {s[0]}: {s[1]} - {s[4]} (Last sent: {s[6] or 'Never'})")