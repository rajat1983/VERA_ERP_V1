import requests
from bs4 import BeautifulSoup

REALTIME_KEYWORDS = [
    "who is", "current", "latest", "now", "today", "news",
    "price", "score", "update", "recent", "live"
]

def needs_realtime(query):
    q = query.lower()
    return any(k in q for k in REALTIME_KEYWORDS)

def fetch_from_wikipedia(query):
    try:
        api_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        res = requests.get(api_url, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        return data.get("extract")
    except:
        return None

def fetch_from_duckduckgo(query):
    try:
        url = "https://duckduckgo.com/html/"
        params = {"q": query}
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.post(url, data=params, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        snippets = soup.select(".result__snippet")
        text = " ".join(s.get_text() for s in snippets[:3])
        return text.strip() if text else None
    except:
        return None

def fetch_realtime_context(query):
    wiki = fetch_from_wikipedia(query)
    ddg = fetch_from_duckduckgo(query)

    combined = ""
    if wiki:
        combined += wiki + "\n"
    if ddg:
        combined += ddg

    return combined.strip() if combined.strip() else None
