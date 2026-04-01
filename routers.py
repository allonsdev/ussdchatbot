"""
router.py
---------
Receives the USSD input string, resolves the active session, and delegates
to the correct state handler in states.py.

This file intentionally contains NO business logic – it only:
  1. Parses raw USSD text
  2. Guards against unauthenticated access
  3. Calls _render_state() from states.py
"""

from session import get_session, update_session
from states import _render_state, state_start, con, end
from texts import t


def route(session_id: str, phone: str, raw_text: str) -> str:
    """
    Entry point called by app.py.

    Parameters
    ----------
    session_id : str
        The USSD session identifier from the gateway.
    phone : str
        The caller's phone number (from the gateway, used only as fallback).
    raw_text : str
        The full USSD string accumulated by the gateway (e.g. "1*2*0771234567").

    Returns
    -------
    str
        A "CON …" or "END …" string for the gateway.
    """

    session = get_session(session_id)

    if session is None:
        # This should not happen if app.py calls create_session first,
        # but guard defensively.
        return end(t("session_error"))

    # Split input into individual steps; the last element is the latest input
    steps = [s.strip() for s in raw_text.split("*")] if raw_text else []
    user_input = steps[-1] if steps else ""

    # ------------------------------------------------------------------
    # Guard: states after AUTH require authentication
    # ------------------------------------------------------------------
    protected_states = {
        "LANGUAGE", "MAIN_MENU",
        "WALLET_MENU", "WALLET_BALANCE", "WALLET_SEND_RECIPIENT",
        "WALLET_SEND_AMOUNT", "WALLET_SEND_CONFIRM", "WALLET_STATEMENT",
        "SUPPORT_MENU", "SUPPORT_CREATE_ISSUE", "SUPPORT_TRACK_ENTER",
        "SUPPORT_CALLBACK",
        "FAQ_LIST", "FAQ_ANSWER",
        "ACCOUNT_MENU", "ACCOUNT_CHANGE_PIN",
        "ACCOUNT_REQUEST_OTP", "ACCOUNT_VERIFY_OTP",
    }

    current_state = session.get("state", "START")
    is_authenticated = bool(session.get("authenticated"))

    if current_state in protected_states and not is_authenticated:
        # Force back to start
        update_session(session_id, state="START")
        session = get_session(session_id)
        return state_start(session, "")

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    return _render_state(session, user_input)