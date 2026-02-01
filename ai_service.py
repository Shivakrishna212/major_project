from google import genai
import os
import json
import re
import time
import requests 

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")   

if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found!")

MODEL_NAME = "gemma-3-27b-it" 
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ Error initializing Gemini Client: {e}")

# --- HELPER: JSON CLEANER ---
def clean_json_text(text):
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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            cleaned_text = clean_json_text(response.text)
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                if "control character" in str(e):
                    cleaned_text = cleaned_text.replace('\n', '\\n').replace('\t', '\\t')
                    data = json.loads(cleaned_text)
                else:
                    raise e 

            if 'quiz' in data and isinstance(data['quiz'], list):
                idx_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                for q in data['quiz']:
                    ans = str(q.get('correct_answer', '')).replace('.', '').strip().upper()
                    opts = q.get('options', [])
                    if ans in idx_map and idx_map[ans] < len(opts):
                        q['correct_answer'] = opts[idx_map[ans]]
            return data
        except Exception as e:
            print(f"⚠️ AI JSON Error (Attempt {attempt+1}): {e}")
            if "503" in str(e) or "429" in str(e): time.sleep(2)
    return None

# --- 📸 WIKIMEDIA SEARCH (DIRECT LINKING) ---

def search_wikimedia_image(topic, subtopic):
    """Searches Wikimedia and returns the direct image URL."""
    clean_subtopic = subtopic.replace("Module", "").replace("Foundations", "").strip()
    
    url = "https://commons.wikimedia.org/w/api.php"
    
    # Prioritize diagrams and structures
    search_terms = [
        f"{topic} {clean_subtopic} diagram",
        f"{topic} architecture",
        f"{topic} structure",
        f"{clean_subtopic} diagram"
    ]

    for search_term in search_terms:
        print(f"🔍 Searching Wikimedia for: '{search_term}'")
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {search_term}", # Look for images
            "gsrnamespace": 6, 
            "gsrlimit": 5, 
            "prop": "imageinfo",
            "iiprop": "url", # Just get the URL
            "format": "json"
        }

        try:
            # We use a standard User-Agent so Wiki doesn't block us
            headers = { 'User-Agent': 'LearnAI_Student_App/1.0 (educational use)' }
            res = requests.get(url, params=params, headers=headers)
            data = res.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                image_info = page_data.get("imageinfo", [{}])[0]
                image_url = image_info.get("url")
                
                # Filter: Ensure it's a standard image format
                if image_url and ('.jpg' in image_url.lower() or '.png' in image_url.lower() or '.jpeg' in image_url.lower()):
                    print(f"✅ Found Image: {image_url}")
                    return image_url # <--- Return the Wiki URL directly!

        except Exception as e:
            print(f"⚠️ Wiki Search Error: {e}")
            
    return None

# --- CONTENT GENERATION FUNCTIONS ---

def generate_topic_intro(topic):
    prompt = f"""
    The user wants to learn about: '{topic}'.
    Generate a concise but engaging introduction.
    Return JSON: 
    {{ 
        "topic": "{topic}", 
        "intro": "**Markdown introduction** covering what it is, why it's important, and real-world applications.", 
        "hook": "A short, catchy tagline." 
    }}
    """
    return _get_json_response(prompt) or {"topic": topic, "intro": f"Welcome to {topic}!"}

def generate_roadmap(topic):
    prompt = f"""
    Create a comprehensive learning roadmap for '{topic}'.
    Break the topic down into 5-8 logical modules.
    Return strictly valid JSON: 
    {{ 
        "topic_name": "{topic}",
        "roadmap": [ {{ "title": "Module 1: Name", "keywords": ["Key1", "Key2"] }} ] 
    }}
    """
    return _get_json_response(prompt) or {"roadmap": []}

def generate_sub_roadmap(topic, module_title):
    prompt = f"""
    The user is learning '{topic}'. Current Module: '{module_title}'.
    Break this into 4-6 specific sub-topics/lessons.
    Return strictly valid JSON:
    {{ "sub_roadmap": [ {{ "title": "Lesson 1 Title", "keywords": ["tag1"] }} ] }}
    """
    for attempt in range(3):
        data = _get_json_response(prompt)
        if data and data.get('sub_roadmap') and len(data['sub_roadmap']) > 0:
            return data
        time.sleep(1)
    return {"sub_roadmap": []}

def generate_node_content(topic_name, node_title, attempt_count=1, failed_questions=None):
    difficulty = "beginner"
    clean_title = node_title.split(':')[-1].strip()
    
    # 1. 📸 Fetch Direct URL
    image_url = search_wikimedia_image(topic_name, clean_title)

    # 2. Generate Content
    prompt = f"""
    Teach '{topic_name}' -> '{node_title}'. Level: {difficulty}.
    Return strictly valid JSON:
    1. 'content': Markdown lesson (use \\n for newlines). Must be detailed (>150 words). Include code examples if coding related.
    2. 'quiz': 3 MCQs with 'explanation'.
    
    Structure: 
    {{ 
        "content": "# Heading\\nText...", 
        "quiz": [
            {{
                "question": "Q?", 
                "options": ["A", "B", "C", "D"], 
                "correct_answer": "A", 
                "explanation": "Reasoning..."
            }}
        ] 
    }}
    """
    
    for attempt in range(3):
        data = _get_json_response(prompt)
        if data and data.get('content') and len(data['content']) > 50:
            # ✅ Attach the direct URL
            if image_url: 
                data['image_url'] = image_url
            return data
        time.sleep(1)

    return {
        "content": "## Content Generation Failed\nPlease try refreshing this node.",
        "quiz": [],
        "image_url": image_url 
    }

def generate_remedial_content(topic_name, node_title, failed_concepts):
    print(f"🚑 Generating Remedial Lesson: {node_title}")
    prompt = f"""
    The user FAILED the quiz for: '{node_title}' (Subject: {topic_name}).
    Concepts failed: {failed_concepts}.

    Goal: RE-WRITE the lesson to be SIMPLER (EL15). Use analogies.
    Generate a NEW, EASIER quiz (3 questions).
    
    Output JSON: {{ "content": "Markdown...", "quiz": [...] }}
    """
    return _get_json_response(prompt)

def generate_doubt_answer(topic, node, question):
    try:
        return client.models.generate_content(model=MODEL_NAME, contents=f"Context: {topic} - {node}. Question: {question}").text
    except: return "I'm having trouble connecting right now."