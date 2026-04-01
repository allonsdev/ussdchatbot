def ussd():
    
    session_id = request.form.get('sessionId')
    phone = request.form.get('phoneNumber')
    print(phone)
    text = request.form.get('text', '')

    steps = text.split('*') if text else []

    conn = get_db()

    # --------------------------
    # GET SESSION
    # --------------------------
    session = conn.execute(
        "SELECT phone, authenticated, status FROM sessions WHERE session_id=?",
        (session_id,)
    ).fetchone()

    # --------------------------
    # CREATE SESSION IF NEW
    # --------------------------
    if not session:
        conn.execute("""
            INSERT INTO sessions (session_id, phone, authenticated, step, last_input, status)
            VALUES (?, ?, 0, 0, '', ?)
        """, (session_id, phone, STATE_START))
        conn.commit()

        return TEXT["enter_phone"]["en"]


    phone_db, auth, status = session

    # --------------------------
    # LANGUAGE (SAFE)
    # --------------------------
    lang = "en"
    if len(steps) >= 1:
        lang = LANGUAGES.get(steps[0], "en")


    # =========================================================
    # 1. START → AUTH METHOD
    # =========================================================
    if status == STATE_START:

        conn.execute("""
            UPDATE sessions SET status=?
            WHERE session_id=?
        """, (STATE_AUTH_METHOD, session_id))
        conn.commit()

        return TEXT["select_option"][lang]


    # =========================================================
    # 2. AUTH METHOD
    # =========================================================
    if status == STATE_AUTH_METHOD:

        if len(steps) < 2:
            return TEXT["select_option"][lang]

        choice = steps[1]

        # PIN FLOW
        if choice == "1":

            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_PIN, session_id))
            conn.commit()

            return TEXT["enter_pin"][lang]

        # OTP FLOW
        if choice == "2":

            generate_otp(phone_db)

            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_OTP, session_id))
            conn.commit()

            return TEXT["enter_otp"][lang]

        return TEXT["invalid_choice"][lang]


    # =========================================================
    # 3. PIN AUTH
    # =========================================================
    if status == STATE_PIN:

        if len(steps) < 3:
            return TEXT["enter_pin"][lang]

        pin = steps[2]

        stored = conn.execute(
            "SELECT pin FROM users WHERE phone=?",
            (phone_db,)
        ).fetchone()

        if stored and stored[0] == pin:

            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_AUTHENTICATED, session_id))
            conn.commit()

            return TEXT["main_menu"][lang]

        return TEXT["invalid_pin"][lang]


    # =========================================================
    # 4. OTP AUTH
    # =========================================================
    if status == STATE_OTP:

        if len(steps) < 3:
            return TEXT["enter_otp"][lang]

        otp = steps[2]

        if verify_otp(phone_db, otp):

            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_AUTHENTICATED, session_id))
            conn.commit()

            return TEXT["main_menu"][lang]

        return TEXT["otp_invalid"][lang]


    # =========================================================
    # 5. AUTHENTICATED → MAIN MENU
    # =========================================================
    if status == STATE_AUTHENTICATED:

        if len(steps) < 2:
            return TEXT["main_menu"][lang]

        choice = steps[1]

        # --------------------------
        # WALLET
        # --------------------------
        if choice == "1":

            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_WALLET, session_id))
            conn.commit()

            return TEXT["wallet"][lang]


        # --------------------------
        # SUPPORT
        # --------------------------
        if choice == "2":

            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_SUPPORT, session_id))
            conn.commit()

            return TEXT["support"][lang]


        # --------------------------
        # FAQ
        # --------------------------
        if choice == "3":

            faqs = conn.execute(
                "SELECT id, question FROM faqs"
            ).fetchall()

            msg = "CON FAQS:\n"
            for f in faqs:
                msg += f"{f[0]}. {f[1]}\n"

            return msg


        # --------------------------
        # ACCOUNT
        # --------------------------
        if choice == "4":
            conn.execute("""
                UPDATE sessions SET status=?
                WHERE session_id=?
            """, (STATE_ACCOUNT, session_id))
            conn.commit()

            return "CON 1.Change PIN\n2.Request OTP\n3.Verify OTP"


        return TEXT["invalid_choice"][lang]


    # =========================================================
    # 6. WALLET MODULE
    # =========================================================
    if status == STATE_WALLET:

        if len(steps) < 3:
            return TEXT["wallet"][lang]

        action = steps[2]

        # BALANCE
        if action == "1":
            return f"END {TEXT['balance'][lang]} {get_wallet(phone_db)}"

        # SEND MONEY
        if action == "2":

            if len(steps) == 3:
                return TEXT["enter_recipient"][lang]

            if len(steps) == 4:
                return TEXT["enter_amount"][lang]

            if len(steps) == 5:
                ok = transfer_money(phone_db, steps[3], float(steps[4]))

                if ok:
                    return f"END {TEXT['sent'][lang]}"
                return f"END {TEXT['insufficient'][lang]}"

        return TEXT["invalid"][lang]


    # =========================================================
    # 7. SUPPORT MODULE
    # =========================================================
    if status == STATE_SUPPORT:

        if len(steps) < 3:
            return TEXT["support"][lang]

        action = steps[2]

        # CREATE TICKET
        if action == "1":

            if len(steps) == 3:
                return TEXT["enter_issue"][lang]

            if len(steps) == 4:
                tid = str(uuid.uuid4())[:6]

                conn.execute(
                    "INSERT INTO issues VALUES (?, ?, ?, ?)",
                    (tid, phone_db, steps[3], "OPEN")
                )
                conn.commit()

                return f"END {TEXT['ticket_created'][lang]} {tid}"

        # TRACK TICKET
        if action == "2":

            if len(steps) == 3:
                return TEXT["enter_ticket"][lang]

            if len(steps) == 4:
                r = conn.execute(
                    "SELECT status FROM issues WHERE ticket_id=?",
                    (steps[3],)
                ).fetchone()

                return f"END {r[0] if r else 'Not found'}"

        # CALLBACK
        if action == "3":

            conn.execute(
                "INSERT INTO callbacks (phone) VALUES (?)",
                (phone_db,)
            )
            conn.commit()

            return f"END {TEXT['callback'][lang]}"


    # =========================================================
    # 8. ACCOUNT MODULE
    # =========================================================
    if status == STATE_ACCOUNT:

        if len(steps) < 3:
            return "CON 1.Change PIN\n2.Request OTP\n3.Verify OTP"

        action = steps[2]

        # CHANGE PIN
        if action == "1":

            if len(steps) == 3:
                return "CON Enter new PIN"

            if len(steps) == 4:
                conn.execute(
                    "INSERT OR REPLACE INTO users VALUES (?, ?)",
                    (phone_db, steps[3])
                )
                conn.commit()

                return f"END {TEXT['pin_updated'][lang]}"

        # REQUEST OTP
        if action == "2":
            generate_otp(phone_db)
            return f"END {TEXT['otp_sent'][lang]}"

        # VERIFY OTP
        if action == "3":

            if len(steps) == 3:
                return "CON Enter OTP"

            if len(steps) == 4:

                if verify_otp(phone_db, steps[3]):
                    return "END OK"

                return f"END {TEXT['otp_invalid'][lang]}"

curl -X POST https://api.africastalking.com/ussd \
-H "ApiKey: atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "sessionId=12345" \
-d "serviceCode=*123#" \
-d "phoneNumber=+27700000000" \
-d "text="