from ai_service import generate_narrative

print("Testing Gemini API...")

# Simulate a user asking about "Photosynthesis"
result = generate_narrative("Photosynthesis", mode="topic_generation")

if result:
    print("\nSUCCESS! Here is what Gemini sent back:")
    print("Story Preview:", result['story'][:100], "...")
    print("Quiz Question 1:", result['quiz'][0]['q'])
else:
    print("\nFAILED. Check your API Key.")