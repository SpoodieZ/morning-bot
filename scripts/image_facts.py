import subprocess
import json
import time
import os
import urllib.request

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TEMPO_BIN = os.path.expanduser("~/.tempo/bin/tempo")

PERPLEXITY_URL = "https://perplexity.mpp.paywithlocus.com/perplexity/chat"
FLUX_URL = "https://stablestudio.dev/api/generate/flux-2-pro/generate"
JOBS_URL = "https://stablestudio.dev/api/jobs/{}"


def tempo_post(url, body, retries=3):
    for attempt in range(retries):
        result = subprocess.run(
            [TEMPO_BIN, "request", "-j", "-X", "POST", "--json", json.dumps(body), url],
            capture_output=True, text=True, timeout=90
        )
        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode == 0 and output:
            return output
        print(f"  tempo_post attempt {attempt+1}/{retries} failed (rc={result.returncode}): {output[:100]}")
        time.sleep(3)
    raise RuntimeError(f"tempo POST failed after {retries} attempts")


def tempo_get(url):
    result = subprocess.run(
        [TEMPO_BIN, "request", "-j", url],
        capture_output=True, text=True, timeout=30
    )
    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        raise RuntimeError(f"tempo GET failed: {output}")
    return output


def get_fact_and_prompt(index):
    body = {
        "model": "sonar",
        "messages": [{
            "role": "user",
            "content": (
                f"Fact #{index}: Share 1 surprising, fascinating fact about science, history, nature, or technology. "
                "Write on 2 lines exactly:\n"
                "Line 1 (FACT:): The fact in Vietnamese, 2-3 vivid sentences, no opening like 'Đây là' or 'Hôm nay'.\n"
                "Line 2 (IMAGE:): A detailed English prompt for a photo-realistic AI image that visually represents this fact. "
                "Be specific about lighting, colors, scene, style."
            )
        }]
    }
    raw = tempo_post(PERPLEXITY_URL, body)
    content = json.loads(raw)["data"]["choices"][0]["message"]["content"].strip()

    fact_vi = ""
    image_prompt = ""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("FACT:"):
            fact_vi = line[5:].strip()
        elif line.startswith("IMAGE:"):
            image_prompt = line[6:].strip()

    if not fact_vi or not image_prompt:
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        fact_vi = lines[0] if lines else content
        image_prompt = lines[1] if len(lines) > 1 else f"Photo-realistic scene: {fact_vi[:100]}"

    return fact_vi, image_prompt


def generate_image(prompt):
    body = {
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "resolution": "1 MP",
        "output_format": "webp",
    }
    raw = tempo_post(FLUX_URL, body)
    data = json.loads(raw)
    return data["jobId"]


def poll_job(job_id, max_attempts=24, interval=5):
    url = JOBS_URL.format(job_id)
    for attempt in range(max_attempts):
        raw = tempo_get(url)
        data = json.loads(raw)
        status = data.get("status")
        if status == "complete":
            return data["result"]["imageUrl"]
        if status == "error":
            raise RuntimeError(f"Generation failed: {data.get('error')}")
        print(f"  [{attempt+1}] status={status} progress={data.get('progress', '?')}%")
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id} timed out")


def send_photo(photo_url, caption):
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def send_text(message):
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


errors = []
for i in range(1, 3):
    try:
        print(f"\n=== Image fact {i}/2 ===")
        fact_vi, image_prompt = get_fact_and_prompt(i)
        print(f"Fact: {fact_vi[:80]}...")
        print(f"Prompt: {image_prompt[:80]}...")

        job_id = generate_image(image_prompt)
        print(f"Job: {job_id}, polling...")

        image_url = poll_job(job_id)
        print(f"Done: {image_url}")

        caption = f"🎨 <b>Fact #{i} hôm nay</b>\n\n{fact_vi}"
        send_photo(image_url, caption)
        print("Sent to Telegram.")

    except Exception as e:
        msg = f"[Image {i}] {type(e).__name__}: {e}"
        print(f"ERROR: {msg}")
        errors.append(msg)

if errors:
    send_text("⚠️ Image bot lỗi:\n" + "\n".join(errors))
    raise SystemExit(1)

print("\nDone.")
