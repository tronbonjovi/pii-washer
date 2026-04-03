# GitHub Actions Cross-Platform Release Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up GitHub Actions workflows for CI (test on every push/PR) and cross-platform release builds (Windows, macOS, Linux executables uploaded to GitHub Releases on tag push).

**Architecture:** Two workflow files — a CI workflow that runs tests on every push/PR, and a release workflow triggered by version tags (`v*`) that builds desktop executables for all three platforms and uploads them as release assets. The release workflow builds the frontend first, then bundles it into each platform's PyInstaller build.

**Tech Stack:** GitHub Actions, PyInstaller, Node.js, Python 3.13, spaCy `en_core_web_lg`

---

## Task 1: Create CI workflow (test on push/PR)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('pyproject.toml') }}
          restore-keys: ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint with Ruff
        run: ruff check .

      - name: Run backend tests
        run: pytest pii_washer/tests/ --ignore=pii_washer/tests/test_pii_detection_engine.py --ignore=pii_washer/tests/test_name_recognizer.py -v

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: pii-washer-ui/package-lock.json

      - name: Install dependencies
        working-directory: pii-washer-ui
        run: npm ci

      - name: Lint
        working-directory: pii-washer-ui
        run: npm run lint

      - name: Type check and build
        working-directory: pii-washer-ui
        run: npm run build

      - name: Run tests
        working-directory: pii-washer-ui
        run: npm test
```

- [ ] **Step 3: Verify YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

If `yaml` module not available, just visually inspect the file for indentation issues.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow for backend and frontend tests"
```

---

## Task 2: Create release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release workflow**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write

jobs:
  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: pii-washer-ui/package-lock.json

      - name: Install and build frontend
        working-directory: pii-washer-ui
        run: |
          npm ci
          npm run build

      - name: Upload frontend dist
        uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: pii-washer-ui/dist/

  build-desktop:
    needs: build-frontend
    strategy:
      matrix:
        include:
          - os: windows-latest
            artifact-name: pii-washer-windows
            exe-name: pii-washer.exe
            pyinstaller-args: --name pii-washer --icon assets/app-icons/pii-washer-app-icon.ico
          - os: macos-latest
            artifact-name: pii-washer-macos
            exe-name: pii-washer
            pyinstaller-args: --name pii-washer
          - os: ubuntu-latest
            artifact-name: pii-washer-linux
            exe-name: pii-washer
            pyinstaller-args: --name pii-washer

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-release-${{ hashFiles('pyproject.toml') }}
          restore-keys: ${{ runner.os }}-pip-release-

      - name: Cache spaCy model
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-spacy-en_core_web_lg-3.8.0

      - name: Install Python dependencies
        run: |
          pip install -e ".[desktop]"
          pip install pyinstaller
          pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

      - name: Download frontend dist
        uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: ui/

      - name: Copy icon (Windows)
        if: runner.os == 'Windows'
        shell: bash
        run: mkdir -p icon && cp assets/app-icons/pii-washer-app-icon.ico icon/

      - name: Build with PyInstaller
        run: |
          pyinstaller ${{ matrix.pyinstaller-args }} \
            --onefile \
            --add-data "ui:ui" \
            --add-data "pii_washer/data:pii_washer/data" \
            --hidden-import pii_washer \
            --hidden-import pii_washer.api \
            --hidden-import pii_washer.api.main \
            --hidden-import pii_washer.extractors \
            --hidden-import pii_washer.extractors.docx \
            --hidden-import pii_washer.extractors.pdf \
            --hidden-import pii_washer.extractors.csv_ext \
            --hidden-import pii_washer.extractors.xlsx \
            --hidden-import pii_washer.extractors.html \
            pyinstaller_entry.py

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact-name }}
          path: dist/${{ matrix.exe-name }}

  create-release:
    needs: build-desktop
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: release-artifacts/

      - name: Prepare release assets
        run: |
          mkdir -p release-assets
          cp release-artifacts/pii-washer-windows/pii-washer.exe release-assets/pii-washer-windows.exe
          cp release-artifacts/pii-washer-macos/pii-washer release-assets/pii-washer-macos
          cp release-artifacts/pii-washer-linux/pii-washer release-assets/pii-washer-linux
          chmod +x release-assets/pii-washer-macos release-assets/pii-washer-linux

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            release-assets/pii-washer-windows.exe
            release-assets/pii-washer-macos
            release-assets/pii-washer-linux
```

- [ ] **Step 2: Verify YAML syntax**

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add cross-platform release workflow"
```

---

## Task 3: Create a PyInstaller .spec file

**Files:**
- Create: `pii-washer.spec`
- Modify: `.gitignore` — remove `*.spec` from ignore list (or add `!pii-washer.spec`)

The release workflow above uses PyInstaller CLI flags, but a `.spec` file gives more control over what gets bundled. This task creates a checked-in `.spec` file as an alternative approach if the CLI flags prove insufficient.

- [ ] **Step 1: Check if .spec is gitignored**

```bash
git check-ignore pii-washer.spec
```

If ignored, add `!pii-washer.spec` to `.gitignore` to allowlist it.

- [ ] **Step 2: Create the spec file**

This step should be done AFTER testing the release workflow. If the CLI flag approach works, this task can be skipped. If PyInstaller needs finer-grained control (hidden imports, data files, exclusions), convert the working CLI command to a `.spec` file using `pyi-makespec`.

- [ ] **Step 3: Commit if created**

```bash
git add pii-washer.spec .gitignore
git commit -m "build: add PyInstaller spec file for release builds"
```

---

## Task 4: Test the CI workflow

- [ ] **Step 1: Push branch and open PR**

Push the workflow files to a test branch and open a PR against main. The CI workflow should trigger automatically.

- [ ] **Step 2: Monitor CI run**

```bash
gh run list --limit 5
gh run watch
```

- [ ] **Step 3: Fix any failures**

Common issues:
- Test imports failing (missing deps in CI environment)
- Ruff version mismatch
- Node.js version issues
- Path issues between OS runners

- [ ] **Step 4: Verify CI passes**

Both `backend-tests` and `frontend-tests` jobs should show green.

---

## Task 5: Test the release workflow

- [ ] **Step 1: Create a test tag**

```bash
git tag v1.2.0-rc1
git push origin v1.2.0-rc1
```

- [ ] **Step 2: Monitor release build**

```bash
gh run list --limit 5
gh run watch
```

The release workflow has 3 stages:
1. Build frontend (fast, ~1 min)
2. Build desktop apps on 3 platforms in parallel (~5-10 min each — spaCy model download is the bottleneck)
3. Create GitHub release with assets

- [ ] **Step 3: Verify release assets**

```bash
gh release view v1.2.0-rc1
```

Should show three downloadable assets: `pii-washer-windows.exe`, `pii-washer-macos`, `pii-washer-linux`.

- [ ] **Step 4: Fix any failures and iterate**

Common issues:
- PyInstaller hidden imports missing (add to `--hidden-import` list)
- Data files not bundled correctly (adjust `--add-data` paths)
- spaCy model not found at runtime (needs to be in the bundled package path)
- macOS code signing warnings (expected without a certificate)
- Windows Defender flagging (expected without code signing)

- [ ] **Step 5: Clean up test tag if needed**

```bash
gh release delete v1.2.0-rc1 --yes
git push --delete origin v1.2.0-rc1
git tag -d v1.2.0-rc1
```

---

## Task 6: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Update README**

Add a "Downloads" section near the top, or update the existing "Quick start" section to mention that releases are now built automatically:

```markdown
### Option A: Download the desktop app

Grab the latest release for your platform from the [releases page](https://github.com/tronbonjovi/pii-washer/releases/latest):
- **Windows:** `pii-washer-windows.exe`
- **macOS:** `pii-washer-macos`
- **Linux:** `pii-washer-linux`
```

- [ ] **Step 2: Update roadmap**

Move "Cross-platform release builds" from medium-term to completed.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/roadmap.md
git commit -m "docs: update README and roadmap for cross-platform releases"
```

---

## Notes

**Build time:** The release workflow will take 10-15 minutes due to the spaCy model download (~560MB per platform). Caching helps on subsequent runs but the first run for each OS will be slow.

**Known limitations:**
- macOS build may trigger Gatekeeper warnings without code signing (roadmap item: "Code signing")
- Windows build may trigger SmartScreen warnings without code signing
- The spaCy model makes each executable ~400-500MB — this is inherent to the current architecture

**Cost:** GitHub Actions is free for public repos. The release workflow uses ~30 minutes of runner time per release (3 platforms × ~10 min each). Free tier includes 2,000 minutes/month.
