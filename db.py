"""Database module for CampusFix AI.

Provides SQLite initialization and connection handling.
"""

from pathlib import Path
import sqlite3
from typing import Optional, Union

from triage import triage_complaint

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "campusfix.db"

MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 2000
MAX_BUILDING_LENGTH = 100
MAX_ROOM_LENGTH = 50


def get_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a connection to the SQLite database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Connection with Row row_factory enabled.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    """Safely initialize the SQLite database without overwriting existing data.

    Creates the complaints table if it does not already exist.

    Args:
        db_path: Path to the SQLite database file.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
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
            """
        )
        conn.commit()


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
) -> int:
    """Create a new complaint record in the database using parameterized SQL.

    If auto_triage is True and no category is provided, applies deterministic
    rule-based triage to determine category, priority, reason, and source.

    Args:
        title: Brief title summarizing the maintenance issue.
        description: Detailed explanation of the issue.
        building: Name or identifier of the campus building.
        room: Room or area identifier (e.g., A-101).
        category: Optional category override.
        priority: Optional priority override.
        triage_reason: Optional reason string.
        triage_source: Optional triage source identifier.
        auto_triage: Whether to auto-triage untriaged inputs via rule-based engine.
        db_path: Path to the SQLite database file.

    Returns:
        The integer ID of the created complaint record.

    Raises:
        ValueError: If any required field is empty, whitespace-only, or exceeds length limits.
        sqlite3.Error: If a database error occurs.
    """
    clean_title = (title or "").strip()
    clean_description = (description or "").strip()
    clean_building = (building or "").strip()
    clean_room = (room or "").strip()

    if not clean_title:
        raise ValueError("Title is required and cannot be empty or whitespace.")
    if not clean_description:
        raise ValueError("Description is required and cannot be empty or whitespace.")
    if not clean_building:
        raise ValueError("Building is required and cannot be empty or whitespace.")
    if not clean_room:
        raise ValueError("Room number is required and cannot be empty or whitespace.")

    if len(clean_title) > MAX_TITLE_LENGTH:
        raise ValueError(f"Title must not exceed {MAX_TITLE_LENGTH} characters.")
    if len(clean_description) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"Description must not exceed {MAX_DESCRIPTION_LENGTH} characters.")
    if len(clean_building) > MAX_BUILDING_LENGTH:
        raise ValueError(f"Building must not exceed {MAX_BUILDING_LENGTH} characters.")
    if len(clean_room) > MAX_ROOM_LENGTH:
        raise ValueError(f"Room number must not exceed {MAX_ROOM_LENGTH} characters.")

    if auto_triage and category is None:
        t_res = triage_complaint(clean_title, clean_description)
        category = t_res.category
        priority = t_res.priority
        triage_reason = t_res.reason
        triage_source = t_res.source
    elif triage_source is None:
        triage_source = "Not triaged"

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO complaints (
                title,
                description,
                building,
                room,
                status,
                category,
                priority,
                triage_reason,
                triage_source
            )
            VALUES (?, ?, ?, ?, 'Reported', ?, ?, ?, ?)
            """,
            (
                clean_title,
                clean_description,
                clean_building,
                clean_room,
                category,
                priority,
                triage_reason,
                triage_source,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def triage_untriaged_complaints(
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> int:
    """Find all untriaged complaints, apply rule-based triage, and persist suggestions.

    Does not alter ticket IDs or statuses.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        The number of tickets successfully triaged.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, description
            FROM complaints
            WHERE triage_source = 'Not triaged' OR category IS NULL
            """
        )
        rows = cursor.fetchall()
        count = 0
        for row in rows:
            res = triage_complaint(row["title"], row["description"])
            cursor.execute(
                """
                UPDATE complaints
                SET category = ?,
                    priority = ?,
                    triage_reason = ?,
                    triage_source = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (res.category, res.priority, res.reason, res.source, row["id"]),
            )
            count += 1
        conn.commit()
        return count



def get_complaint(
    complaint_id: int,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> Optional[sqlite3.Row]:
    """Retrieve a single complaint record by its primary key ID using parameterized SQL.

    Args:
        complaint_id: Primary key of the complaint to fetch.
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Row if found, otherwise None.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM complaints WHERE id = ?",
            (complaint_id,),
        )
        return cursor.fetchone()


def format_ticket_id(complaint_id: int) -> str:
    """Format an integer complaint primary key into a human-readable ticket ID.

    Examples:
        1 -> 'CF-000001'
        2 -> 'CF-000002'

    Args:
        complaint_id: Positive integer database ID.

    Returns:
        Formatted ticket ID string.

    Raises:
        ValueError: If complaint_id is not a positive integer.
    """
    if not isinstance(complaint_id, int) or complaint_id <= 0:
        raise ValueError(
            f"Complaint ID must be a positive integer, got {complaint_id!r}"
        )
    return f"CF-{complaint_id:06d}"


def parse_ticket_id(ticket_id: str) -> Optional[int]:
    """Parse a human-readable ticket ID into its integer primary key.

    Accepts format 'CF-000001' (case-insensitive, trims leading/trailing whitespace).

    Args:
        ticket_id: Ticket ID string to parse.

    Returns:
        The integer primary key if valid, or None if the format is invalid.
    """
    import re

    if not ticket_id or not isinstance(ticket_id, str):
        return None

    cleaned = ticket_id.strip()
    match = re.match(r"^CF-(\d+)$", cleaned, re.IGNORECASE)
    if not match:
        return None

    try:
        val = int(match.group(1))
        return val if val > 0 else None
    except ValueError:
        return None


def get_complaint_by_ticket_id(
    ticket_id: str,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> Optional[sqlite3.Row]:
    """Perform a read-only lookup of a complaint by its formatted ticket ID.

    Args:
        ticket_id: Ticket ID string (e.g. 'CF-000001').
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Row if found, or None if the ID is invalid or not found.
    """
    parsed_id = parse_ticket_id(ticket_id)
    if parsed_id is None:
        return None
    return get_complaint(parsed_id, db_path=db_path)


def get_complaint_counts(
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> dict:
    """Calculate complaint summary counts from SQLite.

    Definitions:
        - Total: all complaints in the database.
        - Pending: complaints with status 'Reported' or 'In Progress'.
        - Resolved: complaints with status 'Resolved'.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        dict containing 'total', 'pending', and 'resolved' integer counts.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN status IN ('Reported', 'In Progress') THEN 1 ELSE 0 END), 0) AS pending,
                COALESCE(SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END), 0) AS resolved
            FROM complaints
            """
        )
        row = cursor.fetchone()
        return {
            "total": int(row["total"]) if row and row["total"] is not None else 0,
            "pending": int(row["pending"]) if row and row["pending"] is not None else 0,
            "resolved": int(row["resolved"]) if row and row["resolved"] is not None else 0,
        }



def get_all_complaints(
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> list[sqlite3.Row]:
    """Retrieve all complaints from SQLite, ordered by newest first (ID descending).

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        List of sqlite3.Row objects representing all complaints.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                building,
                room,
                status,
                category,
                priority,
                triage_reason,
                triage_source,
                created_at,
                updated_at
            FROM complaints
            ORDER BY id DESC
            """
        )
        return cursor.fetchall()


ALLOWED_STATUS_TRANSITIONS = {
    "Reported": ["In Progress"],
    "In Progress": ["Resolved"],
    "Resolved": [],
}


def update_complaint_status(
    complaint_id: int,
    new_status: str,
    expected_current_status: Optional[str] = None,
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> bool:
    """Transition a complaint's status strictly according to the state machine.

    Enforces allowed transitions:
        Reported -> In Progress -> Resolved

    Rejects backward transitions, skipped transitions, and advances from Resolved.
    Updates the updated_at timestamp upon success.

    Args:
        complaint_id: Integer primary key of the complaint.
        new_status: Target status to transition to.
        expected_current_status: Optional expected status for optimistic concurrency check.
        db_path: Path to the SQLite database file.

    Returns:
        True if the update succeeded.

    Raises:
        ValueError: If complaint does not exist, status transition is invalid,
            or a stale update is detected.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM complaints WHERE id = ?",
            (complaint_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Complaint #{complaint_id} not found.")

        current_status = row["status"]

        if expected_current_status and current_status != expected_current_status:
            raise ValueError(
                f"Stale update detected: ticket is currently '{current_status}', "
                f"expected '{expected_current_status}'."
            )

        if current_status == "Resolved":
            raise ValueError("A resolved ticket cannot be advanced further.")

        allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition from '{current_status}' to '{new_status}'. "
                f"Allowed transition: {allowed[0] if allowed else 'None'}."
            )

        cursor.execute(
            """
            UPDATE complaints
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = ?
            """,
            (new_status, complaint_id, current_status),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                "Update failed: ticket was concurrently updated or does not exist."
            )

        conn.commit()
        return True




