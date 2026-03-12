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

# ================================================================
# FLASK INITIALIZATION
# ================================================================

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Replace in production with env variable

# ================================================================
# AFRICAS TALKING SANDBOX CONFIG
# ================================================================

USERNAME = "sandbox"  # Sandbox username
API_KEY = "atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a"  # Replace with your sandbox key
SMS_URL = "https://api.sandbox.africastalking.com/version1/messaging"

# ================================================================
# SECURE TLS SESSION (TLS 1.2 ONLY)
# ================================================================

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

DB = "support.db"


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
    if not phone.startswith("+263"):
        return "+263" + phone.lstrip("0")
    return phone


def init_db():
    """
    Create all required tables if they don't exist.
    Includes:
    - issues
    - agents
    - tasks
    - kpi_snapshots
    - ussd_sessions
    - churn
    """
    conn = get_db()
    c = conn.cursor()

    # ISSUES
    c.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        issue TEXT,
        escalation_type TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        agent_id TEXT,
        resolution_notes TEXT,
        closed_at TIMESTAMP,
        priority TEXT,
        category TEXT,
        sla_due TIMESTAMP,
        sla_status TEXT
    )
    """)

    # AGENTS
    c.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        full_name TEXT,
        role TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # TASK BOARD
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT,
        title TEXT,
        description TEXT,
        status TEXT,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # KPI SNAPSHOTS
    c.execute("""
    CREATE TABLE IF NOT EXISTS kpi_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total INTEGER,
        resolved INTEGER,
        pending INTEGER,
        calls INTEGER,
        avg_sla REAL,
        churn_rate REAL
    )
    """)

    # USSD SESSION PERSISTENCE
    c.execute("""
    CREATE TABLE IF NOT EXISTS ussd_sessions (
        session_id TEXT PRIMARY KEY,
        phone TEXT,
        step TEXT,
        data TEXT,
        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # CHURN TRACKING
    c.execute("""
    CREATE TABLE IF NOT EXISTS churn (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization TEXT,
        risk_score REAL,
        risk_level TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # DEMO AGENTS
    c.execute("SELECT COUNT(*) FROM agents")
    if c.fetchone()[0] == 0:
        c.execute("""
        INSERT INTO agents (agent_id, password, full_name, role)
        VALUES
        ('A01','pass123','Admin One','support'),
        ('A02','abc789','Admin Two','support')
        """)

    conn.commit()
    conn.close()


# ================================================================
# AUTH VALIDATION
# ================================================================

def validate_agent(agent_id, password):
    """
    Validate agent login credentials.
    Agent ID format: A01, A02, etc.
    Password: min 6 chars with letters + numbers.
    """
    if not re.match(r'^[A-Z]\d{2}$', agent_id):
        return "Incorrect format. Agent ID must be like A01."
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


def update_sla_status():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    UPDATE issues
    SET sla_status = CASE
        WHEN status='resolved' THEN 'met'
        WHEN sla_due < CURRENT_TIMESTAMP THEN 'breached'
        ELSE 'in_sla'
    END
    """)

    conn.commit()
    conn.close()


# ================================================================
# SMS HELPERS
# ================================================================

# def send_sms(phone, message):
#     try:
#         resp = session_http.post(
#             SMS_URL,
#             headers={"apiKey": API_KEY},
#             data={"username": USERNAME, "to": phone, "message": message},
#             timeout=10
#         )
#         return resp.status_code == 201
#     except Exception as e:
#         print("SMS error:", e)
#         return False


# def auto_reply(phone):
#     send_sms(phone, "Your issue has been logged. Agent will contact you.")


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
            return redirect('/')
        return validation
    return render_template("login.html")


@app.route('/')
def dashboard():
    if 'agent_id' not in session:
        return redirect('/login')

    status = request.args.get("status")
    escalation_type = request.args.get("type")

    update_sla_status()
    issues = get_issues(status, escalation_type)

    return render_template("dashboard.html", issues=issues)


@app.route('/resolve', methods=['POST'])
def resolve_issue():
    if 'agent_id' not in session:
        return redirect('/login')

    agent_id = session['agent_id']
    issue_id = request.form['issue_id']
    action = request.form['action']
    message = request.form.get('message', '')

    conn = get_db()
    c = conn.cursor()
    phone = c.execute("SELECT phone FROM issues WHERE id=?", (issue_id,)).fetchone()[0]
    conn.close()

    phone = sanitize_number(phone)
    status = "pending"

    if action == "sms":
        if send_sms(phone, message):
            status = "resolved"
            auto_reply(phone)
        else:
            status = "failed"

    elif action == "call":
        status = "Call Initiated"
        print(f"Call request: {phone} by {agent_id}")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
    UPDATE issues SET status=?, agent_id=?, resolution_notes=?, closed_at=?
    WHERE id=?
    """, (status, agent_id, message, datetime.datetime.now(), issue_id))
    conn.commit()
    conn.close()

    snapshot_kpi()
    return redirect(url_for('dashboard'))


# ================================================================
# CHART ENDPOINT
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


# ================================================================
# STARTUP
# ================================================================



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
   
if __name__ == "__main__":
    init_db()
    snapshot_kpi()
    app.run(port=5001, debug=True)