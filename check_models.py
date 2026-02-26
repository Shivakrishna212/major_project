from google import genai
import os


client = genai.Client(api_key=API_KEY)

print("Fetching available models...")
try:
    # simply list them all to find the right name
    for m in client.models.list():
        print(f"Found: {m.name}")
            
except Exception as e:
    print(f"Error: {e}")
