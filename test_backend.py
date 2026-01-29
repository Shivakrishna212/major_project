import requests
import time

BASE_URL = "http://127.0.0.1:5000/api"

def test_topic_generation():
    print("--- TESTING BACKEND FLOW (TOPIC) ---")
    
    # 1. Send the Request (Simulating React)
    payload = {"topic": "The Water Cycle"}
    print(f"1. Sending request for: {payload['topic']}...")
    
    try:
        response = requests.post(f"{BASE_URL}/topic", json=payload)
        
        if response.status_code == 201:
            data = response.json()
            narrative_id = data['narrative_id']
            print(f"✅ Success! Created Narrative ID: {narrative_id}")
            return narrative_id
        else:
            print(f"❌ Failed. Status: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def test_get_narrative(narrative_id):
    print("\n--- TESTING DATA RETRIEVAL ---")
    
    # 2. Retrieve the data (Simulating the User reading the story)
    print(f"2. Fetching Narrative ID: {narrative_id}...")
    
    response = requests.get(f"{BASE_URL}/narrative/{narrative_id}")
    
    if response.status_code == 200:
        data = response.json()
        story_preview = str(data['story'])[:50]
        quiz_count = len(data['quiz'])
        
        print(f"✅ Data Retrieved!")
        print(f"   Story Preview: {story_preview}...")
        print(f"   Quiz Questions: {quiz_count}")
        return True
    else:
        print(f"❌ Failed to get data.")
        return False

if __name__ == "__main__":
    # Wait a second to make sure server is ready
    time.sleep(1)
    
    # Run tests
    n_id = test_topic_generation()
    if n_id:
        test_get_narrative(n_id)