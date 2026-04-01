import sqlite3

DB = "support.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print("🛠️ Initializing database...")

    # ----------------------------
    # AGENTS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY,
        password TEXT,
        full_name TEXT,
        role TEXT
    )
    """)

    # ----------------------------
    # USERS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY,
        pin TEXT,
        password TEXT,
        created_at TIMESTAMP
    )
    """)

    # ----------------------------
    # WALLETS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        phone TEXT PRIMARY KEY,
        balance REAL DEFAULT 0
    )
    """)

    # ----------------------------
    # TRANSACTIONS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        amount REAL,
        type TEXT,
        status TEXT,
        created_at TIMESTAMP
    )
    """)

    # ----------------------------
    # OTP CODES
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        code TEXT,
        status TEXT,
        created_at TIMESTAMP
    )
    """)

    # ----------------------------
    # USSD FLOW SESSIONS (STATE)
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        phone TEXT,
        authenticated INTEGER DEFAULT 0,
        step INTEGER DEFAULT 0,
        last_input TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ----------------------------
    # USSD ANALYTICS SESSIONS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS ussd_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        phone TEXT,
        status TEXT,
        last_input TEXT,
        step INTEGER,
        created_at TIMESTAMP
    )
    """)

    # ----------------------------
    # ISSUES / TICKETS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT UNIQUE,
        phone TEXT,
        issue TEXT,
        escalation_type TEXT,
        status TEXT,
        created_at TIMESTAMP,
        agent_id TEXT,
        resolution_notes TEXT,
        closed_at TIMESTAMP,
        priority TEXT,
        category TEXT,
        sla_due TIMESTAMP,
        sla_status TEXT
    )
    """)

    # ----------------------------
    # CALLBACKS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS callbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        status TEXT,
        created_at TIMESTAMP
    )
    """)

    # ----------------------------
    # TASKS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT,
        title TEXT,
        description TEXT,
        status TEXT,
        due_date TIMESTAMP
    )
    """)

    # ----------------------------
    # NOTIFICATIONS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT,
        status TEXT,
        created_at TIMESTAMP
    )
    """)

    # ----------------------------
    # KPI SNAPSHOTS
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS kpi_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TIMESTAMP,
        total INTEGER,
        resolved INTEGER,
        pending INTEGER,
        calls INTEGER,
        avg_sla REAL,
        churn_rate REAL
    )
    """)

    # ----------------------------
    # FAQS (CHATBOT FALLBACK)
    # ----------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT
    )
    """)

    conn.commit()
    conn.close()

    print("✅ Database initialized successfully!")


if __name__ == "__main__":
    init_db()
    import sqlite3

DB = "support.db"

def migrate_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print("🛠️ Running database migration...")

    # --------------------------
    # SESSIONS (ADD NEW FIELDS)
    # --------------------------
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN lang TEXT DEFAULT 'en'")
    except:
        pass

    try:
        c.execute("ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'STARTED'")
    except:
        pass

    try:
        c.execute("ALTER TABLE sessions ADD COLUMN authenticated INTEGER DEFAULT 0")
    except:
        pass

    try:
        c.execute("ALTER TABLE sessions ADD COLUMN step INTEGER DEFAULT 0")
    except:
        pass

    # --------------------------
    # OTP CODES (FIX + SAFETY)
    # --------------------------
    try:
        c.execute("ALTER TABLE otp_codes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass

    try:
        c.execute("ALTER TABLE otp_codes ADD COLUMN status TEXT DEFAULT 'PENDING'")
    except:
        pass

    # --------------------------
    # USERS (ENSURE PIN FLOW SAFE)
    # --------------------------
    try:
        c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
    except:
        pass

    # --------------------------
    # WALLETS (SAFE INIT DEFAULT)
    # --------------------------
    try:
        c.execute("ALTER TABLE wallets ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass

    # --------------------------
    # TRANSACTIONS (IMPROVE TRACKING)
    # --------------------------
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN receiver TEXT")
    except:
        pass

    try:
        c.execute("ALTER TABLE transactions ADD COLUMN reference TEXT")
    except:
        pass

    # --------------------------
    # ISSUES (YOU ALREADY GOOD BUT ENSURE CONSISTENCY)
    # --------------------------
    try:
        c.execute("ALTER TABLE issues ADD COLUMN updated_at TIMESTAMP")
    except:
        pass

    try:
        c.execute("ALTER TABLE issues ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass

    # --------------------------
    # CALLBACKS
    # --------------------------
    try:
        c.execute("ALTER TABLE callbacks ADD COLUMN status TEXT DEFAULT 'PENDING'")
    except:
        pass

    # --------------------------
    # USSD SESSIONS (OPTIONAL TRACKING TABLE)
    # --------------------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS ussd_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        phone TEXT,
        input TEXT,
        step TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print("✅ Migration completed successfully!")


if __name__ == "__main__":
    migrate_db()