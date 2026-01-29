from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

# ✅ CORRECT IMPORTS
from ai_service import (
    generate_topic_intro, 
    generate_roadmap, 
    generate_sub_roadmap,
    generate_node_content,
    generate_doubt_answer
)

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
DB_NAME = "learning_app.db"
# Increased workers to handle parallel lesson generation
executor = ThreadPoolExecutor(max_workers=6) 

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
                level INTEGER DEFAULT 1
            )
        ''')
        
        # 2. Progress
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

        # 3. Chat Messages
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

        # 4. Module Lessons (Caching)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS module_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER,
                node_index INTEGER,
                node_title TEXT,
                content TEXT,
                image_url TEXT,
                quiz_data TEXT,
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
        
        conn.commit()

init_db()

# --- HELPER: ZOMBIE CHECK ---
def is_topic_active(attempt_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM progress WHERE id = ?", (attempt_id,))
            return cursor.fetchone() is not None
    except:
        return False

# --- PRE-FETCHING TASKS ---

def prefetch_lesson_task(attempt_id, node_index, topic_name, node_title):
    """Generates content for a specific lesson."""
    if not is_topic_active(attempt_id): return

    try:
        # Check Cache First
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM module_lessons WHERE attempt_id = ? AND node_title = ?", (attempt_id, node_title))
            if cursor.fetchone(): return 

        print(f"🔮 [Pre-fetch] Pre-writing Lesson: {node_title}")
        
        # ⚠️ Slight delay to stagger multiple lesson requests
        time.sleep(node_index * 1.5) 

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

def prefetch_sub_roadmap_task(attempt_id, module_index, topic_name, module_title):
    """Generates the Drill-Down map AND triggers lesson generation for that module."""
    if not is_topic_active(attempt_id): return 

    try:
        # 1. Check if already exists
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sub_roadmaps WHERE attempt_id = ? AND module_index = ?", (attempt_id, module_index))
            if cursor.fetchone(): return 

        print(f"🔮 [Pre-fetch] Predicting Next Module: {module_title}")
        time.sleep(1) 
        
        # 2. Generate
        result = generate_sub_roadmap(topic_name, module_title)
        
        if not is_topic_active(attempt_id): return

        # 3. Save
        if result and result.get('sub_roadmap'):
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO sub_roadmaps (attempt_id, module_index, sub_roadmap_data) VALUES (?, ?, ?)", 
                               (attempt_id, module_index, json.dumps(result['sub_roadmap'])))
                conn.commit()
            print(f"✅ [Pre-fetch] Saved Module Structure: {module_title}")

            # 🚀 FULL MODULE BUFFER: Start generating ALL lessons for this module
            # We prioritize the first 3 lessons
            sub_map = result['sub_roadmap']
            for i, node in enumerate(sub_map[:3]): 
                executor.submit(prefetch_lesson_task, attempt_id, i, topic_name, node['title'])

    except Exception as e:
        print(f"⚠️ Pre-fetch Sub-Map Failed: {e}")

# --- AUTH ROUTES (Unchanged) ---
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
        cursor.execute("SELECT id, name, xp, level FROM users WHERE email = ? AND password = ?", (email, hashed_pw))
        user = cursor.fetchone()
        if user:
            return jsonify({"message": "Login successful", "user": {"id": user['id'], "name": user['name'], "xp": user['xp'], "level": user['level']}}), 200
        else: return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/get_user_history', methods=['POST'])
def get_user_history():
    data = request.json
    user_id = data.get('user_id')
    if not user_id: return jsonify({"history": []})
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

@app.route('/api/get_user_stats', methods=['POST'])
def get_user_stats():
    data = request.json
    user_id = data.get('user_id')
    stats = { "topics_started": 0, "modules_completed": 0, "total_xp": 0, "level": 1 }
    if not user_id: return jsonify(stats)
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT xp, level FROM users WHERE id = ?", (user_id,))
            user_row = cursor.fetchone()
            if user_row:
                stats['total_xp'] = user_row[0]
                stats['level'] = user_row[1]
            cursor.execute("SELECT completed_modules FROM progress WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            stats['topics_started'] = len(rows)
            for row in rows:
                try:
                    modules_list = json.loads(row[0])
                    stats['modules_completed'] += len(modules_list)
                except: pass
    except: pass
    return jsonify(stats)

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    data = request.json
    user_id = data.get('user_id')
    new_name = data.get('name')
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, user_id))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/delete_topic', methods=['POST'])
def delete_topic():
    data = request.json
    attempt_id = data.get('attempt_id')
    if not attempt_id: return jsonify({"error": "ID required"}), 400
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM module_lessons WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM sub_roadmaps WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM progress WHERE id = ?", (attempt_id,))
            conn.commit()
            print(f"🗑️ Topic {attempt_id} deleted.")
            return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# --- CHAT ROUTES ---

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
    if not user_message: return jsonify({"error": "Empty message"}), 400

    user_msg_id, ai_msg_id = None, None
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_messages (attempt_id, node_title, sender, message) VALUES (?, ?, ?, ?)", (attempt_id, node_title, 'user', user_message))
            user_msg_id = cursor.lastrowid
            conn.commit()
    except Exception as e: return jsonify({"error": str(e)}), 500

    ai_response_text = generate_doubt_answer(node_title, node_title, user_message) 

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_messages (attempt_id, node_title, sender, message) VALUES (?, ?, ?, ?)", (attempt_id, node_title, 'ai', ai_response_text))
            ai_msg_id = cursor.lastrowid
            conn.commit()
    except: pass

    return jsonify({
        "user_message": {"id": user_msg_id, "sender": "user", "text": user_message},
        "ai_message": {"id": ai_msg_id, "sender": "ai", "text": ai_response_text}
    })

@app.route('/api/delete_chat_interaction', methods=['POST'])
def delete_chat_interaction():
    data = request.json
    message_id = data.get('message_id')
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM chat_messages WHERE id > ? ORDER BY id ASC LIMIT 1", (message_id,))
            next_row = cursor.fetchone()
            cursor.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))
            if next_row:
                 cursor.execute("SELECT sender FROM chat_messages WHERE id = ?", (next_row[0],))
                 sender_row = cursor.fetchone()
                 if sender_row and sender_row[0] == 'ai':
                     cursor.execute("DELETE FROM chat_messages WHERE id = ?", (next_row[0],))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# --- CORE LOGIC ---

@app.route('/api/start_topic', methods=['POST'])
def start_topic():
    data = request.json
    topic = data.get('topic')
    user_id = data.get('user_id')
    if not topic: return jsonify({"error": "Topic is required"}), 400

    def background_task():
        print(f"🚀 [Thread] Generating Intro for: {topic}")
        intro = generate_topic_intro(topic)
        attempt_id = 0
        if user_id:
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO progress (user_id, topic_name, completed_modules, definition_data) VALUES (?, ?, ?, ?)", (user_id, intro['topic'], "[]", json.dumps(intro)))
                    conn.commit()
                    attempt_id = cursor.lastrowid
            except Exception as e: print(f"❌ DB Error: {e}")
        return {"attempt_id": attempt_id, "definition": intro}

    future = executor.submit(background_task)
    return jsonify(future.result())

@app.route('/api/get_roadmap', methods=['POST'])
def get_roadmap():
    data = request.json
    attempt_id = data.get('attempt_id')
    if not attempt_id: return jsonify({"error": "No ID"}), 400
    
    topic_name = "General Learning"
    completed_modules = []
    cached_roadmap = None
    cached_definition = None

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name, completed_modules, roadmap_data, definition_data FROM progress WHERE id = ?", (attempt_id,))
        row = cursor.fetchone()
        if row:
            topic_name = row['topic_name']
            try: completed_modules = json.loads(row['completed_modules'])
            except: completed_modules = []
            if row['roadmap_data']:
                try: cached_roadmap = json.loads(row['roadmap_data'])
                except: pass
            if row['definition_data']:
                try: cached_definition = json.loads(row['definition_data'])
                except: pass

    roadmap_to_process = []
    
    if cached_roadmap:
        roadmap_to_process = cached_roadmap
    else:
        print(f"🗺️ [Thread] Generating Roadmap for: {topic_name}")
        new_data = generate_roadmap(topic_name)
        if new_data and new_data.get('roadmap'):
            roadmap_to_process = new_data['roadmap']
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE progress SET roadmap_data = ? WHERE id = ?", (json.dumps(roadmap_to_process), attempt_id))
                    conn.commit()
            except: pass

    # 🚀 CHAIN REACTION: Trigger pre-fetch for Module 1
    if roadmap_to_process and len(roadmap_to_process) > 0:
        first_module_title = roadmap_to_process[0]['title']
        executor.submit(prefetch_sub_roadmap_task, attempt_id, 0, topic_name, first_module_title)

    return jsonify({ 
        "roadmap": roadmap_to_process, 
        "completed_indices": completed_modules, 
        "definition": cached_definition 
    })

@app.route('/api/get_sub_roadmap', methods=['POST'])
def get_sub_roadmap():
    data = request.json
    attempt_id = data.get('attempt_id')
    module_index = data.get('module_index')
    module_title = data.get('module_title')

    # 1. Fetch from Cache
    cached_data = None
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT sub_roadmap_data FROM sub_roadmaps WHERE attempt_id = ? AND module_index = ?", (attempt_id, module_index))
        row = cursor.fetchone()
        if row:
            print(f"⚡ [Cache] Serving Sub-Roadmap for: {module_title}")
            cached_data = json.loads(row['sub_roadmap_data'])

    # 2. Get Context
    topic_name = ""
    next_module_title = None
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name, roadmap_data FROM progress WHERE id = ?", (attempt_id,))
        row = cursor.fetchone()
        if row: 
            topic_name = row['topic_name']
            try:
                full_roadmap = json.loads(row['roadmap_data'])
                if module_index + 1 < len(full_roadmap):
                    next_module_title = full_roadmap[module_index + 1]['title']
            except: pass

    final_sub_map = []

    if cached_data:
        final_sub_map = cached_data
    else:
        print(f"🗺️ [Thread] Generating Sub-Roadmap: {module_title}")
        result = generate_sub_roadmap(topic_name, module_title)
        
        if not is_topic_active(attempt_id): return jsonify({})

        if result and result.get('sub_roadmap'):
            final_sub_map = result['sub_roadmap']
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO sub_roadmaps (attempt_id, module_index, sub_roadmap_data) VALUES (?, ?, ?)", (attempt_id, module_index, json.dumps(final_sub_map)))
                    conn.commit()
            except: pass

    # ==========================================================
    # 🚀 IMPROVED CHAIN REACTION LOGIC (Horizontal THEN Vertical)
    # ==========================================================
    
    # 1. PRIORITY: Fill ALL lessons in CURRENT module first
    if final_sub_map and len(final_sub_map) > 0:
        # Loop through ALL nodes, not just the first one
        for i, node in enumerate(final_sub_map):
            executor.submit(prefetch_lesson_task, attempt_id, i, topic_name, node['title'])
    
    # 2. SECONDARY: Start buffering NEXT module structure
    if next_module_title:
        executor.submit(prefetch_sub_roadmap_task, attempt_id, module_index + 1, topic_name, next_module_title)

    return jsonify({"sub_roadmap": final_sub_map})

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
            print(f"⚡ [Cache] Serving Lesson for: {node_title}")
            return jsonify({ "content": row['content'], "image_url": row['image_url'], "quiz": json.loads(row['quiz_data']) if row['quiz_data'] else [] })

    topic_name = "General"
    if attempt_id:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic_name FROM progress WHERE id = ?", (attempt_id,))
            row = cursor.fetchone()
            if row: topic_name = row[0]

    def content_task():
        if not is_topic_active(attempt_id): return {}
        print(f"📚 [Thread] Generating Content: {node_title}")
        result = generate_node_content(topic_name, node_title)
        
        if not is_topic_active(attempt_id): return result

        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO module_lessons (attempt_id, node_index, node_title, content, image_url, quiz_data) VALUES (?, ?, ?, ?, ?, ?)", 
                               (attempt_id, node_index, node_title, result['content'], result.get('image_url'), json.dumps(result['quiz'])))
                conn.commit()
        except: pass
        return result

    future = executor.submit(content_task)
    return jsonify(future.result())

@app.route('/api/submit_node_quiz', methods=['POST'])
def submit_node_quiz():
    data = request.json
    attempt_id = data.get('attempt_id')
    passed = data.get('passed')
    xp_gained = 0
    new_level = 1
    new_xp = 0

    if passed and attempt_id:
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                xp_gained = 50
                cursor.execute("UPDATE users SET xp = xp + ? WHERE id = (SELECT user_id FROM progress WHERE id=?)", (xp_gained, attempt_id))
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
        except: pass

    return jsonify({ "success": True, "xp_gained": xp_gained, "total_xp": new_xp, "level": new_level })

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)