"""SQLite persistence for CampusFix. Migrations never reset existing tickets."""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sqlite3
from typing import Optional, Union

from triage import ALLOWED_CATEGORIES, ALLOWED_PRIORITIES, RULE_BASED_SOURCE, triage_complaint

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "campusfix.db"
MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 2000
MAX_BUILDING_LENGTH = 100
MAX_ROOM_LENGTH = 50
STUDENT_PRIORITY_SOURCE = "Student selected"
STAFF_PRIORITY_SOURCE = "Staff override"
AI_ACCEPTED_SOURCE = "AI suggestion accepted by staff"
ALLOWED_STATUS_TRANSITIONS = {
    "Reported": ["In Progress"],
    "In Progress": ["Resolved"],
    "Resolved": [],
}


def get_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


@contextmanager
def _database(db_path=DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    """Create a new database or add missing columns to the original schema.

    Existing IDs, priorities, timestamps and statuses are not changed. Legacy
    priority provenance is backfilled only when no provenance was recorded.
    """
    with _database(db_path) as conn:
        # Serialize first-run migrations if two Streamlit sessions start together.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                building TEXT NOT NULL,
                room TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Reported',
                category TEXT,
                priority TEXT,
                triage_reason TEXT,
                triage_source TEXT NOT NULL DEFAULT 'Not triaged',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(complaints)")}
        additions = {
            "requested_priority": "TEXT",
            "rule_suggested_priority": "TEXT",
            "priority_source": "TEXT",
            "ai_review_json": "TEXT",
            "ai_reviewed_at": "TEXT",
        }
        for name, sql_type in additions.items():
            if name not in existing:
                # Both identifiers and types come from the fixed dictionary above.
                conn.execute(f"ALTER TABLE complaints ADD COLUMN {name} {sql_type}")
        conn.execute("""
            UPDATE complaints
            SET priority_source = CASE
                WHEN priority IS NULL THEN 'Not set'
                WHEN triage_source = ? THEN ?
                ELSE 'Existing priority'
            END
            WHERE priority_source IS NULL OR trim(priority_source) = ''
        """, (RULE_BASED_SOURCE, RULE_BASED_SOURCE))
        conn.execute("""
            UPDATE complaints SET rule_suggested_priority = priority
            WHERE rule_suggested_priority IS NULL AND triage_source = ?
        """, (RULE_BASED_SOURCE,))


def _validate_priority(priority, allow_none=False):
    if priority is None and allow_none:
        return
    if priority not in ALLOWED_PRIORITIES:
        raise ValueError("Priority must be High, Medium, or Low.")


def _validate_fields(title, description, building, room):
    clean = []
    for label, value, maximum in (
        ("Title", title, MAX_TITLE_LENGTH),
        ("Description", description, MAX_DESCRIPTION_LENGTH),
        ("Building", building, MAX_BUILDING_LENGTH),
        ("Room number", room, MAX_ROOM_LENGTH),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required and cannot be empty or whitespace.")
        value = value.strip()
        if len(value) > maximum:
            raise ValueError(f"{label} must not exceed {maximum} characters.")
        clean.append(value)
    return clean


def create_complaint(
    title: str,
    description: str,
    building: str,
    room: str,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    triage_reason: Optional[str] = None,
    triage_source: Optional[str] = None,
    auto_triage: bool = True,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
    requested_priority: Optional[str] = None,
) -> int:
    title, description, building, room = _validate_fields(title, description, building, room)
    _validate_priority(priority, allow_none=True)
    _validate_priority(requested_priority, allow_none=True)
    if requested_priority is not None and priority is not None and requested_priority != priority:
        raise ValueError("Conflicting requested priorities were supplied.")
    if category is not None and category not in ALLOWED_CATEGORIES:
        raise ValueError("Unknown complaint category.")
    chosen = requested_priority if requested_priority is not None else priority
    suggestion = triage_complaint(title, description) if auto_triage else None
    if suggestion:
        category = category or suggestion.category
        triage_reason = triage_reason if triage_reason is not None else suggestion.reason
        triage_source = triage_source or suggestion.source
    rule_priority = suggestion.priority if suggestion else None
    current_priority = chosen if chosen is not None else rule_priority
    priority_source = STUDENT_PRIORITY_SOURCE if chosen is not None else (
        RULE_BASED_SOURCE if suggestion else "Not set"
    )
    with _database(db_path) as conn:
        cur = conn.execute("""
            INSERT INTO complaints (
                title, description, building, room, status, category, priority,
                triage_reason, triage_source, requested_priority,
                rule_suggested_priority, priority_source
            ) VALUES (?, ?, ?, ?, 'Reported', ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, description, building, room, category, current_priority,
            triage_reason, triage_source or "Not triaged", chosen,
            rule_priority, priority_source,
        ))
        return int(cur.lastrowid)


def get_complaint(complaint_id: int, db_path=DEFAULT_DB_PATH) -> Optional[sqlite3.Row]:
    with _database(db_path) as conn:
        return conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()


def get_all_complaints(db_path=DEFAULT_DB_PATH) -> list[sqlite3.Row]:
    with _database(db_path) as conn:
        return conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()


def format_ticket_id(complaint_id: int) -> str:
    if type(complaint_id) is not int or complaint_id <= 0:
        raise ValueError("Complaint ID must be a positive integer.")
    return f"CF-{complaint_id:06d}"


def parse_ticket_id(ticket_id: str) -> Optional[int]:
    if not isinstance(ticket_id, str):
        return None
    match = re.fullmatch(r"CF-([0-9]{1,18})", ticket_id.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    value = int(match.group(1))
    return value if 0 < value <= 9223372036854775807 else None


def get_complaint_by_ticket_id(ticket_id: str, db_path=DEFAULT_DB_PATH):
    parsed = parse_ticket_id(ticket_id)
    return None if parsed is None else get_complaint(parsed, db_path=db_path)


def get_complaint_counts(db_path=DEFAULT_DB_PATH) -> dict:
    with _database(db_path) as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status IN ('Reported', 'In Progress') THEN 1 ELSE 0 END), 0) AS pending,
            COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved
            FROM complaints
        """).fetchone()
        return {key: int(row[key]) for key in ("total", "pending", "resolved")}


def update_complaint_status(
    complaint_id: int,
    new_status: str,
    expected_current_status: Optional[str] = None,
    db_path=DEFAULT_DB_PATH,
) -> bool:
    with _database(db_path) as conn:
        row = conn.execute("SELECT status FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if row is None:
            raise ValueError("Ticket not found.")
        current = row["status"]
        if expected_current_status is not None and current != expected_current_status:
            raise ValueError("This ticket was updated elsewhere. Reload it and try again.")
        if new_status not in ALLOWED_STATUS_TRANSITIONS.get(current, []):
            raise ValueError(f"Invalid transition from '{current}' to '{new_status}'.")
        cur = conn.execute("""
            UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = ?
        """, (new_status, complaint_id, current))
        if cur.rowcount != 1:
            raise ValueError("This ticket changed while saving. Reload and try again.")
    return True


def update_complaint_priority(
    complaint_id: int,
    new_priority: str,
    expected_current_priority: Optional[str] = None,
    db_path=DEFAULT_DB_PATH,
    source: str = STAFF_PRIORITY_SOURCE,
) -> bool:
    _validate_priority(new_priority)
    if source not in (STAFF_PRIORITY_SOURCE, AI_ACCEPTED_SOURCE):
        raise ValueError("Unknown manual priority source.")
    with _database(db_path) as conn:
        row = conn.execute("SELECT priority FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if row is None:
            raise ValueError("Ticket not found.")
        current = row["priority"]
        if expected_current_priority is not None and current != expected_current_priority:
            raise ValueError("Priority changed elsewhere. Reload the ticket and try again.")
        cur = conn.execute("""
            UPDATE complaints SET priority = ?, priority_source = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND priority IS ?
        """, (new_priority, source, complaint_id, current))
        if cur.rowcount != 1:
            raise ValueError("This ticket changed while saving. Reload and try again.")
    return True


def _apply_rule_suggestion(conn, row):
    result = triage_complaint(row["title"], row["description"])
    # Evaluate provenance in the UPDATE itself: a concurrent staff override must
    # survive even if this function was given an older snapshot of the ticket.
    conn.execute("""
        UPDATE complaints SET category = ?, rule_suggested_priority = ?,
        triage_reason = ?, triage_source = ?,
        priority = CASE WHEN COALESCE(priority_source, '') IN ('', 'Not set', ?)
            THEN ? ELSE priority END,
        priority_source = CASE WHEN COALESCE(priority_source, '') IN ('', 'Not set', ?)
            THEN ? ELSE priority_source END,
        updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (
        result.category, result.priority, result.reason, result.source,
        RULE_BASED_SOURCE, result.priority, RULE_BASED_SOURCE, RULE_BASED_SOURCE, row["id"],
    ))


def refresh_rule_suggestion(complaint_id: int, db_path=DEFAULT_DB_PATH) -> bool:
    """Explicitly refresh rules; never overwrite a student/staff priority."""
    with _database(db_path) as conn:
        row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if row is None:
            raise ValueError("Ticket not found.")
        _apply_rule_suggestion(conn, row)
    return True


def triage_untriaged_complaints(db_path=DEFAULT_DB_PATH) -> int:
    with _database(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM complaints
            WHERE triage_source IS NULL OR triage_source = 'Not triaged' OR category IS NULL
        """).fetchall()
        for row in rows:
            _apply_rule_suggestion(conn, row)
        return len(rows)


def save_ai_review(complaint_id: int, review: dict, db_path=DEFAULT_DB_PATH) -> None:
    """Cache advisory output only. Current priority/status are never changed."""
    from ai_assistant import validate_review
    clean = validate_review(review)
    clean["source"] = review.get("source", "Local AI — Gemma 4 E4B")
    clean["model"] = review.get("model", "gemma4:e4b")
    with _database(db_path) as conn:
        cur = conn.execute("""
            UPDATE complaints SET ai_review_json = ?, ai_reviewed_at = ? WHERE id = ?
        """, (
            json.dumps(clean, ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(timespec="seconds"), complaint_id,
        ))
        if cur.rowcount != 1:
            raise ValueError("Ticket not found.")


def get_saved_ai_review(ticket) -> Optional[dict]:
    if not ticket or not ticket["ai_review_json"]:
        return None
    try:
        from ai_assistant import validate_review
        raw = json.loads(ticket["ai_review_json"])
        clean = validate_review(raw)
        clean["source"] = raw.get("source", "Local AI — Gemma 4 E4B")
        clean["model"] = raw.get("model", "gemma4:e4b")
        return clean
    except (ValueError, TypeError, KeyError):
        return None
