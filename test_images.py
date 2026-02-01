from ai_service import search_wikimedia_image

print("Testing Wikipedia Image Search...")
# Try a topic that likely has diagrams on Wikipedia
url = search_wikimedia_image("mvc", "architecture")

if url:
    print(f"✅ Success! Image: {url}")
else:
    print("❌ No image found (or download failed).")