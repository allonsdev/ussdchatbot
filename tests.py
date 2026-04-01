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