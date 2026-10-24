"""Small, self-contained presentation helpers. User text is always escaped."""

import html
from datetime import datetime
import streamlit as st

CSS = """
<style>
:root { --cf-ink:#152534; --cf-muted:#657787; --cf-teal:#0f766e; }
[data-testid="stAppViewContainer"] { background:#f5f7fb; }
[data-testid="stHeader"] { background:rgba(245,247,251,.92); }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid #e7edf3; }
[data-testid="stSidebar"] > div:first-child { padding-top:1.8rem; }
[data-testid="stMainBlockContainer"] { max-width:1270px; padding-top:4rem; padding-bottom:3rem; }
h1,h2,h3 { color:var(--cf-ink); letter-spacing:-.035em; }
h1 { font-weight:750 !important; line-height:1.12 !important; }
p, label { line-height:1.6; }
[data-testid="stMetricLabel"] { color:var(--cf-muted); font-size:.85rem; }
[data-testid="stMetricValue"] { color:var(--cf-ink); font-size:2.2rem; font-weight:700; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px !important; }
[data-testid="stForm"] { background:white; border:1px solid #e3eaf0; border-radius:18px; padding:1.3rem; }
.stButton button, .stFormSubmitButton button { border-radius:10px; font-weight:600; min-height:2.65rem; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { border-radius:10px; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.4rem .15rem; }
.cf-brand { display:flex; align-items:center; gap:11px; margin-bottom:2rem; }
.cf-logo { width:43px; height:43px; border-radius:13px; background:#0f766e; color:white;
 display:flex; align-items:center; justify-content:center; font-weight:800; font-size:20px; letter-spacing:-2px; }
.cf-brand-name { font-size:1.3rem; font-weight:750; letter-spacing:-.6px; color:#152534; }
.cf-brand-name span { color:#0f766e; }
.cf-brand-sub { font-size:.7rem; color:#81919e; letter-spacing:.09em; text-transform:uppercase; }
.cf-eyebrow { color:#0f766e; font-size:.7rem; font-weight:750; letter-spacing:.14em; margin-bottom:.65rem; text-transform:uppercase; }
.cf-subtitle { color:#657787; font-size:1rem; max-width:650px; margin:0 0 1.8rem; }
.cf-kicker { color:#82909d; font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; }
.cf-pill { display:inline-flex; align-items:center; border-radius:99px; padding:5px 11px;
 font-size:.75rem; font-weight:650; margin:0 5px 6px 0; border:1px solid transparent; }
.cf-high { color:#a3293c; background:#fff0f2; border-color:#f9d9df; }
.cf-medium { color:#8a5b0a; background:#fff6de; border-color:#f2e3b6; }
.cf-low { color:#0b7261; background:#e8f7f1; border-color:#cdebe1; }
.cf-neutral { color:#586a7a; background:#eff3f7; border-color:#e2e8ef; }
.cf-progress { color:#2857a5; background:#edf3ff; border-color:#d9e5ff; }
.cf-source { color:#697b8c; font-size:.76rem; line-height:1.5; margin:2px 0 12px; }
.cf-field-label { color:#7a8b99; text-transform:uppercase; letter-spacing:.08em; font-size:.66rem; font-weight:700; margin-top:12px; }
.cf-field-value { color:#203543; font-size:.94rem; margin-top:2px; overflow-wrap:anywhere; }
.cf-description { white-space:pre-wrap; color:#405464; font-size:.93rem; line-height:1.7; overflow-wrap:anywhere; }
.cf-mini-step { display:flex; align-items:flex-start; gap:12px; margin:1rem 0; }
.cf-step-no { background:#e7f4ef; color:#0f766e; width:27px; height:27px; border-radius:9px;
 display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:.72rem; font-weight:750; }
.cf-step-text { color:#657787; font-size:.83rem; line-height:1.6; }
.cf-step-text strong { color:#253c4c; }
.cf-footer { color:#8795a1; font-size:.72rem; padding-top:1.4rem; border-top:1px solid #e5ebf1; margin-top:2.3rem; }
@media(max-width:700px) {
 [data-testid="stMainBlockContainer"] { padding:3.75rem .9rem 2rem; }
 h1 { font-size:1.9rem !important; }
 [data-testid="stForm"] { padding:1rem; }
 .cf-subtitle { font-size:.9rem; }
}
</style>
"""


def setup():
    st.set_page_config(page_title="CampusFix AI", page_icon="🛠️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def heading(eyebrow, title, subtitle):
    st.markdown(f'<div class="cf-eyebrow">{esc(eyebrow)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<p class="cf-subtitle">{esc(subtitle)}</p>', unsafe_allow_html=True)


def badge(value, kind="priority"):
    styles = {"High":"high", "Medium":"medium", "Low":"low", "Reported":"medium",
              "In Progress":"progress", "Resolved":"low"}
    style = styles.get(value, "neutral")
    return f'<span class="cf-pill cf-{style}">{esc(value or "Not set")}</span>'


def field(label, value):
    st.markdown(
        f'<div class="cf-field-label">{esc(label)}</div><div class="cf-field-value">{esc(value or "—")}</div>',
        unsafe_allow_html=True,
    )


def nice_time(value):
    if not value:
        return "—"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.strftime("%d %b %Y · %H:%M UTC")
    except (ValueError, AttributeError):
        return str(value)


def ticket_card(ticket, ticket_id):
    t = dict(ticket)
    with st.container(border=True):
        st.caption(ticket_id)
        st.markdown(f'<h3 style="margin:0 0 12px">{esc(t["title"])}</h3>', unsafe_allow_html=True)
        st.markdown(badge(t["status"], "status") + badge(t["priority"]), unsafe_allow_html=True)
        left, right = st.columns([2, 1])
        with left:
            field("Location", f'{t["building"]} · {t["room"]}')
            st.markdown('<div class="cf-field-label">Description</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cf-description">{esc(t["description"])}</div>', unsafe_allow_html=True)
        with right:
            field("Category", t["category"] or "Not triaged")
            field("Priority chosen by", t.get("priority_source") or "Not set")
            field("Created", nice_time(t["created_at"]))
            field("Last updated", nice_time(t["updated_at"]))


def rule_details(ticket):
    t = dict(ticket)
    with st.expander("Why this priority?", expanded=False):
        a, b = st.columns(2)
        with a:
            field("Student requested", t.get("requested_priority") or "Automatic suggestion")
            field("Current priority", t.get("priority") or "Not set")
        with b:
            field("Rule recommends", t.get("rule_suggested_priority") or "Not triaged")
            field("Recommendation source", t.get("triage_source") or "Not triaged")
        st.text(t.get("triage_reason") or "No rule assessment yet.")
        st.caption("Suggestions are advisory. Manual choices remain separate; staff make the final decision.")
