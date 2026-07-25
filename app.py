"""Attenborough Mode — backend proxy.

POST /narrate
  body: { "image": "<base64 jpeg, no data: prefix>" }
  resp: { "narration": "Here, in the fluorescent glow of the conference room..." }

POST /tts
  body: { "text": "..." }
  resp: audio/wav spoken by Gemini TTS with a dramatic documentary delivery
        (pauses + emphasis). Falls back to browser TTS only if the call errors.
"""
import base64
import io
import os
import wave

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

# --- Gemini TTS config ----------------------------------------------------
# One provider for both narration and voice — no separate key needed.
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview").strip()
# Prebuilt voice. "Charon" = deep + informative, a good Attenborough fit.
# Alternatives to try: "Orus" (firm), "Fenrir" (excitable), "Puck", "Kore".
TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Orus").strip()
# Delivery direction — read as a style instruction, not spoken aloud. Kept
# smooth and flowing (no "dramatic pauses") so lines don't feel awkward.
TTS_STYLE = (
    "Narrate this in a warm, engaging wildlife-documentary voice with a "
    "smooth, natural, flowing delivery at a lively and steady pace:"
)
# Gemini TTS returns raw PCM: 24 kHz, 16-bit, mono.
TTS_RATE, TTS_WIDTH, TTS_CHANNELS = 24000, 2, 1

client = genai.Client()  # reads GEMINI_API_KEY from the environment


def pcm_to_wav(pcm: bytes) -> bytes:
    """Wrap raw PCM from Gemini TTS in a WAV header the browser can play."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(TTS_CHANNELS)
        w.setsampwidth(TTS_WIDTH)
        w.setframerate(TTS_RATE)
        w.writeframes(pcm)
    return buf.getvalue()

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
- 1 to 2 sentences. Enough for a vivid, detailed observation, but no more — \
it is spoken aloud in real time. Keep the posh Attenborough formality.
- Stay in character as Attenborough at all times. Never break the fourth wall.
- VARY your sentence openings. Do NOT reuse an opening from your recent lines \
below. Rotate between styles like "Here we see...", "Observe...", "In a rare \
moment...", "And now...", "Notice how...", or diving straight into the action.
- Reference specific things you actually see in THIS frame.
- Do not repeat observations or phrasing from your recent narration below.
- If the frame is unclear or dark, treat it as the creature retreating into \
shadow — never say "I can't see."
- COMEDY SPICE: sparingly — roughly one line in three, never every line — slip \
ONE bit of Gen Z slang into your otherwise posh narration for absurd contrast \
(e.g. "lowkey", "no cap", "it's giving", "rizz", "cooked", "the audacity", \
"understood the assignment", "menace behaviour", "ate"). Keep the plummy \
Attenborough cadence around it; the joke is the clash. Do not overuse it and \
never let it become the whole sentence.

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
    return jsonify(status="ok", model=MODEL, tts="gemini", voice=TTS_VOICE)


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
                # room for a 1-2 sentence narration.
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
    """Speak narration via Gemini TTS with dramatic documentary delivery."""
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify(error="no text"), 400
    try:
        resp = client.models.generate_content(
            model=TTS_MODEL,
            contents=f"{TTS_STYLE} {text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=TTS_VOICE
                        )
                    )
                ),
            ),
        )
        pcm = resp.candidates[0].content.parts[0].inline_data.data
        return Response(pcm_to_wav(pcm), mimetype="audio/wav")
    except Exception as e:
        # On any failure the frontend falls back to the browser voice.
        print("tts error:", e)
        return jsonify(error="tts failed"), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
