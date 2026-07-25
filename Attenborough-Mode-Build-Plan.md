---
title: Attenborough Mode — Hackathon Build Plan
created: 2026-07-25
tags: [hackathon, gemini, project-plan]
team_size: 2
time_budget: 4 hours
status: planning
---

# 🦁 Attenborough Mode — Build Plan

> **The pitch:** Webcam stream → frames sampled every few seconds → **Gemini** narrates whatever you're doing as a nature documentary → piped through **TTS** → the whole room watches it narrate the judges.
>
> Zero utility. Enormous demo energy. That's the point.

---

## 1. Executive Summary

| Item | Decision |
|------|----------|
| **Core loop** | Capture webcam frame → send to Gemini Vision → get Attenborough-style narration → speak it via TTS |
| **Sampling rate** | 1 frame every **4–6 seconds** (tunable; balances API cost, latency, and "documentary pacing") |
| **Recommended stack** | Single-page **web app** (HTML + vanilla JS) + tiny **backend proxy** to hide the API key |
| **Gemini model** | `gemini-2.0-flash` (fast, cheap, multimodal, great for live demos) |
| **TTS options** | Browser `SpeechSynthesis` (free, instant) → upgrade to **ElevenLabs** (British voice = the money shot) if time allows |
| **Winning factor** | The *voice* and the *prompt personality*. Nail the Attenborough tone. |

**Golden rule for a 4-hour hack:** Get an ugly end-to-end loop working in the first 90 minutes. Everything after is polish. **A working ugly demo beats a beautiful broken one.**

---

## 2. Architecture Overview

```
┌─────────────┐   frame (every ~5s)   ┌──────────────┐
│  Browser    │ ────────────────────► │  Backend     │
│  <video>    │   base64 JPEG          │  proxy       │
│  webcam     │                        │  (Node/py)   │
│             │ ◄──────────────────── │              │
│  Canvas grab│   narration text       │  holds API   │
│  + TTS play │                        │  key         │
└─────────────┘                        └──────┬───────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Google Gemini   │
                                    │  gemini-2.0-flash│
                                    │  (vision + text) │
                                    └──────────────────┘
```

**Why a backend proxy?**
- Keeps your `GEMINI_API_KEY` out of the browser (never ship keys client-side).
- Lets you swap TTS providers server-side later.
- If you're *really* pressed for time, you *can* call Gemini directly from the browser with the key — acceptable for a throwaway demo, but the proxy is ~20 lines and worth it.

**Data flow per tick:**
1. `setInterval` fires every ~5s.
2. Draw current `<video>` frame to a hidden `<canvas>`, export as JPEG (downscale to ~640px wide — smaller = faster + cheaper).
3. POST base64 image to `/narrate`.
4. Backend calls Gemini with the image + system prompt.
5. Return narration string.
6. Frontend feeds text to TTS and plays it.

---

## 3. Tech Stack Decision

### Recommended: Web App (fastest to demo, runs on the presenter laptop)

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | Plain HTML/CSS/JS (no framework) | No build step, no npm hell, instant iteration |
| Webcam | `navigator.mediaDevices.getUserMedia` | Native browser API |
| Frame grab | `<canvas>.toDataURL('image/jpeg', 0.7)` | Built-in |
| Backend | **Node + Express** *or* **Python + Flask** | Whichever the pair knows best |
| Gemini SDK | `@google/genai` (Node) or `google-genai` (Python) | Official, well-documented |
| TTS (v1) | Web Speech API `SpeechSynthesis` | Zero setup, works offline |
| TTS (v2) | ElevenLabs API | British documentary voice = huge upgrade |

### Alternative: Pure Python (if both are Python devs and don't want a browser)
- `opencv-python` for webcam capture + frame sampling
- `google-genai` for Gemini
- `pyttsx3` (offline) or ElevenLabs for TTS
- **Downside:** harder to make it look pretty on the projector. The browser version *looks* like a product.

> **Verdict:** Go **web app**. It demos better and the UI sells the joke.

---

## 4. Phased Timeline (4 Hours)

### ⏱️ Phase 0 — Setup & Alignment (0:00–0:20)
**Both together. Do NOT skip. Misalignment here costs an hour later.**

- [ ] Get a **Google Gemini API key** → [aistudio.google.com](https://aistudio.google.com) → "Get API key" (free tier is fine for a demo).
- [ ] Agree on stack (Node vs Python) — pick what you *both* know.
- [ ] Create repo, `.gitignore` (ignore `.env`, `node_modules`), push skeleton.
- [ ] Create shared `.env` with `GEMINI_API_KEY=...` (and `ELEVENLABS_API_KEY` placeholder).
- [ ] **Test the key works** with a one-line curl/script before writing any app code. (See Appendix A.)
- [ ] Divide ownership (see §5) and agree on the **API contract** between frontend and backend:
  ```
  POST /narrate
  body: { "image": "<base64 jpeg, no data: prefix>" }
  resp: { "narration": "Here, in the fluorescent glow of the conference room..." }
  ```

> ✅ **Exit criteria:** Both can run the repo locally. The Gemini key returns a response from a test script.

---

### ⏱️ Phase 1 — Vertical Slice / End-to-End Skeleton (0:20–1:30)
**Goal: an ugly but COMPLETE loop.** Webcam → Gemini → text on screen → robotic TTS voice. No styling.

**Person A (Frontend/Capture):**
- [ ] Page with `<video>` showing webcam feed (`getUserMedia`).
- [ ] Hidden `<canvas>`; function to grab a frame → base64 JPEG.
- [ ] `setInterval` every 5s → POST to `/narrate` → log response.
- [ ] Display returned narration text as a caption overlay.
- [ ] Wire browser `SpeechSynthesis` to speak the returned text.

**Person B (Backend/Gemini):**
- [ ] Server with `/narrate` endpoint accepting base64 image.
- [ ] Call Gemini `gemini-2.0-flash` with image + a **basic** narration prompt.
- [ ] Return `{ narration }`. Handle errors (return a fallback line, never crash).
- [ ] Add CORS so the frontend can call it locally.

> ✅ **Exit criteria (THE most important milestone):** You point the webcam at yourself, and ~5s later a voice says something about you as if you're wildlife. **If this works by 1:30, you have a demo no matter what.**

---

### ⏱️ Phase 2 — Personality & Prompt Engineering (1:30–2:30)
**This is where the project wins or loses.** The tech is trivial; the *charm* is everything.

**Person B (owns prompt) + Person A (feeds test frames):**
- [ ] Craft the **system prompt** to nail the Attenborough voice (see §6 for a ready-to-use prompt).
- [ ] Add **continuity**: pass the last 1–2 narrations back to Gemini so it doesn't repeat itself and builds a "story."
- [ ] Tune **length**: 1–2 sentences per frame. Long narrations lag behind the TTS and desync.
- [ ] Add **variety controls**: instruct it to vary openings ("Here we see…", "Observe…", "In a rare moment…").
- [ ] Tune **sampling interval** so speech finishes before the next narration starts (avoid overlap — see §8 pacing).

**Person A (parallel — TTS upgrade):**
- [ ] Swap `SpeechSynthesis` for **ElevenLabs** with a deep British male voice (this is a *massive* perceived-quality jump).
- [ ] Backend returns audio (or frontend calls ElevenLabs) → play via `<audio>`.
- [ ] Add a **queue** so narrations play sequentially and never overlap.

> ✅ **Exit criteria:** It sounds like an actual nature documentary. People in the room laugh.

---

### ⏱️ Phase 3 — Demo Polish & UI (2:30–3:20)
**Make it look like a product, not a script.**

**Person A (Frontend/UI):**
- [ ] Fullscreen webcam with cinematic letterbox bars (top/bottom black bars).
- [ ] Animated **subtitle bar** at the bottom (fade in/out, serif font — very BBC).
- [ ] Big **"Start Documentary"** button; a subtle "● REC / LIVE" indicator.
- [ ] Optional: waveform or pulsing dot while narrating.
- [ ] Title card / intro: *"Attenborough Mode — a Nature Documentary"*.

**Person B (Backend/robustness):**
- [ ] Rate-limit / debounce so overlapping requests don't stack up.
- [ ] Graceful fallback narration lines if Gemini errors ("The creature has momentarily eluded us…").
- [ ] Log latency; tune image size + interval for smooth pacing on demo wifi.
- [ ] (Stretch) Cache/skip frames that are nearly identical to save calls.

> ✅ **Exit criteria:** Clean fullscreen experience you'd be proud to project.

---

### ⏱️ Phase 4 — Rehearsal & Buffer (3:20–4:00)
**Do not code new features here. Freeze and rehearse.**

- [ ] **Full dry run** on the *actual demo laptop* + *actual demo wifi* (or hotspot backup).
- [ ] Grant camera + mic permissions ahead of time in the demo browser.
- [ ] Pre-load the page; test volume levels through the room speakers.
- [ ] Prepare a **30-second script**: who says the pitch, when you hit start, the "watch it narrate the judges" moment.
- [ ] **Record a backup video** of it working — if wifi dies during judging, you still have a demo.
- [ ] Charge laptop / plug in. Close Slack, notifications, other tabs.
- [ ] Assign roles for the pitch: one drives, one talks.

> ✅ **Exit criteria:** You've run the demo start-to-finish twice with zero surprises.

---

## 5. Work Division (2 People)

Split by **layer + interface**, so you can work in parallel against a fixed API contract.

### 👤 Person A — "The Face" (Frontend, Capture, TTS, UX)
Owns everything the audience sees and hears.
- Webcam capture + frame sampling
- POSTing frames, displaying narration
- TTS pipeline (SpeechSynthesis → ElevenLabs) + audio queue
- Cinematic UI, subtitles, letterbox, start button
- Demo-day visual polish

### 👤 Person B — "The Voice" (Backend, Gemini, Prompt, Reliability)
Owns the brains and stability.
- Backend proxy + `/narrate` endpoint
- Gemini integration (image + prompt → text)
- **Prompt engineering** (the personality — highest-leverage task)
- Narration continuity/memory, length tuning
- Error handling, fallbacks, rate limiting

### 🤝 Shared / Pairing moments
- Phase 0 setup (together)
- The API contract (agree once, don't change)
- Phase 2 prompt tuning (B writes, A supplies live frames + ears)
- Phase 4 rehearsal (together)

> **Integration tip:** While B builds the real Gemini call, A hardcodes a fake `/narrate` that returns a canned line — so A never blocks on B. Swap in the real endpoint once it's ready.

---

## 6. The Prompt (Highest-Leverage Asset)

### System / instruction prompt (starting point — iterate on this!)

```
You are Sir David Attenborough narrating a live nature documentary.
The image is a frame from a webcam observing "wildlife" — which is
actually just people in a room at a hackathon.

Narrate what you see in the frame as if it were rare and fascinating
animal behaviour. Be witty, warm, and gently absurd. Treat mundane
human actions (typing, drinking coffee, scrolling a phone) as
remarkable evolutionary adaptations or survival rituals.

RULES:
- 1 to 2 sentences ONLY. This is spoken aloud in real time.
- Stay in character as Attenborough at all times. Never break the fourth wall.
- Vary your sentence openings. Do not start every line the same way.
- Reference specific things you actually see in the frame.
- Do not repeat observations from your previous narration (provided below).
- If the frame is unclear or dark, treat it as the creature retreating
  into shadow — never say "I can't see."

Previous narration (for continuity, do not repeat):
{last_narration}
```

### Example outputs to aim for
- *"Here, in the artificial glow of the nesting site, the male has once again returned to his glowing rectangle — a courtship display of remarkable persistence."*
- *"Observe the caffeine ritual. Twice hourly, the creature raises the vessel to its beak. Without it, the colony would surely collapse."*

### Tuning levers
- **Temperature** ~0.9–1.0 for playful variety.
- Feed `{last_narration}` (and optionally the one before) for continuity.
- If it gets repetitive, add "avoid the words: [list of overused words]".
- Keep max output tokens low (~60) to force brevity and reduce latency.

---

## 7. Key Code Snippets (copy-paste starting points)

> Pick Node **or** Python for the backend to match §3.

### 7.1 Frontend — capture + sample loop (vanilla JS)
```html
<video id="cam" autoplay playsinline></video>
<canvas id="grab" style="display:none"></canvas>
<div id="caption"></div>
<script>
const video = document.getElementById('cam');
const canvas = document.getElementById('grab');

navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => { video.srcObject = stream; });

function grabFrame() {
  const w = 640, h = 480;
  canvas.width = w; canvas.height = h;
  canvas.getContext('2d').drawImage(video, 0, 0, w, h);
  return canvas.toDataURL('image/jpeg', 0.7).split(',')[1]; // strip prefix
}

async function tick() {
  const image = grabFrame();
  const res = await fetch('http://localhost:3000/narrate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image })
  });
  const { narration } = await res.json();
  document.getElementById('caption').textContent = narration;
  speak(narration);
}

// Kick off after a Start button click (browsers need a user gesture for audio)
function start() { tick(); setInterval(tick, 5000); }

function speak(text) {
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.9; u.pitch = 0.8;
  // pick a British voice if available
  const v = speechSynthesis.getVoices().find(v => /en-GB/i.test(v.lang));
  if (v) u.voice = v;
  speechSynthesis.speak(u);
}
</script>
```

### 7.2 Backend — Node + Express + Gemini
```js
import express from 'express';
import cors from 'cors';
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

let last = "";

app.post('/narrate', async (req, res) => {
  try {
    const { image } = req.body;
    const prompt = `You are Sir David Attenborough... (see §6).
Previous narration (do not repeat): ${last}`;

    const result = await ai.models.generateContent({
      model: 'gemini-2.0-flash',
      contents: [{
        role: 'user',
        parts: [
          { text: prompt },
          { inlineData: { mimeType: 'image/jpeg', data: image } }
        ]
      }],
      config: { temperature: 0.95, maxOutputTokens: 80 }
    });

    const narration = result.text?.trim() || "The creature has momentarily eluded us.";
    last = narration;
    res.json({ narration });
  } catch (e) {
    console.error(e);
    res.json({ narration: "Here, the wildlife retreats into shadow, beyond our lens." });
  }
});

app.listen(3000, () => console.log('narrator on :3000'));
```

### 7.3 Backend — Python + Flask + Gemini (alternative)
```python
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
app = Flask(__name__)
CORS(app)
last = {"text": ""}

@app.post("/narrate")
def narrate():
    try:
        image_b64 = request.json["image"]
        import base64
        img_bytes = base64.b64decode(image_b64)
        prompt = f"You are Sir David Attenborough... (see §6). Previous: {last['text']}"

        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            ],
            config=types.GenerateContentConfig(temperature=0.95, max_output_tokens=80),
        )
        text = (resp.text or "").strip() or "The creature has momentarily eluded us."
        last["text"] = text
        return jsonify(narration=text)
    except Exception as e:
        print(e)
        return jsonify(narration="Here, the wildlife retreats into shadow.")

app.run(port=3000)
```

### 7.4 ElevenLabs TTS upgrade (frontend fetch → play audio)
```js
async function speakEleven(text) {
  const res = await fetch('http://localhost:3000/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  const blob = await res.blob();
  const audio = new Audio(URL.createObjectURL(blob));
  audioQueue.push(audio);       // queue so lines never overlap
  playNext();
}
```
> Add a `/tts` backend route that calls ElevenLabs `text-to-speech` with a deep British voice ID and streams the MP3 back. Keep the API key server-side.

---

## 8. Pacing & The Overlap Problem (read this — it bites everyone)

The classic bug: narration N+1 starts before narration N finishes speaking → chaos.

**Fixes (do at least the first two):**
1. **Audio queue** — never play a new clip until the current one ends (`utterance.onend` / `audio.onended`).
2. **Skip, don't stack** — if a narration is still playing when the timer fires, *skip that tick* rather than queueing forever.
3. **Interval ≥ speech length** — 1–2 sentences ≈ 5–7s spoken, so a 5–6s interval roughly matches. Tune live.
4. **Cap output length** in the prompt (`maxOutputTokens`) so lines stay short.

---

## 9. Risk Register & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Demo wifi dies | Medium | **Pre-record a backup video**; bring a phone hotspot |
| Camera permission blocked on demo laptop | Medium | Grant + test in Phase 4 on the real machine |
| Narrations overlap / desync | High | Audio queue + skip-if-busy (see §8) |
| Gemini rate limit / latency spike | Medium | Fallback lines; increase interval; downscale image |
| Prompt sounds flat/generic | High | Spend real time in Phase 2; use §6 + continuity |
| API key leaked in client | Low | Backend proxy; `.env` in `.gitignore` |
| TTS voice sounds robotic | Medium | Upgrade to ElevenLabs British voice |
| Running out of time | Medium | Phase 1 slice by 1:30 guarantees *a* demo |

---

## 10. Scope Guard — MVP vs Stretch

### ✅ MVP (must have by 3:20) — the demo that wins
- Webcam feed on screen
- Frame every ~5s → Gemini → Attenborough narration
- TTS speaks it (British voice ideal)
- Basic cinematic UI + subtitles
- No overlap; doesn't crash

### 🌟 Stretch (only if ahead of schedule)
- ElevenLabs premium voice (do this first if time)
- Narration "story arc" / memory across the whole session
- Multiple modes (Attenborough / true-crime / sports commentator toggle)
- On-screen "species classification" cards ("Homo sapiens, developer variant")
- Sound effects / documentary background music
- Save the session as a shareable highlight reel

### 🚫 Explicitly OUT of scope (do not build)
- User accounts / auth
- Persistence / database
- Mobile responsiveness
- Multi-user / rooms
- Anything not visible in the 60-second demo

---

## 11. Pre-Demo Checklist (Phase 4)

- [ ] Runs on the actual demo laptop + browser
- [ ] Camera + mic permissions granted
- [ ] Volume tested through room speakers
- [ ] API key has quota remaining
- [ ] Backup video recorded and on the desktop
- [ ] Hotspot ready as wifi fallback
- [ ] Notifications silenced, extra tabs closed, laptop charging
- [ ] 30-second pitch script rehearsed; roles assigned (driver + speaker)
- [ ] The "point it at the judges" finale planned 🎯

---

## Appendix A — First 5 Minutes: Verify the Key

**Node:**
```bash
npm init -y && npm i @google/genai
node -e "import('@google/genai').then(async ({GoogleGenAI})=>{const ai=new GoogleGenAI({apiKey:process.env.GEMINI_API_KEY});const r=await ai.models.generateContent({model:'gemini-2.0-flash',contents:'Say hi as David Attenborough in one sentence.'});console.log(r.text)})"
```

**Python:**
```bash
pip install google-genai
python -c "from google import genai,os; c=genai.Client(api_key=os.environ['GEMINI_API_KEY']); print(c.models.generate_content(model='gemini-2.0-flash', contents='Say hi as David Attenborough in one sentence.').text)"
```

If that prints a sentence, you're clear to build.

---

## Appendix B — Quick Reference Links
- Gemini API key + playground: **aistudio.google.com**
- Gemini docs: **ai.google.dev/gemini-api/docs**
- Node SDK: `@google/genai` · Python SDK: `google-genai`
- ElevenLabs: **elevenlabs.io** (TTS API + voice library)

---

### One-line reminder for the whole team
> **Ugly-but-working by 1:30. Personality by 2:30. Pretty by 3:20. Rehearse till 4:00. The voice is the product.**
