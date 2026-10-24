# Apply this update without Antigravity credits

These are updated source files for your existing CampusFix project, not a new stack. No database or virtual environment is included.

## 1. Save and back up

Stop the running Streamlit app (Ctrl+C in its terminal), save your open editor files, and copy your project folder somewhere safe. Keep your current `campusfix.db`.

## 2. Copy the update

Extract the ZIP. Copy the **contents** of its `campusfixai` folder into the project folder that contains your current `app.py`. Replace the old source files when asked.

The update contains `app.py`, `db.py`, `triage.py`, `ui.py`, `ai_assistant.py`, `requirements.txt`, `.gitignore`, `.streamlit/config.toml`, docs and `tests/`.

**Do not delete or replace your database, `.venv`, `.env`, or secrets.** The ZIP does not contain them. If your editor has an old file open with unsaved changes, reload it from disk instead of saving the old version over the update.

## 3. Install and run using your existing environment

Windows / PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

If your environment is named `venv`, substitute that for `.venv`. If you already activated it, `python -m pip ...` and `python -m streamlit ...` work too.

The first run adds missing database columns without resetting existing tickets. Old Other/Medium priorities are deliberately not silently downgraded; explicitly refresh their rule suggestion from Staff desk if desired. New unmatched automatic reports default to Other/Low.

## 4. Optional Gemma

Keep Ollama running on the same computer as Streamlit:

```bash
ollama run gemma4:e4b "Reply with READY."
```

Then open a ticket, expand **Local AI assistant**, choose a task and click **Ask local assistant**. Reporting still works if the model is unavailable. Known hazards use a clearly labelled safety rule instead of AI-generated repair advice.

## 5. Test and demo

```bash
python -m pytest -q
```

Create one automatic unmatched report and one manual-High report. In Staff desk, change priority, progress the status, and verify the totals. Test an AI request only if local Gemma is actually running.

## 6. Update your repository yourself

These changes have **not been pushed** to your GitHub account. Copy them locally, review, commit and push, or upload the changed source files through the website. Exclude the environment and real database.

Your existing repo tracks `campusfix.db`. `git rm --cached campusfix.db` removes it from tracking without deleting your local copy; it does not remove older history. Read the Git hygiene section in README before publishing real complaint data.
