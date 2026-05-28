import urllib.request
import urllib.parse
import re
import ssl

def ddg_lite_search(query: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    url = "https://lite.duckduckgo.com/lite/"
    data = urllib.parse.urlencode({'q': query}).encode('utf-8')
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, context=context, timeout=5) as response:
            html = response.read().decode('utf-8')
            
            # Extract links and descriptions
            # In DDG Lite:
            # Table contains result links and snippets
            # Links: <td class="result-snippet">...</td> or standard tables
            # Snippets are usually in <td class="result-snippet">...</td>
            # Title is in <a class="result-link" href="...">...</a>
            
            titles = re.findall(r'<a[^>]+class="result-link"[^>]*>(.*?)</a>', html, re.DOTALL)
            snippets = re.findall(r'<td class="result-snippet"[^>]*>(.*?)</td>', html, re.DOTALL)
            
            results = []
            for i in range(min(3, len(titles), len(snippets))):
                title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                snippet = re.sub(r'\s+', ' ', snippet)
                results.append(f"Source {i+1}: {title}\nSummary: {snippet}")
                
            if not results:
                return f"No general web results found."
            return "\n\n".join(results)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print(ddg_lite_search("berita terpopuler hari ini"))
