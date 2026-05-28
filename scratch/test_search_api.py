import urllib.request
import urllib.parse
import json
import ssl

def web_search_ddg_api(query: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=context, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract fields
            abstract = data.get("AbstractText", "")
            results = []
            
            if abstract:
                results.append(f"Abstract: {abstract}")
                
            related_topics = data.get("RelatedTopics", [])
            for i, topic in enumerate(related_topics[:3]):
                if "Text" in topic:
                    results.append(f"Topic {i+1}: {topic['Text']}")
                    
            if not results:
                # Fallback: maybe it's a search term that doesn't have an instant answer
                # Let's try searching text via a different method, or we can use another simple service.
                return f"No direct instant answer found for: {query}. Try searching specifically."
                
            return "\n\n".join(results)
    except Exception as e:
        return f"Error during search: {str(e)}"

if __name__ == "__main__":
    print(web_search_ddg_api("presiden indonesia"))
    print("\n---\n")
    print(web_search_ddg_api("who is current prime minister of UK"))
