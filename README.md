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
# Optional — for the deep British documentary voice:
ELEVENLABS_API_KEY=your_key_from_elevenlabs.io
```

> Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com) → "Get API key".
> Each person uses their own key.
>
> **Voice:** without `ELEVENLABS_API_KEY` the app uses the browser's built-in
> voice (robotic). Add a free [elevenlabs.io](https://elevenlabs.io) key to get a
> lifelike deep British voice. Optional overrides: `ELEVENLABS_VOICE_ID`
> (defaults to "George") and `ELEVENLABS_MODEL` (defaults to `eleven_flash_v2_5`).

Run the backend:

```bash
python app.py          # serves on http://localhost:3000
```

Then open **http://localhost:3000/** in Chrome, grant camera access, and hit **Start Documentary**.

## How it works

```
Browser (webcam) --base64 JPEG--> Flask /narrate --image--> Gemini --text--> Browser (caption + TTS)
```

- **Frontend** (`public/index.html`): captures a webcam frame every ~5s, POSTs it, shows the caption, and speaks it with the browser's Speech Synthesis.
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
