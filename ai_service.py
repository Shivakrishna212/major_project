from google import genai
import os
import json
import re
import time
import requests 
import shutil

# --- CONFIGURATION ---
# 🔑 PASTE YOUR KEYS HERE
API_KEY = os.environ.get("GEMINI_API_KEY")   
SEARCH_ENGINE_ID = os.environ.get("search_engine_id")

if not API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found in environment variables!")

# Model Configuration
MODEL_NAME = "gemma-3-27b-it" 
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"❌ Error initializing Gemini Client: {e}")

def clean_json_text(text):
    """Robust JSON cleaner."""
    if not text: return ""
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0: return text[start:end]
    return text

def _get_json_response(prompt):
    """
    Standard generation with basic JSON parsing retries.
    Does NOT check for content quality (empty strings), just valid JSON syntax.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            cleaned_text = clean_json_text(response.text)
            
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                # Fallback: Try escaping newlines if control chars failed it
                if "control character" in str(e):
                    cleaned_text = cleaned_text.replace('\n', '\\n').replace('\t', '\\t')
                    data = json.loads(cleaned_text)
                else:
                    raise e 

            # Fix Quiz Options if needed
            if 'quiz' in data and isinstance(data['quiz'], list):
                idx_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                for q in data['quiz']:
                    ans = str(q.get('correct_answer', '')).replace('.', '').strip().upper()
                    opts = q.get('options', [])
                    if ans in idx_map and idx_map[ans] < len(opts):
                        q['correct_answer'] = opts[idx_map[ans]]
            return data
        except Exception as e:
            print(f"⚠️ AI JSON Syntax Error (Attempt {attempt+1}): {e}")
            if "503" in str(e) or "429" in str(e): time.sleep(2)
            
    return None

# --- SEARCH & DOWNLOAD ---

def download_image_locally(url, topic, subtopic):
    try:
        save_dir = os.path.join("static", "images")
        os.makedirs(save_dir, exist_ok=True)

        safe_topic = "".join(x for x in topic if x.isalnum())
        safe_sub = "".join(x for x in subtopic if x.isalnum())[:10]
        filename = f"{safe_topic}_{safe_sub}.jpg"
        file_path = os.path.join(save_dir, filename)

        print(f"⬇️ Downloading: {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            print("✅ Image saved locally.")
            return f"[http://127.0.0.1:5000/static/images/](http://127.0.0.1:5000/static/images/){filename}" 
        else:
            print(f"❌ Download failed (Status {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ Save Error: {e}")
        return None

def search_educational_image(topic, subtopic):
    if not SEARCH_ENGINE_ID or not API_KEY or "YOUR_" in API_KEY:
        # print("❌ API Keys missing. Skipping image search.")
        return None

    url = "[https://www.googleapis.com/customsearch/v1](https://www.googleapis.com/customsearch/v1)"
    clean_subtopic = subtopic.replace("Module", "").replace("Foundations", "").strip()

    queries = [
        f"{topic} {clean_subtopic} diagram site:geeksforgeeks.org OR site:javatpoint.com",
        f"{topic} {clean_subtopic} architecture diagram",
        f"{topic} diagram structure"
    ]

    for query in queries:
        print(f"🔍 Google Search: {query}")
        params = { 'q': query, 'cx': SEARCH_ENGINE_ID, 'key': API_KEY, 'searchType': 'image', 'num': 1, 'safe': 'active' }
        try:
            res = requests.get(url, params=params)
            data = res.json()
            if 'items' in data and len(data['items']) > 0:
                image_url = data['items'][0]['link']
                local_path = download_image_locally(image_url, topic, subtopic)
                if local_path: return local_path
        except: pass
    return None

# --- CORE FUNCTIONS (WITH QUALITY RETRY LOOP) ---

def generate_topic_intro(topic):
    prompt = f"Topic: {topic}. Return JSON: {{ 'topic': '{topic}', 'definition': 'Short definition', 'hook': 'Why learn this?' }}"
    return _get_json_response(prompt) or {"topic": topic, "definition": "Error."}

def generate_roadmap(topic):
    prompt = f"""
    Create a comprehensive learning roadmap for '{topic}'.
    Break the topic down into a logical number of modules (5-10).
    Return strictly valid JSON: 
    {{ "roadmap": [ {{ "title": "Module 1: Title", "keywords": ["K1", "K2"] }} ] }}
    """
    # Roadmap generation is usually reliable, simple retry is enough
    return _get_json_response(prompt) or {"roadmap": []}

def generate_sub_roadmap(topic, module_title):
    prompt = f"""
    The user is learning '{topic}'. Module: '{module_title}'.
    Break this into 4-6 specific sub-topics.
    Return strictly valid JSON:
    {{ "sub_roadmap": [ {{ "title": "Sub-topic 1", "keywords": ["k1"] }} ] }}
    """
    
    # ✅ RETRY LOOP 1: Ensure we don't get an empty list
    max_retries = 3
    for attempt in range(max_retries):
        data = _get_json_response(prompt)
        
        # VALIDATION
        if data and data.get('sub_roadmap') and len(data['sub_roadmap']) > 0:
            return data
            
        print(f"⚠️ Generated Sub-Roadmap was empty. Retrying ({attempt+1}/{max_retries})...")
        time.sleep(1)
        
    return {"sub_roadmap": []}

def generate_node_content(topic_name, node_title, attempt_count=1, failed_questions=None):
    difficulty = "beginner"
    clean_title = node_title.split(':')[-1].strip()
    
    # 1. Search Image (Once is enough)
    image_url = search_educational_image(topic_name, clean_title)

    # 2. Generate Content (With Retry)
    prompt = f"""
    Teach '{topic_name}' -> '{node_title}'. Level: {difficulty}.
    Return strictly valid JSON:
    1. 'content': Markdown lesson (use \\n for newlines). Must be detailed (>100 words).
    2. 'quiz': 3 MCQs.
    
    Structure: {{ "content": "# Heading\\nText...", "quiz": [...] }}
    """
    
    # ✅ RETRY LOOP 2: Ensure content is not empty
    max_retries = 3
    for attempt in range(max_retries):
        data = _get_json_response(prompt)
        
        # VALIDATION: Check if content exists and is substantial
        if data and data.get('content') and len(data['content']) > 100:
            if image_url: data['image_url'] = image_url
            return data
            
        print(f"⚠️ Generated Lesson Content was empty/short. Retrying ({attempt+1}/{max_retries})...")
        time.sleep(1)

    # Fallback if all 3 attempts fail
    return {
        "content": "## Generation Failed\nWe couldn't generate this lesson after multiple attempts. Please try refreshing or clicking the node again.",
        "quiz": [],
        "image_url": image_url
    }

def generate_doubt_answer(topic, node, question):
    try:
        return client.models.generate_content(model=MODEL_NAME, contents=f"Context: {topic} {node}. Q: {question}").text
    except: return "Error."