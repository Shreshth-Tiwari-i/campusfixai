# CampusFix AI

> **Transparent, deterministic campus facility maintenance tracking and triage.**

CampusFix AI is a lightweight, reliable facility reporting and tracking portal designed for college campuses. It replaces messy WhatsApp messages, informal verbal complaints, and lost paper logs with structured ticket submission, deterministic rule-based triage, live dashboard metrics, and a controlled maintenance lifecycle.

---

## Problem & Solution

### The Problem
On college campuses, facility issues (broken projectors, leaking washrooms, flickering lights, hazardous exposed wiring) are typically reported via informal channels. This creates:
- **No visibility for students**: Students report an issue once and never know if anyone is working on it.
- **Untriaged hazards**: Safety issues (sparks, severe leaks) sit in the same queue as minor cosmetic requests.
- **Loss of accountability**: Maintenance staff lack a centralized queue with lifecycle history and audit timestamps.

### The Solution
CampusFix AI provides:
1. **Structured Student Reporting**: Clean form with validation, character limits, and whitespace trimming.
2. **Deterministic Rule-Based Triage**: Instant suggestions for category, priority, and rationale without hallucinated AI responses.
3. **Transparent Ticket IDs**: Easy-to-remember zero-padded reference numbers (`CF-000001`) tied directly to database primary keys.
4. **Real-Time Live Dashboard**: Instant status visibility (`Total`, `Pending`, `Resolved`) calculated directly from SQLite.
5. **Enforced Maintenance Lifecycle**: Unidirectional state machine (`Reported` $\rightarrow$ `In Progress` $\rightarrow$ `Resolved`) with database-level guards.
6. **Public Status Lookup**: Read-only status checking by Ticket ID for students.

---

## Implemented Features

| Feature | Description |
|---|---|
| **Issue Reporting** | Form capturing Title, Description, Building, and Room (accepts alphanumeric strings like `A-101`). Enforces required fields and length limits. |
| **XSS & HTML Safety** | All user inputs are sanitized with `html.escape` to ensure complaint text is never rendered as raw HTML. |
| **Human-Readable Ticket IDs** | Displays format `CF-000001` using the database row's `lastrowid`. Never computed from row counts or `MAX(id)`. |
| **Rule-Based Triage Engine** | Evaluates keyword rules in documented order to assign Category (`Electrical`, `Plumbing`, `Network`, `AV/Equipment`, `Other`) and Priority (`High`, `Medium`, `Low`). |
| **Bilingual Keyword Support** | Recognizes common English and Hindi/Hinglish terms (e.g. *bijli*, *pankha*, *nal leak*, *paani tapak raha*, *spark ho raha*, *plaster ukhad gaya*). |
| **Real-Time Dashboard** | Metric cards for **Total**, **Pending** (*Reported* + *In Progress*), and **Resolved**, plus an interactive table updating immediately upon submission. |
| **Status Indicators** | Visual badges for ticket lifecycle (`🟡 Reported`, `🔵 In Progress`, `🟢 Resolved`) and priority (`🔴 High`, `🟠 Medium`, `🟢 Low`). |
| **Read-Only Status Lookup** | Students enter their Ticket ID to verify current status, location, timestamps, and triage suggestions. |
| **Demo Admin Panel** | Staff portal to select tickets, view details, advance status through valid transitions, or run bulk triage on legacy tickets. |
| **Database State Machine** | Strict database-level transition enforcement: blocks backward transitions, skipped transitions, and alterations to resolved tickets. |

---

## Actual Technology Stack

- **Language**: Python 3.14 (compatible with Python 3.10+)
- **Web Framework**: [Streamlit](https://streamlit.io/) (v1.66.1)
- **Database**: [SQLite 3](https://www.sqlite.org/) (embedded relational database with `sqlite3.Row` factory)
- **Test Framework**: [pytest](https://docs.pytest.org/) (v9.1.1) with 30 automated unit and integration tests
- **Security & Core Libraries**: Python standard library (`html`, `re`, `pathlib`, `typing`)

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher installed on your system.
- Git (optional, for version tracking).

### 2. Windows (PowerShell)
```powershell
# Clone or navigate to the project root
cd c:\Project\campusfixai

# Create a project virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py
```

### 3. Linux / macOS (bash/zsh)
```bash
# Navigate to the project root
cd campusfixai

# Create a project virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py
```

The application will be accessible at: **`http://localhost:8501`**

---

## Running the Automated Test Suite

CampusFix AI includes a 30-test automated test suite covering database schema, input validation, state transitions, ticket lookup, triage keywords, and end-to-end workflows.

```powershell
# Windows
.venv\Scripts\pytest.exe -v

# Linux / macOS
pytest -v
```

---

## How SQLite Persistence Works

1. **Storage Engine**: Data is persisted in a local SQLite database file named `campusfix.db` located in the project directory.
2. **Safe Initialization**: On startup, `db.init_db()` executes `CREATE TABLE IF NOT EXISTS complaints (...)`. Existing complaints and table schema are preserved across server restarts and crashes.
3. **Primary Key Auto-Increment**: The `id INTEGER PRIMARY KEY AUTOINCREMENT` column generates monotonic IDs. Newly created complaints return `cursor.lastrowid`, which formats directly into `CF-{id:06d}`.
4. **Optimistic Concurrency & Transactions**: Status transitions execute atomic parameterized SQL (`UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = ?`). If another user modified the ticket concurrently, `cursor.rowcount == 0` and the update is rejected with an explicit error.
5. **Isolated Testing**: Automated tests use pytest's `tmp_path` fixture to create throwaway temporary databases (`test_campusfix.db`), ensuring test runs never mutate or wipe development data.

---

## Transparent Rule-Based Triage

Rather than relying on opaque cloud APIs or unverified LLMs, CampusFix AI uses an explicit, deterministic keyword engine in `triage.py`:

```
+-----------------------------------------------------------------------------------+
|                            Documented Rule Hierarchy                              |
+-----------------------------------------------------------------------------------+
| Tier 1: Immediate Safety Hazards (Priority: High)                                 |
|         - Electrical hazard (sparks, exposed wires, burning smell, short circuit)  |
|         - Flooding hazard (severe flooding, pipe burst, water overflow)           |
+-----------------------------------------------------------------------------------+
| Tier 2: Core Utilities (Priority: Medium)                                         |
|         - Plumbing (leaks, taps, clogged drains, flush)                           |
|         - Network (Wi-Fi, Ethernet, router offline)                               |
|         - AV/Equipment (projector, microphone, speaker, HDMI)                     |
|         - Standard Electrical (fans, lights, AC, switches)                        |
+-----------------------------------------------------------------------------------+
| Tier 3: Minor Damage (Priority: Low)                                              |
|         - Cosmetic (paint peeling, scratches, stains, chipped tiles)              |
+-----------------------------------------------------------------------------------+
| Tier 4: Fallback (Priority: Medium)                                               |
|         - Unmatched text defaults to: Category 'Other', "Manual review needed"    |
+-----------------------------------------------------------------------------------+
```

- **Triage Source**: Always explicitly tagged as **`Rule-based suggestion`**.
- **Transparency**: Every suggestion displays the exact keyword that triggered the rule (e.g. *Rule matched 'Electrical hazard' on keyword 'sparks'*).
- **No False Claims**: The application never claims an artificial intelligence or neural network evaluated the ticket.

---

## Limitations

1. **No Production Authentication**: The demo admin panel includes an unauthenticated role switcher for demonstration and evaluation purposes. A production release requires campus SSO / LDAP integration.
2. **No Verified AI Accuracy**: Category and priority assignments are heuristic keyword suggestions. Ambiguous or misspelled descriptions may trigger the fallback category.
3. **No Emergency-Response Guarantee**: CampusFix AI is an administrative facility ticketing platform. Critical life-safety emergencies (fires, gas leaks) require direct contact with campus emergency services.
4. **Single-Node SQLite**: Suitable for single-campus pilots (~10,000 tickets/year), but enterprise multi-campus deployments will require PostgreSQL.

---

## Next Step: Campus Pilot

The immediate next milestone is a **4-week live pilot with college maintenance staff and hostel wardens**:
- Deploy on a local campus server for one hostel block and one academic wing.
- Validate triage keyword match rates against real student vernacular and regional terms.
- Measure average resolution time from `Reported` to `Resolved`.
- Gather usability feedback from facility technicians.

---

## Known Remaining Issues

1. **Browser Hard Reload State**: When a student hard-refreshes the browser page (`F5`), Streamlit resets session state, hiding the previous submission banner. Students can instantly retrieve their ticket using the **"Check Ticket Status"** section.
2. **Attachment Support**: The MVP does not currently support image or photo attachments for reported issues.
3. **Keyword Overlap**: While documented rule hierarchy guarantees deterministic evaluation, complex multi-issue complaints (e.g. *"light bulb fell into leaking sink"*) will match the higher-priority rule (Electrical) first.
