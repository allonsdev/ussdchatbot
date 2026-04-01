"""
db.py
-----
Single source of truth for:
  • SQLite connection factory
  • Table creation   (init_db)
  • Schema migration (migrate_db)
  • Seed data        (_seed_*)

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

DB_PATH = "support.db"


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """
    Return a new SQLite connection.
    - row_factory=sqlite3.Row  → access columns by name
    - WAL journal mode         → safe concurrent reads during writes
    - foreign_keys=ON          → enforce FK constraints
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# init_db  –  create every table (safe to call on every startup)
# ---------------------------------------------------------------------------

def init_db():
    """Create all application tables if they do not already exist."""
    conn = get_db()
    c = conn.cursor()

    print("[db] Initialising tables …")

    # ── AGENTS ──────────────────────────────────────────────────────────────
    # Support-desk staff who handle tickets in the admin portal.
    c.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id    TEXT PRIMARY KEY,
            password    TEXT NOT NULL,
            full_name   TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'agent',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── USERS ───────────────────────────────────────────────────────────────
    # USSD end-users.
    # `pin`      – 4-digit USSD authentication PIN
    # `password` – reserved for future web / app login
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            phone       TEXT PRIMARY KEY,
            pin         TEXT,
            password    TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── WALLETS ─────────────────────────────────────────────────────────────
    # One wallet row per phone.  New rows are seeded with 100 units.
    c.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            phone       TEXT PRIMARY KEY,
            balance     REAL NOT NULL DEFAULT 100,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── TRANSACTIONS ────────────────────────────────────────────────────────
    # Full money-movement audit log.
    # type    : SEND | RECEIVE | DEPOSIT | WITHDRAWAL
    # status  : SUCCESS | FAILED | PENDING
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

    # ── OTP CODES ───────────────────────────────────────────────────────────
    # 4-digit one-time passwords sent via AfricasTalking SMS API.
    # status : PENDING | USED | EXPIRED
    c.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT NOT NULL,
            code        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'PENDING',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── USSD SESSIONS (state machine) ───────────────────────────────────────
    # One row per live AfricasTalking USSD session.
    # state     : current state string  (e.g. WALLET_SEND_RECIPIENT)
    # lang      : chosen language code  (en | nd | sn)
    # temp_data : JSON blob for multi-step flow data (recipient, amount …)
    # step      : legacy numeric step counter (kept for compatibility)
    # status    : ACTIVE | ENDED | TIMEOUT
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

    # ── USSD ANALYTICS / AUDIT LOG ──────────────────────────────────────────
    # Append-only log of every USSD exchange.
    # Mirrors the AfricasTalking POST fields so dashboards can correlate.
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

    # ── ISSUES / SUPPORT TICKETS ─────────────────────────────────────────────
    # Full-featured ticket with SLA tracking and agent assignment.
    # escalation_type : NONE | TIER2 | MANAGEMENT
    # sla_status      : ON_TRACK | BREACHED | RESOLVED
    # priority        : LOW | MEDIUM | HIGH | CRITICAL
    # category        : WALLET | ACCOUNT | TECHNICAL | BILLING | OTHER
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

    # ── CALLBACKS ────────────────────────────────────────────────────────────
    # Customer requests for an agent to call them back.
    # status : PENDING | IN_PROGRESS | COMPLETED | CANCELLED
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

    # ── TASKS ────────────────────────────────────────────────────────────────
    # Internal tasks assigned to agents via the admin portal.
    # status : OPEN | IN_PROGRESS | DONE | CANCELLED
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

    # ── NOTIFICATIONS ────────────────────────────────────────────────────────
    # Outbound messages queued for AfricasTalking SMS / push delivery.
    # channel : SMS | PUSH | EMAIL
    # status  : QUEUED | SENT | FAILED
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

    # ── KPI SNAPSHOTS ────────────────────────────────────────────────────────
    # Daily/hourly snapshots for the analytics dashboard.
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

    # ── FAQS ─────────────────────────────────────────────────────────────────
    # Shown in the USSD FAQ menu and used as chatbot fallback answers.
    # lang     : en | nd | sn
    # category : WALLET | ACCOUNT | SUPPORT | GENERAL
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

    # Seed all reference / demo data
    _seed_agents()
    _seed_users()
    _seed_wallets()
    _seed_faqs()
    _seed_tasks()
    _seed_kpi_snapshots()

    print("[db] ✅ All tables initialised and seeded.")


# ---------------------------------------------------------------------------
# migrate_db  –  safe incremental schema changes
# ---------------------------------------------------------------------------

def migrate_db():
    """
    Apply incremental column / table additions without touching existing data.
    Add new _safe_add_column() calls here whenever the schema evolves.
    """
    conn = get_db()
    c = conn.cursor()

    print("[db] Running migrations …")

    # sessions
    _safe_add_column(c, "sessions", "state",          "TEXT NOT NULL DEFAULT 'START'")
    _safe_add_column(c, "sessions", "lang",            "TEXT NOT NULL DEFAULT 'en'")
    _safe_add_column(c, "sessions", "temp_data",       "TEXT NOT NULL DEFAULT '{}'")
    _safe_add_column(c, "sessions", "step",            "INTEGER NOT NULL DEFAULT 0")
    _safe_add_column(c, "sessions", "last_input",      "TEXT")
    _safe_add_column(c, "sessions", "status",          "TEXT NOT NULL DEFAULT 'ACTIVE'")
    _safe_add_column(c, "sessions", "updated_at",      "TEXT DEFAULT CURRENT_TIMESTAMP")

    # otp_codes
    _safe_add_column(c, "otp_codes", "status",         "TEXT NOT NULL DEFAULT 'PENDING'")
    _safe_add_column(c, "otp_codes", "created_at",     "TEXT DEFAULT CURRENT_TIMESTAMP")

    # users
    _safe_add_column(c, "users", "password",           "TEXT")
    _safe_add_column(c, "users", "created_at",         "TEXT DEFAULT CURRENT_TIMESTAMP")

    # wallets
    _safe_add_column(c, "wallets", "created_at",       "TEXT DEFAULT CURRENT_TIMESTAMP")
    _safe_add_column(c, "wallets", "updated_at",       "TEXT DEFAULT CURRENT_TIMESTAMP")

    # transactions
    _safe_add_column(c, "transactions", "receiver",    "TEXT")
    _safe_add_column(c, "transactions", "reference",   "TEXT")
    _safe_add_column(c, "transactions", "type",        "TEXT NOT NULL DEFAULT 'SEND'")
    _safe_add_column(c, "transactions", "status",      "TEXT NOT NULL DEFAULT 'SUCCESS'")

    # issues
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

    # callbacks
    _safe_add_column(c, "callbacks", "agent_id",       "TEXT")
    _safe_add_column(c, "callbacks", "notes",          "TEXT")
    _safe_add_column(c, "callbacks", "updated_at",     "TEXT DEFAULT CURRENT_TIMESTAMP")

    # agents
    _safe_add_column(c, "agents", "created_at",        "TEXT DEFAULT CURRENT_TIMESTAMP")

    # faqs
    _safe_add_column(c, "faqs", "category",            "TEXT NOT NULL DEFAULT 'GENERAL'")
    _safe_add_column(c, "faqs", "lang",                "TEXT NOT NULL DEFAULT 'en'")
    _safe_add_column(c, "faqs", "created_at",          "TEXT DEFAULT CURRENT_TIMESTAMP")

    # notifications
    _safe_add_column(c, "notifications", "channel",    "TEXT NOT NULL DEFAULT 'SMS'")
    _safe_add_column(c, "notifications", "sent_at",    "TEXT")

    # Ensure ussd_logs exists (created by older init_db as ussd_sessions – recreate correctly)
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
    # ussd_logs extras
    _safe_add_column(c, "ussd_logs", "service_code",   "TEXT")
    _safe_add_column(c, "ussd_logs", "network_code",   "TEXT")
    _safe_add_column(c, "ussd_logs", "state",          "TEXT")
    _safe_add_column(c, "ussd_logs", "response",       "TEXT")

    conn.commit()
    conn.close()
    print("[db] ✅ Migration complete.")


# ---------------------------------------------------------------------------
# Seed functions  –  each is idempotent (skips if rows already exist)
# ---------------------------------------------------------------------------

def _seed_agents():
    """Seed demo support agents."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO agents (agent_id, password, full_name, role) VALUES (?, ?, ?, ?)",
            [
                ("AGT001", "pass1234",  "Thembi Dube",    "admin"),
                ("AGT002", "pass1234",  "Rudo Moyo",      "agent"),
                ("AGT003", "pass1234",  "Sipho Ncube",    "agent"),
                ("AGT004", "pass1234",  "Chiedza Mutasa", "supervisor"),
            ],
        )
        conn.commit()
        print("[seed] agents ✓")
    conn.close()


def _seed_users():
    """Seed demo USSD users with known PINs."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO users (phone, pin) VALUES (?, ?)",
            [
                ("+263771000001", "1234"),
                ("+263771000002", "5678"),
                ("+263771000003", "0000"),
                ("+27707317823",  "1111"),   # dev / test number
            ],
        )
        conn.commit()
        print("[seed] users ✓")
    conn.close()


def _seed_wallets():
    """Seed wallets for demo users with starting balances."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM wallets").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO wallets (phone, balance) VALUES (?, ?)",
            [
                ("+263771000001", 500.00),
                ("+263771000002", 250.00),
                ("+263771000003", 100.00),
                ("+27707317823",  999.00),
            ],
        )
        conn.commit()
        print("[seed] wallets ✓")
    conn.close()


def _seed_faqs():
    """Seed FAQ entries in all three supported languages."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM faqs").fetchone()[0] == 0:
        faqs = [
            # ── English ────────────────────────────────────────────────────
            ("How do I check my balance?",
             "Dial *123#, select Wallet > Balance.",
             "WALLET", "en"),
            ("How do I send money?",
             "Dial *123#, select Wallet > Send Money and follow the prompts.",
             "WALLET", "en"),
            ("How do I change my PIN?",
             "Dial *123#, select Account > Change PIN.",
             "ACCOUNT", "en"),
            ("What do I do if I forget my PIN?",
             "Choose 'Use OTP' at login to authenticate with a one-time password.",
             "ACCOUNT", "en"),
            ("How do I log a support ticket?",
             "Dial *123#, select Support > Create Ticket and describe your issue.",
             "SUPPORT", "en"),
            ("How do I track my ticket?",
             "Dial *123#, select Support > Track Ticket and enter your ticket ID.",
             "SUPPORT", "en"),
            # ── Ndebele ────────────────────────────────────────────────────
            ("Ngibona kanjani ibhalansi yami?",
             "Shayela *123#, khetha I-Wallet > Ibhalansi.",
             "WALLET", "nd"),
            ("Ngithunela kanjani imali?",
             "Shayela *123#, khetha I-Wallet > Thumela Imali.",
             "WALLET", "nd"),
            ("Ngishintsha kanjani i-PIN yami?",
             "Shayela *123#, khetha I-Akhawunti > Shintsha i-PIN.",
             "ACCOUNT", "nd"),
            ("Ngidala kanjani ithikithi losizo?",
             "Shayela *123#, khetha Usizo > Dala Ithikithi.",
             "SUPPORT", "nd"),
            # ── Shona ──────────────────────────────────────────────────────
            ("Ndinoona sei mari yangu?",
             "Daiira *123#, sarudza Wallet > Balance.",
             "WALLET", "sn"),
            ("Ndinotumira sei mari?",
             "Daiira *123#, sarudza Wallet > Tumira Mari.",
             "WALLET", "sn"),
            ("Ndinochinja sei PIN yangu?",
             "Daiira *123#, sarudza Account > Chinja PIN.",
             "ACCOUNT", "sn"),
            ("Ndinogadzira sei ticket yekubatsirwa?",
             "Daiira *123#, sarudza Rubatsiro > Gadzira Ticket.",
             "SUPPORT", "sn"),
        ]
        c.executemany(
            "INSERT INTO faqs (question, answer, category, lang) VALUES (?, ?, ?, ?)",
            faqs,
        )
        conn.commit()
        print("[seed] faqs ✓")
    conn.close()


def _seed_tasks():
    """Seed demo agent tasks."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
        c.executemany(
            """INSERT INTO tasks (agent_id, title, description, status, due_date)
               VALUES (?, ?, ?, ?, ?)""",
            [
                ("AGT002", "Follow up on ticket TKT001",
                 "Customer reported wallet not updating after transfer.", "OPEN", "2026-03-30"),
                ("AGT003", "Call back +263771000002",
                 "Customer requested callback regarding PIN reset.", "IN_PROGRESS", "2026-03-29"),
                ("AGT002", "Escalate billing complaint",
                 "Customer charged twice for same transaction.", "OPEN", "2026-03-31"),
                ("AGT004", "Review SLA report for March",
                 "Prepare monthly SLA compliance summary.", "OPEN", "2026-03-28"),
            ],
        )
        conn.commit()
        print("[seed] tasks ✓")
    conn.close()


def _seed_kpi_snapshots():
    """Seed a week of sample KPI data for the analytics dashboard."""
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM kpi_snapshots").fetchone()[0] == 0:
        snapshots = [
            ("2026-03-21", 120, 95,  25, 40, 3.2, 0.05),
            ("2026-03-22", 135, 110, 25, 55, 2.9, 0.04),
            ("2026-03-23", 98,  80,  18, 30, 3.5, 0.06),
            ("2026-03-24", 145, 120, 25, 60, 2.7, 0.03),
            ("2026-03-25", 160, 130, 30, 70, 3.0, 0.04),
            ("2026-03-26", 172, 140, 32, 75, 2.8, 0.03),
            ("2026-03-27", 180, 155, 25, 80, 2.5, 0.02),
        ]
        c.executemany(
            """INSERT INTO kpi_snapshots
               (snapshot_date, total, resolved, pending, calls, avg_sla, churn_rate)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            snapshots,
        )
        conn.commit()
        print("[seed] kpi_snapshots ✓")
    conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_add_column(cursor, table: str, column: str, definition: str):
    """Add a column only if it does not already exist. Silently skips if present."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except sqlite3.OperationalError:
        pass  # column already exists – fine


# ---------------------------------------------------------------------------
# Standalone runner  →  python db.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    migrate_db()