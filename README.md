# CampusFix AI

A campus maintenance demo: report an issue, choose its priority, track its ticket, and let staff take it from **Reported → In Progress → Resolved**.

## What works

- Required title, description, building and room fields with server-side validation.
- Persistent SQLite tickets such as `CF-000001` and read-only student lookup.
- Dashboard totals, pending/resolved counts, search, and status/priority/building filters.
- A student can select **Low / Medium / High**, or use automatic rules.
- Staff can override priority separately from status. Priority provenance stays visible.
- Transparent rule-based category/priority suggestions. **Other defaults to Low only if no more specific or hazard rule matches.**
- Optional, on-demand **Gemma 4 E4B via local Ollama**: review priority, request safe checks, or ask a short maintenance question.
- AI recommendations do not automatically change the ticket. Staff must explicitly accept them.
- Known hazard keywords trigger fixed escalation guidance instead of model-generated DIY instructions. That output is labelled **Safety rule — AI not called**, not AI-generated.
- Responsive Streamlit interface with a sidebar, metric cards, separate workspaces, and clear source labels.

## Run the existing project

Requires Python 3.10+ and a modern browser. Use your existing project environment if it already works.

### Windows / PowerShell — no activation required

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

### macOS / Linux — no activation required

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Open `http://localhost:8501`. Reporting, tracking, rules and staff controls do **not** require Ollama.

## Optional local AI

Install/start Ollama, then:

```bash
ollama pull gemma4:e4b
ollama run gemma4:e4b "Reply with READY."
```

Open a saved ticket under **Track a ticket** or **Staff desk**, expand **Local AI assistant**, choose **Review priority** or **Suggest safe next steps**, and click **Ask local assistant**. A question is optional.

The Python server calls `http://127.0.0.1:11434/api/chat`, using `gemma4:e4b`, schema-shaped JSON, validation, and bounded timeouts. There are no model tools, cloud inference fallback, automatic repairs, or autonomous status updates. Model quality and speed depend on the hardware and report; no accuracy claim is made.

**Ollama and Streamlit must run on the same computer.** A remote preview/cloud deployment cannot call Ollama on a judge's or your laptop through its own `localhost`. The sidebar includes an explicit model-availability check; it does not claim that the model is connected before checking.

If the model is offline, missing, slow, or returns invalid output, show an explicit warning and leave the complaint unchanged. Old valid assessments, if any, remain labelled with their review timestamp. Advice is generated only on request. A priority-only review does not include unrequested DIY steps.

`OLLAMA_BASE_URL` can point to another **loopback** port on the same computer. Non-local endpoints are rejected by this local-only helper. Initial model/package downloads need internet; inference goes to the local endpoint.

## Priorities and existing records

- `priority` is the **current** queue priority.
- `requested_priority` records the student's optional selection.
- `rule_suggested_priority` records the separate rule recommendation.
- `priority_source` shows whether it came from rules, the student, staff, or an AI recommendation explicitly accepted by staff.
- `ai_review_json` / `ai_reviewed_at` cache advisory output only. Saving advice does not change status, current priority or the ticket's modification timestamp.

On startup, `init_db()` adds missing columns to the original schema. **It does not delete tickets, reset IDs, change statuses, or silently lower existing priorities.** It backfills provenance where it was absent.

For legacy Other/Medium tickets, staff can explicitly use **Rule-based maintenance tools → Refresh this rule suggestion**. Automatically set priorities may then follow the new rules; student/staff choices remain unchanged. Existing manually set priorities are never overwritten by rule refresh or bulk triage.

Back up `campusfix.db` before applying an update. Do not delete it to obtain a clean screenshot. For a separate synthetic demo database, use `CAMPUSFIX_DB_PATH` to point at a different path. Automated tests use temporary databases.

## Tests

From your project environment:

```bash
python -m pytest -q
```

The included suite covers original-schema migration, persistent IDs, validation, manual priority, provenance, status transitions, counts, triage rules including Hindi, mocked local AI success/failure, safety gating, and Streamlit UI workflows. AI HTTP tests use mocks; they are not evidence of a successful real Gemma inference. Run a real-model check on your own machine before demonstrating AI.

## Demo flow

1. Report a missing room label with automatic priority: **Other / Low**.
2. Report another issue with a manually selected priority; show its source.
3. Open Staff desk and change priority independently of status.
4. Move a ticket through In Progress to Resolved; show dashboard totals.
5. If Ollama is available, request a priority review or safe checks, then show that the current priority is unchanged until staff explicitly acts.
6. Explain the next step: a pilot with actual college maintenance staff, after authentication and deployment review.

See `demo_script.md` for a 90-second narrative.

## Git hygiene

Commit source, requirements, tests, docs and `.streamlit/config.toml`. Do not commit virtual environments, real complaint databases, passwords, or `.streamlit/secrets.toml`.

**The source repository originally tracked `campusfix.db`, even though `.gitignore` listed it.** Ignoring a file does not untrack it. To stop tracking it while keeping your local copy:

```bash
git rm --cached campusfix.db
git add .gitignore
git commit -m "Keep local complaint database out of source control"
```

This does not erase a database already present in Git history. If it contains real personal information or credentials, handle that exposure separately; remove sensitive history where necessary and rotate exposed credentials. The update ZIP contains no database or real complaint records.

## Limitations / before a real campus pilot

- **Demo Admin is not authenticated.** A page/role label is not authorization. Do not expose real campus data publicly. Add campus SSO, server-side role checks, permissions and auditing before a pilot.
- Priority rules are heuristics, not verified hazard detection. Gemma can also be wrong, and the conservative safety filter is not a guarantee.
- This portal is not an emergency response service. Keep away from danger and follow campus emergency procedures rather than waiting for a ticket.
- SQLite is a simple single-server demo store. Assess concurrency, hosting persistence, access controls and backups before deployment; no production capacity claim is made.
- No photo attachments, notifications or student accounts yet.
