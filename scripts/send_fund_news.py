import subprocess
import json
import requests
import os
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TEMPO_BIN = os.path.expanduser("~/.tempo/bin/tempo")

def search_exa(query, num_results=5, hours_back=24):
    payload = {
        "query": query,
        "numResults": num_results,
        "text": {"maxCharacters": 400},
        "startPublishedDate": get_hours_ago(hours_back),
        "includeDomains": [
            "theblock.co", "coindesk.com", "decrypt.co",
            "cointelegraph.com", "blockworks.co", "dlnews.com",
            "techcrunch.com", "bloomberg.com", "reuters.com"
        ]
    }
    result = subprocess.run(
        [TEMPO_BIN, "request", "-X", "POST",
         "--json", json.dumps(payload),
         "https://exa.mpp.tempo.xyz/search"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout).get("results", [])
        except Exception:
            pass
    return []

def get_hours_ago(hours):
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def fmt_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return ""

# Search queries
queries = [
    "crypto venture capital investment fund raise 2024 2025",
    "web3 fund portfolio investment announcement blockchain",
    "a16z multicoin polychain binance labs investment news",
]

all_results = []
seen_urls = set()

for query in queries:
    results = search_exa(query, num_results=4, hours_back=48)
    for r in results:
        url = r.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            all_results.append(r)

# Deduplicate and sort by date
all_results = sorted(
    all_results,
    key=lambda x: x.get("publishedDate") or "",
    reverse=True
)[:7]

if not all_results:
    message = "📰 *Tin tức quỹ đầu tư Crypto/Web3*\n\n_Không tìm thấy tin mới trong 48h qua._"
else:
    lines = ["📊 *Tin tức quỹ đầu tư Crypto/Web3 hôm nay*\n"]
    for i, r in enumerate(all_results, 1):
        title = r.get("title", "No title").strip()
        url = r.get("url", "")
        date = fmt_date(r.get("publishedDate", ""))
        text = r.get("text", "").strip()[:150].replace("\n", " ")

        date_txt = f" _({date})_" if date else ""
        lines.append(f"*{i}.* [{title}]({url}){date_txt}")
        if text:
            lines.append(f"_{text}..._\n")

    lines.append("\n_Powered by Exa × Tempo_")
    message = "\n".join(lines)

resp = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    },
    timeout=10
)
print(f"Telegram response: {resp.status_code} - {resp.text[:120]}")
