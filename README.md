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

## Notes

- Model: `gemini-flash-latest` (the plan's `gemini-2.0-flash` is unavailable on new free-tier accounts). It's a thinking model, so the backend sets a small `thinking_budget` and a generous token cap.
- Two modes: **live webcam** and **upload a video** — both narrated by the same pipeline, with a downloadable transcript.
- Run in stable mode with `python app.py`; set `FLASK_DEBUG=1` for auto-reload while developing.
- Full build plan and phased timeline: [`Attenborough-Mode-Build-Plan.md`](Attenborough-Mode-Build-Plan.md).
