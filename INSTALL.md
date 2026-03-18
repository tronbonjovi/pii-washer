# Pii Washer — Installation Guide

## Requirements

- **Python 3.11-3.13** (3.13 recommended)
  - Python 3.14 is **not supported** — spaCy's pydantic v1 dependency is incompatible with it.
  - On Windows, install from [python.org](https://www.python.org/downloads/) or use `py -3.13` if you have the Python Launcher.
- **Node.js 18+** (for the React frontend)
- **Git** (to clone the repository)
- **4 GB+ disk space** (the spaCy language model is ~560 MB)

## Step-by-step setup

### 1. Clone the repository

```bash
git clone https://github.com/tronbonjovi/pii-washer.git
cd pii-washer
```

### 2. Create a Python virtual environment

Use Python 3.13 explicitly to avoid version issues.

**Windows:**
```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Confirm you're on the right version:
```bash
python --version
# Should show Python 3.13.x
```

### 3. Install the Python backend

```bash
pip install -e .
```

This installs Presidio Analyzer, spaCy, FastAPI, and the Pii Washer package itself in editable mode.

To also install development/test dependencies:
```bash
pip install -e ".[dev]"
```

### 4. Install the spaCy language model

The NER model must be installed via direct URL (it is not available on PyPI):

```bash
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

This downloads ~560 MB. A stable internet connection is required for this step only — after installation, Pii Washer runs entirely offline.

### 5. Install the frontend

```bash
cd pii-washer-ui
npm install
cd ..
```

### 6. Launch Pii Washer

You need two terminals — one for the backend, one for the frontend.

**Terminal 1 — Backend:**
```bash
uvicorn pii_washer.api.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd pii-washer-ui
npm run dev
```

Open **http://localhost:5173** in your browser. The Vite dev server proxies API requests to the FastAPI backend automatically.

## Verifying the installation

Run the test suite to confirm everything is working:

```bash
pytest
```

## Troubleshooting

### "No module named pii_washer"
Make sure your virtual environment is activated and you ran `pip install -e .` from the project root.

### spaCy model errors
If you see errors about `en_core_web_lg` not being found, re-run the model install command from step 4. Do **not** use `python -m spacy download en_core_web_lg` — it is unreliable on Python 3.13+.

### Python 3.14 crashes on import
spaCy is incompatible with Python 3.14 due to its pydantic v1 dependency. Downgrade to Python 3.13.

### "Access is denied" when recreating the venv on Windows
Kill any running Python processes before deleting or recreating the `.venv` directory.
