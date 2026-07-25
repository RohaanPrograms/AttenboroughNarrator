# 🦁 Attenborough Mode

> Webcam → a frame every few seconds → **Gemini** narrates whatever you're doing as a nature documentary → spoken aloud. Zero utility, maximum demo energy.

## Quick start

```bash
git clone https://github.com/RohaanPrograms/AttenboroughNarrator.git
cd AttenboroughNarrator
pip install -r requirements.txt
```

Create a `.env` file in the project root (it's gitignored — **never commit it**):

```
GEMINI_API_KEY=your_key_from_aistudio.google.com
# Optional voice overrides:
# GEMINI_TTS_VOICE=Charon      # try: Orus, Fenrir, Puck, Kore
```

> Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com) → "Get API key".
> Each person uses their own key.
>
> **Voice:** narration is spoken by **Gemini TTS** using the *same* key — one
> provider, no extra setup. It's instructed to deliver lines in a smooth,
> flowing wildlife-documentary style with a refined British (RP) accent. Change
> the voice with `GEMINI_TTS_VOICE` (default "Charon"). If TTS ever errors, it
> falls back to the browser's built-in voice automatically.

Run the backend:

```bash
python app.py          # serves on http://localhost:3000
```

Then open **http://localhost:3000/** in Chrome, grant camera access, and hit **Start Documentary**.

## Two ways to use it

- **Live** — hit **Start Documentary**, allow the camera, and it narrates you in real time.
- **Upload a Video** — pick any video file and it narrates that instead.

Both modes also give you a **downloadable transcript** of every narrated line
(with timestamps).

## Recording & narrated-video export

- **Uploaded videos download automatically.** When an uploaded clip finishes,
  the browser saves **`attenborough-narrated-video.webm`** — the source video
  (kept at its own aspect ratio) with the Gemini narration mixed in and the
  subtitles burned on. Documentary-style: narration over the (muted) footage.
- **Live sessions:** tick **"Record live session as a video"** on the home
  screen before you start; it downloads **`attenborough-recording.webm`** when
  you press Stop.

How it's made: the frame + subtitles are composited onto a `<canvas>`
(`captureStream`), the Gemini TTS audio is tapped via the Web Audio API, and
both tracks are muxed by `MediaRecorder` into a WebM. Narration trails the
video slightly (AI latency), and the recording runs a touch past the end so the
final lines finish — so the export is a little longer than the source. Lines
that fall back to the browser voice (rare) aren't captured in the audio.

## How it works

```
Browser (webcam) --base64 JPEG--> Flask /narrate --image--> Gemini --text--> Browser (caption + TTS)
```

- **Frontend** (`public/index.html`): captures a webcam frame every ~6s, POSTs it, shows the caption, and plays the spoken audio (queued so lines never overlap).
- **Backend** (`app.py`): `/narrate` proxy that holds the API key and calls Gemini with the Attenborough system prompt.

## API contract

```
POST /narrate
  body: { "image": "<base64 jpeg, no data: prefix>" }
  resp: { "narration": "Here, in the fluorescent glow of the conference room..." }

POST /tts
  body: { "text": "..." }
  resp: audio/wav  (Gemini TTS, British documentary voice)
```

## Powered by Gemini

The **entire pipeline runs on Gemini** through one key and the official
`google-genai` SDK — multimodal vision describes the scene, text generation
shapes it, and native TTS speaks it. No other AI services involved.

| Gemini feature | Where we use it |
|---|---|
| **Multimodal vision** (image + text → text) | Send each frame (JPEG) + instruction to `generate_content` → the narration. Model `gemini-flash-latest`. |
| **Native Text-to-Speech** (text → audio) | `generate_content` with `response_modalities=["AUDIO"]` + `SpeechConfig`/`PrebuiltVoiceConfig`. Model `gemini-3.1-flash-tts-preview`, voice "Charon". |
| **Prompt-controlled voice delivery** | Accent (British RP), pace, and emphasis are steered purely by a natural-language style prompt prefixed to the TTS text. |
| **Thinking budget control** | `ThinkingConfig(thinking_budget=128)` caps internal reasoning so lines aren't truncated (both models are thinking models). |
| **Generation config** | `temperature` (playful variety) and `max_output_tokens` (length/cost). |
| **Text generation** | `elongate()` rewrites too-short narrations into longer flowing passages so audio playback stays gapless. |
| **Prompt engineering + continuity** | A crafted system prompt, plus the last 3 narrations fed back in so it doesn't repeat itself and builds a loose story. |
| **Model discovery** | `client.models.list()` to find the TTS model available on the account. |

## Future improvements

**Reduce the delay between on-screen movement and the narration/transcript.**
Today a frame is sampled every ~6s, then vision → text → TTS run in sequence
and the audio is buffered in a small queue, so a narrated line can trail the
action by roughly 10–20s. Ideas to tighten that:

- **Gemini Live API** — stream audio + video in real time instead of the
  frame-by-frame request/response loop. The single biggest win; narration
  could react to movement in near real time.
- **Streaming responses** — stream the narration text token-by-token and
  begin TTS on the first sentence rather than waiting for the whole reply.
- **Motion-triggered sampling** — detect frame changes client-side and narrate
  when something actually happens, instead of on a fixed timer, so lines track
  real movement rather than arbitrary intervals.
- **Trim the pipeline** — a faster / lower-thinking model, smaller frames, and
  a shorter interval / queue reduce end-to-end latency (trading some
  gap-filling and detail).
- **Skip the elongation round-trip** — pre-size narrations to the interval in
  the first call instead of a second `generate_content` to lengthen short
  lines.
- **Pre-fetch the next frame** — kick off the next request slightly before the
  current line finishes so audio is always ready with no idle gap.

## Notes

- Model: `gemini-flash-latest` (the plan's `gemini-2.0-flash` is unavailable on new free-tier accounts). It's a thinking model, so the backend sets a small `thinking_budget` and a generous token cap.
- Two modes: **live webcam** and **upload a video** — both narrated by the same pipeline, with a downloadable transcript.
- Run in stable mode with `python app.py`; set `FLASK_DEBUG=1` for auto-reload while developing.
- Full build plan and phased timeline: [`Attenborough-Mode-Build-Plan.md`](Attenborough-Mode-Build-Plan.md).
