import sqlite3
import json

DB_NAME = "learning_app.db"

def inspect_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='progress';")
        if not cursor.fetchone():
            print("❌ Table 'progress' does not exist!")
            return

        # 2. Get the latest entry
        print("\n--- 🔍 INSPECTING LATEST ENTRY ---")
        cursor.execute("SELECT id, topic_name, roadmap_data, definition_data FROM progress ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()

        if not row:
            print("❌ No data found in 'progress' table.")
            return

        print(f"ID: {row['id']}")
        print(f"Topic: {row['topic_name']}")
        
        # 3. Check Roadmap Data Integrity
        raw_roadmap = row['roadmap_data']
        print(f"\n[Raw Roadmap Data (First 100 chars)]:\n{str(raw_roadmap)[:100]}...")

        try:
            parsed = json.loads(raw_roadmap)
            print("\n✅ JSON Parsing: SUCCESS")
            print(f"Type: {type(parsed)}")
            if isinstance(parsed, list):
                print(f"Items: {len(parsed)}")
                print(f"First Item Keys: {parsed[0].keys() if len(parsed) > 0 else 'Empty'}")
            elif isinstance(parsed, dict):
                print(f"Keys: {parsed.keys()}")
            
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON Parsing: FAILED")
            print(f"Error: {e}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_data()