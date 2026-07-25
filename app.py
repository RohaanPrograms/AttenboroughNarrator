"""Attenborough Mode — backend proxy.

POST /narrate
  body: { "image": "<base64 jpeg, no data: prefix>" }
  resp: { "narration": "Here, in the fluorescent glow of the conference room..." }
"""
import base64
import os

from flask import Flask, jsonify, request, send_from_directory
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

client = genai.Client()  # reads GEMINI_API_KEY from the environment

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

# In-memory continuity: the last narration, fed back for Phase 2.
last = {"text": ""}

SYSTEM_PROMPT = """You are Sir David Attenborough narrating a live nature \
documentary. The image is a frame from a webcam observing "wildlife" — which \
is actually just people in a room at a hackathon.

Narrate what you see as if it were rare and fascinating animal behaviour. Be \
witty, warm, and gently absurd. Treat mundane human actions (typing, drinking \
coffee, scrolling a phone) as remarkable evolutionary adaptations.

RULES:
- 1 to 2 sentences ONLY. This is spoken aloud in real time.
- Stay in character as Attenborough. Never break the fourth wall.
- Vary your sentence openings.
- Reference specific things you actually see in the frame.
- Do not repeat observations from your previous narration (below).
- If the frame is unclear or dark, treat it as the creature retreating into \
shadow — never say "I can't see."

Previous narration (for continuity, do not repeat):
{last_narration}"""


@app.get("/health")
def health():
    return jsonify(status="ok", model=MODEL)


@app.post("/narrate")
def narrate():
    try:
        image_b64 = request.json["image"]
        img_bytes = base64.b64decode(image_b64)
        prompt = SYSTEM_PROMPT.format(last_narration=last["text"] or "(none yet)")

        resp = client.models.generate_content(
            model=MODEL,
            contents=[
                prompt,
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
        last["text"] = text
        return jsonify(narration=text)
    except Exception as e:  # never crash the demo — always return a line
        print("narrate error:", e)
        return jsonify(narration="Here, the wildlife retreats into shadow, beyond our lens.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
