import os
from google import genai
from google.genai import types

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found.")
    exit(1)

client = genai.Client(api_key=API_KEY)

def test_grounding():
    try:
        # Define Google Search as a tool
        config = types.GenerateContentConfig(
            system_instruction="Jawablah dengan memanfaatkan hasil pencarian Google jika diperlukan.",
            # Native Google Search Tool
            tools=[{"google_search": {}}],
            temperature=0.7
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="siapa juara liga champion eropa tahun ini atau tahun lalu?",
            config=config
        )
        
        print("Response text:")
        print(response.text)
        
        # Check if grounding metadata exists
        metadata = response.candidates[0].grounding_metadata
        if metadata:
            print("\nGrounding Metadata:")
            print(f"Search entry point: {metadata.search_entry_point}")
            print(f"Web search queries: {metadata.web_search_queries}")
            if metadata.grounding_chunks:
                print("\nGrounding Chunks (Sources):")
                for chunk in metadata.grounding_chunks:
                    if chunk.web:
                        print(f"- {chunk.web.title}: {chunk.web.uri}")
        else:
            print("\nNo grounding metadata found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_grounding()
