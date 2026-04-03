# Pii Washer

Local-only PII detection and text sanitization. Paste text containing personal data, get a clean version with all sensitive items replaced by consistent placeholders. You can use this to "de-personalize" text to use with LLMs and when you get a response back, "re-personalize" to swap the placeholders for the originals.

> **Important:** PII detection is not perfect and will miss things. Detection is currently US/English-only — international formats (non-US phone numbers, national IDs from other countries, etc.) are not supported. This tool is designed to assist a human, not replace one. Always review the results before sending text anywhere. An "Add PII" feature is included so you can manually tag anything the detector missed.

## What it does

1. **Depersonalize** — Paste text containing names, emails, phone numbers, addresses, and other PII. Pii Washer detects them and replaces each with a unique placeholder (e.g., `[PERSON_1]`, `[EMAIL_1]`).
2. **Work with clean text** — Copy the depersonalized version into ChatGPT, Claude, or any other tool. No real PII is transmitted.
3. **Repersonalize** — Paste the AI's response back. Pii Washer swaps the placeholders for the original values, giving you a fully restored document.

### Supported file formats

| Format | Extensions |
|---|---|
| Plain text | .txt, .md |
| Documents | .docx, .pdf |
| Spreadsheets | .csv, .xlsx |
| Web pages | .html |

Paste text directly or upload a file. All processing happens in memory — files are never written to disk.

Placeholder mappings are consistent within a session — the same name always gets the same placeholder. Use "Start Over" in the header to reset and begin a new task. The gear icon in the header opens a settings menu with an **About** dialog and **Check for Updates** (compares your local version against the latest GitHub release).

## Privacy

- Runs entirely on your local machine — the only network call is the optional "Check for Updates" request to the GitHub releases API.
- All data is held in memory only and securely cleared on reset or shutdown.

## Quick start

### Option A: Download the desktop app (Windows)

Grab **pii-washer.exe** from the [latest release](https://github.com/tronbonjovi/pii-washer/releases/latest). Double-click to run — no install, no Python, no setup.

### Option B: Run from source

Requires **Python 3.11-3.13** (3.13 recommended) and **Node.js 18+**. See [INSTALL.md](INSTALL.md) for detailed instructions.

```bash
git clone https://github.com/tronbonjovi/pii-washer.git
cd pii-washer

# Backend
python3.13 -m venv .venv && source .venv/bin/activate    # Linux/macOS
# py -3.13 -m venv .venv && .venv\Scripts\activate       # Windows
pip install -e .
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# Frontend
cd pii-washer-ui && npm install && cd ..

# Run (two terminals)
uvicorn pii_washer.api.main:app --reload                 # Terminal 1: backend on :8000
cd pii-washer-ui && npm run dev                           # Terminal 2: frontend on :5173
```

Open **http://localhost:5173** in your browser.

## Detected PII types

| Category | Examples |
|---|---|
| Person names | John Smith, Dr. Martinez |
| Email addresses | user@example.com |
| Phone numbers | (555) 123-4567, +1-555-123-4567 |
| Credit card numbers | Luhn-validated card numbers |
| Social Security numbers | 123-45-6789 |
| Dates of birth | Born on March 5, 1990 |
| IP addresses | 192.168.1.1 |
| Medical record numbers | MRN patterns |
| Locations / organizations | NER-detected entities |

Detection uses Microsoft Presidio with spaCy NER, plus custom regex recognizers for formats Presidio misses.

## Architecture

```
pii_washer/
  api/                        # FastAPI REST API
  document_loader.py          # Text ingestion and validation
  pii_detection_engine.py     # Presidio + spaCy NER + custom recognizers
  placeholder_generator.py    # Deterministic placeholder assignment ([TYPE_N])
  text_substitution_engine.py # Bidirectional text replacement
  session_manager.py          # Workflow orchestration, the API boundary for all operations
  temp_data_store.py          # In-memory storage with secure clear
  tests/                      # Automated tests

pii-washer-ui/                # React 19 + TypeScript + Vite + Tailwind v4
```

All components are wired through `SessionManager`, which acts as the single API boundary. The React frontend talks to the FastAPI backend via `/api/v1/` endpoints.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
