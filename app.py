from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date

# ✅ LOCAL MODULE IMPORTS
from ml_service import train_model, predict_risk
from ai_service import (
    generate_topic_intro, 
    generate_roadmap, 
    generate_sub_roadmap,
    generate_node_content,
    generate_doubt_answer,
    generate_remedial_content
)

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
DB_NAME = "learning_app.db"
executor = ThreadPoolExecutor(max_workers=6) 

# =========================================================
# 🛠️ DATABASE INITIALIZATION
# =========================================================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                streak INTEGER DEFAULT 0,
                last_active_date TEXT
            )
        ''')
        
        # 2. Progress (Topics Started)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                topic_name TEXT,
                completed_modules TEXT DEFAULT '[]',
                roadmap_data TEXT,      
                definition_data TEXT,   
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # 3. Chat Messages (AI Tutor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                node_title TEXT,
                sender TEXT, 
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(attempt_id) REFERENCES progress(id)
            )
        ''')

        # 4. Module Lessons (Content Caching)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS module_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                node_index INTEGER,
                node_title TEXT,
                content TEXT,
                image_url TEXT,
                quiz_data TEXT,
                completed BOOLEAN DEFAULT 0,
                FOREIGN KEY(attempt_id) REFERENCES progress(id)
            )
        ''')

        # 5. Sub-Roadmaps (Drill Down Caching)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_roadmaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                module_index INTEGER,
                sub_roadmap_data TEXT,
                FOREIGN KEY(attempt_id) REFERENCES progress(id)
            )
        ''')

        # 6. User Notes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                node_title TEXT,
                content TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(attempt_id) REFERENCES progress(id)
            )
        ''')
        
        conn.commit()

def run_migrations():
    """Ensure DB schema is up to date without losing data."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Check for 'completed' in module_lessons
            cursor.execute("PRAGMA table_info(module_lessons)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'completed' not in columns:
                cursor.execute("ALTER TABLE module_lessons ADD COLUMN completed BOOLEAN DEFAULT 0")

            # Check for 'streak' and 'last_active_date' in users
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [info[1] for info in cursor.fetchall()]
            
            if 'streak' not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
            
            if 'last_active_date' not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_active_date TEXT")

            conn.commit()
    except Exception as e:
        print(f"Migration Warning: {e}")

# Run DB Init
init_db()
run_migrations()

# =========================================================
# 📂 STATIC FILE SERVING (IMAGES)
# =========================================================
@app.route('/static/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

# =========================================================
# 🔐 AUTHENTICATION
# =========================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    if not email or not password or not name: return jsonify({"error": "Missing fields"}), 400
    hashed_pw = hash_password(password)
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, hashed_pw, name))
            conn.commit()
            return jsonify({"message": "User created successfully!"}), 201
    except sqlite3.IntegrityError: return jsonify({"error": "Email already exists"}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    hashed_pw = hash_password(password)
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, xp, level FROM users WHERE email = ? AND password = ?", (email, hashed_pw, name))
        user = cursor.fetchone()
        if user:
            return jsonify({"message": "Login successful", "user": {"id": user['id'], "name": user['name'], "xp": user['xp'], "level": user['level']}}), 200
        else: return jsonify({"error": "Invalid credentials"}), 401

# =========================================================
# 🧠 AI & ROADMAP GENERATION
# =========================================================

# Helper: Check if topic still exists (Zombie Check)
def is_topic_active(attempt_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM progress WHERE id = ?", (attempt_id,))
            return cursor.fetchone() is not None
    except:
        return False

# Background Task: Pre-fetch Sub-Roadmap
def prefetch_sub_roadmap_task(attempt_id, module_index, topic_name, module_title):
    if not is_topic_active(attempt_id): return 
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sub_roadmaps WHERE attempt_id = ? AND module_index = ?", (attempt_id, module_index))
            if cursor.fetchone(): return 

        print(f"🔮 [Pre-fetch] Predicting Next Module: {module_title}")
        time.sleep(1) 
        result = generate_sub_roadmap(topic_name, module_title)
        
        if not is_topic_active(attempt_id): return

        if result and result.get('sub_roadmap'):
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO sub_roadmaps (attempt_id, module_index, sub_roadmap_data) VALUES (?, ?, ?)", 
                               (attempt_id, module_index, json.dumps(result['sub_roadmap'])))
                conn.commit()
            print(f"✅ [Pre-fetch] Saved Module Structure: {module_title}")
            
            # Helper to prefetch first few lessons of sub-roadmap
            for i, node in enumerate(result['sub_roadmap'][:3]):
                executor.submit(prefetch_lesson_task, attempt_id, i, topic_name, node['title'])

    except Exception as e:
        print(f"⚠️ Pre-fetch Sub-Map Failed: {e}")

# 1. CREATE NEW TOPIC (Generates Full Roadmap)
@app.route('/api/generate_roadmap', methods=['POST'])
def generate_roadmap_api():
    data = request.json
    topic = data.get('topic')
    user_id = data.get('user_id')

    print(f"🧠 Generating roadmap for: {topic}")

    # A. Generate AI Content
    intro_data = generate_topic_intro(topic) # { "intro": "...", "hook": "..." }
    roadmap_data = generate_roadmap(topic)   # { "roadmap": [...] }
    
    clean_topic = roadmap_data.get('topic_name', topic)
    roadmap_list = roadmap_data.get('roadmap', [])

    # B. Save to Database
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO progress (user_id, topic_name, roadmap_data, definition_data, completed_modules)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id, 
            clean_topic, 
            json.dumps(roadmap_list), 
            json.dumps(intro_data),
            '[]'
        ))
        attempt_id = cursor.lastrowid

    # C. Trigger Background Pre-fetch
    if len(roadmap_list) > 0:
        executor.submit(prefetch_sub_roadmap_task, attempt_id, 0, clean_topic, roadmap_list[0]['title'])

    return jsonify({
        "success": True,
        "attempt_id": attempt_id,
        "topic": clean_topic,
        "roadmap": roadmap_list,
        "intro": intro_data # Send back to frontend immediately
    })

# 2. GET FULL ROADMAP (Required for main_map view)
@app.route('/api/get_roadmap', methods=['POST'])
def get_roadmap():
    data = request.json
    attempt_id = data.get('attempt_id')
    if not attempt_id: return jsonify({"error": "No ID"}), 400
    
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name, completed_modules, roadmap_data, definition_data FROM progress WHERE id = ?", (attempt_id,))
        row = cursor.fetchone()
        
        if row:
            return jsonify({
                "topic": row['topic_name'],
                "roadmap": json.loads(row['roadmap_data']),
                "completed_indices": json.loads(row['completed_modules']) if row['completed_modules'] else [],
                "definition": json.loads(row['definition_data']) if row['definition_data'] else None
            })
        else:
            return jsonify({"error": "Topic not found"}), 404

# 3. GET SUB-ROADMAP (Required for sub_map view)
@app.route('/api/get_sub_roadmap', methods=['POST'])
def get_sub_roadmap():
    data = request.json
    attempt_id = data.get('attempt_id')
    module_index = data.get('module_index')
    module_title = data.get('module_title')

    # 1. Check Cache
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT sub_roadmap_data FROM sub_roadmaps WHERE attempt_id = ? AND module_index = ?", (attempt_id, module_index))
        row = cursor.fetchone()
        if row:
            print(f"⚡ [Cache] Serving Sub-Roadmap: {module_title}")
            return jsonify({"sub_roadmap": json.loads(row['sub_roadmap_data'])})

    # 2. Generate if missing
    topic_name = "General"
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name FROM progress WHERE id = ?", (attempt_id,))
        res = cursor.fetchone()
        if res: topic_name = res[0]

    print(f"🗺️ Generating Sub-Roadmap: {module_title}")
    result = generate_sub_roadmap(topic_name, module_title)
    
    if result and result.get('sub_roadmap'):
        final_sub_map = result['sub_roadmap']
        # Save to DB
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sub_roadmaps (attempt_id, module_index, sub_roadmap_data) VALUES (?, ?, ?)", 
                          (attempt_id, module_index, json.dumps(final_sub_map)))
            conn.commit()
            
        # Trigger Lesson Prefetch for first 3 items
        for i, node in enumerate(final_sub_map[:3]): 
            executor.submit(prefetch_lesson_task, attempt_id, i, topic_name, node['title'])
            
        return jsonify({"sub_roadmap": final_sub_map})
        
    return jsonify({"sub_roadmap": []})

# =========================================================
# 📚 LESSON & CONTENT MANAGEMENT
# =========================================================

# Helper: Background Lesson Generation
def prefetch_lesson_task(attempt_id, node_index, topic_name, node_title):
    if not is_topic_active(attempt_id): return
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM module_lessons WHERE attempt_id = ? AND node_title = ?", (attempt_id, node_title))
            if cursor.fetchone(): return 

        print(f"🔮 [Pre-fetch] Writing Lesson: {node_title}")
        result = generate_node_content(topic_name, node_title)
        
        if not is_topic_active(attempt_id): return 

        if result and result.get('content'):
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO module_lessons (attempt_id, node_index, node_title, content, image_url, quiz_data) VALUES (?, ?, ?, ?, ?, ?)", 
                               (attempt_id, node_index, node_title, result['content'], result.get('image_url'), json.dumps(result['quiz'])))
                conn.commit()
            print(f"✅ [Pre-fetch] Saved Lesson: {node_title}")
    except Exception as e:
        print(f"⚠️ Pre-fetch Lesson Failed: {e}")

@app.route('/api/get_node', methods=['POST'])
def get_node():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    node_index = data.get('node_index')
    
    # 1. Check Cache
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT content, image_url, quiz_data FROM module_lessons WHERE attempt_id = ? AND node_title = ?", (attempt_id, node_title))
        row = cursor.fetchone()
        if row:
            return jsonify({ 
                "content": row['content'], 
                "image_url": row['image_url'], 
                "quiz": json.loads(row['quiz_data']) if row['quiz_data'] else [] 
            })

    # 2. Generate Content
    topic_name = "General"
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name FROM progress WHERE id = ?", (attempt_id,))
        res = cursor.fetchone()
        if res: topic_name = res[0]

    print(f"📚 Generating Content: {node_title}")
    result = generate_node_content(topic_name, node_title)
    
    # Save to DB
    if result and result.get('content'):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO module_lessons (attempt_id, node_index, node_title, content, image_url, quiz_data) VALUES (?, ?, ?, ?, ?, ?)", 
                           (attempt_id, node_index, node_title, result['content'], result.get('image_url'), json.dumps(result['quiz'])))
            conn.commit()
            
    return jsonify(result)

# =========================================================
# 🎓 QUIZ & PROGRESS TRACKING
# =========================================================

@app.route('/api/submit_node_quiz', methods=['POST'])
def submit_node_quiz():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    passed = data.get('passed')
    xp_gained = 0
    new_level = 1
    new_xp = 0

    if passed and attempt_id:
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                
                # Mark lesson complete
                cursor.execute("UPDATE module_lessons SET completed = 1 WHERE attempt_id = ? AND node_title = ?", (attempt_id, node_title))
                
                # Add XP
                xp_gained = 50
                cursor.execute("UPDATE users SET xp = xp + ? WHERE id = (SELECT user_id FROM progress WHERE id=?)", (xp_gained, attempt_id))
                
                # Check Level Up
                cursor.execute("SELECT xp, level FROM users WHERE id = (SELECT user_id FROM progress WHERE id=?)", (attempt_id,))
                user_row = cursor.fetchone()
                if user_row:
                    current_xp, current_level = user_row[0], user_row[1]
                    calc_level = (current_xp // 100) + 1
                    if calc_level > current_level:
                        cursor.execute("UPDATE users SET level = ? WHERE id = (SELECT user_id FROM progress WHERE id=?)", (calc_level, attempt_id))
                        new_level = calc_level
                    else: new_level = current_level
                    new_xp = current_xp
                conn.commit()
        except: pass

    return jsonify({ "success": True, "xp_gained": xp_gained, "total_xp": new_xp, "level": new_level })

@app.route('/api/mark_module_complete', methods=['POST'])
def mark_module_complete():
    data = request.json
    attempt_id = data.get('attempt_id')
    module_index = data.get('module_index')
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT completed_modules FROM progress WHERE id = ?", (attempt_id,))
            row = cursor.fetchone()
            completed_list = json.loads(row[0]) if row and row[0] else []
            if module_index not in completed_list:
                completed_list.append(module_index)
                cursor.execute("UPDATE progress SET completed_modules = ? WHERE id = ?", (json.dumps(completed_list), attempt_id))
                conn.commit()
            return jsonify({"success": True, "completed_modules": completed_list})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/regenerate_remedial', methods=['POST'])
def regenerate_remedial():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    failed_questions = data.get('failed_questions')
    
    topic_name = "General"
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name FROM progress WHERE id = ?", (attempt_id,))
        res = cursor.fetchone()
        if res: topic_name = res[0]

    result = generate_remedial_content(topic_name, node_title, str(failed_questions))
    
    if result and result.get('content'):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE module_lessons 
                SET content = ?, quiz_data = ? 
                WHERE attempt_id = ? AND node_title = ?
            """, (result['content'], json.dumps(result['quiz']), attempt_id, node_title))
            conn.commit()
        return jsonify({"success": True, "new_content": result})
            
    return jsonify({"error": "Failed to generate"}), 500

# =========================================================
# 💬 CHAT & NOTES
# =========================================================

@app.route('/api/get_node_chat', methods=['POST'])
def get_node_chat():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    messages = []
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, sender, message FROM chat_messages WHERE attempt_id = ? AND node_title = ? ORDER BY id ASC", (attempt_id, node_title))
            rows = cursor.fetchall()
            for row in rows: messages.append({ "id": row['id'], "sender": row['sender'], "text": row['message'] })
    except: pass
    return jsonify({"messages": messages})

@app.route('/api/send_chat_message', methods=['POST'])
def send_chat_message():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    user_message = data.get('message')
    
    # Save User Msg
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_messages (attempt_id, node_title, sender, message) VALUES (?, ?, ?, ?)", (attempt_id, node_title, 'user', user_message))
        user_msg_id = cursor.lastrowid
        conn.commit()

    # Get AI Response
    ai_response_text = generate_doubt_answer(node_title, node_title, user_message) 

    # Save AI Msg
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_messages (attempt_id, node_title, sender, message) VALUES (?, ?, ?, ?)", (attempt_id, node_title, 'ai', ai_response_text))
        ai_msg_id = cursor.lastrowid
        conn.commit()

    return jsonify({
        "user_message": {"id": user_msg_id, "sender": "user", "text": user_message},
        "ai_message": {"id": ai_msg_id, "sender": "ai", "text": ai_response_text}
    })

@app.route('/api/save_notes', methods=['POST'])
def save_notes():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    content = data.get('content')
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_notes WHERE attempt_id = ? AND node_title = ?", (attempt_id, node_title))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE user_notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content, row[0]))
            else:
                cursor.execute("INSERT INTO user_notes (attempt_id, node_title, content) VALUES (?, ?, ?)", (attempt_id, node_title, content))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/get_notes', methods=['POST'])
def get_notes():
    data = request.json
    attempt_id = data.get('attempt_id')
    node_title = data.get('node_title')
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM user_notes WHERE attempt_id = ? AND node_title = ?", (attempt_id, node_title))
            row = cursor.fetchone()
            return jsonify({"content": row['content'] if row else ""})
    except: return jsonify({"content": ""})

# =========================================================
# 👤 USER PROFILE & DASHBOARD
# =========================================================

@app.route('/api/get_user_history', methods=['POST'])
def get_user_history():
    data = request.json
    user_id = data.get('user_id')
    history = []
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, topic_name FROM progress WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
            rows = cursor.fetchall()
            for row in rows: history.append({ "id": row['id'], "topic": row['topic_name'] })
    except: pass
    return jsonify({"history": history})

@app.route('/api/delete_topic', methods=['POST'])
def delete_topic():
    data = request.json
    attempt_id = data.get('attempt_id')
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # Cascade delete (manual since SQLite FK cascade might be off)
            cursor.execute("DELETE FROM chat_messages WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM module_lessons WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM sub_roadmaps WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM user_notes WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM progress WHERE id = ?", (attempt_id,))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/update_streak', methods=['POST'])
def update_streak():
    data = request.json
    user_id = data.get('user_id')
    if not user_id: return jsonify({"error": "No User ID"}), 400

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT streak, last_active_date FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row: return jsonify({"error": "User not found"}), 404
            
            current_streak = row[0] or 0
            last_date_str = row[1]
            today_str = date.today().isoformat()
            
            new_streak = current_streak
            message = "Streak unchanged"
            
            if last_date_str == today_str:
                pass 
            elif last_date_str:
                last_date = date.fromisoformat(last_date_str)
                delta = (date.today() - last_date).days
                if delta == 1:
                    new_streak += 1
                    message = "🔥 Streak increased!"
                else:
                    new_streak = 1
                    message = "💔 Streak reset"
            else:
                new_streak = 1
                message = "🔥 First streak day!"

            cursor.execute("UPDATE users SET streak = ?, last_active_date = ? WHERE id = ?", (new_streak, today_str, user_id))
            conn.commit()
            
            return jsonify({
                "streak": new_streak, 
                "message": message,
                "just_increased": (new_streak > current_streak and new_streak > 1)
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# 🤖 ML & NOTIFICATIONS
# =========================================================

@app.route('/api/predict_dropout_risk', methods=['POST'])
def get_dropout_risk():
    data = request.json
    user_id = data.get('user_id')
    try:
        result = predict_risk(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_notifications', methods=['POST'])
def get_notifications():
    data = request.json
    user_id = data.get('user_id')
    notifications = []
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT xp, streak, last_active_date FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user: return jsonify({"notifications": []})

            # 1. Welcome Msg
            notifications.append({
                "id": 1, "type": "info", "title": "Welcome!", "message": "Start learning to earn XP.", "time": "Just now"
            })

            # 2. Streak Msg
            if user['streak'] > 0:
                notifications.append({
                    "id": 2, "type": "success", "title": "🔥 Streak Active!", "message": f"{user['streak']} day streak.", "time": "Today"
                })

            # 3. Risk Msg
            if user['xp'] < 50 and user['streak'] == 0:
                 notifications.append({
                    "id": 3, "type": "warning", "title": "⚠️ Risk Alert", "message": "You are falling behind.", "time": "2h ago"
                })

            # 4. Inactivity Msg
            if user['last_active_date']:
                last_date = datetime.strptime(user['last_active_date'], "%Y-%m-%d").date()
                days_gap = (datetime.now().date() - last_date).days
                if days_gap > 2:
                    notifications.append({
                        "id": 4, "type": "mail", "title": "💌 We missed you...", "message": f"Gone for {days_gap} days.", "time": f"{days_gap}d ago"
                    })

    except Exception as e: print(e)
    return jsonify({"notifications": notifications})

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)