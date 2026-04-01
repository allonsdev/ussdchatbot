"""
db.py
-----
Single source of truth for:
  • SQLite connection factory
  • Table creation   (init_db)
  • Schema migration (migrate_db)
  • Seed data        (_seed_*)  ← 100+ realistic rows per table

AfricasTalking USSD gateway – POST fields received per request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    sessionId   – unique session ID per dial  → stored in sessions.session_id
    phoneNumber – caller MSISDN (E.164)       → stored as sessions.phone
    text        – accumulated input string    → parsed in router.py
    serviceCode – USSD short code (*123#)     → logged in ussd_logs.service_code
    networkCode – MNO network code string     → logged in ussd_logs.network_code

The `phone` column everywhere in the DB corresponds 1-to-1 with
AfricasTalking's `phoneNumber` field, e.g. "+263771234567".
"""

import sqlite3
import random
import uuid
from datetime import datetime, timedelta

DB_PATH = "support.db"

# ---------------------------------------------------------------------------
# Shared reference data used across seed functions
# ---------------------------------------------------------------------------

PHONES = [
    "+263771000001", "+263771000002", "+263771000003", "+263771000004",
    "+263771000005", "+263771000006", "+263771000007", "+263771000008",
    "+263771000009", "+263771000010", "+263771000011", "+263771000012",
    "+263771000013", "+263771000014", "+263771000015", "+263771000016",
    "+263771000017", "+263771000018", "+263771000019", "+263771000020",
    "+263772000001", "+263772000002", "+263772000003", "+263772000004",
    "+263772000005", "+263772000006", "+263772000007", "+263772000008",
    "+263772000009", "+263772000010", "+263773000001", "+263773000002",
    "+263773000003", "+263773000004", "+263773000005", "+263773000006",
    "+263773000007", "+263773000008", "+263773000009", "+263773000010",
    "+27707317823",  "+27711000001",  "+27711000002",  "+27711000003",
    "+27711000004",  "+27711000005",  "+27711000006",  "+27711000007",
    "+27711000008",  "+27711000009",  "+27721000001",  "+27721000002",
    "+27721000003",  "+27721000004",  "+27721000005",  "+27721000006",
    "+27721000007",  "+27721000008",  "+27721000009",  "+27721000010",
    "+263774000001", "+263774000002", "+263774000003", "+263774000004",
    "+263774000005", "+263774000006", "+263774000007", "+263774000008",
    "+263774000009", "+263774000010", "+263775000001", "+263775000002",
    "+263775000003", "+263775000004", "+263775000005", "+263775000006",
    "+263775000007", "+263775000008", "+263775000009", "+263775000010",
    "+27731000001",  "+27731000002",  "+27731000003",  "+27731000004",
    "+27731000005",  "+27731000006",  "+27731000007",  "+27731000008",
    "+27731000009",  "+27731000010",  "+27741000001",  "+27741000002",
    "+27741000003",  "+27741000004",  "+27741000005",  "+27741000006",
    "+27741000007",  "+27741000008",  "+27741000009",  "+27741000010",
]

AGENT_IDS = ["AGT001", "AGT002", "AGT003", "AGT004", "AGT005",
             "AGT006", "AGT007", "AGT008", "AGT009", "AGT010"]

PINS = ["1234", "5678", "0000", "1111", "2222", "3333", "4444", "9999", "1212", "4321"]

FIRST_NAMES = [
    "Thembi", "Rudo", "Sipho", "Chiedza", "Nomsa", "Tariro", "Blessing",
    "Farai", "Tendai", "Nhamo", "Zanele", "Lerato", "Thabo", "Palesa",
    "Lungelo", "Nompumelelo", "Sibusiso", "Thandeka", "Mpho", "Kagiso",
]
LAST_NAMES = [
    "Dube", "Moyo", "Ncube", "Mutasa", "Mhlanga", "Chirwa", "Banda",
    "Nkosi", "Zulu", "Ndlovu", "Sithole", "Mthembu", "Khumalo", "Zwane",
    "Mkhize", "Hadebe", "Ntuli", "Majola", "Cele", "Mnguni",
]

ISSUES_TEXT = [
    "Wallet balance not updating after transfer",
    "Unable to login with PIN",
    "OTP not received on phone",
    "Sent money to wrong number",
    "Account locked after failed attempts",
    "Mini statement showing wrong transactions",
    "Cannot change PIN via USSD",
    "Double charged for single transaction",
    "Balance shows negative after deposit",
    "Session times out too quickly",
    "USSD menu not responding after selection",
    "Received money but balance unchanged",
    "Cannot request callback – menu freezes",
    "FAQ not loading on handset",
    "Language selection not saving",
    "Transfer limit exceeded error on small amount",
    "PIN reset OTP expired before entry",
    "Transaction reference number missing",
    "Wallet deducted but receiver not credited",
    "Agent callback never received",
]

CATEGORIES = ["WALLET", "ACCOUNT", "TECHNICAL", "BILLING", "OTHER"]
PRIORITIES  = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
STATUSES_ISSUE = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
SLA_STATUSES = ["ON_TRACK", "BREACHED", "RESOLVED"]
ESC_TYPES    = ["NONE", "TIER2", "MANAGEMENT"]

TASK_TITLES = [
    "Follow up on overdue ticket",
    "Call customer regarding PIN reset",
    "Investigate double-charge complaint",
    "Review SLA compliance report",
    "Escalate billing dispute to finance",
    "Send welcome SMS to new users",
    "Audit failed OTP records",
    "Update FAQ answers for Q2",
    "Train new agent on USSD flows",
    "Generate monthly KPI snapshot",
    "Close resolved tickets older than 30 days",
    "Verify wallet balances for top users",
    "Respond to callback queue",
    "Review notification delivery failures",
    "Archive old USSD session logs",
]

TASK_STATUSES = ["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"]

NOTIF_MESSAGES = [
    "Your OTP is {otp}. Valid for 5 minutes.",
    "Your wallet balance is {bal}. Dial *123# to transact.",
    "You have received {amt} from {phone}.",
    "Your support ticket {tid} has been updated.",
    "Your PIN has been changed successfully.",
    "A callback has been scheduled for you.",
    "Your ticket {tid} is now RESOLVED.",
    "Low balance alert: your balance is {bal}.",
    "Transaction of {amt} was successful.",
    "Welcome to the platform! Dial *123# to start.",
]

NOTIF_STATUSES  = ["QUEUED", "SENT", "FAILED"]
NOTIF_CHANNELS  = ["SMS", "PUSH"]
LANGS           = ["en", "nd", "sn"]
SERVICE_CODES   = ["*123#", "*321#", "*456#"]
NETWORK_CODES   = ["63902", "63903", "63001", "63004"]
SESSION_STATES  = [
    "START", "ENTER_ID_TYPE", "ENTER_PHONE", "ENTER_ACCOUNT",
    "AUTH_CHOOSE", "AUTH_PIN", "AUTH_OTP_CHOOSE", "AUTH_OTP",
    "LANGUAGE", "MAIN_MENU", "WALLET_MENU", "WALLET_SEND_RECIPIENT",
    "WALLET_BALANCE", "SUPPORT_MENU", "FAQ_LIST", "ACCOUNT_MENU",
]
SESSION_STATUSES = ["ACTIVE", "ENDED", "TIMEOUT"]

RESOLUTION_NOTES = [
    "Issue confirmed and resolved by system restart.",
    "Customer coached on correct PIN entry procedure.",
    "OTP re-sent and customer confirmed receipt.",
    "Transaction reversed and balance corrected.",
    "Account unlocked after identity verification.",
    "Duplicate charge refunded to wallet.",
    "System bug logged and patch deployed.",
    "Customer confirmed callback received.",
    "Mini statement regenerated correctly.",
    "Escalated to Tier 2 – awaiting finance confirmation.",
]

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _rand_date(days_back: int = 90) -> str:
    """Return a random ISO timestamp within the last *days_back* days."""
    offset = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return (datetime.now() - offset).strftime("%Y-%m-%d %H:%M:%S")


def _future_date(days_ahead: int = 30) -> str:
    offset = timedelta(days=random.randint(1, days_ahead))
    return (datetime.now() + offset).strftime("%Y-%m-%d %H:%M:%S")


def _full_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _ticket_id() -> str:
    return "TKT" + str(uuid.uuid4())[:6].upper()


def _session_id() -> str:
    return "SES" + str(uuid.uuid4()).replace("-", "")[:16].upper()


def _ref() -> str:
    return "REF" + str(uuid.uuid4())[:8].upper()


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

def init_db():
    """Create all application tables if they do not already exist."""
    conn = get_db()
    c = conn.cursor()

    print("[db] Initialising tables …")

    c.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id    TEXT PRIMARY KEY,
            password    TEXT NOT NULL,
            full_name   TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'agent',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            phone          TEXT NOT NULL,
            full_name      TEXT,
            status         TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (phone) REFERENCES users(phone)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            phone       TEXT PRIMARY KEY,
            pin         TEXT,
            password    TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            phone       TEXT PRIMARY KEY,
            balance     REAL NOT NULL DEFAULT 100,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender      TEXT NOT NULL,
            receiver    TEXT NOT NULL,
            amount      REAL NOT NULL,
            type        TEXT NOT NULL DEFAULT 'SEND',
            status      TEXT NOT NULL DEFAULT 'SUCCESS',
            reference   TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT NOT NULL,
            code        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'PENDING',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id    TEXT PRIMARY KEY,
            phone         TEXT NOT NULL,
            state         TEXT NOT NULL DEFAULT 'START',
            lang          TEXT NOT NULL DEFAULT 'en',
            temp_data     TEXT NOT NULL DEFAULT '{}',
            authenticated INTEGER NOT NULL DEFAULT 0,
            step          INTEGER NOT NULL DEFAULT 0,
            last_input    TEXT,
            status        TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ussd_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL,
            phone        TEXT NOT NULL,
            service_code TEXT,
            network_code TEXT,
            input        TEXT,
            state        TEXT,
            response     TEXT,
            status       TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id        TEXT UNIQUE NOT NULL,
            phone            TEXT NOT NULL,
            issue            TEXT NOT NULL,
            description      TEXT,
            escalation_type  TEXT NOT NULL DEFAULT 'NONE',
            status           TEXT NOT NULL DEFAULT 'OPEN',
            priority         TEXT NOT NULL DEFAULT 'MEDIUM',
            category         TEXT NOT NULL DEFAULT 'OTHER',
            agent_id         TEXT,
            resolution_notes TEXT,
            sla_due          TEXT,
            sla_status       TEXT NOT NULL DEFAULT 'ON_TRACK',
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            closed_at        TEXT,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS callbacks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'PENDING',
            agent_id    TEXT,
            notes       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id    TEXT NOT NULL,
            title       TEXT NOT NULL,
            description TEXT,
            status      TEXT NOT NULL DEFAULT 'OPEN',
            due_date    TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT NOT NULL,
            message     TEXT NOT NULL,
            channel     TEXT NOT NULL DEFAULT 'SMS',
            status      TEXT NOT NULL DEFAULT 'QUEUED',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            sent_at     TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kpi_snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            total         INTEGER NOT NULL DEFAULT 0,
            resolved      INTEGER NOT NULL DEFAULT 0,
            pending       INTEGER NOT NULL DEFAULT 0,
            calls         INTEGER NOT NULL DEFAULT 0,
            avg_sla       REAL    NOT NULL DEFAULT 0,
            churn_rate    REAL    NOT NULL DEFAULT 0,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            category    TEXT NOT NULL DEFAULT 'GENERAL',
            lang        TEXT NOT NULL DEFAULT 'en',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    _seed_agents()
    _seed_users()
    _seed_accounts()
    _seed_wallets()
    _seed_transactions()
    _seed_otp_codes()
    _seed_sessions()
    _seed_ussd_logs()
    _seed_issues()
    _seed_callbacks()
    _seed_tasks()
    _seed_notifications()
    _seed_kpi_snapshots()
    _seed_faqs()

    print("[db] ✅ All tables initialised and seeded.")


# ---------------------------------------------------------------------------
# migrate_db
# ---------------------------------------------------------------------------

def migrate_db():
    conn = get_db()
    c = conn.cursor()
    print("[db] Running migrations …")

    _safe_add_column(c, "sessions", "state",          "TEXT NOT NULL DEFAULT 'START'")
    _safe_add_column(c, "sessions", "lang",            "TEXT NOT NULL DEFAULT 'en'")
    _safe_add_column(c, "sessions", "temp_data",       "TEXT NOT NULL DEFAULT '{}'")
    _safe_add_column(c, "sessions", "step",            "INTEGER NOT NULL DEFAULT 0")
    _safe_add_column(c, "sessions", "last_input",      "TEXT")
    _safe_add_column(c, "sessions", "status",          "TEXT NOT NULL DEFAULT 'ACTIVE'")
    _safe_add_column(c, "sessions", "updated_at",      "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "otp_codes", "status",         "TEXT NOT NULL DEFAULT 'PENDING'")
    _safe_add_column(c, "otp_codes", "created_at",     "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "users", "password",           "TEXT")
    _safe_add_column(c, "users", "created_at",         "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "wallets", "created_at",       "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "wallets", "updated_at",       "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "transactions", "receiver",    "TEXT")
    _safe_add_column(c, "transactions", "reference",   "TEXT")
    _safe_add_column(c, "transactions", "type",        "TEXT NOT NULL DEFAULT 'SEND'")
    _safe_add_column(c, "transactions", "status",      "TEXT NOT NULL DEFAULT 'SUCCESS'")
    _safe_add_column(c, "issues", "description",       "TEXT")
    _safe_add_column(c, "issues", "priority",          "TEXT NOT NULL DEFAULT 'MEDIUM'")
    _safe_add_column(c, "issues", "category",          "TEXT NOT NULL DEFAULT 'OTHER'")
    _safe_add_column(c, "issues", "updated_at",        "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "issues", "sla_due",           "TEXT")
    _safe_add_column(c, "issues", "sla_status",        "TEXT NOT NULL DEFAULT 'ON_TRACK'")
    _safe_add_column(c, "issues", "agent_id",          "TEXT")
    _safe_add_column(c, "issues", "resolution_notes",  "TEXT")
    _safe_add_column(c, "issues", "closed_at",         "TEXT")
    _safe_add_column(c, "issues", "escalation_type",   "TEXT NOT NULL DEFAULT 'NONE'")
    _safe_add_column(c, "callbacks", "agent_id",       "TEXT")
    _safe_add_column(c, "callbacks", "notes",          "TEXT")
    _safe_add_column(c, "callbacks", "updated_at",     "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "agents", "created_at",        "TEXT DEFAULT CURRENT_TIMESTAMP")
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            phone          TEXT NOT NULL,
            full_name      TEXT,
            status         TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (phone) REFERENCES users(phone)
        )
    """)
    _safe_add_column(c, "faqs", "category",            "TEXT NOT NULL DEFAULT 'GENERAL'")
    _safe_add_column(c, "faqs", "lang",                "TEXT NOT NULL DEFAULT 'en'")
    _safe_add_column(c, "faqs", "created_at",          "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "notifications", "channel",    "TEXT NOT NULL DEFAULT 'SMS'")
    _safe_add_column(c, "notifications", "sent_at",    "TEXT")

    c.execute("""
        CREATE TABLE IF NOT EXISTS ussd_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL,
            phone        TEXT NOT NULL,
            service_code TEXT,
            network_code TEXT,
            input        TEXT,
            state        TEXT,
            response     TEXT,
            status       TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _safe_add_column(c, "ussd_logs", "service_code", "TEXT")
    _safe_add_column(c, "ussd_logs", "network_code", "TEXT")
    _safe_add_column(c, "ussd_logs", "state",        "TEXT")
    _safe_add_column(c, "ussd_logs", "response",     "TEXT")

    conn.commit()
    conn.close()
    print("[db] ✅ Migration complete.")


# ===========================================================================
# SEED FUNCTIONS  –  100+ rows per table, all idempotent
# ===========================================================================

def _seed_agents():
    """10 agents with varied roles."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM agents").fetchone()[0] > 0:
        conn.close(); return

    roles = ["admin", "supervisor", "agent", "agent", "agent",
             "agent", "agent", "agent", "agent", "agent"]
    rows = []
    for i, aid in enumerate(AGENT_IDS):
        rows.append((
            aid,
            "pass1234",
            f"{FIRST_NAMES[i]} {LAST_NAMES[i]}",
            roles[i],
            _rand_date(365),
        ))
    c.executemany(
        "INSERT INTO agents (agent_id, password, full_name, role, created_at) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] agents          → {len(rows)} rows")


def _seed_users():
    """100 users, one per phone number in PHONES list."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close(); return

    rows = [(p, random.choice(PINS), None, _rand_date(365)) for p in PHONES]
    c.executemany(
        "INSERT INTO users (phone, pin, password, created_at) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] users           → {len(rows)} rows")


def _seed_accounts():
    """100 account numbers mapped to the PHONES list (one per user)."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    for i, phone in enumerate(PHONES):
        acc_num = f"ACC{str(i + 1).zfill(6)}"   # ACC000001 … ACC000100
        rows.append((acc_num, phone, _full_name(), "ACTIVE", _rand_date(365)))
    c.executemany(
        "INSERT INTO accounts (account_number, phone, full_name, status, created_at) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] accounts        → {len(rows)} rows")


def _seed_wallets():
    """100 wallets with realistic randomised balances."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM wallets").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    for p in PHONES:
        bal   = round(random.uniform(10.0, 2000.0), 2)
        ts    = _rand_date(30)
        rows.append((p, bal, ts, ts))
    c.executemany(
        "INSERT INTO wallets (phone, balance, created_at, updated_at) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] wallets         → {len(rows)} rows")


def _seed_transactions():
    """200 realistic money-transfer records."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] > 0:
        conn.close(); return

    tx_types   = ["SEND", "RECEIVE", "DEPOSIT", "WITHDRAWAL"]
    tx_statuses = ["SUCCESS", "SUCCESS", "SUCCESS", "FAILED", "PENDING"]
    rows = []
    for _ in range(200):
        sender   = random.choice(PHONES)
        receiver = random.choice([p for p in PHONES if p != sender])
        rows.append((
            sender,
            receiver,
            round(random.uniform(1.0, 500.0), 2),
            random.choice(tx_types),
            random.choice(tx_statuses),
            _ref(),
            _rand_date(90),
        ))
    c.executemany(
        "INSERT INTO transactions (sender, receiver, amount, type, status, reference, created_at) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] transactions    → {len(rows)} rows")


def _seed_otp_codes():
    """150 OTP records with mixed statuses."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM otp_codes").fetchone()[0] > 0:
        conn.close(); return

    otp_statuses = ["USED", "USED", "USED", "EXPIRED", "PENDING"]
    rows = []
    for _ in range(150):
        rows.append((
            random.choice(PHONES),
            str(random.randint(1000, 9999)),
            random.choice(otp_statuses),
            _rand_date(30),
        ))
    c.executemany(
        "INSERT INTO otp_codes (phone, code, status, created_at) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] otp_codes       → {len(rows)} rows")


def _seed_sessions():
    """120 USSD sessions with varied states and languages."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    for _ in range(120):
        ts = _rand_date(60)
        rows.append((
            _session_id(),
            random.choice(PHONES),
            random.choice(SESSION_STATES),
            random.choice(LANGS),
            "{}",
            random.randint(0, 1),
            random.randint(1, 5),
            str(random.randint(1, 4)),
            random.choice(SESSION_STATUSES),
            ts,
            ts,
        ))
    c.executemany(
        """INSERT INTO sessions
           (session_id, phone, state, lang, temp_data, authenticated,
            step, last_input, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] sessions        → {len(rows)} rows")


def _seed_ussd_logs():
    """300 USSD audit log entries."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM ussd_logs").fetchone()[0] > 0:
        conn.close(); return

    inputs    = ["", "1", "2", "3", "4", "1", "2", "0771234567", "100", "1234"]
    responses_pool = [
        "CON Main Menu:\n1. Wallet\n2. Support\n3. FAQ\n4. Account",
        "CON Wallet:\n1. Balance\n2. Send Money\n3. Mini Statement",
        "CON Enter recipient phone number:",
        "CON Enter amount to send:",
        "END Successfully sent 50.00 to +263771000002.",
        "END Your balance is 345.50",
        "CON Support:\n1. Create Ticket\n2. Track Ticket\n3. Request Callback",
        "END Ticket created. Your ID: TKT1A2B3C",
        "CON Enter your PIN:",
        "END Invalid PIN. Goodbye.",
    ]
    rows = []
    for _ in range(300):
        rows.append((
            _session_id(),
            random.choice(PHONES),
            random.choice(SERVICE_CODES),
            random.choice(NETWORK_CODES),
            random.choice(inputs),
            random.choice(SESSION_STATES),
            random.choice(responses_pool),
            random.choice(SESSION_STATUSES),
            _rand_date(60),
        ))
    c.executemany(
        """INSERT INTO ussd_logs
           (session_id, phone, service_code, network_code, input, state, response, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] ussd_logs       → {len(rows)} rows")


def _seed_issues():
    """120 support tickets with full SLA and agent assignment data."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM issues").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    for _ in range(120):
        created  = _rand_date(90)
        status   = random.choice(STATUSES_ISSUE)
        closed   = _rand_date(30) if status in ("RESOLVED", "CLOSED") else None
        sla_due  = _future_date(7)
        agent    = random.choice(AGENT_IDS)
        issue_txt = random.choice(ISSUES_TEXT)
        rows.append((
            _ticket_id(),
            random.choice(PHONES),
            issue_txt,
            issue_txt + " — detailed description provided by customer via USSD.",
            random.choice(ESC_TYPES),
            status,
            random.choice(PRIORITIES),
            random.choice(CATEGORIES),
            agent,
            random.choice(RESOLUTION_NOTES) if status in ("RESOLVED", "CLOSED") else None,
            sla_due,
            random.choice(SLA_STATUSES),
            created,
            created,
            closed,
        ))
    c.executemany(
        """INSERT INTO issues
           (ticket_id, phone, issue, description, escalation_type, status,
            priority, category, agent_id, resolution_notes, sla_due, sla_status,
            created_at, updated_at, closed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] issues          → {len(rows)} rows")


def _seed_callbacks():
    """110 callback requests with agent assignments."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM callbacks").fetchone()[0] > 0:
        conn.close(); return

    cb_statuses = ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    cb_notes    = [
        "Customer available after 14:00.",
        "Tried calling twice – no answer.",
        "Callback completed. Issue resolved.",
        "Customer requested reschedule.",
        "Transferred to supervisor.",
        "Will retry tomorrow morning.",
        None,
    ]
    rows = []
    for _ in range(110):
        ts = _rand_date(60)
        rows.append((
            random.choice(PHONES),
            random.choice(cb_statuses),
            random.choice(AGENT_IDS),
            random.choice(cb_notes),
            ts,
            ts,
        ))
    c.executemany(
        "INSERT INTO callbacks (phone, status, agent_id, notes, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] callbacks       → {len(rows)} rows")


def _seed_tasks():
    """100 agent tasks spread across all agents."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    for i in range(100):
        title = TASK_TITLES[i % len(TASK_TITLES)]
        rows.append((
            random.choice(AGENT_IDS),
            title,
            f"{title} — assigned as part of weekly queue management.",
            random.choice(TASK_STATUSES),
            _future_date(30),
            _rand_date(60),
        ))
    c.executemany(
        "INSERT INTO tasks (agent_id, title, description, status, due_date, created_at) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] tasks           → {len(rows)} rows")


def _seed_notifications():
    """200 notification records across SMS and PUSH channels."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    for _ in range(200):
        phone   = random.choice(PHONES)
        status  = random.choice(NOTIF_STATUSES)
        sent_at = _rand_date(30) if status == "SENT" else None
        # Fill template placeholders with dummy values
        msg = random.choice(NOTIF_MESSAGES).format(
            otp=str(random.randint(1000, 9999)),
            bal=f"{random.uniform(10, 500):.2f}",
            amt=f"{random.uniform(1, 300):.2f}",
            phone=random.choice(PHONES),
            tid=_ticket_id(),
        )
        rows.append((
            phone,
            msg,
            random.choice(NOTIF_CHANNELS),
            status,
            _rand_date(30),
            sent_at,
        ))
    c.executemany(
        "INSERT INTO notifications (phone, message, channel, status, created_at, sent_at) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] notifications   → {len(rows)} rows")


def _seed_kpi_snapshots():
    """100 daily KPI snapshots covering ~3 months."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM kpi_snapshots").fetchone()[0] > 0:
        conn.close(); return

    rows = []
    base = datetime.now() - timedelta(days=100)
    for i in range(100):
        day      = base + timedelta(days=i)
        total    = random.randint(80, 220)
        resolved = random.randint(int(total * 0.5), int(total * 0.9))
        pending  = total - resolved
        rows.append((
            day.strftime("%Y-%m-%d"),
            total,
            resolved,
            pending,
            random.randint(20, 100),
            round(random.uniform(1.5, 5.0), 2),
            round(random.uniform(0.01, 0.10), 4),
            day.strftime("%Y-%m-%d %H:%M:%S"),
        ))
    c.executemany(
        """INSERT INTO kpi_snapshots
           (snapshot_date, total, resolved, pending, calls, avg_sla, churn_rate, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit(); conn.close()
    print(f"[seed] kpi_snapshots   → {len(rows)} rows")


def _seed_faqs():
    """42 FAQs across 3 languages and 5 categories (14 per language)."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM faqs").fetchone()[0] > 0:
        conn.close(); return

    faqs = [
        # ── English ──────────────────────────────────────────────────────────
        ("How do I check my balance?",                "Dial *123#, select Wallet > Balance.", "WALLET", "en"),
        ("How do I send money?",                      "Dial *123#, select Wallet > Send Money and follow the prompts.", "WALLET", "en"),
        ("What is the minimum transfer amount?",      "The minimum transfer is $0.50.", "WALLET", "en"),
        ("What is the maximum transfer amount?",      "The maximum single transfer is $500.00.", "WALLET", "en"),
        ("How do I view my mini statement?",          "Dial *123#, select Wallet > Mini Statement.", "WALLET", "en"),
        ("How do I change my PIN?",                   "Dial *123#, select Account > Change PIN.", "ACCOUNT", "en"),
        ("What do I do if I forget my PIN?",          "Choose 'Use OTP' at login to authenticate with a one-time password.", "ACCOUNT", "en"),
        ("How do I request an OTP?",                  "Dial *123#, select Account > Request OTP.", "ACCOUNT", "en"),
        ("How long is an OTP valid?",                 "OTPs are valid for 5 minutes only.", "ACCOUNT", "en"),
        ("How do I log a support ticket?",            "Dial *123#, select Support > Create Ticket and describe your issue.", "SUPPORT", "en"),
        ("How do I track my support ticket?",         "Dial *123#, select Support > Track Ticket and enter your ticket ID.", "SUPPORT", "en"),
        ("How do I request a callback?",              "Dial *123#, select Support > Request Callback.", "SUPPORT", "en"),
        ("What are your support operating hours?",    "Support agents are available Monday–Friday, 08:00–17:00 CAT.", "GENERAL", "en"),
        ("How do I change my display language?",      "After login, select your preferred language from the language menu.", "GENERAL", "en"),

        # ── Ndebele ──────────────────────────────────────────────────────────
        ("Ngibona kanjani ibhalansi yami?",           "Shayela *123#, khetha I-Wallet > Ibhalansi.", "WALLET", "nd"),
        ("Ngithunela kanjani imali?",                 "Shayela *123#, khetha I-Wallet > Thumela Imali.", "WALLET", "nd"),
        ("Yimalini imali encane yokudlulisela?",      "Imali encane yokudlulisela i-$0.50.", "WALLET", "nd"),
        ("Yimalini imali enkulu yokudlulisela?",      "Imali enkulu yokudlulisela i-$500.00 ngesendlalelo esisodwa.", "WALLET", "nd"),
        ("Ngibona kanjani umlando wami omfushane?",   "Shayela *123#, khetha I-Wallet > Umlando.", "WALLET", "nd"),
        ("Ngishintsha kanjani i-PIN yami?",           "Shayela *123#, khetha I-Akhawunti > Shintsha i-PIN.", "ACCOUNT", "nd"),
        ("Ngenzani uma ngilibele i-PIN yami?",        "Khetha 'Sebenzisa OTP' ekufikeni ukuze ungene nge-OTP.", "ACCOUNT", "nd"),
        ("Ngicela kanjani i-OTP?",                    "Shayela *123#, khetha I-Akhawunti > Cela i-OTP.", "ACCOUNT", "nd"),
        ("I-OTP ihlala isikhathi esingakanani?",      "Ama-OTP ahlala imizuzu emi-5 kuphela.", "ACCOUNT", "nd"),
        ("Ngidala kanjani ithikithi losizo?",         "Shayela *123#, khetha Usizo > Dala Ithikithi.", "SUPPORT", "nd"),
        ("Ngilandelela kanjani ithikithi lami?",      "Shayela *123#, khetha Usizo > Landelela Ithikithi.", "SUPPORT", "nd"),
        ("Ngicela kanjani ukubizwa?",                 "Shayela *123#, khetha Usizo > Cela Ukubizwa.", "SUPPORT", "nd"),
        ("Likhona nini usizo?",                       "Abasebenzi bosizo bayatholakala Mso.–Jol., 08:00–17:00 CAT.", "GENERAL", "nd"),
        ("Ngishintsha kanjani ulimi lwami?",          "Ngemuva kokungena, khetha ulimi lwakho kusuka kumenyu yolimi.", "GENERAL", "nd"),

        # ── Shona ────────────────────────────────────────────────────────────
        ("Ndinoona sei mari yangu?",                  "Daiira *123#, sarudza Wallet > Balance.", "WALLET", "sn"),
        ("Ndinotumira sei mari?",                     "Daiira *123#, sarudza Wallet > Tumira Mari.", "WALLET", "sn"),
        ("Chii chinongedza mari yekutumira?",         "Mari yekungedza kutumira i-$0.50.", "WALLET", "sn"),
        ("Chii chinopamidzira mari yekutumira?",      "Mari inopamidzirwa kutumira i-$500.00 pachinhu chimwe.", "WALLET", "sn"),
        ("Ndinoona sei nhoroondo yangu pfupi?",       "Daiira *123#, sarudza Wallet > Nhoroondo.", "WALLET", "sn"),
        ("Ndinochinja sei PIN yangu?",                "Daiira *123#, sarudza Account > Chinja PIN.", "ACCOUNT", "sn"),
        ("Ndinoitei kana ndakanganwa PIN yangu?",     "Sarudza 'Shandisa OTP' pakupinda kuti upinde ne-OTP.", "ACCOUNT", "sn"),
        ("Ndinokumbira sei OTP?",                     "Daiira *123#, sarudza Account > Kumbira OTP.", "ACCOUNT", "sn"),
        ("OTP inogarira nguva yakareba sei?",         "OTP inoshanda kwemaminitsi mashanu chete.", "ACCOUNT", "sn"),
        ("Ndinogadzira sei ticket yekubatsirwa?",     "Daiira *123#, sarudza Rubatsiro > Gadzira Ticket.", "SUPPORT", "sn"),
        ("Ndinotarisa sei ticket yangu?",             "Daiira *123#, sarudza Rubatsiro > Tarisa Ticket.", "SUPPORT", "sn"),
        ("Ndinokumbira sei callback?",                "Daiira *123#, sarudza Rubatsiro > Kumbira Callback.", "SUPPORT", "sn"),
        ("Rubatsiro runowanikwa nguva dzipi?",        "Vatariri verubatsiro vanowanikwa Mvuri–Chishanu, 08:00–17:00 CAT.", "GENERAL", "sn"),
        ("Ndinochinja sei mutauro wangu?",            "Mushure mekupinda, sarudza mutauro wako kubva pamenyu yemutauro.", "GENERAL", "sn"),
    ]
    c.executemany(
        "INSERT INTO faqs (question, answer, category, lang) VALUES (?,?,?,?)",
        faqs,
    )
    conn.commit(); conn.close()
    print(f"[seed] faqs            → {len(faqs)} rows")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_add_column(cursor, table: str, column: str, definition: str):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except sqlite3.OperationalError:
        pass


# ---------------------------------------------------------------------------
# Standalone runner  →  python db.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    migrate_db()