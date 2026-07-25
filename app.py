"""Attenborough Mode — backend proxy.

POST /narrate
  body: { "image": "<base64 jpeg, no data: prefix>" }
  resp: { "narration": "Here, in the fluorescent glow of the conference room..." }

POST /tts
  body: { "text": "..." }
  resp: audio/wav spoken by Gemini TTS with a smooth, flowing documentary
        delivery. Falls back to browser TTS only if the call errors.
"""
import base64
import io
import os
import time
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
TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Charon").strip()
# Delivery direction — read as a style instruction, not spoken aloud. Tuned
# for smooth, continuous delivery (no awkward gaps): tested ~9.8s vs ~18.4s
# for the older "dramatic pauses" wording on the same line.
TTS_STYLE = (
    "Narrate in a warm, intimate wildlife-documentary style with quiet wonder "
    "and gentle curiosity. Keep the delivery smooth, natural, and continuous "
    "at a moderately brisk pace. Use subtle emphasis on important words, but "
    "avoid long or frequent pauses. Let sentences flow together naturally so "
    "the narration stays engaging and matches live video without awkward gaps."
)
# Gemini TTS returns raw PCM: 24 kHz, 16-bit, mono.
TTS_RATE, TTS_WIDTH, TTS_CHANNELS = 24000, 2, 1
# The TTS preview model can hiccup under load; retry before falling back.
TTS_RETRIES = int(os.environ.get("TTS_RETRIES", "3"))

# --- Pacing / flow --------------------------------------------------------
# If a narration would be spoken in less time than the frontend's sampling
# interval, the player drains the queue faster than it refills → silent gaps.
# So we lengthen short lines with in-character filler until they roughly span
# the interval, keeping playback continuous.
TARGET_SECONDS = float(os.environ.get("TARGET_SECONDS", "6.5"))  # ~ frontend INTERVAL_MS
WORDS_PER_SEC = 2.0  # measured pace of this TTS voice (~19 words ≈ 9.8s)

client = genai.Client()  # reads GEMINI_API_KEY from the environment


def estimate_seconds(text: str) -> float:
    """Rough spoken duration of a line, from its word count."""
    return len(text.split()) / WORDS_PER_SEC


def elongate(text: str) -> str:
    """Expand a too-short narration with gentle filler so playback stays gapless.

    Note: we deliberately do NOT ask for a word count — that makes the model
    visibly "count" and leak its reasoning into the output.
    """
    prompt = (
        "You are Sir David Attenborough narrating wildlife. Take this single "
        "narration line and say it again as ONE longer, unbroken, flowing "
        "passage — linger on the SAME moment with a little more gentle detail "
        "so it takes a few seconds longer to speak aloud. Do not add notes, "
        "labels, quotation marks, or word counts. Output ONLY the narration "
        "passage itself:\n\n" + text
    )
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.85,
                # This rewrite spends a lot of tokens "thinking"; give it plenty
                # of headroom so the expanded line is never truncated.
                max_output_tokens=600,
                thinking_config=types.ThinkingConfig(thinking_budget=128),
            ),
        )
        return (resp.text or "").strip() or text
    except Exception as e:
        print("elongate error:", e)
        return text


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
documentary. The image is a frame from a camera observing "wildlife" — which \
is really just an ordinary person (or people) going about everyday life.

Narrate ONLY what you can actually see happening in THIS frame, as if it were \
rare and fascinating animal behaviour. Be witty, warm, and gently absurd. \
Treat whatever mundane action you observe — a gesture, a stretch, a sip, a \
glance, a bit of fidgeting, tidying, eating, chatting — as a remarkable \
evolutionary adaptation or survival ritual. Do NOT assume a setting or activity \
you cannot see (do not mention coding, computers, or offices unless they are \
clearly visible in the frame).

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


@app.after_request
def no_cache(resp):
    # During active dev/demo, never let the browser run a stale index.html.
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


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
                # gemini-flash-latest is a thinking model that can spend a lot
                # of tokens reasoning; give generous headroom so the 1-2 sentence
                # narration is never truncated mid-line.
                max_output_tokens=500,
                thinking_config=types.ThinkingConfig(thinking_budget=128),
            ),
        )
        text = (resp.text or "").strip() or "The creature has momentarily eluded us."
        # Keep playback gapless: stretch lines that would be too short to speak.
        if estimate_seconds(text) < TARGET_SECONDS:
            text = elongate(text)
        history.append(text)
        del history[:-5]  # keep memory bounded
        return jsonify(narration=text)
    except Exception as e:  # never crash the demo — always return a line
        print("narrate error:", e)
        return jsonify(narration="Here, the wildlife retreats into shadow, beyond our lens.")


@app.post("/tts")
def tts():
    """Speak narration via Gemini TTS with a smooth documentary delivery.

    The TTS model is a preview model that occasionally returns transient
    "high demand" (503) errors. We retry a few times so a momentary blip
    doesn't drop the listener to the robotic browser voice.
    """
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify(error="no text"), 400

    last_err = None
    for attempt in range(TTS_RETRIES):
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
            last_err = e
            print(f"tts error (attempt {attempt + 1}/{TTS_RETRIES}):", e)
            time.sleep(0.6 * (attempt + 1))  # brief backoff before retrying

    # All retries failed — frontend falls back to the browser voice.
    print("tts giving up:", last_err)
    return jsonify(error="tts failed"), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
