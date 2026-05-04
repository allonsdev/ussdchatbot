import sys
import ssl
import sqlite3
import random
import datetime
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import re
import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import json
import socket
import subprocess
import urllib.parse
import shlex
import os
import uuid

from db import init_db, migrate_db, get_db
from session import create_session, get_session
from routers import route

# ================================================================
# FLASK INITIALIZATION
# ================================================================

app = Flask(__name__)
app.secret_key = "my_fixed_secret_key_1234"  # Replace in production with env variable

print(app.secret_key)

# ================================================================
# AFRICAS TALKING SANDBOX CONFIG
# ================================================================

USERNAME = "sandbox"
API_KEY  = "atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a"
SMS_URL  = "https://api.sandbox.africastalking.com/version1/messaging"

print("PYTHON EXECUTABLE:", sys.executable)
print("OPENSSL VERSION:", ssl.OPENSSL_VERSION)

# ================================================================
# DATABASE CONFIG
# ================================================================

DB = "support.db"


def get_connection():
    """Returns a connection with Row factory so columns are accessible by name."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """Raw connection — used by legacy helpers; row_factory NOT set here."""
    return sqlite3.connect(DB)


# ================================================================
# TLS ADAPTER
# ================================================================

class TLS12Adapter(HTTPAdapter):
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

# ================================================================
# TLS VERIFICATION
# ================================================================

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


# ================================================================
# UNIFIED SMS SENDER
# ================================================================

OPS_NUMBER = "+263779767541"


def _send_to_ops(customer_phone: str, message: str,
                 api_key=API_KEY, username=USERNAME):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return

    full_message = f"[{customer_phone}] {message}"
    data = {
        "username": username,
        "to":       OPS_NUMBER,
        "message":  full_message,
    }
    encoded_data = urllib.parse.urlencode(data)
    cmd = (
        f'curl -s -X POST {SMS_URL} '
        f'-d "{encoded_data}" '
        f'-H "apiKey: {api_key}"'
    )
    result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    print("\n📩 SMS API Response:")
    print(result.stdout.strip())
    if result.stderr.strip():
        print("Errors:", result.stderr.strip())


def send_sms(customer_phone: str, message: str,
             api_key=API_KEY, username=USERNAME):
    _send_to_ops(customer_phone, message, api_key, username)


def send_callback_request(customer_phone: str, agent_message: str = None,
                           api_key=API_KEY, username=USERNAME):
    base = (
        "Hello! I need your assistance. "
        "Could you please call me back? at this number "
        + str(customer_phone)
        + " Thank you."
    )
    if agent_message and agent_message.strip():
        full = f"{base} | Agent note: {agent_message.strip()}"
    else:
        full = base
    _send_to_ops(customer_phone, full, api_key, username)


def send_booking(phone, message=None, api_key=API_KEY, username=USERNAME):
    send_callback_request(phone, agent_message=message,
                           api_key=api_key, username=username)


# ================================================================
# PHONE NORMALISATION
# ================================================================

def sanitize_number(phone):
    if not phone:
        return phone
    phone = phone.strip()
    if phone.startswith("0"):
        return "+27" + phone[1:]
    if not phone.startswith("+27"):
        return "+27" + phone.lstrip("0")
    return phone


# ================================================================
# AUTH VALIDATION
# ================================================================

def validate_agent(agent_id, password):
    if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', password):
        return "Password must be at least 6 characters and include letters and numbers."

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password FROM agents WHERE agent_id=?", (agent_id,))
    row = c.fetchone()
    conn.close()

    return True if row and row[0] == password else "Invalid credentials"


# ================================================================
# USSD SESSION HELPERS
# ================================================================

def save_ussd_session(session_id, phone, step, data):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO ussd_sessions (session_id, phone, step, data, updated)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (session_id, phone, step, json.dumps(data)))
    conn.commit()
    conn.close()


def get_ussd_session(session_id):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("""
        SELECT phone, step, data FROM ussd_sessions WHERE session_id=?
    """, (session_id,)).fetchone()
    conn.close()
    if row:
        return {
            "phone": row[0],
            "step":  row[1],
            "data":  json.loads(row[2]) if row[2] else {}
        }
    return None


# ================================================================
# KPI SNAPSHOT
# ================================================================

def snapshot_kpi():
    conn = get_db()
    c = conn.cursor()

    total    = c.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    resolved = c.execute("SELECT COUNT(*) FROM issues WHERE status='resolved'").fetchone()[0]
    pending  = c.execute("SELECT COUNT(*) FROM issues WHERE status='pending'").fetchone()[0]
    calls    = c.execute("SELECT COUNT(*) FROM issues WHERE escalation_type='call'").fetchone()[0]

    avg_sla = c.execute("""
        SELECT AVG(JULIANDAY(closed_at) - JULIANDAY(created_at))
        FROM issues WHERE status='resolved'
    """).fetchone()[0] or 0

    churn_rate = random.uniform(0, 1)

    c.execute("""
        INSERT INTO kpi_snapshots (total, resolved, pending, calls, avg_sla, churn_rate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (total, resolved, pending, calls, avg_sla, churn_rate))

    conn.commit()
    conn.close()


# ================================================================
# SLA
# ================================================================

def calculate_sla(hours=48):
    return datetime.datetime.now() + datetime.timedelta(hours=hours)


# ================================================================
# ISSUE LOGGING
# ================================================================

def log_issue(session_id, phone_number, issue_text, escalation_type):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT agent_id FROM agents")
    agents = cursor.fetchall()
    assigned_agent = random.choice(agents)["agent_id"] if agents else None

    created_at = datetime.datetime.utcnow()
    sla_due    = created_at + datetime.timedelta(hours=24)

    cursor.execute("""
        INSERT INTO issues (
            phone, issue, escalation_type, status, created_at,
            agent_id, resolution_notes, closed_at, priority,
            category, sla_due, sla_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        phone_number, issue_text, escalation_type, "Open",
        created_at, assigned_agent, None, None,
        "Medium", "General", sla_due, "Within SLA"
    ))

    conn.commit()
    conn.close()


# ================================================================
# OTP
# ================================================================

def generate_otp(phone):
    code = str(random.randint(1000, 9999))
    conn = get_db()
    conn.execute(
        "INSERT INTO otp_codes (phone, code, status, created_at) "
        "VALUES (?, ?, 'PENDING', CURRENT_TIMESTAMP)",
        (phone, code)
    )
    conn.commit()
    conn.close()
    send_sms(phone, f"Your OTP is {code}. Valid for 5 minutes.")
    return code


def verify_otp(phone, user_code):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("""
        SELECT id, code, created_at
        FROM otp_codes
        WHERE phone=? AND status='PENDING'
        ORDER BY created_at DESC LIMIT 1
    """, (phone,)).fetchone()

    if not row:
        return False

    otp_id, code, created_at = row
    created_time = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")

    if datetime.datetime.now() - created_time > datetime.timedelta(minutes=5):
        return False

    if code == user_code:
        c.execute("UPDATE otp_codes SET status='USED' WHERE id=?", (otp_id,))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


# ================================================================
# WALLET HELPERS (kept for DB compatibility)
# ================================================================

def get_wallet(phone):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM wallets WHERE phone=?", (phone,))
    r = c.fetchone()
    if not r:
        c.execute("INSERT INTO wallets VALUES (?, ?)", (phone, 100))
        conn.commit()
        conn.close()
        return 100
    conn.close()
    return r[0]


def transfer_money(sender, receiver, amount):
    if get_wallet(sender) < amount:
        return False
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE wallets SET balance = balance - ? WHERE phone=?", (amount, sender))
    c.execute("INSERT OR IGNORE INTO wallets VALUES (?, 0)", (receiver,))
    c.execute("UPDATE wallets SET balance = balance + ? WHERE phone=?", (amount, receiver))
    conn.commit()
    conn.close()
    return True


# ================================================================
# MULTILINGUAL HELPERS
# ================================================================

LANGUAGES = {"1": "en", "2": "nd", "3": "sn"}

TEXT = {
    "welcome":        {"en": "Welcome",            "nd": "Siyakwamukela",        "sn": "Tinokugamuchirai"},
    "invalid":        {"en": "Invalid input",       "nd": "Okungavumelekile",     "sn": "Zvisiri izvo"},
    "invalid_pin":    {"en": "Invalid PIN",         "nd": "I-PIN ayilungile",     "sn": "PIN haina kunaka"},
    "invalid_choice": {"en": "Invalid choice",      "nd": "Ukhetho alulungile",   "sn": "Sarudzo haina kunaka"},
    "session_error":  {"en": "Session error",       "nd": "Iphutha leseshini",    "sn": "Session error"},
    "enter_phone":    {"en": "Enter phone number:", "nd": "Faka inombolo yocingo:","sn": "Isa nhamba yefoni:"},
    "select_option":  {
        "en": "Select option:\n1. Enter PIN\n2. Use OTP",
        "nd": "Khetha inketho:\n1. Faka i-PIN\n2. Sebenzisa OTP",
        "sn": "Sarudza:\n1. Isa PIN\n2. Shandisa OTP"
    },
    "enter_pin":      {"en": "Enter your PIN",      "nd": "Faka i-PIN yakho",     "sn": "Isa PIN yako"},
    "enter_otp":      {"en": "Enter OTP",           "nd": "Faka i-OTP",           "sn": "Isa OTP"},
    "main_menu": {
        "en": "1. Support\n2. FAQ\n3. Account",
        "nd": "1. Usizo\n2. FAQ\n3. I-Akhawunti",
        "sn": "1. Rubatsiro\n2. FAQ\n3. Account"
    },
    "support": {
        "en": "1. Create Ticket\n2. Track Ticket\n3. Callback",
        "nd": "1. Dala Ithikithi\n2. Landelela\n3. Call back",
        "sn": "1. Gadzira Ticket\n2. Tarisa\n3. Callback"
    },
    "ticket_created": {"en": "Ticket created",      "nd": "Ithikithi lidaliwe",   "sn": "Ticket yagadzirwa"},
    "enter_issue":    {"en": "Describe issue",      "nd": "Chaza inkinga",        "sn": "Tsanangura dambudziko"},
    "enter_ticket":   {"en": "Enter ticket ID",     "nd": "Faka i-ID",            "sn": "Isa ticket ID"},
    "callback":       {"en": "Callback requested",  "nd": "I-call back iceliwe",  "sn": "Callback yakumbirwa"},
    "otp_sent":       {"en": "OTP sent",            "nd": "OTP ithunyelwe",       "sn": "OTP yatumirwa"},
    "otp_invalid":    {"en": "Invalid OTP",         "nd": "OTP ayilungile",       "sn": "OTP haina kunaka"},
    "pin_updated":    {"en": "PIN updated",         "nd": "PIN iguquliwe",        "sn": "PIN yashandurwa"},
}


def t(key, lang="en"):
    return TEXT.get(key, {}).get(lang, TEXT.get(key, {}).get("en", key))


def language_menu():
    return "CON Select Language:\n1. English\n2. Ndebele\n3. Shona"


def main_menu(lang):
    return f"CON {t('welcome', lang)}\n{t('main_menu', lang)}"


def support_menu(lang):
    return f"CON {t('support', lang)}"


# ================================================================
# USSD AUDIT LOG
# ================================================================

def _log_ussd(session_id, phone, service_code, network_code, user_input, state, response):
    try:
        conn = get_db()
        conn.execute(
            """
            INSERT INTO ussd_logs
                (session_id, phone, service_code, network_code, input, state, response, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
            (session_id, phone, service_code, network_code, user_input, state, response),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        app.logger.warning("[ussd_log] failed: %s", exc)


# ================================================================
# FLASK ROUTES
# ================================================================

@app.route('/test')
def test():
    session['foo'] = 'bar'
    return f"Session works! foo={session.get('foo')}"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        agent_id   = request.form['agent_id']
        password   = request.form['password']
        validation = validate_agent(agent_id, password)
        if validation is True:
            session['agent_id'] = agent_id
            return redirect('/')
        return validation
    return render_template("login.html")


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/login')


@app.route('/')
def dashboard():
    if 'agent_id' not in session:
        return redirect('/login')

    # ── Use get_connection() so rows are accessible by column name ──────────
    conn = get_connection()
    c    = conn.cursor()

    status          = request.args.get("status")
    escalation_type = request.args.get("type")

    query  = "SELECT * FROM issues WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if escalation_type:
        query += " AND escalation_type=?"
        params.append(escalation_type)

    c.execute(query, params)
    # Convert to plain dicts so Jinja can use issue.id, issue.status, etc.
    issues = [dict(row) for row in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM users");                               users_count          = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM agents");                              agents_count         = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tasks WHERE status!='Done'");         open_tasks_count     = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM notifications WHERE status='unread'"); unread_notifications = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM otp_codes WHERE status='used'");      otp_used_count       = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sessions");                           sessions_count       = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM faqs");                               faqs_count           = c.fetchone()[0]

    c.execute("SELECT agent_id, title, status, due_date FROM tasks ORDER BY due_date ASC LIMIT 20")
    tasks = c.fetchall()

    c.execute("SELECT phone, message, status, created_at FROM notifications ORDER BY created_at DESC LIMIT 20")
    notifications = c.fetchall()

    c.execute("SELECT snapshot_date, resolved, pending, avg_sla FROM kpi_snapshots ORDER BY snapshot_date ASC LIMIT 30")
    snapshot_raw      = c.fetchall()
    snapshot_labels   = [r[0] for r in snapshot_raw]
    snapshot_resolved = [r[1] for r in snapshot_raw]
    snapshot_pending  = [r[2] for r in snapshot_raw]
    snapshot_avg_sla  = [r[3] for r in snapshot_raw]

    c.execute("SELECT status, COUNT(*) FROM otp_codes GROUP BY status")
    otp_raw    = dict(c.fetchall())
    otp_labels = list(otp_raw.keys())
    otp_data   = list(otp_raw.values())

    c.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    task_raw           = c.fetchall()
    task_status_labels = [r[0] for r in task_raw]
    task_status_data   = [r[1] for r in task_raw]

    c.execute("SELECT status, COUNT(*) FROM sessions GROUP BY status")
    session_raw           = c.fetchall()
    session_status_labels = [r[0] for r in session_raw]
    session_status_data   = [r[1] for r in session_raw]

    conn.close()

    return render_template(
        "dashboard.html",
        agent_id=session['agent_id'],
        issues=issues,
        users_count=users_count,
        agents_count=agents_count,
        open_tasks_count=open_tasks_count,
        unread_notifications=unread_notifications,
        otp_used_count=otp_used_count,
        sessions_count=sessions_count,
        faqs_count=faqs_count,
        tasks=tasks,
        notifications=notifications,
        snapshot_labels=snapshot_labels,
        snapshot_resolved=snapshot_resolved,
        snapshot_pending=snapshot_pending,
        snapshot_avg_sla=snapshot_avg_sla,
        otp_labels=otp_labels,
        otp_data=otp_data,
        task_status_labels=task_status_labels,
        task_status_data=task_status_data,
        session_status_labels=session_status_labels,
        session_status_data=session_status_data,
    )


@app.route('/kpi')
def kpi():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("""
        SELECT snapshot_date, resolved, pending
        FROM kpi_snapshots
        ORDER BY snapshot_date DESC LIMIT 30
    """).fetchall()
    conn.close()
    return jsonify({
        "labels":   [r[0] for r in rows],
        "resolved": [r[1] for r in rows],
        "pending":  [r[2] for r in rows],
    })


@app.route('/address', methods=['POST'])
def address():
    if 'agent_id' not in session:
        return redirect('/login')

    issue_id = request.form.get('issue_id')
    topic    = request.form.get('topic')
    comment  = request.form.get('comment')

    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT phone FROM issues WHERE id=?", (issue_id,)).fetchone()
    customer_phone = row[0] if row else "unknown"

    send_sms(customer_phone, f"{topic}: {comment}")

    c.execute("""
        UPDATE issues SET resolution_notes=?, category=?, status='pending'
        WHERE id=?
    """, (comment, topic, issue_id))
    conn.commit()
    conn.close()

    return redirect('/')


@app.route('/resolve', methods=['POST'])
def resolve_issue():
    if 'agent_id' not in session:
        return redirect('/login')

    issue_id         = request.form.get('issue_id')
    resolution_notes = request.form.get('resolution_notes')
    agent_id         = session['agent_id']

    conn = sqlite3.connect("support.db")
    c = conn.cursor()
    row = c.execute("SELECT phone FROM issues WHERE id=?", (issue_id,)).fetchone()
    customer_phone = row[0] if row else "unknown"

    send_sms(customer_phone, f"Ticket {issue_id} resolved: {resolution_notes}")

    c.execute("""
        UPDATE issues
        SET status           = 'Resolved',
            resolution_notes = ?,
            agent_id         = ?,
            closed_at        = CURRENT_TIMESTAMP,
            sla_status       = CASE
                                 WHEN sla_due >= CURRENT_TIMESTAMP THEN 'Within SLA'
                                 ELSE 'Breached'
                               END
        WHERE id = ?
    """, (resolution_notes, agent_id, issue_id))
    conn.commit()
    conn.close()

    return redirect('/')


@app.route('/send_sms_action', methods=['POST'])
def send_sms_action():
    if 'agent_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data    = request.get_json()
    phone   = data.get('phone', '').strip()
    message = data.get('message', '').strip()

    if not phone or not message:
        return jsonify({'error': 'Missing phone or message'}), 400

    send_sms(phone, message)

    conn = sqlite3.connect("support.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO notifications (phone, message, status, created_at)
        VALUES (?, ?, 'unread', CURRENT_TIMESTAMP)
    """, (phone, f"[Agent SMS] {message}"))
    conn.commit()
    conn.close()

    return jsonify({'status': 'sent', 'phone': phone})


@app.route('/initiate_callback', methods=['POST'])
def initiate_callback():
    if 'agent_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data          = request.get_json()
    issue_id      = data.get('issue_id')
    phone         = data.get('phone', '').strip()
    agent_message = data.get('message', '').strip()

    if not phone:
        return jsonify({'error': 'Missing phone'}), 400

    send_callback_request(phone, agent_message=agent_message)

    conn = sqlite3.connect("support.db")
    c = conn.cursor()
    c.execute("UPDATE issues SET escalation_type='callback' WHERE id=?", (issue_id,))
    note = "[Callback Initiated] Agent will call customer back"
    if agent_message:
        note += f" | Note: {agent_message}"
    c.execute("""
        INSERT INTO notifications (phone, message, status, created_at)
        VALUES (?, ?, 'unread', CURRENT_TIMESTAMP)
    """, (phone, note))
    conn.commit()
    conn.close()

    return jsonify({'status': 'callback_initiated', 'phone': phone})


@app.route('/resolve_with_method', methods=['POST'])
def resolve_with_method():
    """
    Persists Resolved status + escalation_type (method) + resolution_notes
    in the DB so data survives page refresh.
    """
    if 'agent_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data     = request.get_json()
    issue_id = data.get('issue_id')
    method   = data.get('method', '').strip()          # 'sms' or 'callback'
    notes    = data.get('notes', f'Resolved via {method}').strip()
    agent_id = session['agent_id']

    if not issue_id:
        return jsonify({'error': 'Missing issue_id'}), 400

    if not method:
        return jsonify({'error': 'Missing method'}), 400

    try:
        conn = sqlite3.connect("support.db")
        c    = conn.cursor()

        # Persist EVERYTHING: status, method (escalation_type), notes, agent, timestamp, SLA
        c.execute("""
            UPDATE issues
            SET status           = 'Resolved',
                escalation_type  = ?,
                resolution_notes = ?,
                agent_id         = ?,
                closed_at        = CURRENT_TIMESTAMP,
                sla_status       = CASE
                                     WHEN sla_due >= CURRENT_TIMESTAMP THEN 'Within SLA'
                                     ELSE 'Breached'
                                   END
            WHERE id = ?
        """, (method, notes, agent_id, issue_id))

        if c.rowcount == 0:
            conn.close()
            return jsonify({'error': f'Issue {issue_id} not found'}), 404

        conn.commit()
        conn.close()

        return jsonify({
            'status':   'resolved',
            'method':   method,
            'notes':    notes,
            'issue_id': issue_id
        })

    except Exception as e:
        app.logger.error("resolve_with_method error: %s", e)
        return jsonify({'error': str(e)}), 500


# ================================================================
# USSD ENDPOINT
# ================================================================

@app.route('/ussd', methods=['POST'])
def ussd():
    session_id   = request.form.get("sessionId",   "").strip()
    phone        = request.form.get("phoneNumber", "").strip()
    raw_text     = request.form.get("text",        "").strip()
    service_code = request.form.get("serviceCode", "").strip()
    network_code = request.form.get("networkCode", "").strip()

    app.logger.debug(
        "USSD ← sessionId=%s phone=%s serviceCode=%s networkCode=%s text=%r",
        session_id, phone, service_code, network_code, raw_text,
    )

    if not session_id or not phone:
        return "END Missing required gateway fields (sessionId / phoneNumber).", 400

    if not get_session(session_id):
        create_session(session_id, phone)

    response = route(session_id, phone, raw_text)

    steps      = [s.strip() for s in raw_text.split("*")] if raw_text else []
    user_input = steps[-1] if steps else ""
    sess       = get_session(session_id)
    state      = sess["state"] if sess else "UNKNOWN"

    _log_ussd(session_id, phone, service_code, network_code, user_input, state, response)

    app.logger.debug("USSD → %r", response)
    return response, 200, {"Content-Type": "text/plain"}


# ================================================================

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)