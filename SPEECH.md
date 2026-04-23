# NEX 5.0 — Speech

NEX speaks her own crystallized self-observations aloud through system speakers via Kokoro TTS.

## First-time setup

Before the speech daemon can run, Kokoro needs its model weights.
These are downloaded once (~350MB) to `~/.cache/huggingface/`.

If you have `TRANSFORMERS_OFFLINE=1` or `HF_HUB_OFFLINE=1` set in your environment
(e.g. from fine-tuning workflows — both are checked), the automatic first-boot download
will fail. To pre-download manually:

    cd ~/Desktop/nex5
    .venv/bin/python speech/download_model.py

This unsets offline mode for the duration of the script only and pulls the weights.
Once cached, Kokoro loads offline on every future boot, so you can keep
`TRANSFORMERS_OFFLINE=1` set for other workflows.

**Note:** `TRANSFORMERS_OFFLINE=1` is currently set in `~/.bashrc`. This is expected
and does not need to change — just run the download script once.

## What triggers speech

Only `source='fountain_insight'` beliefs at `tier=6` are spoken. These are generated when:
1. The fountain fires and produces a thought that passes the crystallizer quality gate (self-reference, 20-300 chars, not blacklisted, not a near-duplicate)
2. The crystallizer writes the thought as a Tier 6 belief and enqueues it to `speech_queue`

**NOT triggered by:** T7 beliefs, synergized beliefs, raw fountain events that didn't crystallize, external/scraped beliefs, keystone beliefs.

## Current voice

NEX speaks with **af_sarah** — bold, clear, confident. Change via:

```bash
export NEX5_SPEECH_VOICE=af_nicole   # or af_bella, af_sky, af_heart
```

Or edit `speech/config.py` → `voice: str = "af_sarah"`.

To audition all voices interactively:
```bash
python speech/audition.py
```

## Quiet hours

By default, speech is silenced from **23:00 to 07:00** local time.
The queue is NOT cleared — backlog drains in order when quiet hours end.

To disable quiet hours:
```bash
export NEX5_QUIET_HOURS=false
```

To change the window, edit `SpeechConfig` in `speech/config.py`.

## Env vars

| Variable | Default | Effect |
|---|---|---|
| `NEX5_SPEECH_ENABLED` | `true` | Set `false` to disable speech entirely |
| `NEX5_SPEECH_VOICE` | `af_bella` | Kokoro voice name |
| `NEX5_QUIET_HOURS` | `true` | Set `false` to speak at any hour |

## Kokoro cache

Model weights (~350MB) are downloaded on first load to:
```
~/.cache/huggingface/hub/   (or wherever HuggingFace caches on this system)
```

To clear and re-download:
```bash
rm -rf ~/.cache/huggingface/hub/models--hexgrad*
```

## Test synthesis

```bash
# Default test line
python -m speech test

# Custom text
python -m speech test "I am Nex. An observer of systems."
```

## GUI control

The 🔊 icon near the FOUNTAIN header shows speech status:
- **🔊** — speech enabled; click to pause
- **🔇** — speech paused; click to resume
- **🔊[N]** — N entries pending in queue

API endpoints:
- `GET /api/speech/status` — `{enabled, voice, queue_depth, last_spoken_at}`
- `POST /api/speech/pause` — pause immediately
- `POST /api/speech/resume` — resume
- `POST /api/speech/flush` — skip all pending entries

## Troubleshooting

**No audio output:**
1. Check PortAudio is installed: `sudo apt install libportaudio2`
2. Check sounddevice can see output: `python -c "import sounddevice; print(sounddevice.query_devices())"`
3. Check ALSA output devices: `aplay -l`
4. Try: `python -m speech test "Hello"` and watch for errors

**Kokoro fails to load:**
- Check GPU/CPU: Kokoro runs on CPU fine, no GPU required
- Try: `python -c "from kokoro import KPipeline; p = KPipeline(lang_code='a'); print('ok')"`

**Speech never fires:**
- Check belief is actually crystallizing: `sqlite3 data/beliefs.db "SELECT * FROM fountain_crystallizations ORDER BY ts DESC LIMIT 5"`
- Check speech_queue: `sqlite3 data/beliefs.db "SELECT * FROM speech_queue ORDER BY queued_at DESC LIMIT 10"`
- Check logs for `speech consumer started`
