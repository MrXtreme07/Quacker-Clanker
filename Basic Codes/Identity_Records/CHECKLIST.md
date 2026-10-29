# Identity_Records – VQA action logger checklist

Goal: camera → vision model → **one action word** → `actions.db` → dashboard (`server.py`).

**Status (2026-10-22):** model chosen (**LFM2-VL-450M**, 82%, 1.5 s/photo), keyword NLP done, DB link done.
Only LFM2-VL-450M is kept on the Pi; the other models and test scripts were removed (results kept below).
Open: live camera test, test photos for 5 actions, git commit.

## Files
| Path | What it is |
|---|---|
| `main.py` | Original BLIP logger (unchanged) |
| `server.py`, `dashboard.html` | Flask dashboard on port 5000 (unchanged) |
| `actions.db` | Shared database (both loggers write here) |
| `main_vqa/main_vqa.py` | New logger: llama-server vision model → one word → `actions.db` |
| `main_vqa/action_words.py` | Keyword NLP: model sentence → action word |
| `vqa_scripts/` | Original standalone SmolVLM scripts (kept for reference; SmolVLM model deleted, so they won't run) |
| `scripts/test_set/` | 50 reviewed test photos + `labels.csv`, `excluded.txt`, `contact_sheet.jpg` |
| `scripts/results/` | Model comparison results (`summary.md`, per-model CSVs, server logs) |

## 0. Safety
- [x] Old Wikimedia test images deleted (contained paintings/drawings)
- [x] Test images come only from a labelled dataset of real photos (no web image search)
- [x] Contact sheet reviewed; 10 unsuitable photos removed and listed in `scripts/test_set/excluded.txt`
- [ ] Rule for new photos: real photos only, no paintings/drawings/nudity, review contact sheet before testing

## 1. Test set — `scripts/test_set/`
- [x] 50 reviewed photos from `Bingsu/Human_Action_Recognition` (train split)
- [x] Actions covered: sitting, eating, drinking, running, sleeping, typing (`using_laptop`; "working" also accepted)
- [ ] Not covered by the dataset: walking, standing, talking, reading, exercising

## 2. Keyword NLP — `main_vqa/action_words.py`
- [x] Verb forms → action (sits/sat/seated → sitting, jogging → running, asleep/lying → sleeping …)
- [x] Object clues → action (burger → eating, cup/bottle → drinking, laptop → typing, bed → sleeping …)
- [x] Specific actions beat posture ("sitting at a table eating" → eating)
- [x] "no person" → `none`; nothing matched → `unknown` (neither is saved to the DB)
- [x] Unit test: 30/30 sentences passed (test script since removed)
- [ ] Decide: should "sitting … on his phone" be sitting or talking? (main source of remaining misses)

## 3. Database link — `main_vqa/main_vqa.py`
- [x] Writes to the shared `actions.db` (same table as `main.py`, dashboard unchanged)
- [x] New columns `raw_text` (model's full sentence) and `model` (which model), added automatically
- [x] Tested on a copy of the DB: rows saved, dashboard API still works
- [x] End-to-end test with a fake camera (4 test photos played as video, LFM2 model, DB copy):
      4 photos → 4 rows (sitting, eating, drinking, typing), each with the right sentence and model name
- [x] Dashboard (`server.py`) on that DB: `/`, `/api/stats`, `/api/actions` all OK; every field the page reads is present
- [x] Fixed: saved sentence/confidence belonged to the *next* action (now saved per action)
- [x] Fixed: "resting" no longer counts as sleeping
- [x] Fixed: flicker rows under 2 s while the vote switches are no longer saved (`MIN_SECONDS`)
- [ ] Look at the dashboard in a browser (couldn't screenshot it from the test environment)
- [ ] Live camera test (needs a camera on `/dev/video0`; Pi ribbon camera would need picamera2)

## 4. Model comparison (done — script removed, results in `scripts/results/`)
- [x] 6 models tested with 2 prompts each (moondream2 skipped: only a 3.7 GB f16 build, too big for 4 GB Pi)
- [x] Found: asking for "one word from a list" makes bigger models lazy (LFM2 said "sitting" 37/50 times).
      Asking them to **describe** the action, then using the keyword NLP, works much better.
- [x] Fixed Qwen3-VL out-of-memory crash by capping context to 4096 tokens (`-c 4096`)

Best result per model (50 photos, Pi 5):

| Model | Prompt | Accuracy | s/photo | Peak RAM |
|---|---|---|---|---|
| Qwen3-VL-2B-Instruct | describe | 88% | 6.1 | 3.3 GB ⚠ almost all RAM |
| InternVL3-1B-Instruct | describe | 86% | 10.9 | 1.7 GB |
| **LFM2-VL-450M** | **describe** | **82%** | **1.5** | **1.0 GB** |
| SmolVLM2-500M-Video | describe | 80% | 7.1 | 1.5 GB |
| SmolVLM-256M (old default) | list | 76% | 6.0 | 1.0 GB |
| SmolVLM-500M | list | 68% | 6.7 | 1.7 GB |

Full per-action table: `scripts/results/summary.md`; every answer: `scripts/results/<model>.<prompt>.csv`.
Only LFM2-VL-450M is still cached (`~/.cache/huggingface/hub`, ~0.5 GB); the other models were deleted.

## 5. Pick the winner
- [x] **LFM2-VL-450M + describe prompt** — 4× faster than the rest, 82%, only 1 GB RAM
- [x] Set as `DEFAULT_MODEL` / `DEFAULT_PROMPT` in `main_vqa/main_vqa.py`
- [x] Other models deleted from the Pi (re-download with `--model ggml-org/<name>-GGUF` if ever needed)

## 6. Next
- [ ] Connect a camera and do a live run → check new rows (`raw_text`, `model`) in `actions.db` and the dashboard
- [ ] Test photos for walking, standing, talking, reading, exercising
- [ ] Commit to git

## How to run (from `Identity_Records`)
```bash
python3 main_vqa/main_vqa.py                          # live camera → actions.db (LFM2, describe)
python3 main_vqa/main_vqa.py --image photo.jpg        # check one photo
python3 server.py                                     # dashboard http://localhost:5000
```
