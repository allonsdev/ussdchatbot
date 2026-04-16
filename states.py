"""
states.py
---------
Contains the business logic for every USSD state.

Response helpers
~~~~~~~~~~~~~~~~
    con(text)   → "CON <text>"   (keep session open, show menu)
    end(text)   → "END <text>"   (close session)

State machine
~~~~~~~~~~~~~
Every public function receives (session: dict, user_input: str) and returns
a USSD response string.  The router in router.py dispatches to these
functions based on session["state"].

Auth flow
~~~~~~~~~
    START → ENTER_PHONE → AUTH_CHOOSE → AUTH_PIN  ─┐
                                      └→ AUTH_OTP  ─┤
                                         AUTH_OTP_MENU (send menu via OTP) ─┤
                                                    └→ LANGUAGE → MAIN_MENU → …
"""
import sys
import ssl
import sqlite3
import random
import datetime
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import re
import ssl
import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import datetime
import json
import random
import socket
import ssl
import subprocess
import urllib.parse
import shlex
import os
# --------------------------
from flask import Flask, request
import sqlite3
from datetime import datetime
import uuid
import random
import random
import uuid
from datetime import datetime, timedelta

from db import get_db
from session import update_session, set_temp, clear_temp, get_session
from texts import t, LANGUAGES
from utils import (
    is_valid_phone, is_valid_account, is_valid_amount, is_valid_pin, is_valid_otp,
    safe_float, fmt_amount,
)


USERNAME = "sandbox"  # Sandbox username
API_KEY = "atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a"  # Replace with your sandbox key
SMS_URL = "https://api.sandbox.africastalking.com/version1/messaging"

# Debug info
print("PYTHON EXECUTABLE:", sys.executable)
print("OPENSSL VERSION:", ssl.OPENSSL_VERSION)

class TLS12Adapter(HTTPAdapter):
    """
    Forces TLS 1.2 for all HTTPS requests.
    Prevents SSL handshake errors on older environments.
    """
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context(cafile=certifi.where())
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = ctx
        self.poolmanager = PoolManager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        ctx = ssl.create_default_context(cafile=certifi.where())
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = ctx
        return super().proxy_manager_for(*args, **kwargs)


session_http = requests.Session()
session_http.trust_env = False
session_http.mount("https://", TLS12Adapter())


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def verify_tls13(host="api.sandbox.africastalking.com", port=443):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs()

    try:
        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print(f"✅ Connected to {host}:{port}")
                print(f"TLS version in use: {ssock.version()}")
                print(f"Cipher in use: {ssock.cipher()}")
                return True
    except ssl.SSLError as e:
        print(f"❌ SSL error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    

def send_booking_sms(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox"):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return
    phonev2 = "+27707317823"
    # URL-encode form data
    data = {
        "username": username,
        "to": phonev2,
        "message": message
    }
    encoded_data = urllib.parse.urlencode(data)

    # Build curl command
    cmd = f'curl -s -X POST https://api.sandbox.africastalking.com/version1/messaging -d "{encoded_data}" -H "apiKey: {api_key}"'

    # Run the command
    result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)

    print("\n📩 SMS API Response:")
    print(result.stdout.strip())
    if result.stderr.strip():
        print("Errors:", result.stderr.strip())



def con(text: str) -> str:
    return f"CON {text}"


def end(text: str) -> str:
    return f"END {text}"


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def _generate_and_store_otp(phone: str) -> str:
    """Generate a 4-digit OTP, persist it, and return the code."""
    code = str(random.randint(1000, 9999))
    conn = get_db()
    conn.execute(
        "INSERT INTO otp_codes (phone, code, status) VALUES (?, ?, 'PENDING')",
        (phone, code),
    )
    conn.commit()
    conn.close()
    
    



    send_booking_sms(phone, "Your OTP is " + code)
    # ── REPLACE this stub with your real SMS gateway call ──────────────────
    print(f"[OTP] {phone} → {code}")
    # send_sms(phone, f"Your OTP is {code}. Valid for 5 minutes.")
    # ───────────────────────────────────────────────────────────────────────
    return code


def _verify_otp(phone: str, user_code: str) -> bool:
    """Validate latest PENDING OTP for phone within 5-minute window."""
    
    
    print(phone)
    
    conn = get_db()
    conn.set_trace_callback(print)  # this will print all SQL queries

    row = conn.execute(
        """
        SELECT id, code, created_at
        FROM otp_codes
        WHERE phone = ? AND status = 'PENDING'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (phone,),
    ).fetchone()
    
    if not row:
        conn.close()
        return False

    otp_id, code, created_at_str = row["id"], row["code"], row["created_at"]
    
    print(row)
    if code == user_code:
        conn.execute(
            "UPDATE otp_codes SET status='USED' WHERE id=?", (otp_id,)
        )
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


# ---------------------------------------------------------------------------
# Wallet helpers
# ---------------------------------------------------------------------------

def _get_balance(phone: str) -> float:
    conn = get_db()
    row = conn.execute(
        "SELECT balance FROM wallets WHERE phone=?", (phone,)
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT OR IGNORE INTO wallets (phone, balance) VALUES (?, 100)",
            (phone,),
        )
        conn.commit()
        conn.close()
        return 100.0
    conn.close()
    return float(row["balance"])


def _transfer(sender: str, receiver: str, amount: float) -> bool:
    if _get_balance(sender) < amount:
        return False
    conn = get_db()
    conn.execute(
        "UPDATE wallets SET balance=balance-?, updated_at=CURRENT_TIMESTAMP WHERE phone=?",
        (amount, sender),
    )
    conn.execute(
        "INSERT OR IGNORE INTO wallets (phone, balance) VALUES (?, 0)", (receiver,)
    )
    conn.execute(
        "UPDATE wallets SET balance=balance+?, updated_at=CURRENT_TIMESTAMP WHERE phone=?",
        (amount, receiver),
    )
    conn.execute(
        "INSERT INTO transactions (sender, receiver, amount) VALUES (?, ?, ?)",
        (sender, receiver, amount),
    )
    conn.commit()
    conn.close()
    return True


def _mini_statement(phone: str, limit: int = 5) -> list:
    conn = get_db()
    rows = conn.execute(
        """
        SELECT sender, receiver, amount, created_at
        FROM   transactions
        WHERE  sender=? OR receiver=?
        ORDER  BY created_at DESC
        LIMIT  ?
        """,
        (phone, phone, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ===========================================================================
# STATE HANDLERS
# Each function signature: (session: dict, user_input: str) → str
# ===========================================================================

# ---------------------------------------------------------------------------
# Step 1 – Identity type selection  (phone number  OR  account number)
# ---------------------------------------------------------------------------

def state_start(session: dict, user_input: str) -> str:
    """
    Entry point: ask the subscriber how they want to identify themselves.
        1 → Phone number
        2 → Account number
    """
    sid = session["session_id"]
    update_session(sid, state="ENTER_ID_TYPE")
    return con(t("select_id_type", "en"))


def state_enter_id_type(session: dict, user_input: str) -> str:
    """
    Route to the appropriate input prompt based on the subscriber's choice.
    """
    sid = session["session_id"]

    if user_input == "1":
        update_session(sid, state="ENTER_PHONE")
        return con(t("enter_phone", "en"))

    if user_input == "2":
        update_session(sid, state="ENTER_ACCOUNT")
        return con(t("enter_account", "en"))

    # Invalid choice – re-show the menu
    return con(t("select_id_type", "en"))


def state_enter_phone(session: dict, user_input: str) -> str:
    """
    Validate a phone number, store it on the session, then go to auth.
    """
    sid = session["session_id"]

    if not user_input or not is_valid_phone(user_input.strip()):
        return con(t("invalid_input", "en") + "\n" + t("enter_phone", "en"))

    update_session(sid, state="AUTH_CHOOSE", phone=user_input.strip())
    return con(t("select_auth", "en"))


def state_enter_account(session: dict, user_input: str) -> str:
    """
    Validate an account number, resolve it to a phone (or store as-is),
    then go to auth.

    Account numbers are expected to be 6-20 alphanumeric characters.
    Replace the lookup logic below with a real DB query if accounts are
    stored separately from phone numbers.
    """
    sid = session["session_id"]
    value = (user_input or "").strip()

    if not is_valid_account(value):
        return con(t("invalid_input", "en") + "\n" + t("enter_account", "en"))

    # ── Optional: resolve account number → phone via your accounts table ──
    # conn = get_db()
    # row = conn.execute(
    #     "SELECT phone FROM accounts WHERE account_number=?", (value,)
    # ).fetchone()
    # conn.close()
    # if not row:
    #     return con(t("account_not_found", "en") + "\n" + t("enter_account", "en"))
    # phone = row["phone"]
    # ──────────────────────────────────────────────────────────────────────

    # Until the accounts table is wired up, treat the account number as the
    # session identity directly (same as a phone number).
    phone = value

    update_session(sid, state="AUTH_CHOOSE", phone=phone)
    return con(t("select_auth", "en"))


# ---------------------------------------------------------------------------
# Step 2 – Auth-method selection
# ---------------------------------------------------------------------------

def state_auth_choose(session: dict, user_input: str) -> str:
    """
    User picks:
        1 → PIN
        2 → OTP  (sub-menu: enter OTP  OR  send menu via OTP)
    """
    sid = session["session_id"]

    if user_input == "1":
        update_session(sid, state="AUTH_PIN")
        return con(t("enter_pin", "en"))

    if user_input == "2":
        # Offer the OTP sub-menu before sending anything
        update_session(sid, state="AUTH_OTP_CHOOSE")
        return con(t("select_otp_action", "en"))

    return con(t("select_auth", "en"))

def send_booking(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox"):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return
    phonev2 = "+27707317823"
    
    messagev2 ="Hello! I need your assistance. Could you please call me back? at this number" + str(phone)+ " Thank you."
    data = {
        "username": username,
        "to": phonev2,
        "message": messagev2
    }
    encoded_data = urllib.parse.urlencode(data)

    # Build curl command
    cmd = f'curl -s -X POST https://api.sandbox.africastalking.com/version1/messaging -d "{encoded_data}" -H "apiKey: {api_key}"'

    # Run the command
    result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)

    print("\n📩 SMS API Response:")
    print(result.stdout.strip())
    if result.stderr.strip():
        print("Errors:", result.stderr.strip())

# ---------------------------------------------------------------------------
# Step 3a – PIN authentication
# ---------------------------------------------------------------------------

def state_auth_pin(session: dict, user_input: str) -> str:
    """Validate the PIN the subscriber entered."""
    sid = session["session_id"]
    phone = session["phone"]

    conn = get_db()
    row = conn.execute(
        "SELECT pin FROM users WHERE phone=?", (phone,)
    ).fetchone()
    conn.close()

    if row and row["pin"] == user_input:
        update_session(sid, state="LANGUAGE", authenticated=1)
        return con(t("choose_language", "en"))

    return con(t("invalid_pin", "en"))


# ---------------------------------------------------------------------------
# Step 3b – OTP sub-menu (enter OTP | send menu via OTP)
# ---------------------------------------------------------------------------

def state_auth_otp_choose(session: dict, user_input: str) -> str:
    """
    1 → Enter OTP manually (OTP already sent, or subscriber has one)
    2 → Send main-menu shortcut via SMS/OTP so they can act without re-dialling
    """
    sid = session["session_id"]
    phone = session["phone"]

    if user_input == "1":
        # Send OTP now and wait for the subscriber to type it
        _generate_and_store_otp(phone)
        update_session(sid, state="AUTH_OTP")
        return con(t("otp_sent", "en") + "\n" + t("enter_otp", "en"))

    if user_input == "2":
        # Generate OTP, send the menu via SMS, then end the USSD session
        otp = _generate_and_store_otp(phone)
        send_booking(phone, otp)          # see stub below
        update_session(sid, state="START")      # reset for next dial-in
        return end(t("menu_sent_via_sms", "en"))

    return con(t("select_otp_action", "en"))


def _send_menu_via_sms(phone: str, otp: str) -> None:
    """
    Stub: replace with your real SMS-gateway call.
    Sends the subscriber a message containing their OTP and a deep-link /
    summary of the main menu so they can act without re-dialling.
    """
    menu_summary = (
        f"Your OTP: {otp}\n"
        "Reply with:\n"
        "1-Wallet 2-Support 3-FAQ 4-Account"
    )
    print(f"[SMS MENU] {phone} → {menu_summary}")
    # send_sms(phone, menu_summary)


# ---------------------------------------------------------------------------
# Step 3c – OTP entry and verification
# ---------------------------------------------------------------------------

def state_auth_otp(session: dict, user_input: str) -> str:
    """Validate the OTP the subscriber typed."""
    sid = session["session_id"]
    
    print(session["phone"])

    if _verify_otp(session["phone"], user_input):
        update_session(sid, state="LANGUAGE", authenticated=1)
        return con(t("choose_language", "en"))

    return con(t("invalid_otp", "en"))


# ---------------------------------------------------------------------------
# Step 4 – Language selection
# ---------------------------------------------------------------------------

def state_language(session: dict, user_input: str) -> str:
    """User selects language, then go to main menu."""
    sid = session["session_id"]
    lang = LANGUAGES.get(user_input, "en")
    update_session(sid, state="MAIN_MENU", lang=lang)
    return con(t("main_menu", lang))


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def state_main_menu(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    routes = {
        "1": "WALLET_MENU",
        "2": "SUPPORT_MENU",
        "3": "FAQ_LIST",
        "4": "ACCOUNT_MENU",
    }
    next_state = routes.get(user_input)
    if next_state:
        update_session(sid, state=next_state)
        return _render_state(get_session(sid), "")
    return con(t("main_menu", lang))


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

def state_wallet_menu(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]
    routes = {"1": "WALLET_BALANCE", "2": "WALLET_SEND_RECIPIENT", "3": "WALLET_STATEMENT"}
    next_state = routes.get(user_input)
    if next_state:
        update_session(sid, state=next_state)
        return _render_state(get_session(sid), "")
    return con(t("wallet_menu", lang))


def state_wallet_balance(session: dict, user_input: str) -> str:
    lang = session["lang"]
    bal = _get_balance(session["phone"])
    update_session(session["session_id"], state="MAIN_MENU")
    return end(f"{t('balance', lang)} {fmt_amount(bal)}")


def state_wallet_send_recipient(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    if not user_input:
        return con(t("enter_recipient", lang))

    if not is_valid_phone(user_input):
        return con(t("invalid_input", lang) + "\n" + t("enter_recipient", lang))

    set_temp(sid, recipient=user_input)
    update_session(sid, state="WALLET_SEND_AMOUNT")
    return con(t("enter_amount", lang))


def state_wallet_send_amount(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    if not is_valid_amount(user_input):
        return con(t("invalid_input", lang) + "\n" + t("enter_amount", lang))

    set_temp(sid, amount=user_input)
    temp = get_session(sid)["temp_data"]
    recipient = temp.get("recipient", "?")
    amount = temp.get("amount", "?")

    update_session(sid, state="WALLET_SEND_CONFIRM")
    return con(t("confirm_send", lang, amount=amount, recipient=recipient))


def state_wallet_send_confirm(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]
    temp = session["temp_data"]
    recipient = temp.get("recipient")
    amount = safe_float(temp.get("amount"))

    clear_temp(sid)
    update_session(sid, state="MAIN_MENU")

    if user_input == "1":
        if _transfer(session["phone"], recipient, amount):
            return end(t("sent", lang, amount=fmt_amount(amount), recipient=recipient))
        return end(t("insufficient", lang))
    return end(t("cancelled", lang))


def state_wallet_statement(session: dict, user_input: str) -> str:
    lang = session["lang"]
    txns = _mini_statement(session["phone"])
    update_session(session["session_id"], state="MAIN_MENU")

    if not txns:
        return end(t("no_transactions", lang))

    lines = [t("mini_statement", lang, n=len(txns))]
    for tx in txns:
        direction = "Sent" if tx["sender"] == session["phone"] else "Recv"
        lines.append(f"{direction} {fmt_amount(tx['amount'])} – {tx['created_at'][:10]}")
    return end("\n".join(lines))


# ---------------------------------------------------------------------------
# Support
# ---------------------------------------------------------------------------

def state_support_menu(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]
    routes = {
        "1": "SUPPORT_CREATE_ISSUE",
        "2": "SUPPORT_TRACK_ENTER",
        "3": "SUPPORT_CALLBACK",
    }
    next_state = routes.get(user_input)
    if next_state:
        update_session(sid, state=next_state)
        return _render_state(get_session(sid), "")
    return con(t("support_menu", lang))


def state_support_create_issue(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    if not user_input:
        return con(t("enter_issue", lang))

    tid = str(uuid.uuid4())[:6].upper()
    conn = get_db()
    from datetime import datetime

    conn.execute(
        "INSERT INTO issues (ticket_id, phone, issue, status, created_at) VALUES (?, ?, ?, 'OPEN', ?)",
        (tid, session["phone"], user_input, datetime.now())
    )
    conn.commit()
    conn.close()

    update_session(sid, state="MAIN_MENU")
    return end(t("ticket_created", lang, tid=tid))


def state_support_track_enter(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    if not user_input:
        return con(t("enter_ticket_id", lang))

    conn = get_db()
    row = conn.execute(
        "SELECT status FROM issues WHERE ticket_id=?", (user_input.upper(),)
    ).fetchone()
    conn.close()

    update_session(sid, state="MAIN_MENU")
    if row:
        return end(t("ticket_status", lang, tid=user_input.upper(), status=row["status"]))
    return end(t("ticket_not_found", lang))


def state_support_callback(session: dict, user_input: str) -> str:
    lang = session["lang"]
    conn = get_db()
    conn.execute("INSERT INTO callbacks (phone) VALUES (?)", (session["phone"],))
    conn.commit()
    conn.close()
    
    send_booking((session["phone"]),(session["phone"]))
    update_session(session["session_id"], state="MAIN_MENU")
    return end(t("callback_requested", lang))


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

from texts import t, get_faqs
 
 
def state_faq_list(session: dict, user_input: str) -> str:
    """
    Show the FAQ list in the user's chosen language.
    On first entry user_input is empty; on second entry it holds their choice.
    """
    sid  = session["session_id"]
    lang = session["lang"]
    faqs = get_faqs(lang)           # ← fully localised, no DB
 
    # First visit: display the menu and wait for a selection
    if not user_input:
        lines = [t("faq_menu", lang)]
        for faq in faqs:
            lines.append(f"{faq['id']}. {faq['question']}")
        update_session(sid, state="FAQ_ANSWER")
        return con("\n".join(lines))
 
    # The user typed their answer on the same dial-through
    return _show_faq_answer(session, user_input, faqs)
 
 
def state_faq_answer(session: dict, user_input: str) -> str:
    """Called when the user replies to the FAQ list screen."""
    lang = session["lang"]
    faqs = get_faqs(lang)
    return _show_faq_answer(session, user_input, faqs)
 
 
def _show_faq_answer(session: dict, user_input: str, faqs: list) -> str:
    """Display the answer for the selected FAQ number, all in session lang."""
    sid  = session["session_id"]
    lang = session["lang"]
 
    try:
        faq_id = int(user_input)
    except (ValueError, TypeError):
        update_session(sid, state="MAIN_MENU")
        return end(t("invalid_input", lang))
 
    for faq in faqs:
        if faq["id"] == faq_id:
            update_session(sid, state="MAIN_MENU")
            return end(f"{faq['question']}\n{faq['answer']}")
 
    update_session(sid, state="MAIN_MENU")
    return end(t("faq_not_found", lang))
 

# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

def state_account_menu(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]
    routes = {
        "1": "ACCOUNT_CHANGE_PIN",
        "2": "ACCOUNT_REQUEST_OTP",
        "3": "ACCOUNT_VERIFY_OTP",
    }
    next_state = routes.get(user_input)
    if next_state:
        update_session(sid, state=next_state)
        return _render_state(get_session(sid), "")
    return con(t("account_menu", lang))


def state_account_change_pin(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    if not user_input:
        return con(t("enter_new_pin", lang))

    if not is_valid_pin(user_input):
        return con(t("invalid_input", lang) + "\n" + t("enter_new_pin", lang))

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO users (phone, pin) VALUES (?, ?)",
        (session["phone"], user_input),
    )
    conn.commit()
    conn.close()

    update_session(sid, state="MAIN_MENU")
    return end(t("pin_updated", lang))


def state_account_request_otp(session: dict, user_input: str) -> str:
    lang = session["lang"]
    _generate_and_store_otp(session["phone"])
    update_session(session["session_id"], state="MAIN_MENU")
    return end(t("otp_sent", lang))


def state_account_verify_otp(session: dict, user_input: str) -> str:
    sid = session["session_id"]
    lang = session["lang"]

    if not user_input:
        return con(t("enter_otp", lang))

    if _verify_otp(session["phone"], user_input):
        update_session(sid, state="MAIN_MENU")
        return end(t("otp_verified", lang))

    return con(t("invalid_otp", lang))


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def state_fallback(session: dict, user_input: str) -> str:
    lang = session.get("lang", "en")
    update_session(session["session_id"], state="MAIN_MENU")
    return con(t("main_menu", lang))


# ===========================================================================
# DISPATCH TABLE  ←  add new states here
# ===========================================================================

DISPATCH: dict = {
    # ── Auth flow ──────────────────────────────────────────────────────────
    "START":                    state_start,
    "ENTER_ID_TYPE":            state_enter_id_type,     # phone vs account menu
    "ENTER_PHONE":              state_enter_phone,       # phone number entry
    "ENTER_ACCOUNT":            state_enter_account,     # account number entry
    "AUTH_CHOOSE":              state_auth_choose,
    "AUTH_PIN":                 state_auth_pin,
    "AUTH_OTP_CHOOSE":          state_auth_otp_choose,   # OTP sub-menu
    "AUTH_OTP":                 state_auth_otp,
    # ── Post-auth ──────────────────────────────────────────────────────────
    "LANGUAGE":                 state_language,
    "MAIN_MENU":                state_main_menu,
    # ── Wallet ────────────────────────────────────────────────────────────
    "WALLET_MENU":              state_wallet_menu,
    "WALLET_BALANCE":           state_wallet_balance,
    "WALLET_SEND_RECIPIENT":    state_wallet_send_recipient,
    "WALLET_SEND_AMOUNT":       state_wallet_send_amount,
    "WALLET_SEND_CONFIRM":      state_wallet_send_confirm,
    "WALLET_STATEMENT":         state_wallet_statement,
    # ── Support ───────────────────────────────────────────────────────────
    "SUPPORT_MENU":             state_support_menu,
    "SUPPORT_CREATE_ISSUE":     state_support_create_issue,
    "SUPPORT_TRACK_ENTER":      state_support_track_enter,
    "SUPPORT_CALLBACK":         state_support_callback,
    # ── FAQ ───────────────────────────────────────────────────────────────
    "FAQ_LIST":                 state_faq_list,
    "FAQ_ANSWER":               state_faq_answer,
    # ── Account ───────────────────────────────────────────────────────────
    "ACCOUNT_MENU":             state_account_menu,
    "ACCOUNT_CHANGE_PIN":       state_account_change_pin,
    "ACCOUNT_REQUEST_OTP":      state_account_request_otp,
    "ACCOUNT_VERIFY_OTP":       state_account_verify_otp,
}


def _render_state(session: dict, user_input: str) -> str:
    """Dispatch to the right handler for the current session state."""
    state = session.get("state", "START")
    handler = DISPATCH.get(state, state_fallback)
    return handler(session, user_input)