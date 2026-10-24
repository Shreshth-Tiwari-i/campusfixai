# CampusFix AI — 90-Second Demonstration Script

**Target Time:** 90 Seconds  
**Objective:** Present a complete, transparent walkthrough of CampusFix AI from issue reporting to resolution.

---

## Timeline & Action Script

| Time | Section | Screen Action | Speaker Narration |
|---|---|---|---|
| **0:00 - 0:15** | **Introduction** | Open browser to `http://localhost:8501`. Show the clean, wide-layout application header. | *"Welcome to CampusFix AI. On college campuses, facility maintenance complaints get lost in WhatsApp chats and verbal requests. CampusFix AI provides a reliable, transparent ticketing system with deterministic triage, live metrics, and staff accountability."* |
| **0:15 - 0:35** | **1. Report an Issue** | Scroll to **"Report an Issue"**. Fill form:<br>• **Title:** `Sparks from wall socket`<br>• **Description:** `Visible sparks and a burning smell near the laboratory door`<br>• **Building:** `Science Block`<br>• **Room:** `A-101`<br>Click **"Submit Report"**. | *"Let's submit a student complaint. The form validates all required fields, trims whitespace, and protects against HTML injection. As soon as we submit, the system writes to SQLite and immediately evaluates the issue."* |
| **0:35 - 0:45** | **2. Ticket ID & Triage** | Highlight the submission confirmation banner and the **Triage Suggestion Details** expander. | *"The student immediately gets a permanent Ticket ID: `CF-000001`. Notice our transparent triage engine: it categorized this as `Electrical` with `🔴 High` priority because it matched the keyword 'sparks'. Notice the source: 'Rule-based suggestion'—we never falsely claim a neural model processed it."* |
| **0:45 - 0:55** | **3. Live Dashboard** | Scroll up to the **"Dashboard"**. Point out metric cards (`Total: 1`, `Pending: 1`, `Resolved: 0`) and the top row of the table. | *"Without refreshing or restarting the server, our live dashboard reflects the new ticket instantly. Total is 1, Pending is 1, and the table displays the ticket ID, status badge `🟡 Reported`, priority, and triage reason."* |
| **0:55 - 1:10** | **4. Status Progression** | Scroll down to **"Demo Admin"**. Select `CF-000001`.<br>1. Click **"Move to In Progress"**.<br>2. Click **"Move to Resolved"**. | *"Now let's switch to maintenance staff. In our Demo Admin panel, staff select the ticket to inspect details. Our database enforces a strict state machine: tickets can only move from Reported to In Progress, and then to Resolved. Once marked Resolved, further advancement is disabled."* |
| **1:10 - 1:20** | **5. Confirm Resolution** | 1. Check Dashboard totals: `Pending: 0`, `Resolved: 1`.<br>2. In **"Check Ticket Status"**, enter `CF-000001` and click **"Check Status"**. | *"Looking back at our dashboard, Pending has dropped to 0 and Resolved is 1. The student can check their ticket anytime using 'Check Ticket Status', confirming it is `🟢 Resolved` with the exact updated timestamp."* |
| **1:20 - 1:30** | **6. Triage & Next Step** | Highlight the **"Triage Untriaged Tickets"** button and conclude. | *"CampusFix AI uses 100% deterministic, transparent rules with zero AI hallucinations and full SQLite persistence. Our immediate next step is a live 4-week pilot with college maintenance staff. Thank you!"* |

---

## Preparation Checklist Before Demo

1. **Clean Test Database**:
   ```powershell
   # If you want to start with a fresh demonstration database:
   Remove-Item campusfix.db -ErrorAction SilentlyContinue
   ```
2. **Launch Application**:
   ```powershell
   .venv\Scripts\Activate.ps1
   streamlit run app.py
   ```
3. **Browser Setup**:
   - Open [http://localhost:8501](http://localhost:8501) in your browser.
   - Set zoom level to 100% or 110% for crisp readability.
