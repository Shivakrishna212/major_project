import sqlite3
import random
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_NAME = "learning_app.db"

def create_connection():
    return sqlite3.connect(DB_NAME)

def clear_data(conn):
    """Wipe old data so we don't have duplicates"""
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE email LIKE '%@fake.com'")
    c.execute("DELETE FROM progress WHERE topic_name = 'Python Basics'")
    conn.commit()
    print("🧹 Cleared old fake data.")

def seed_users(conn):
    c = conn.cursor()
    users = []
    
    # We will create 3 types of students to "Teach" the AI patterns
    
    # 🟢 GROUP A: The "Achievers" (20 students)
    # - High XP, Logged in recently, Good quiz scores
    for i in range(20):
        users.append({
            "email": f"achiever{i}@fake.com",
            "name": f"Achiever Alex {i}",
            "xp": random.randint(500, 2000),
            "level": random.randint(5, 10),
            "type": "good"
        })

    # 🟠 GROUP B: The "Strugglers" (20 students)
    # - Low XP, Failed modules, Logged in 3-7 days ago
    for i in range(20):
        users.append({
            "email": f"struggler{i}@fake.com",
            "name": f"Struggler Sam {i}",
            "xp": random.randint(50, 300),
            "level": random.randint(1, 3),
            "type": "risk"
        })

    # 🔴 GROUP C: The "Dropouts" (10 students)
    # - Zero recent activity, stopped at Module 1
    for i in range(10):
        users.append({
            "email": f"dropout{i}@fake.com",
            "name": f"Dropout Danny {i}",
            "xp": random.randint(0, 100),
            "level": 1,
            "type": "gone"
        })

    print(f"🌱 Seeding {len(users)} fake users...")

    for u in users:
        # Create User
        pw = generate_password_hash("password123")
        c.execute("INSERT INTO users (email, password, name, xp, level) VALUES (?, ?, ?, ?, ?)", 
                  (u['email'], pw, u['name'], u['xp'], u['level']))
        user_id = c.lastrowid

        # Create Fake Progress (The most important part for ML)
        days_ago = 0
        modules = []
        
        if u['type'] == 'good':
            days_ago = random.randint(0, 2) # Active recently
            modules = [0, 1, 2, 3] # Finished many modules
        elif u['type'] == 'risk':
            days_ago = random.randint(3, 8) # Inactive for a week
            modules = [0] # Stuck on Module 1
        else:
            days_ago = random.randint(15, 30) # Gone for a month
            modules = [] # Did nothing

        # Fake "Last Login" simulation (We will calculate this from progress timestamp in real app)
        # For now, we just assume the 'progress' entry timestamp is their last active time.
        last_active = datetime.now() - timedelta(days=days_ago)
        
        c.execute("INSERT INTO progress (user_id, topic_name, completed_modules, definition_data) VALUES (?, ?, ?, ?)",
                  (user_id, "Python Basics", json.dumps(modules), '{"fake": true}'))
        
    conn.commit()
    print("✅ Database populated with patterns!")

if __name__ == "__main__":
    try:
        conn = create_connection()
        clear_data(conn)
        seed_users(conn)
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")