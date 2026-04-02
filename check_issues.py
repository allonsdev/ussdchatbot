# LANGUAGES
# --------------------------
LANGUAGES = {
    "1": "en",
    "2": "nd",
    "3": "sn"
}

TEXT = {
    "welcome": {
        "en": "Welcome",
        "nd": "Siyakwamukela",
        "sn": "Tinokugamuchirai"
    },

    "main_menu": {
        "en": "1. Wallet\n2. Support\n3. FAQ\n4. Account",
        "nd": "1. Isikhwama\n2. Usizo\n3. FAQ\n4. I-Akhawunti",
        "sn": "1. Chikwama\n2. Rubatsiro\n3. FAQ\n4. Homwe"
    },

    "wallet": {
        "en": "1. Balance\n2. Send Money\n3. Mini Statement",
        "nd": "1. Ibhalansi\n2. Thumela Imali\n3. Umlando Omfushane",
        "sn": "1. Mari iripo\n2. Tumira Mari\n3. Nhoroondo Pfupi"
    },

    "support": {
        "en": "1. Create Ticket\n2. Track Ticket\n3. Request Callback",
        "nd": "1. Dala Ithikithi\n2. Landela Ithikithi\n3. Cela Ukubizwa",
        "sn": "1. Gadzira Tiketi\n2. Tevera Tiketi\n3. Kumbira Kufonerwa"
    },

    "balance": {
        "en": "Your balance is",
        "nd": "Ibhalansi yakho ngu",
        "sn": "Mari yako iri"
    },

    "insufficient": {
        "en": "Insufficient balance",
        "nd": "Imali ayanele",
        "sn": "Mari haina kukwana"
    },

    "sent": {
        "en": "Money sent",
        "nd": "Imali ithunyelwe",
        "sn": "Mari yatumirwa"
    },

    "enter_recipient": {
        "en": "Enter recipient number",
        "nd": "Faka inombolo yomamukeli",
        "sn": "Isa nhamba yemunhu"
    },

    "enter_amount": {
        "en": "Enter amount",
        "nd": "Faka inani lemali",
        "sn": "Isa huwandu hwemari"
    },

    "invalid": {
        "en": "Invalid input",
        "nd": "Okungavumelekile",
        "sn": "Zvisiri izvo"
    },

    "ticket_created": {
        "en": "Ticket created successfully",
        "nd": "Ithikithi lidaliwe ngempumelelo",
        "sn": "Tiketi ragadzirwa zvakanaka"
    },

    "enter_issue": {
        "en": "Describe your issue",
        "nd": "Chaza inkinga yakho",
        "sn": "Tsanangura dambudziko rako"
    },

    "enter_ticket": {
        "en": "Enter ticket ID",
        "nd": "Faka i-ID yethikithi",
        "sn": "Isa ID yetiketi"
    },

    "callback": {
        "en": "Callback requested",
        "nd": "Ukubizwa sekuceliwe",
        "sn": "Kufonerwa kwakumbirwa"
    },

    "otp_sent": {
        "en": "OTP sent successfully",
        "nd": "OTP ithunyelwe ngempumelelo",
        "sn": "OTP yatumirwa zvakanaka"
    },

    "otp_invalid": {
        "en": "Invalid OTP",
        "nd": "OTP ayilungile",
        "sn": "OTP haina kunaka"
    },

    "pin_updated": {
        "en": "PIN updated successfully",
        "nd": "I-PIN iguqulwe ngempumelelo",
        "sn": "PIN yashandurwa zvakanaka"
    },

    "enter_phone": {
        "en": "Enter phone number:",
        "nd": "Faka inombolo yocingo:",
        "sn": "Isa nhamba yefoni:"
    },

    "select_option": {
        "en": "Select option:\n1. Enter PIN\n2. Use OTP",
        "nd": "Khetha inketho:\n1. Faka i-PIN\n2. Sebenzisa i-OTP",
        "sn": "Sarudza:\n1. Isa PIN\n2. Shandisa OTP"
    },

    "enter_pin": {
        "en": "Enter your PIN",
        "nd": "Faka i-PIN yakho",
        "sn": "Isa PIN yako"
    },

    "enter_otp": {
        "en": "Enter OTP",
        "nd": "Faka i-OTP",
        "sn": "Isa OTP"
    },

    "invalid_pin": {
        "en": "Invalid PIN",
        "nd": "I-PIN ayilungile",
        "sn": "PIN haina kunaka"
    },

    "invalid_choice": {
        "en": "Invalid choice",
        "nd": "Ukhetho alulungile",
        "sn": "Sarudzo haina kunaka"
    },

    "session_error": {
        "en": "Session error. Please try again.",
        "nd": "Iphutha leseshini. Zama futhi.",
        "sn": "Session yakanganisika. Edzazve."
    }
}

def t(key, lang="en"):
    return TEXT.get(key, {}).get(lang, TEXT.get(key, {}).get("en", key))

# --------------------------
# DATABASE
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


import random

def generate_otp(phone):
    code = str(random.randint(1000, 9999))

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO otp_codes (phone, code, status)
        VALUES (?, ?, ?)
    """, (phone, code, "PENDING"))

    conn.commit()
    conn.close()
    
    
    send_booking_sms(
        "+27707317823",
        "Here is your OTP :" + str(code)
    )
    print("OTP:", code)

from datetime import datetime, timedelta

def verify_otp(phone, user_code):
    conn = get_db()
    c = conn.cursor()

    # get latest OTP only
    row = c.execute("""
        SELECT id, code, created_at
        FROM otp_codes
        WHERE phone=? AND status='PENDING'
        ORDER BY created_at DESC
        LIMIT 1
    """, (phone,)).fetchone()

    if not row:
        conn.close()
        return False

    otp_id, code, created_at = row

    # ✅ FIX: handle microseconds correctly
    created_time = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")

    # ⏱️ expiry (5 minutes)
    if datetime.now() - created_time > timedelta(minutes=5):
        conn.close()
        return False

    # ✅ check match
    if code == user_code:
        c.execute("""
            UPDATE otp_codes
            SET status='USED'
            WHERE id=?
        """, (otp_id,))

        conn.commit()
        conn.close()
        return True

    conn.close()
    return False
# --------------------------
# MENUS
# --------------------------
def language_menu():
    return "CON Choose Language:\n1. English\n2. Ndebele\n3. Shona"


def main_menu(lang):
    return f"CON {t('welcome', lang)}\n{t('main_menu', lang)}"


def wallet_menu(lang):
    return f"CON {t('wallet', lang)}"


def support_menu(lang):
    return f"CON {t('support', lang)}"


@app.route('/ussd', methods=['POST'])
def ussd():
    session_id = request.form.get('sessionId')
    phone = request.form.get('phoneNumber')
    text = request.form.get('text', '')

    steps = text.split('*')

    if text == "":
        return "CON Enter phone number:"

    if len(steps) == 1:
        phone_input = steps[0].strip()

        conn = get_db()

        conn.execute("""
            INSERT OR IGNORE INTO sessions (
                session_id, phone, authenticated, step, last_input, status, created_at
            )
            VALUES (?, ?, 0, 1, ?, ?, CURRENT_TIMESTAMP)
        """, (session_id, phone_input, phone_input, "STARTED"))

        conn.commit()
        conn.close()

        return "CON Select option:\n1. Enter PIN\n2. Use OTP"

    # --------------------------
    # STEP 2: SELECT OPTION
    # --------------------------
    if len(steps) == 2:
        choice = steps[1].strip()

        conn = get_db()

        if choice == "1":
            conn.execute("""
                UPDATE sessions
                SET status='PIN_SELECTED', step=2
                WHERE session_id=?
            """, (session_id,))
            conn.commit()
            conn.close()

            return "CON Enter your PIN"

        elif choice == "2":
            session = conn.execute(
                "SELECT phone FROM sessions WHERE session_id=?",
                (session_id,)
            ).fetchone()

            if not session:
                conn.close()
                return "END Session error"

            phone = session[0]

            generate_otp(phone)

            conn.execute("""
                UPDATE sessions
                SET status='OTP_SENT', step=2
                WHERE session_id=?
            """, (session_id,))
            conn.commit()
            conn.close()

            return "CON Enter the OTP sent to your phone"

        conn.close()
        return "CON Invalid choice\n1. Enter PIN\n2. Use OTP"

    # --------------------------
    # STEP 3: VERIFY PIN OR OTP
    # --------------------------
    if len(steps) == 3:
        user_input = steps[2].strip()

        conn = get_db()

        session = conn.execute(
            "SELECT phone, status FROM sessions WHERE session_id=?",
            (session_id,)
        ).fetchone()

        if not session:
            conn.close()
            return "END Session error"

        phone, status = session

        # -------------------------
        # PIN FLOW
        # -------------------------
        if status == "PIN_SELECTED":
            stored_row = conn.execute(
                "SELECT pin FROM users WHERE phone=?",
                (phone,)
            ).fetchone()

            if stored_row and stored_row[0] == user_input:
                conn.execute("""
                    UPDATE sessions
                    SET authenticated=1, status='AUTHENTICATED', step=3
                    WHERE session_id=?
                """, (session_id,))
                conn.commit()
                conn.close()

                return language_menu()

            conn.close()
            return "CON Invalid PIN"

        # -------------------------
        # OTP FLOW
        # -------------------------
        if status == "OTP_SENT":
            if verify_otp(phone, user_input):
                conn.execute("""
                    UPDATE sessions
                    SET authenticated=1, status='AUTHENTICATED', step=3
                    WHERE session_id=?
                """, (session_id,))
                conn.commit()
                conn.close()

                return language_menu()

            conn.close()
            return "CON Invalid OTP"

        conn.close()
        return "END Invalid session state"


    
    # --------------------------
    lang = LANGUAGES.get(steps[0], "en") if len(steps) > 0 else "en"
        




    # --------------------------
    # MAIN MENU
    # --------------------------
    if len(steps) == 4:
        choice = steps[3]

        if choice == "1":
            return wallet_menu(lang)

        if choice == "2":
            return support_menu(lang)

        if choice == "3":
            faqs = get_db().cursor().execute(
                "SELECT id, question FROM faqs"
            ).fetchall()

            msg = "CON FAQs:\n"
            for f in faqs:
                msg += f"{f[0]}. {f[1]}\n"
            return msg

        if choice == "4":
            return "CON 1.Change PIN\n2.Request OTP\n3.Verify OTP"

    # --------------------------
    # WALLET
    # --------------------------
    if steps[3] == "1":

        if len(steps) == 5 and steps[4] == "1":
            return f"END {t('balance', lang)} {get_wallet(phone)}"

        if len(steps) == 5 and steps[4] == "2":
            return f"CON {t('enter_recipient', lang)}"

        if len(steps) == 6:
            return f"CON {t('enter_amount', lang)}"

        if len(steps) == 7:
            if transfer_money(phone, steps[5], float(steps[6])):
                return f"END {t('sent', lang)} {steps[6]}"
            return f"END {t('insufficient', lang)}"

    # --------------------------
    # SUPPORT
    # --------------------------
    if steps[3] == "2":

        if len(steps) == 5:
            return f"CON {t('support', lang)}:\n1.Create\n2.Track\n3.Live"

        if len(steps) == 6 and steps[5] == "1":
            return f"CON {t('enter_issue', lang)}"

        if len(steps) == 7 and steps[5] == "1":
            tid = str(uuid.uuid4())[:6]
            conn = get_db()
            conn.execute(
                "INSERT INTO issues VALUES (?, ?, ?, ?)",
                (tid, phone, steps[6], "OPEN")
            )
            conn.commit()
            conn.close()
            return f"END {t('ticket_created', lang)} {tid}"

        if len(steps) == 6 and steps[5] == "2":
            return f"CON {t('enter_ticket', lang)}"

        if len(steps) == 7 and steps[5] == "2":
            r = get_db().cursor().execute(
                "SELECT status FROM issues WHERE ticket_id=?",
                (steps[6],)
            ).fetchone()
            return f"END {r[0] if r else 'Not found'}"

        if len(steps) == 6 and steps[5] == "3":
            conn = get_db()
            conn.execute("INSERT INTO callbacks (phone) VALUES (?)", (phone,))
            conn.commit()
            conn.close()
            return f"END {t('callback', lang)}"

    # --------------------------
    # ACCOUNT
    # --------------------------
    if steps[3] == "4":

        if steps[4] == "1" and len(steps) == 5:
            return "CON Enter new PIN"

        if steps[4] == "1" and len(steps) == 6:
            conn = get_db()
            conn.execute(
                "INSERT OR REPLACE INTO users VALUES (?, ?)",
                (phone, steps[5])
            )
            conn.commit()
            conn.close()
            return f"END {t('pin_updated', lang)}"

        if steps[4] == "2":
            generate_otp(phone)
            return f"END {t('otp_sent', lang)}"

        if steps[4] == "3" and len(steps) == 5:
            return "CON Enter OTP"

        if steps[4] == "3" and len(steps) == 6:
            if verify_otp(phone, steps[5]):
                return "END OK"
            return f"END {t('otp_invalid', lang)}"

    return f"END {t('invalid', lang)}"

# RUN APP