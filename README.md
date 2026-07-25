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
> provider, no extra setup. It's instructed to deliver lines like a wildlife
> documentary, with dramatic pauses and emphasis. Change the voice with
> `GEMINI_TTS_VOICE` (default "Charon"). If TTS ever errors, it falls back to
> the browser's built-in voice automatically.

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
```

## Notes

- Model: `gemini-flash-latest` (the plan's `gemini-2.0-flash` is unavailable on new free-tier accounts). It's a thinking model, so the backend sets a small `thinking_budget` and a generous token cap.
- Full build plan and phased timeline: [`Attenborough-Mode-Build-Plan.md`](Attenborough-Mode-Build-Plan.md).
