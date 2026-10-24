"""Main Streamlit application for CampusFix AI."""

import html
import streamlit as st
from db import (
    MAX_BUILDING_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_ROOM_LENGTH,
    MAX_TITLE_LENGTH,
    create_complaint,
    format_ticket_id,
    get_all_complaints,
    get_complaint,
    get_complaint_counts,
    init_db,
    parse_ticket_id,
    triage_untriaged_complaints,
    update_complaint_status,
)

# Initialize the database safely on application startup
init_db()

st.set_page_config(
    page_title="CampusFix AI",
    page_icon="🛠️",
    layout="wide",
)


def format_status_indicator(status: str) -> str:
    """Format status string with a visual indicator."""
    if status == "Reported":
        return "🟡 Reported"
    elif status == "In Progress":
        return "🔵 In Progress"
    elif status == "Resolved":
        return "🟢 Resolved"
    return status


def format_priority_indicator(priority: str) -> str:
    """Format priority string with a color indicator."""
    if priority == "High":
        return "🔴 High"
    elif priority == "Medium":
        return "🟠 Medium"
    elif priority == "Low":
        return "🟢 Low"
    return priority or "-"


# Application Header
st.title("CampusFix AI")
st.caption("Campus maintenance and facility issue reporting system")

# ================= Section 1: Dashboard =================
st.header("📊 Dashboard")

counts = get_complaint_counts()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Complaints", counts["total"], help="All complaints submitted")
with col2:
    st.metric(
        "Pending Complaints",
        counts["pending"],
        help="Reported + In Progress complaints requiring resolution",
    )
with col3:
    st.metric(
        "Resolved Complaints",
        counts["resolved"],
        help="Complaints that have been marked Resolved",
    )

st.subheader("All Tickets")
all_complaints = get_all_complaints()
if not all_complaints:
    st.info("No complaints have been recorded yet. The database is empty.")
else:
    table_rows = [
        {
            "Ticket ID": format_ticket_id(row["id"]),
            "Title": html.escape(row["title"]),
            "Building": html.escape(row["building"]),
            "Room": html.escape(row["room"]),
            "Status": format_status_indicator(row["status"]),
            "Category": row["category"] if row["category"] else "Not triaged",
            "Priority": format_priority_indicator(row["priority"] if row["priority"] else "-"),
            "Triage Reason": row["triage_reason"] if row["triage_reason"] else "-",
            "Triage Source": row["triage_source"] if row["triage_source"] else "Not triaged",
            "Creation Time": row["created_at"],
        }
        for row in all_complaints
    ]
    st.dataframe(
        table_rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ticket ID": st.column_config.TextColumn("Ticket ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Building": st.column_config.TextColumn("Building", width="small"),
            "Room": st.column_config.TextColumn("Room", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "Triage Reason": st.column_config.TextColumn("Triage Reason", width="medium"),
            "Triage Source": st.column_config.TextColumn("Triage Source", width="small"),
            "Creation Time": st.column_config.TextColumn("Created At", width="medium"),
        },
    )

# ================= Section 2: Report an Issue =================
st.divider()
st.header("📝 Report an Issue")

# Display recent submission confirmation with rule-based triage details if available
if st.session_state.get("submitted_id"):
    sub_ticket = get_complaint(st.session_state["submitted_id"])
    if sub_ticket:
        ticket_id = format_ticket_id(sub_ticket["id"])
        safe_title = html.escape(sub_ticket["title"])
        safe_desc = html.escape(sub_ticket["description"])
        st.success(f"Complaint **{safe_title}** submitted successfully! Current status: **Reported**")
        st.info(
            f"### Your Ticket ID: **`{ticket_id}`**\n\n"
            "⚠️ **Please save this Ticket ID!** You will need it to check the status of your request."
        )
        with st.expander("Triage Suggestion Details", expanded=True):
            st.markdown(
                f"- **Category:** {sub_ticket['category']}\n"
                f"- **Priority:** {format_priority_indicator(sub_ticket['priority'])}\n"
                f"- **Explanation:** {sub_ticket['triage_reason']}\n"
                f"- **Triage Source:** {sub_ticket['triage_source']}"
            )

with st.form("report_issue_form", clear_on_submit=True):
    title = st.text_input(
        "Title *",
        max_chars=MAX_TITLE_LENGTH,
        placeholder="e.g. Leaking faucet in 2nd floor restroom",
        help=f"Brief summary of the issue (max {MAX_TITLE_LENGTH} characters)",
    )
    description = st.text_area(
        "Description *",
        max_chars=MAX_DESCRIPTION_LENGTH,
        placeholder="Provide details about the issue, exact spot, hazard level, etc.",
        help=f"Full details of the maintenance problem (max {MAX_DESCRIPTION_LENGTH} characters)",
    )
    building = st.text_input(
        "Building *",
        max_chars=MAX_BUILDING_LENGTH,
        placeholder="e.g. Science Block, Engineering Hall, Hostel B",
        help=f"Campus building or facility name (max {MAX_BUILDING_LENGTH} characters)",
    )
    room = st.text_input(
        "Room number *",
        max_chars=MAX_ROOM_LENGTH,
        placeholder="e.g. A-101, Lab 3, Restroom 2F",
        help=f"Room or area identifier (max {MAX_ROOM_LENGTH} characters)",
    )

    submitted = st.form_submit_button("Submit Report", type="primary")

if submitted:
    clean_title = (title or "").strip()
    clean_desc = (description or "").strip()
    clean_building = (building or "").strip()
    clean_room = (room or "").strip()

    if not clean_title or not clean_desc or not clean_building or not clean_room:
        st.session_state.pop("submitted_id", None)
        st.error("All fields are required. Please fill in all fields before submitting.")
    else:
        try:
            complaint_id = create_complaint(
                title=clean_title,
                description=clean_desc,
                building=clean_building,
                room=clean_room,
                auto_triage=True,
            )
            st.session_state["submitted_id"] = complaint_id
            st.rerun()
        except ValueError as err:
            st.session_state.pop("submitted_id", None)
            st.error(f"Validation error: {err}")
        except Exception as err:
            st.session_state.pop("submitted_id", None)
            st.error(f"Failed to submit complaint due to a database error: {err}")

# ================= Section 3: Check Ticket Status =================
st.divider()
st.header("🔍 Check Ticket Status")

with st.form("check_status_form"):
    search_ticket_id = st.text_input(
        "Ticket ID",
        placeholder="e.g. CF-000001",
        help="Enter the 6-digit reference ID you received when submitting your issue",
    )
    status_submitted = st.form_submit_button("Check Status")

if status_submitted:
    raw_query = (search_ticket_id or "").strip()
    if not raw_query:
        st.warning("Please enter a Ticket ID to check.")
    else:
        parsed_id = parse_ticket_id(raw_query)
        if parsed_id is None:
            st.error(
                f"Invalid Ticket ID format: '{raw_query}'. Ticket IDs must be in the format CF-000001."
            )
        else:
            ticket = get_complaint(parsed_id)
            if ticket is None:
                st.warning(
                    f"No ticket found with ID '{format_ticket_id(parsed_id)}'. Please verify your Ticket ID and try again."
                )
            else:
                formatted_id = format_ticket_id(ticket["id"])
                safe_title = html.escape(ticket["title"])
                safe_building = html.escape(ticket["building"])
                safe_room = html.escape(ticket["room"])
                safe_desc = html.escape(ticket["description"])

                st.success(f"Ticket Found: {formatted_id}")
                st.markdown(f"### {safe_title}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Location:** {safe_building}, Room {safe_room}")
                    st.markdown(f"**Status:** {format_status_indicator(ticket['status'])}")
                    st.markdown(f"**Description:** {safe_desc}")
                with col_b:
                    st.markdown(f"**Category:** {ticket['category'] if ticket['category'] else 'Not triaged'}")
                    st.markdown(f"**Priority:** {format_priority_indicator(ticket['priority'])}")
                    st.markdown(f"**Triage Reason:** {ticket['triage_reason'] if ticket['triage_reason'] else '-'}")
                    st.markdown(f"**Triage Source:** {ticket['triage_source'] if ticket['triage_source'] else 'Not triaged'}")
                    st.markdown(f"**Created At:** {ticket['created_at']}")
                    st.markdown(f"**Last Updated:** {ticket['updated_at']}")

# ================= Section 4: Demo Admin =================
st.divider()
st.header("⚙️ Demo Admin — production authentication is not implemented")

# Bulk Triage Action for existing untriaged tickets
st.markdown("#### Maintenance Triage Actions")
if st.button("Triage Untriaged Tickets", key="btn_triage_untriaged"):
    triaged_count = triage_untriaged_complaints()
    if triaged_count > 0:
        st.success(
            f"Successfully evaluated and triaged {triaged_count} untriaged ticket(s) using rule-based suggestions."
        )
        st.rerun()
    else:
        st.info("All tickets in the database are already triaged.")

admin_complaints = get_all_complaints()
if not admin_complaints:
    st.info("No tickets available to manage.")
else:
    st.markdown("#### Ticket Lifecycle Management")
    ticket_options = {
        f"{format_ticket_id(c['id'])} — {c['title'][:40]} [{c['status']}]": c["id"]
        for c in admin_complaints
    }

    selected_label = st.selectbox(
        "Select a ticket to manage:",
        options=list(ticket_options.keys()),
        key="admin_ticket_select",
    )

    selected_id = ticket_options[selected_label]
    fresh_ticket = get_complaint(selected_id)

    if fresh_ticket is None:
        st.warning("Selected ticket no longer exists.")
    else:
        st.subheader(f"Ticket Details: {format_ticket_id(fresh_ticket['id'])}")
        safe_title = html.escape(fresh_ticket["title"])
        safe_building = html.escape(fresh_ticket["building"])
        safe_room = html.escape(fresh_ticket["room"])
        safe_desc = html.escape(fresh_ticket["description"])

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.markdown(f"**Title:** {safe_title}")
            st.markdown(f"**Location:** {safe_building}, Room {safe_room}")
            st.markdown(f"**Current Status:** {format_status_indicator(fresh_ticket['status'])}")
            st.markdown(f"**Description:** {safe_desc}")
        with d_col2:
            st.markdown(f"**Category:** {fresh_ticket['category'] if fresh_ticket['category'] else 'Not triaged'}")
            st.markdown(f"**Suggested Priority:** {format_priority_indicator(fresh_ticket['priority'])}")
            st.markdown(f"**Triage Reason:** {fresh_ticket['triage_reason'] if fresh_ticket['triage_reason'] else '-'}")
            st.markdown(f"**Triage Source:** {fresh_ticket['triage_source'] if fresh_ticket['triage_source'] else 'Not triaged'}")
            st.markdown(f"**Created At:** {fresh_ticket['created_at']}")
            st.markdown(f"**Last Updated:** {fresh_ticket['updated_at']}")

        curr_status = fresh_ticket["status"]
        if curr_status == "Reported":
            if st.button("Move to In Progress", key=f"btn_in_progress_{fresh_ticket['id']}", type="primary"):
                try:
                    update_complaint_status(
                        complaint_id=fresh_ticket["id"],
                        new_status="In Progress",
                        expected_current_status="Reported",
                    )
                    st.success(f"{format_ticket_id(fresh_ticket['id'])} moved to In Progress.")
                    st.rerun()
                except ValueError as err:
                    st.error(f"Cannot update status: {err}")
                except Exception as err:
                    st.error(f"Database error during update: {err}")
        elif curr_status == "In Progress":
            if st.button("Move to Resolved", key=f"btn_resolved_{fresh_ticket['id']}", type="primary"):
                try:
                    update_complaint_status(
                        complaint_id=fresh_ticket["id"],
                        new_status="Resolved",
                        expected_current_status="In Progress",
                    )
                    st.success(f"{format_ticket_id(fresh_ticket['id'])} moved to Resolved.")
                    st.rerun()
                except ValueError as err:
                    st.error(f"Cannot update status: {err}")
                except Exception as err:
                    st.error(f"Database error during update: {err}")
        elif curr_status == "Resolved":
            st.info("This ticket is **Resolved** and cannot be advanced further.")
