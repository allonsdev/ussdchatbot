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

STATE_START = "START"
STATE_AUTH_METHOD = "AUTH_METHOD"
STATE_PIN = "PIN"
STATE_OTP = "OTP"
STATE_AUTHENTICATED = "AUTHENTICATED"
STATE_MAIN_MENU = "MAIN_MENU"
STATE_WALLET = "WALLET"
STATE_SUPPORT = "SUPPORT"
STATE_ACCOUNT = "ACCOUNT"


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

USERNAME = "sandbox"  # Sandbox username
API_KEY = "atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a"  # Replace with your sandbox key
SMS_URL = "https://api.sandbox.africastalking.com/version1/messaging"

# Debug info
print("PYTHON EXECUTABLE:", sys.executable)
print("OPENSSL VERSION:", ssl.OPENSSL_VERSION)


# --------------------------
# DATABASE CONFIG
# --------------------------
DB = "support.db"

def get_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


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

# ================================================================
# DATABASE HELPERS
# ================================================================

@app.route("/test")
def test():
    session['foo'] = 'bar'
    return f"Session works! foo={session.get('foo')}"

def get_db():
    return sqlite3.connect(DB)


def sanitize_number(phone):
    """
    Normalize Zimbabwe phone numbers to +263 format.
    """
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
    """
    Validate agent login credentials.
    Agent ID format: A01, A02, etc.
    Password: min 6 chars with letters + numbers.
    """
    if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$', password):
        return "Password must be at least 6 characters and include letters and numbers."

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password FROM agents WHERE agent_id=?", (agent_id,))
    print(agent_id)
    row = c.fetchone()
    print(row[0])
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
            "step": row[1],
            "data": json.loads(row[2]) if row[2] else {}
        }
    return None


# ================================================================
# KPI SNAPSHOT GENERATION
# ================================================================

def snapshot_kpi():
    conn = get_db()
    c = conn.cursor()

    total = c.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    resolved = c.execute("SELECT COUNT(*) FROM issues WHERE status='resolved'").fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM issues WHERE status='pending'").fetchone()[0]
    calls = c.execute("SELECT COUNT(*) FROM issues WHERE escalation_type='call'").fetchone()[0]

    avg_sla = c.execute("""
    SELECT AVG(
        JULIANDAY(closed_at) - JULIANDAY(created_at)
    ) FROM issues WHERE status='resolved'
    """).fetchone()[0] or 0

    churn_rate = random.uniform(0, 1)  # Placeholder (replace with real formula)

    c.execute("""
    INSERT INTO kpi_snapshots
    (total, resolved, pending, calls, avg_sla, churn_rate)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (total, resolved, pending, calls, avg_sla, churn_rate))

    conn.commit()
    conn.close()


# ================================================================
# SLA TRACKING
# ================================================================

def calculate_sla(hours=48):
    return datetime.datetime.now() + datetime.timedelta(hours=hours)


# def update_sla_status():
#     conn = get_db()
#     c = conn.cursor()

#     c.execute("""
#     UPDATE issues
#     SET sla_status = CASE
#         WHEN status='resolved' THEN 'met'
#         WHEN sla_due < CURRENT_TIMESTAMP THEN 'breached'
#         ELSE 'in_sla'
#     END
#     """)

#     conn.commit()
#     conn.close()


# ================================================================
# SMS HELPERS
# ================================================================

def send_sms(phone, message):
    try:
        resp = session_http.post(
            SMS_URL,
            headers={"apiKey": API_KEY},
            data={"username": USERNAME, "to": phone, "message": message},
            timeout=10
        )
        return resp.status_code == 201
    except Exception as e:
        print("SMS error:", e)
        return False


def auto_reply(phone):
    send_sms(phone, "Your issue has been logged. Agent will contact you.")




def send_booking_sms(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox"):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return

    # URL-encode form data
    data = {
        "username": username,
        "to": phone,
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

# --------------------------
# Step 3: Example usage
# --------------------------


def send_booking(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox"):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return
    
    
    messagev2 ="Hello! I need your assistance. Could you please call me back? at this number" + str(phone)+ " Thank you."
    data = {
        "username": username,
        "to": phone,
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
    
    
    
@app.route('/address', methods=['POST'])
def address():
    if 'agent_id' not in session:
        return redirect('/login')

    issue_id = request.form['issue_id']
    topic = request.form['topic']
    comment = request.form['comment']

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT phone FROM issues WHERE id=?", (issue_id,))
    row = c.fetchone()
    conn.close()

    phone = "+27707317823"
    if not phone:
        return redirect('/')

    message = f"{topic}: {comment}"

    # Send SMS via TLS curl method
    send_sms_tls(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox")

    # Update DB with notes
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE issues
        SET resolution_notes=?, status='pending'
        WHERE id=?
    """, (message, issue_id))
    conn.commit()
    conn.close()

    return redirect('/')




def send_sms_tls(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox"):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return

    # URL-encode form data
    data = {
        "username": username,
        "to": phone,
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

# ================================================================
# DASHBOARD DATA
# ================================================================

def get_issues(status=None, escalation_type=None):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT id, phone, issue, escalation_type, status, created_at, agent_id FROM issues"
    params = []

    if status or escalation_type:
        query += " WHERE "
        conditions = []
        if status:
            conditions.append("status=?")
            params.append(status)
        if escalation_type:
            conditions.append("escalation_type=?")
            params.append(escalation_type)
        query += " AND ".join(conditions)

    return c.execute(query, params).fetchall()


# ================================================================
# FLASK ROUTES
# ================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        agent_id = request.form['agent_id']
        password = request.form['password']
        validation = validate_agent(agent_id, password)
        if validation is True:
            session['agent_id'] = agent_id
            print(session['agent_id'])
            return redirect('/')
        return validation
    return render_template("login.html")


@app.route('/address', methods=['POST'])
def address_issue():
    if 'agent_id' not in session:
        return redirect('/login')

    issue_id = request.form.get('issue_id')
    topic    = request.form.get('topic')
    comment  = request.form.get('comment')

    conn = sqlite3.connect("support.db")
    c = conn.cursor()
    c.execute("""
        UPDATE issues
        SET resolution_notes = ?,
            category = ?
        WHERE id = ?
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


    phone = "+27707317823"
    if not phone:
        return redirect('/')

    message = f"{issue_id}: {resolution_notes}"

    # Send SMS via TLS curl method
    send_sms_tls(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox")
    conn = sqlite3.connect("support.db")
    c = conn.cursor()
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




@app.route('/')
def dashboard():
    if 'agent_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("support.db")
    c = conn.cursor()

    # --------------------------
    # FILTERS
    # --------------------------
    status = request.args.get("status")
    escalation_type = request.args.get("type")

    # --------------------------
    # ISSUES
    # --------------------------
    query = "SELECT * FROM issues WHERE 1=1"
    params = []

    if status:
        query += " AND status=?"
        params.append(status)

    if escalation_type:
        query += " AND escalation_type=?"
        params.append(escalation_type)

    c.execute(query, params)
    issues = c.fetchall()

    # --------------------------
    # KPIs
    # --------------------------
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM agents")
    agents_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status!='Done'")
    open_tasks_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM notifications WHERE status='unread'")
    unread_notifications = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM otp_codes WHERE status='used'")
    otp_used_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM sessions")
    sessions_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM faqs")
    faqs_count = c.fetchone()[0]

    # --------------------------
    # TASKS TABLE
    # --------------------------
    c.execute("""
        SELECT agent_id, title, status, due_date
        FROM tasks
        ORDER BY due_date ASC LIMIT 20
    """)
    tasks = c.fetchall()

    # --------------------------
    # NOTIFICATIONS TABLE
    # --------------------------
    c.execute("""
        SELECT phone, message, status, created_at
        FROM notifications
        ORDER BY created_at DESC LIMIT 20
    """)
    notifications = c.fetchall()

    # --------------------------
    # CHART: KPI Snapshots Trend
    # --------------------------
    c.execute("""
        SELECT snapshot_date, resolved, pending, avg_sla
        FROM kpi_snapshots
        ORDER BY snapshot_date ASC LIMIT 30
    """)
    snapshot_raw = c.fetchall()
    snapshot_labels = [row[0] for row in snapshot_raw]
    snapshot_resolved = [row[1] for row in snapshot_raw]
    snapshot_pending = [row[2] for row in snapshot_raw]
    snapshot_avg_sla = [row[3] for row in snapshot_raw]

    # --------------------------
    # CHART: OTP Usage
    # --------------------------
    c.execute("""
        SELECT status, COUNT(*)
        FROM otp_codes
        GROUP BY status
    """)
    otp_raw = dict(c.fetchall())
    otp_labels = list(otp_raw.keys())
    otp_data = list(otp_raw.values())

    # --------------------------
    # CHART: Task Status Breakdown
    # --------------------------
    c.execute("""
        SELECT status, COUNT(*)
        FROM tasks
        GROUP BY status
    """)
    task_raw = c.fetchall()
    task_status_labels = [row[0] for row in task_raw]
    task_status_data = [row[1] for row in task_raw]

    # --------------------------
    # CHART: Wallet Balances (Top 10)
    # --------------------------
    c.execute("""
        SELECT phone, balance
        FROM wallets
        ORDER BY balance DESC LIMIT 10
    """)
    wallet_raw = c.fetchall()
    wallets= wallet_raw
    wallet_labels = [row[0] for row in wallet_raw]
    wallet_data = [row[1] for row in wallet_raw]

    # --------------------------
    # CHART: Session Status Breakdown
    # --------------------------
    c.execute("""
        SELECT status, COUNT(*)
        FROM sessions
        GROUP BY status
    """)
    session_raw = c.fetchall()
    session_status_labels = [row[0] for row in session_raw]
    session_status_data = [row[1] for row in session_raw]

    conn.close()

    # --------------------------
    # RENDER
    # --------------------------
    return render_template(
        "dashboard.html",
        issues=issues,
        wallets=wallets,
        # KPIs
        users_count=users_count,
        agents_count=agents_count,
        open_tasks_count=open_tasks_count,
        unread_notifications=unread_notifications,
        otp_used_count=otp_used_count,
        sessions_count=sessions_count,
        faqs_count=faqs_count,

        # Tables
        tasks=tasks,
        notifications=notifications,

        # Charts
        snapshot_labels=snapshot_labels,
        snapshot_resolved=snapshot_resolved,
        snapshot_pending=snapshot_pending,
        snapshot_avg_sla=snapshot_avg_sla,
        otp_labels=otp_labels,
        otp_data=otp_data,
        task_status_labels=task_status_labels,
        task_status_data=task_status_data,
        wallet_labels=wallet_labels,
        wallet_data=wallet_data,
        session_status_labels=session_status_labels,
        session_status_data=session_status_data,
    )
    
# ================================================================

@app.route('/kpi')
def kpi():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("""
    SELECT snapshot_date, resolved, pending
    FROM kpi_snapshots
    ORDER BY snapshot_date DESC
    LIMIT 30
    """).fetchall()
    conn.close()

    return jsonify({
        "labels": [r[0] for r in rows],
        "resolved": [r[1] for r in rows],
        "pending": [r[2] for r in rows]
    })
# --------------------------
# LOG ISSUE INTO SUPPORT.DB
# --------------------------
def log_issue(session_id, phone_number, issue_text, escalation_type):

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch agents
    cursor.execute("SELECT agent_id FROM agents")
    agents = cursor.fetchall()

    if agents:
        assigned_agent = random.choice(agents)["agent_id"]
    else:
        assigned_agent = None

    created_at = datetime.datetime.utcnow()
    sla_due = created_at + datetime.timedelta(hours=24)

    cursor.execute("""
        INSERT INTO issues (
            phone,
            issue,
            escalation_type,
            status,
            created_at,
            agent_id,
            resolution_notes,
            closed_at,
            priority,
            category,
            sla_due,
            sla_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        phone_number,
        issue_text,
        escalation_type,
        "Open",
        created_at,
        assigned_agent,
        None,
        None,
        "Medium",
        "General",
        sla_due,
        "Within SLA"
    ))

    conn.commit()
    conn.close()



def get_db():
    return sqlite3.connect(DB)

# --------------------------

# --------------------------
# LANGUAGES
# --------------------------
LANGUAGES = {
    "1": "en",
    "2": "nd",
    "3": "sn"
}

TEXT = {
    "welcome": {"en": "Welcome", "nd": "Siyakwamukela", "sn": "Tinokugamuchirai"},
    "invalid": {"en": "Invalid input", "nd": "Okungavumelekile", "sn": "Zvisiri izvo"},
    "invalid_pin": {"en": "Invalid PIN", "nd": "I-PIN ayilungile", "sn": "PIN haina kunaka"},
    "invalid_choice": {"en": "Invalid choice", "nd": "Ukhetho alulungile", "sn": "Sarudzo haina kunaka"},
    "session_error": {"en": "Session error", "nd": "Iphutha leseshini", "sn": "Session error"},
    "enter_phone": {"en": "Enter phone number:", "nd": "Faka inombolo yocingo:", "sn": "Isa nhamba yefoni:"},
    "select_option": {
        "en": "Select option:\n1. Enter PIN\n2. Use OTP",
        "nd": "Khetha inketho:\n1. Faka i-PIN\n2. Sebenzisa OTP",
        "sn": "Sarudza:\n1. Isa PIN\n2. Shandisa OTP"
    },
    "enter_pin": {"en": "Enter your PIN", "nd": "Faka i-PIN yakho", "sn": "Isa PIN yako"},
    "enter_otp": {"en": "Enter OTP", "nd": "Faka i-OTP", "sn": "Isa OTP"},
    "main_menu": {
        "en": "1. Wallet\n2. Support\n3. FAQ\n4. Account",
        "nd": "1. I-Wallet\n2. Usizo\n3. FAQ\n4. I-Akhawunti",
        "sn": "1. Wallet\n2. Rubatsiro\n3. FAQ\n4. Account"
    },
    "wallet": {
        "en": "1. Balance\n2. Send Money\n3. Mini Statement",
        "nd": "1. Ibhalansi\n2. Thumela Imali\n3. Umlando",
        "sn": "1. Balance\n2. Tumira Mari\n3. Nhoroondo"
    },
    "support": {
        "en": "1. Create Ticket\n2. Track Ticket\n3. Callback",
        "nd": "1. Dala Ithikithi\n2. Landelela\n3. Call back",
        "sn": "1. Gadzira Ticket\n2. Tarisa\n3. Callback"
    },
    "balance": {"en": "Your balance is", "nd": "Imali yakho ngu", "sn": "Mari yako i"},
    "sent": {"en": "Sent", "nd": "Kuthunyelwe", "sn": "Watumira"},
    "insufficient": {"en": "Insufficient balance", "nd": "Imali ayanele", "sn": "Mari haina kukwana"},
    "enter_recipient": {"en": "Enter recipient", "nd": "Faka umamukeli", "sn": "Isa anogamuchira"},
    "enter_amount": {"en": "Enter amount", "nd": "Faka inani", "sn": "Isa huwandu"},
    "ticket_created": {"en": "Ticket created", "nd": "Ithikithi lidaliwe", "sn": "Ticket yagadzirwa"},
    "enter_issue": {"en": "Describe issue", "nd": "Chaza inkinga", "sn": "Tsanangura dambudziko"},
    "enter_ticket": {"en": "Enter ticket ID", "nd": "Faka i-ID", "sn": "Isa ticket ID"},
    "callback": {"en": "Callback requested", "nd": "I-call back iceliwe", "sn": "Callback yakumbirwa"},
    "otp_sent": {"en": "OTP sent", "nd": "OTP ithunyelwe", "sn": "OTP yatumirwa"},
    "otp_invalid": {"en": "Invalid OTP", "nd": "OTP ayilungile", "sn": "OTP haina kunaka"},
    "pin_updated": {"en": "PIN updated", "nd": "PIN iguquliwe", "sn": "PIN yashandurwa"}
}

def t(key, lang="en"):
    return TEXT.get(key, {}).get(lang, TEXT.get(key, {}).get("en", key))


# --------------------------
# DB
# --------------------------
def get_db():
    return sqlite3.connect("support.db")


# --------------------------
# CORE FUNCTIONS
# --------------------------
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


def send_sms(phone, msg):
    print("SMS to", phone, ":", msg)


def generate_otp(phone):
    code = str(random.randint(1000, 9999))

    conn = get_db()
    conn.execute(
        "INSERT INTO otp_codes (phone, code, status, created_at) VALUES (?, ?, 'PENDING', CURRENT_TIMESTAMP)",
        (phone, code)
    )
    conn.commit()
    conn.close()

    send_sms(phone, "Your OTP is " + code)
    return code


def verify_otp(phone, user_code):
    conn = get_db()
    c = conn.cursor()
    row = c.execute("""
        SELECT id, code, created_at
        FROM otp_codes
        WHERE phone=? AND status='PENDING'
        ORDER BY created_at DESC
        LIMIT 1
    """, (phone,)).fetchone()

    if not row:
        return False

    otp_id, code, created_at = row

    created_time = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")

    if datetime.now() - created_time > timedelta(minutes=5):
        return False

    if code == user_code:
        c.execute("UPDATE otp_codes SET status='USED' WHERE id=?", (otp_id,))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


# --------------------------
# MENUS
# --------------------------
def language_menu():
    return "CON Select Language:\n1. English\n2. Ndebele\n3. Shona"


def main_menu(lang):
    return f"CON {t('welcome', lang)}\n{t('main_menu', lang)}"


def wallet_menu(lang):
    return f"CON {t('wallet', lang)}"


def support_menu(lang):
    return f"CON {t('support', lang)}"


 
def _log_ussd(session_id: str, phone: str, service_code: str,
               network_code: str, user_input: str, state: str, response: str):
    """Append one row to the ussd_logs audit table."""
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
 

@app.route('/ussd', methods=['POST'])
def ussd():
    session_id   = request.form.get("sessionId",   "").strip()
    phone        = request.form.get("phoneNumber", "").strip()
    raw_text     = request.form.get("text",        "").strip()
    service_code = request.form.get("serviceCode", "").strip()
    network_code = request.form.get("networkCode", "").strip()
    
    
    print(session_id)
    app.logger.debug(
        "USSD ← sessionId=%s phone=%s serviceCode=%s networkCode=%s text=%r",
        session_id, phone, service_code, network_code, raw_text,
    )
 
    # ── Guard: require sessionId and phoneNumber ────────────────────────────
    if not session_id or not phone:
        return "END Missing required gateway fields (sessionId / phoneNumber).", 400
 
    # ── Ensure a session row exists (idempotent) ────────────────────────────
    if not get_session(session_id):
        create_session(session_id, phone)
 
    # ── Route to the correct state handler ─────────────────────────────────
    response = route(session_id, phone, raw_text)
 
    # ── Derive last user input and current state for logging ───────────────
    steps      = [s.strip() for s in raw_text.split("*")] if raw_text else []
    user_input = steps[-1] if steps else ""
    session    = get_session(session_id)
    state      = session["state"] if session else "UNKNOWN"
 
    _log_ussd(session_id, phone, service_code, network_code, user_input, state, response)
 
    app.logger.debug("USSD → %r", response)
    return response, 200, {"Content-Type": "text/plain"}



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)