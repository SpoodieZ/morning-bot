import subprocess
import json
import requests
import random
import os
import re

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TEMPO_BIN = os.path.expanduser("~/.tempo/bin/tempo")

topics = [
    "best stoic quotes marcus aurelius seneca epictetus",
    "motivational quotes success perseverance famous",
    "life wisdom philosophical quotes meaning purpose",
    "quotes happiness inner peace mindfulness",
    "famous quotes growth learning change",
    "quotes courage facing fear overcoming obstacles",
    "quotes kindness compassion humanity",
    "buddhist zen wisdom quotes",
    "quotes about time priorities what matters",
    "quotes discipline focus hard work",
]

topic = random.choice(topics)
print(f"Searching topic: {topic}")

try:
    result = subprocess.run(
        [TEMPO_BIN, "request", "-X", "POST",
         "--json", json.dumps({
             "query": topic,
             "numResults": 5,
             "text": {"maxCharacters": 800},
             "includeDomains": [
                 "brainyquote.com", "goodreads.com",
                 "azquotes.com", "wisdomquotes.com", "quotefancy.com"
             ]
         }),
         "https://exa.mpp.tempo.xyz/search"],
        capture_output=True, text=True, timeout=60
    )

    quotes = []
    if result.returncode == 0:
        data = json.loads(result.stdout)
        for r in data.get("results", []):
            text = r.get("text", "")
            title = r.get("title", "")
            lines = [l.strip() for l in text.replace('\n', '|').split('|') if l.strip()]
            for line in lines:
                line = line.strip('"').strip("'").strip()
                if 40 < len(line) < 220 and not line.startswith("http") and not line[0].isdigit():
                    quotes.append((line, title))

    if quotes:
        quote, source = random.choice(quotes[:10])
        print(f"Found {len(quotes)} quote candidates")
    else:
        fallbacks = [
            ("The impediment to action advances action. What stands in the way becomes the way.", "Marcus Aurelius"),
            ("You have power over your mind, not outside events. Realize this, and you will find strength.", "Marcus Aurelius"),
            ("In the middle of every difficulty lies opportunity.", "Albert Einstein"),
            ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
            ("The journey of a thousand miles begins with one step.", "Lao Tzu"),
        ]
        quote, source = random.choice(fallbacks)
        print("Using fallback quote")

except Exception as e:
    print(f"Error: {e}")
    quote = "The obstacle is the way."
    source = "Marcus Aurelius"

quote = re.sub(r'\s+', ' ', quote).strip()
message = f"☀️ *Quote buổi sáng*\n\n✨ _{quote}_\n\n📖 _{source}_"

resp = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
    timeout=10
)
print(f"Telegram response: {resp.status_code} - {resp.text[:100]}")
