import subprocess
import json
import requests
import os
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TEMPO_BIN = os.path.expanduser("~/.tempo/bin/tempo")

def get_hours_ago(hours):
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def search_exa(query, num_results=5, hours_back=48, domains=None):
    payload = {
        "query": query,
        "numResults": num_results,
        "text": {"maxCharacters": 350},
        "startPublishedDate": get_hours_ago(hours_back),
    }
    if domains:
        payload["includeDomains"] = domains

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

def fmt_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m")
    except Exception:
        return ""

NEWS_DOMAINS = [
    "theblock.co", "coindesk.com", "cointelegraph.com",
    "decrypt.co", "blockworks.co", "dlnews.com",
    "cryptoslate.com", "cryptorank.io", "defillama.com"
]

# Tìm 2 loại: Airdrop mới + Retroactive/Testnet
airdrop_results   = search_exa(
    "crypto airdrop confirmed upcoming token launch free claim 2025 2026",
    num_results=5, hours_back=72, domains=NEWS_DOMAINS
)
retro_results = search_exa(
    "retroactive airdrop testnet farming points program eligible snapshot web3",
    num_results=5, hours_back=72, domains=NEWS_DOMAINS
)

# Gộp & deduplicate
seen = set()
combined = []
for r in airdrop_results + retro_results:
    url = r.get("url", "")
    if url and url not in seen:
        seen.add(url)
        combined.append(r)

combined = sorted(combined, key=lambda x: x.get("publishedDate") or "", reverse=True)[:8]

# Format tin nhắn
today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

if not combined:
    message = (
        f"🪂 *Airdrop & Retroactive — {today}*\n\n"
        "_Không tìm thấy tin mới trong 72h qua._"
    )
else:
    lines = [f"🪂 *Airdrop & Retroactive — {today}*\n"]

    airdrop_items = [r for r in combined if r in airdrop_results[:5]]
    retro_items   = [r for r in combined if r in retro_results[:5] and r not in airdrop_items]

    if airdrop_items:
        lines.append("📌 *Airdrop đang mở / sắp mở*")
        for r in airdrop_items[:4]:
            title = r.get("title", "").strip()
            url   = r.get("url", "")
            date  = fmt_date(r.get("publishedDate", ""))
            snippet = r.get("text", "").strip()[:120].replace("\n", " ")
            date_txt = f" `{date}`" if date else ""
            lines.append(f"• [{title}]({url}){date_txt}")
            if snippet:
                lines.append(f"  _{snippet}..._")

    if retro_items:
        lines.append("\n🔍 *Retroactive / Testnet / Points*")
        for r in retro_items[:4]:
            title = r.get("title", "").strip()
            url   = r.get("url", "")
            date  = fmt_date(r.get("publishedDate", ""))
            snippet = r.get("text", "").strip()[:120].replace("\n", " ")
            date_txt = f" `{date}`" if date else ""
            lines.append(f"• [{title}]({url}){date_txt}")
            if snippet:
                lines.append(f"  _{snippet}..._")

    lines.append("\n_⚠️ DYOR — Tự nghiên cứu trước khi tham gia_")
    lines.append("_Powered by Exa × Tempo_")
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
