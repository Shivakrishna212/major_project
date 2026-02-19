import os
import json
import re
import time
import requests
from google import genai
from google.genai import types

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")   

if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found!")

# ✅ User Requested Model
MODEL_NAME = "gemma-3-27b-it" 

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ Error initializing Gemini Client: {e}")

# --- HELPER: JSON CLEANER ---
def clean_json_text(text):
    """
    Robustly extracts JSON from AI responses, handling markdown blocks 
    and common formatting issues.
    """
    if not text: return ""
    # Remove markdown code blocks
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    
    # Find the outermost JSON object
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0: return text[start:end]
    return text

def _get_json_response(prompt):
    """
    Sends prompt to AI and retries if JSON parsing fails.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # ✅ FIX: Removed 'response_mime_type' because Gemma doesn't support it
            response = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )
            
            cleaned_text = clean_json_text(response.text)
            
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                # Handle control characters that break JSON
                if "control character" in str(e):
                    cleaned_text = cleaned_text.replace('\n', '\\n').replace('\t', '\\t')
                    data = json.loads(cleaned_text)
                else:
                    # If direct parse fails, sometimes models add extra text. 
                    # We rely on clean_json_text, but if that fails, retry.
                    raise e 

            # Fix Quiz Options (Map A/B/C/D to full text if needed)
            if 'quiz' in data and isinstance(data['quiz'], list):
                idx_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                for q in data['quiz']:
                    ans = str(q.get('correct_answer', '')).replace('.', '').strip().upper()
                    opts = q.get('options', [])
                    # If answer is "A", convert it to the actual text of Option A
                    if ans in idx_map and idx_map[ans] < len(opts):
                        q['correct_answer'] = opts[idx_map[ans]]
            
            return data

        except Exception as e:
            print(f"⚠️ AI JSON Error (Attempt {attempt+1}): {e}")
            # Backoff for rate limits
            if "503" in str(e) or "429" in str(e): time.sleep(2)
            
    return None

# --- 📸 SMART WIKIMEDIA SEARCH ---

def search_wikimedia_image(search_term):
    """
    Searches Wikimedia Commons for a SPECIFIC term provided by the AI.
    Returns the URL of the first valid image found.
    """
    if not search_term or len(search_term) < 3: 
        return None

    url = "https://commons.wikimedia.org/w/api.php"
    print(f"🔍 AI Requested Image Search: '{search_term}'")
    
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {search_term}", 
        "gsrnamespace": 6, 
        "gsrlimit": 3,     
        "prop": "imageinfo",
        "iiprop": "url",   
        "format": "json"
    }

    try:
        # ✅ FIX: Enhanced User-Agent to prevent 403 blocks
        headers = { 
            'User-Agent': 'LearnAI_Educational_Project/1.0 (contact: admin@learnai.local)',
            'Accept': 'application/json'
        }
        
        res = requests.get(url, params=params, headers=headers, timeout=10)
        
        # ✅ FIX: Check if the request was blocked/failed before parsing JSON
        if res.status_code != 200:
            print(f"⚠️ Wiki Search Failed: Status {res.status_code}")
            return None

        data = res.json()
        
        pages = data.get("query", {}).get("pages", {})
        
        for page_id, page_data in pages.items():
            image_info = page_data.get("imageinfo", [{}])[0]
            image_url = image_info.get("url")
            
            # Filter for common image formats
            if image_url and ('.jpg' in image_url.lower() or '.png' in image_url.lower() or '.jpeg' in image_url.lower()):
                print(f"✅ Found Image: {image_url}")
                return image_url

    except requests.exceptions.JSONDecodeError:
        print(f"⚠️ Wiki JSON Error. Raw response was not JSON (likely HTML error page).")
    except Exception as e:
        print(f"⚠️ Wiki Search Error: {e}")
        
    return None

# --- CONTENT GENERATION FUNCTIONS ---

def generate_topic_intro(topic):
    prompt = f"""
    The user wants to learn about: '{topic}'.
    Generate a concise but engaging introduction.
    
    You MUST return the result as a valid JSON object. Do not include any text outside the JSON object.
    
    JSON Structure: 
    {{ 
        "topic": "{topic}", 
        "intro": "**Markdown introduction** covering what it is, why it's important, and real-world applications.", 
        "hook": "A short, catchy tagline (max 10 words)." 
    }}
    """
    return _get_json_response(prompt) or {
        "topic": topic, 
        "intro": f"Welcome to **{topic}**! Let's start learning.", 
        "hook": "Start your journey."
    }

def generate_roadmap(topic):
    prompt = f"""
    Create a comprehensive learning roadmap for '{topic}'.
    Break the topic down into exactly 4-6 logical modules.
    
    You MUST return the result as a valid JSON object.
    
    JSON Structure: 
    {{ 
        "topic_name": "{topic}",
        "roadmap": [ 
            {{ "title": "Module 1: Foundations", "description": "Core concepts" }},
            {{ "title": "Module 2: Advanced Topics", "description": "Deep dive" }}
        ] 
    }}
    """
    return _get_json_response(prompt) or {"roadmap": []}

def generate_sub_roadmap(topic_name, module_title):
    prompt = f"""
    The user is learning '{topic_name}'. Current Module: '{module_title}'.
    Break this into 4-6 specific, bite-sized lessons.
    
    You MUST return the result as a valid JSON object.
    
    JSON Structure:
    {{ 
        "sub_roadmap": [ 
            {{ "title": "Lesson 1 Title", "description": "Brief overview" }},
            {{ "title": "Lesson 2 Title", "description": "Brief overview" }}
        ] 
    }}
    """
    return _get_json_response(prompt) or {"sub_roadmap": []}

def generate_node_content(topic_name, node_title):
    """
    Generates the lesson text, quiz, and decides on an image search term.
    It inserts the image into the markdown text automatically replacing [IMAGE].
    """
    prompt = f"""
    Teach the lesson: '{node_title}' (Part of topic: '{topic_name}').
    Target Audience: Beginner/Intermediate Student.
    Tone: Engaging, Clear, Educational.
    
    You MUST return the result as a valid JSON object.
    
    JSON Structure:
    {{
        "content": "Full markdown lesson text here. Use headers (##), bold text, and lists. IMPORTANT: Insert the tag [IMAGE] exactly once in the text where a diagram or photo would be most helpful.",
        "image_search_term": "A specific, simple search query for Wikimedia Commons (e.g. 'Binary Search Tree Diagram' or 'Mitochondria structure'). Do not use generic words like 'image'.",
        "quiz": [
            {{
                "question": "Question text?", 
                "options": ["Option A", "Option B", "Option C", "Option D"], 
                "correct_answer": "Option A", 
                "explanation": "Why is this correct?"
            }},
            {{ "question": "...", "options": [...], "correct_answer": "...", "explanation": "..." }},
            {{ "question": "...", "options": [...], "correct_answer": "...", "explanation": "..." }}
        ]
    }}
    """
    
    data = _get_json_response(prompt)
    
    if data and data.get('content'):
        # 1. Get the search term the AI suggested
        search_term = data.get('image_search_term')
        
        # 2. Find a real image URL using that term
        image_url = search_wikimedia_image(search_term)
        
        # 3. Inject image into Markdown content
        content = data['content']
        
        if image_url:
            # Replace [IMAGE] with standard Markdown image syntax
            # We add a caption using the search term
            image_markdown = f"\n\n![{search_term}]({image_url})\n*Figure: {search_term}*\n\n"
            content = content.replace("[IMAGE]", image_markdown)
        else:
            # If search failed or no term, just remove the tag
            content = content.replace("[IMAGE]", "")
            
        data['content'] = content
        
        # (Optional) Return URL separately if needed by frontend
        if image_url: data['image_url'] = image_url
        
        return data

    # Fallback if generation fails
    return {
        "content": f"## {node_title}\n\nContent generation failed. Please try again.",
        "quiz": [],
        "image_url": None
    }

def generate_doubt_answer(node_title, context, user_question):
    prompt = f"""
    Context: The user is learning '{node_title}'.
    User Question: "{user_question}"
    
    Answer as a helpful AI Tutor. Keep it short (max 3 sentences) and encouraging.
    """
    try:
        # ✅ FIX: Removed explicit model call config to avoid unsupported params
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )
        return response.text
    except:
        return "I'm having trouble connecting to my brain right now. Try again?"

def generate_remedial_content(topic_name, node_title, failed_questions):
    prompt = f"""
    The student failed a quiz on '{node_title}' (Topic: '{topic_name}').
    They struggled with these concepts: {failed_questions}.
    
    Rewrite the lesson to be simpler (Explain Like I'm 10). 
    Focus on the areas they failed.
    
    You MUST return the result as a valid JSON object.
    
    JSON Structure:
    {{
        "content": "Simplified markdown content...",
        "quiz": [ ... easier questions ... ]
    }}
    """
    return _get_json_response(prompt)