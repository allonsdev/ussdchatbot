"""
session.py
----------
USSD session management backed by SQLite.

Each session stores:
    state     – current menu state (string like "MAIN_MENU", "WALLET_SEND_RECIPIENT")
    lang      – language code ("en", "nd", "sn")
    temp_data – JSON blob for multi-step flow data (recipient, amount, etc.)
    authenticated – 0/1
    phone     – normalised phone number
"""

import json
from db import get_db


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_session(session_id: str, phone: str) -> dict:
    """
    Insert a new session row.  If one already exists for *session_id* it is
    returned as-is (idempotent).
    """
    conn = get_db()
    conn.execute(
        """
        INSERT OR IGNORE INTO sessions
            (session_id, phone, state, lang, temp_data, authenticated)
        VALUES (?, ?, 'START', 'en', '{}', 0)
        """,
        (session_id, phone),
    )
    conn.commit()
    conn.close()
    return get_session(session_id)


def get_session(session_id: str) -> dict | None:
    """Return session as a plain dict, or None if not found."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id=?", (session_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    data = dict(row)
    # Deserialise JSON blob safely
    try:
        data["temp_data"] = json.loads(data.get("temp_data") or "{}")
    except (json.JSONDecodeError, TypeError):
        data["temp_data"] = {}
    return data


def update_session(session_id: str, **kwargs) -> None:
    """
    Update one or more session fields by keyword argument.

    Supported keys: state, lang, authenticated, temp_data.
    *temp_data* should be passed as a dict; it will be JSON-serialised.
    """
    if not kwargs:
        return

    # Special handling: serialise temp_data dict → JSON string
    if "temp_data" in kwargs and isinstance(kwargs["temp_data"], dict):
        kwargs["temp_data"] = json.dumps(kwargs["temp_data"])

    set_clause = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [session_id]

    conn = get_db()
    conn.execute(
        f"UPDATE sessions SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE session_id=?",
        values,
    )
    conn.commit()
    conn.close()


def set_temp(session_id: str, **kwargs) -> None:
    """
    Merge key-value pairs into temp_data without overwriting other keys.

    Example:
        set_temp(sid, recipient="0771234567")
        set_temp(sid, amount=5.0)
    """
    session = get_session(session_id)
    if session is None:
        return
    temp = session["temp_data"]
    temp.update(kwargs)
    update_session(session_id, temp_data=temp)


def clear_temp(session_id: str) -> None:
    """Wipe all temporary flow data from the session."""
    update_session(session_id, temp_data={})


def delete_session(session_id: str) -> None:
    """Hard-delete a session row (called on END or timeout cleanup)."""
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()