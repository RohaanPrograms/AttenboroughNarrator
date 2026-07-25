"""Attenborough Mode — backend proxy.

POST /narrate
  body: { "image": "<base64 jpeg, no data: prefix>" }
  resp: { "narration": "Here, in the fluorescent glow of the conference room..." }

POST /tts
  body: { "text": "..." }
  resp: audio/mpeg (MP3) spoken in a deep British voice via ElevenLabs.
        503 if no ELEVENLABS_API_KEY is set (frontend falls back to browser TTS).
"""
import base64
import os

import requests
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types

# Load .env if present; otherwise rely on the shell environment.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# gemini-2.0-flash from the build plan is dead on this account (free-tier
# limit 0). gemini-flash-latest is the working stand-in.
MODEL = "gemini-flash-latest"

# --- ElevenLabs (TTS) config ---------------------------------------------
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
# Default: "George" — a warm, deep British male voice from the ElevenLabs
# default library. Override with ELEVENLABS_VOICE_ID for a different voice.
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb").strip()
# flash model = lowest latency + cheapest, ideal for a live demo.
ELEVEN_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5").strip()

client = genai.Client()  # reads GEMINI_API_KEY from the environment

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

# In-memory continuity: keep the last couple of narrations so Gemini can
# avoid repeating itself and build a loose "story."
history = []  # list[str], most recent last

SYSTEM_PROMPT = """You are Sir David Attenborough narrating a live nature \
documentary. The image is a frame from a webcam observing "wildlife" — which \
is actually just people in a room at a hackathon.

Narrate what you see as if it were rare and fascinating animal behaviour. Be \
witty, warm, and gently absurd. Treat mundane human actions (typing, drinking \
coffee, scrolling a phone) as remarkable evolutionary adaptations or survival \
rituals.

RULES:
- 1 to 2 sentences ONLY. This is spoken aloud in real time.
- Stay in character as Attenborough at all times. Never break the fourth wall.
- VARY your sentence openings. Do NOT reuse an opening from your recent lines \
below. Rotate between styles like "Here we see...", "Observe...", "In a rare \
moment...", "And now...", "Notice how...", or diving straight into the action.
- Reference specific things you actually see in THIS frame.
- Do not repeat observations or phrasing from your recent narration below.
- If the frame is unclear or dark, treat it as the creature retreating into \
shadow — never say "I can't see."

Your recent narration (for continuity — do NOT repeat these):
{recent}"""


def build_prompt():
    recent = "\n".join(f"- {line}" for line in history[-3:]) or "- (none yet)"
    return SYSTEM_PROMPT.format(recent=recent)


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok", model=MODEL, tts="elevenlabs" if ELEVEN_KEY else "browser")


@app.post("/narrate")
def narrate():
    try:
        image_b64 = request.json["image"]
        img_bytes = base64.b64decode(image_b64)

        resp = client.models.generate_content(
            model=MODEL,
            contents=[
                build_prompt(),
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            ],
            config=types.GenerateContentConfig(
                temperature=0.95,
                # gemini-flash-latest is a thinking model. It spends output
                # tokens on internal reasoning, so cap thinking low and leave
                # generous room for the actual 1-2 sentence narration.
                max_output_tokens=250,
                thinking_config=types.ThinkingConfig(thinking_budget=128),
            ),
        )
        text = (resp.text or "").strip() or "The creature has momentarily eluded us."
        history.append(text)
        del history[:-5]  # keep memory bounded
        return jsonify(narration=text)
    except Exception as e:  # never crash the demo — always return a line
        print("narrate error:", e)
        return jsonify(narration="Here, the wildlife retreats into shadow, beyond our lens.")


@app.post("/tts")
def tts():
    """Turn narration text into MP3 audio via ElevenLabs (deep British voice)."""
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify(error="no text"), 400
    if not ELEVEN_KEY:
        # No key configured — tell the frontend to use its browser-TTS fallback.
        return jsonify(error="no ELEVENLABS_API_KEY set"), 503
    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}",
            headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": ELEVEN_MODEL,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        if r.status_code != 200:
            print("tts error:", r.status_code, r.text[:200])
            return jsonify(error="tts failed", status=r.status_code), 502
        return Response(r.content, mimetype="audio/mpeg")
    except Exception as e:
        print("tts exception:", e)
        return jsonify(error="tts exception"), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
