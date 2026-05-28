import urllib.request
import urllib.parse
import json
import ssl

def search_wikipedia(query: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # Query Indonesian Wikipedia
    url = f"https://id.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=context, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            search_results = data.get("query", {}).get("search", [])
            
            if not search_results:
                return f"Tidak ada hasil Wikipedia untuk: {query}"
                
            results = []
            for i, item in enumerate(search_results[:3]):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                # remove html tags like <span class="searchmatch">
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                results.append(f"Wikipedia - {title}\nSnippet: {snippet}")
                
            return "\n\n".join(results)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    import re
    print(search_wikipedia("Presiden Indonesia"))
