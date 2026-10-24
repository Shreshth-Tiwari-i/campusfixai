"""CampusFix AI: report, track, prioritize, and resolve campus issues."""

import os
from pathlib import Path
import sqlite3

import streamlit as st

import ui
from ai_assistant import (
    AIUnavailableError, LOCAL_AI_SOURCE, SAFETY_SOURCE, check_local_model, review_complaint,
)
from db import (
    AI_ACCEPTED_SOURCE, ALLOWED_STATUS_TRANSITIONS, DEFAULT_DB_PATH,
    MAX_BUILDING_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_ROOM_LENGTH, MAX_TITLE_LENGTH,
    STAFF_PRIORITY_SOURCE, create_complaint, format_ticket_id, get_all_complaints,
    get_complaint, get_complaint_counts, get_saved_ai_review, init_db, parse_ticket_id,
    refresh_rule_suggestion, save_ai_review, triage_untriaged_complaints,
    update_complaint_priority, update_complaint_status,
)
from triage import ALLOWED_PRIORITIES, get_safety_notice

ui.setup()
DB_PATH = Path(os.environ.get("CAMPUSFIX_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
init_db(DB_PATH)
PAGES = ["Dashboard", "Report an issue", "Track a ticket", "Staff desk"]
AUTO_PRIORITY = "Use automatic suggestion"


def navigate(page, ticket_id=None):
    # Button callbacks run before the navigation widget is recreated.
    st.session_state["page"] = page
    if ticket_id is not None:
        st.session_state["tracked_id"] = ticket_id
        st.session_state["lookup_query"] = format_ticket_id(ticket_id)
        st.session_state.pop("lookup_error", None)


def flash(message, kind="success"):
    st.session_state["flash"] = (message, kind)


def submit_report():
    st.session_state.pop("report_error", None)
    st.session_state.pop("last_submitted_id", None)
    try:
        choice = st.session_state.get("report_priority", AUTO_PRIORITY)
        complaint_id = create_complaint(
            title=st.session_state.get("report_title", ""),
            description=st.session_state.get("report_description", ""),
            building=st.session_state.get("report_building", ""),
            room=st.session_state.get("report_room", ""),
            requested_priority=None if choice == AUTO_PRIORITY else choice,
            db_path=DB_PATH,
        )
    except (ValueError, sqlite3.Error) as exc:
        st.session_state["report_error"] = str(exc)
        return
    st.session_state["last_submitted_id"] = complaint_id
    for key in ("report_title", "report_description", "report_building", "report_room"):
        st.session_state[key] = ""
    st.session_state["report_priority"] = AUTO_PRIORITY
    flash("Report received. Save your ticket ID to follow its progress.")


def lookup_ticket():
    st.session_state.pop("lookup_error", None)
    st.session_state.pop("tracked_id", None)
    ticket_id = parse_ticket_id(st.session_state.get("lookup_query", ""))
    if ticket_id is None:
        st.session_state["lookup_error"] = "Enter a valid ticket ID, for example CF-000001."
    elif get_complaint(ticket_id, db_path=DB_PATH) is None:
        st.session_state["lookup_error"] = "No matching ticket. Check the ID and try again."
    else:
        st.session_state["tracked_id"] = ticket_id


def save_action(action, message):
    try:
        action()
        flash(message)
        st.rerun()
    except (ValueError, sqlite3.Error) as exc:
        st.error(str(exc))


def assistant_panel(ticket, prefix, staff=False):
    ticket_id = ticket["id"]
    with st.expander("✦  Local AI assistant", expanded=False):
        st.caption("Optional, on demand, and advisory. No automatic priority or status changes.")
        with st.form(f"{prefix}_assistant_form_{ticket_id}"):
            task = st.radio("What would help?", ["Review priority", "Suggest safe next steps"],
                            horizontal=True, key=f"{prefix}_ai_task_{ticket_id}")
            question = st.text_input("Optional question", max_chars=500,
                                     placeholder="e.g. Is there a safe check before staff arrive?",
                                     key=f"{prefix}_ai_question_{ticket_id}")
            ask = st.form_submit_button("Ask local assistant", key=f"{prefix}_ask_ai_{ticket_id}")
        if ask:
            try:
                with st.spinner("Reviewing this report…"):
                    review = review_complaint(
                        dict(ticket), mode="priority" if task == "Review priority" else "advice",
                        question=question,
                    )
                    save_ai_review(ticket_id, review, db_path=DB_PATH)
                flash("Safety guidance ready; no model was called." if review["source"] == SAFETY_SOURCE
                      else "Local AI review saved. The current priority is unchanged.")
                st.rerun()
            except (AIUnavailableError, ValueError, sqlite3.Error) as exc:
                st.warning(str(exc))
                st.caption("The ticket and its existing rule-based suggestion are still available.")
        fresh = get_complaint(ticket_id, db_path=DB_PATH)
        review = get_saved_ai_review(fresh)
        if review:
            st.caption(f'Latest saved review · {ui.nice_time(fresh["ai_reviewed_at"])}')
            st.markdown(ui.badge(review["recommended_priority"]) +
                        f'<span class="cf-source">{ui.esc(review["source"])}</span>', unsafe_allow_html=True)
            st.text(review["priority_reason"])
            if review["safety_warning"]:
                st.warning(review["safety_warning"])
            if review["safe_next_steps"]:
                st.markdown("**Safe checks to consider**")
                for index, step in enumerate(review["safe_next_steps"], 1):
                    st.text(f"{index}. {step}")
            if review["answer"]:
                st.text(review["answer"])
            if review["staff_required"]:
                st.caption("Authorized campus staff should assess or repair this issue.")
            if staff and review["recommended_priority"] != fresh["priority"]:
                if st.button("Apply this recommendation", key=f"apply_ai_{ticket_id}"):
                    source = AI_ACCEPTED_SOURCE if review["source"] == LOCAL_AI_SOURCE else STAFF_PRIORITY_SOURCE
                    save_action(lambda: update_complaint_priority(
                        ticket_id, review["recommended_priority"],
                        expected_current_priority=fresh["priority"], db_path=DB_PATH, source=source,
                    ), "Recommendation applied by staff.")
        else:
            st.info("No model has reviewed this ticket yet. Rule-based suggestions remain available.")
        st.caption("Gemma must run on the same computer as Streamlit. Known hazards use a safety rule instead of AI-generated DIY advice.")


def ticket_details(ticket, prefix, staff=False):
    ui.ticket_card(ticket, format_ticket_id(ticket["id"]))
    safety = get_safety_notice(ticket["title"], ticket["description"])
    if safety:
        st.warning(safety)
        if ticket["priority"] != "High":
            st.warning("The selected priority is lower than the safety-rule recommendation. Staff review is recommended.")
    ui.rule_details(ticket)
    assistant_panel(ticket, prefix, staff=staff)


def dashboard():
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        ui.heading("CAMPUS OVERVIEW", "Keep your campus running.",
                   "Every report has a place. Every fix has a next step.")
    with right:
        st.button("＋ Report an issue", type="primary", use_container_width=True,
                  on_click=navigate, args=("Report an issue",), key="dashboard_report")
    counts = get_complaint_counts(db_path=DB_PATH)
    for col, title, key, help_text in zip(
        st.columns(3), ["Total tickets", "Pending", "Resolved"],
        ["total", "pending", "resolved"],
        ["All reports on this campus", "Reported + In Progress", "Completed maintenance reports"],
    ):
        with col:
            with st.container(border=True):
                st.metric(title, counts[key], help=help_text)
    st.write("")
    rows = get_all_complaints(db_path=DB_PATH)
    st.subheader("Maintenance queue")
    st.caption("Overall totals above stay unchanged when you filter the queue below.")
    if not rows:
        with st.container(border=True):
            st.markdown("### A clearer campus starts with one report.")
            st.write("Broken fan, patchy Wi-Fi, or a leaking tap? Give it a ticket, not another lost message.")
            st.button("Create the first report", on_click=navigate, args=("Report an issue",), key="first_report")
        return
    a, b, c, d = st.columns([2, 1, 1, 1])
    with a:
        query = st.text_input("Search", placeholder="Ticket, issue, or location", max_chars=100, key="queue_search")
    with b:
        status = st.selectbox("Status", ["All statuses", *ALLOWED_STATUS_TRANSITIONS], key="queue_status")
    with c:
        priority = st.selectbox("Priority", ["All priorities", *ALLOWED_PRIORITIES], key="queue_priority")
    with d:
        building = st.selectbox("Building", ["All buildings", *sorted({row["building"] for row in rows})], key="queue_building")
    filtered = []
    for row in rows:
        text = f'{format_ticket_id(row["id"])} {row["title"]} {row["building"]} {row["room"]}'.casefold()
        if query.strip().casefold() not in text:
            continue
        if status != "All statuses" and row["status"] != status:
            continue
        if priority != "All priorities" and row["priority"] != priority:
            continue
        if building != "All buildings" and row["building"] != building:
            continue
        filtered.append(row)
    st.caption(f"{len(filtered)} of {len(rows)} tickets shown · newest first")
    if not filtered:
        st.info("No tickets match these filters. Try another status, priority, or search.")
    else:
        status_icons = {"Reported": "◷", "In Progress": "↗", "Resolved": "✓"}
        priority_icons = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
        st.dataframe([
            {
                "Ticket": format_ticket_id(row["id"]), "Issue": row["title"],
                "Location": f'{row["building"]} · {row["room"]}',
                "Status": f'{status_icons.get(row["status"], "")} {row["status"]}',
                "Priority": f'{priority_icons.get(row["priority"], "")} {row["priority"] or "Not set"}',
                "Category": row["category"] or "Not triaged",
            } for row in filtered
        ], hide_index=True, use_container_width=True,
           column_config={"Issue": st.column_config.TextColumn(width="medium"),
                          "Location": st.column_config.TextColumn(width="medium")})
    with st.expander("How priorities work"):
        st.write("Students can choose a priority or use the rule-based suggestion. Staff can override it. Other defaults to Low only when no hazard or more specific rule matches.")
        st.write("Gemma offers a separate, on-demand recommendation. It never silently changes the queue.")


def report_page():
    ui.heading("REPORT AN ISSUE", "Spot it. Report it. Track it.",
               "Help the right team find the problem. You will receive a ticket ID immediately.")
    if st.session_state.get("report_error"):
        st.error(st.session_state["report_error"])
    if st.session_state.get("last_submitted_id"):
        ticket = get_complaint(st.session_state["last_submitted_id"], db_path=DB_PATH)
        if ticket:
            with st.container(border=True):
                st.markdown("**Your report is on the board.** Save this reference:")
                st.code(format_ticket_id(ticket["id"]), language=None)
                st.markdown(ui.badge(ticket["status"]) + ui.badge(ticket["priority"]), unsafe_allow_html=True)
                st.caption(f'Priority source: {ticket["priority_source"]} · Category: {ticket["category"]}')
                st.button("View this ticket →", on_click=navigate,
                          args=("Track a ticket", ticket["id"]), key="view_submitted")
                safety = get_safety_notice(ticket["title"], ticket["description"])
                if safety:
                    st.warning(safety)
    main, guide = st.columns([2.2, 1], gap="large")
    with main:
        with st.form("report_issue_form"):
            st.markdown("### What needs fixing?")
            st.text_input("Issue title *", max_chars=MAX_TITLE_LENGTH, key="report_title",
                          placeholder="e.g. Projector not working in A-101")
            st.text_area("Describe the issue *", max_chars=MAX_DESCRIPTION_LENGTH, height=135,
                         key="report_description", placeholder="What happened? Where exactly? Who is affected?")
            a, b = st.columns(2)
            with a:
                st.text_input("Building *", max_chars=MAX_BUILDING_LENGTH,
                              key="report_building", placeholder="e.g. Academic Block")
            with b:
                st.text_input("Room / area *", max_chars=MAX_ROOM_LENGTH,
                              key="report_room", placeholder="e.g. A-101 or corridor")
            st.selectbox("Priority", [AUTO_PRIORITY, "Low", "Medium", "High"], key="report_priority",
                         help="Choose your own priority, or let transparent rules suggest one. Staff can adjust it.")
            st.caption("Required fields are marked *. Avoid including passwords or personal information.")
            st.form_submit_button("Submit report →", type="primary", use_container_width=True,
                                  on_click=submit_report, key="submit_report")
    with guide:
        with st.container(border=True):
            st.markdown("#### A small report. A clearer next step.")
            for number, title, text in (
                ("01", "Describe it", "One issue per ticket helps the team take action."),
                ("02", "Pinpoint the location", "Add a building and room or recognizable area."),
                ("03", "Keep your ticket ID", "Check progress without chasing another message."),
            ):
                st.markdown(f'<div class="cf-mini-step"><span class="cf-step-no">{number}</span><div class="cf-step-text"><strong>{title}</strong><br>{text}</div></div>', unsafe_allow_html=True)
        st.warning("Immediate danger? Keep away and contact campus security/maintenance directly. This portal is not an emergency service.")


def track_page():
    ui.heading("TICKET TRACKING", "A clear view of what happens next.",
               "Enter the reference from your report to see its status, priority, and latest assessment.")
    with st.form("lookup_form"):
        st.text_input("Ticket ID", placeholder="CF-000001", key="lookup_query", max_chars=30)
        st.form_submit_button("Find ticket", type="primary", on_click=lookup_ticket, key="find_ticket")
    if st.session_state.get("lookup_error"):
        st.warning(st.session_state["lookup_error"])
    elif st.session_state.get("tracked_id"):
        ticket = get_complaint(st.session_state["tracked_id"], db_path=DB_PATH)
        if ticket:
            ticket_details(ticket, "track")
        else:
            st.info("This ticket is no longer available.")
    else:
        st.caption("Your reference starts with CF-. It is shown immediately after submission.")


def staff_page():
    ui.heading("STAFF WORKSPACE", "Give every report a next step.",
               "Review the details, set the right priority, and keep students informed.")
    st.warning("Demo Admin — production authentication is not implemented. This is not a secure staff-only area; do not expose real campus data publicly.")
    rows = get_all_complaints(db_path=DB_PATH)
    if not rows:
        st.info("No tickets to manage yet. Create a report to try the staff workflow.")
        return
    by_id = {row["id"]: row for row in rows}
    selected_id = st.selectbox("Choose a ticket", list(by_id), key="staff_ticket_id",
                               format_func=lambda value: f'{format_ticket_id(value)} · {by_id[value]["title"][:65]}')
    ticket = get_complaint(selected_id, db_path=DB_PATH)
    if not ticket:
        st.warning("Ticket no longer available.")
        return
    ui.ticket_card(ticket, format_ticket_id(ticket["id"]))
    safety = get_safety_notice(ticket["title"], ticket["description"])
    if safety:
        st.warning(safety)
    status_col, priority_col = st.columns(2)
    with status_col:
        with st.container(border=True):
            st.markdown("#### Move the work forward")
            st.caption("Reported → In Progress → Resolved")
            next_statuses = ALLOWED_STATUS_TRANSITIONS.get(ticket["status"], [])
            if next_statuses:
                next_status = next_statuses[0]
                label = "Start work →" if next_status == "In Progress" else "Mark as resolved ✓"
                if st.button(label, type="primary", use_container_width=True, key=f"advance_{selected_id}"):
                    save_action(lambda: update_complaint_status(
                        selected_id, next_status, expected_current_status=ticket["status"], db_path=DB_PATH,
                    ), f"{format_ticket_id(selected_id)} is now {next_status}.")
            else:
                st.success("Resolved. This ticket has completed its lifecycle.")
    with priority_col:
        with st.form(f"priority_form_{selected_id}"):
            st.markdown("#### Set the current priority")
            st.caption(f'Current source: {ticket["priority_source"] or "Not set"}')
            options = ["Low", "Medium", "High"]
            chosen = st.selectbox("Staff priority", options,
                                   index=options.index(ticket["priority"]) if ticket["priority"] in options else 1,
                                   key=f"staff_priority_{selected_id}")
            if st.form_submit_button("Save priority", key=f"save_priority_{selected_id}"):
                save_action(lambda: update_complaint_priority(
                    selected_id, chosen, expected_current_priority=ticket["priority"], db_path=DB_PATH,
                ), "Priority saved as a staff override. Status is unchanged.")
    ui.rule_details(ticket)
    assistant_panel(ticket, "staff", staff=True)
    with st.expander("Rule-based maintenance tools"):
        st.caption("Refreshing rules never overwrites a student-selected or staff-set priority. Legacy tickets are not silently downgraded.")
        a, b = st.columns(2)
        with a:
            if st.button("Refresh this rule suggestion", key=f"refresh_rule_{selected_id}"):
                save_action(lambda: refresh_rule_suggestion(selected_id, db_path=DB_PATH), "Rule recommendation refreshed.")
        with b:
            if st.button("Triage untriaged tickets", key="bulk_triage"):
                try:
                    changed = triage_untriaged_complaints(db_path=DB_PATH)
                    flash(f"Triaged {changed} ticket(s).")
                    st.rerun()
                except sqlite3.Error as exc:
                    st.error(str(exc))


with st.sidebar:
    st.markdown('<div class="cf-brand"><div class="cf-logo">cf</div><div><div class="cf-brand-name">CampusFix<span> AI</span></div><div class="cf-brand-sub">Campus care, organized</div></div></div>', unsafe_allow_html=True)
    st.caption("WORKSPACE")
    page = st.radio("Navigate", PAGES, key="page", label_visibility="collapsed",
                    format_func=lambda name: {"Dashboard":"◫  Dashboard", "Report an issue":"＋  Report an issue", "Track a ticket":"⌕  Track a ticket", "Staff desk":"⚙  Staff desk"}[name])
    st.divider()
    st.caption("PRIORITY GUIDE")
    st.markdown(ui.badge("High") + ui.badge("Medium") + ui.badge("Low"), unsafe_allow_html=True)
    st.caption("Rules suggest. People decide. Other defaults to Low unless a higher-priority rule matches.")
    with st.expander("Local AI setup"):
        st.caption("Optional. Reporting and tracking work without it.")
        st.code("ollama pull gemma4:e4b\nollama run gemma4:e4b", language="bash")
        if st.button("Check local model", key="check_model"):
            ready, message = check_local_model()
            (st.success if ready else st.info)(message)
        st.caption("Ollama and Streamlit must run on the same computer. A hosted preview cannot access Ollama on your laptop.")
    st.markdown('<div class="cf-footer">DEMO WORKSPACE<br>SQLite storage · no production login</div>', unsafe_allow_html=True)

if "flash" in st.session_state:
    message, kind = st.session_state.pop("flash")
    getattr(st, kind)(message)

if os.environ.get("CAMPUSFIX_DEMO") == "1":
    st.caption("LIVE PREVIEW · Synthetic sample tickets only. Local Gemma is not connected in this hosted preview.")

{"Dashboard": dashboard, "Report an issue": report_page,
 "Track a ticket": track_page, "Staff desk": staff_page}[page]()

st.markdown('<div class="cf-footer">CampusFix AI · Built for a better campus, one resolved ticket at a time.</div>', unsafe_allow_html=True)
