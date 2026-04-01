"""
texts.py
--------
All menu and system texts in multiple languages.
To add a new language: add its code to LANGUAGES and add translations to TEXT.
To add a new string:   add a key to TEXT with translations for each language.
"""

# Supported languages: code → locale tag
LANGUAGES = {
    "1": "en",   # English
    "2": "nd",   # Ndebele
    "3": "sn",   # Shona
}

TEXT: dict[str, dict[str, str]] = {

    # ── Auth / Login ───────────────────────────────────────────────────────
    "enter_phone": {
        "en": "Enter your phone or account number:",
        "nd": "Faka inombolo yocingo noma ye-akhawunti:",
        "sn": "Isa nhamba yefoni kana ye-account:",
    },
    "select_id_type": {
        "en": "Identify yourself via:\n1. Phone number\n2. Account number",
        "nd": "Ziveze nge:\n1. Inombolo yocingo\n2. Inombolo ye-akhawunti",
        "sn": "Zivonese ne:\n1. Nhamba yefoni\n2. Nhamba ye-account",
    },
    "enter_account": {
        "en": "Enter your account number:",
        "nd": "Faka inombolo ye-akhawunti yakho:",
        "sn": "Isa nhamba ye-account yako:",
    },
    "account_not_found": {
        "en": "Account not found. Please try again:",
        "nd": "I-akhawunti ayitholakali. Zama futhi:",
        "sn": "Account haisi kuwanikwa. Edza zvakare:",
    },
    "select_auth": {
        "en": "Login via:\n1. PIN\n2. OTP",
        "nd": "Ngena nge:\n1. PIN\n2. OTP",
        "sn": "Pinda ne:\n1. PIN\n2. OTP",
    },
    # ── OTP sub-menu (shown when user picks OTP at login) ─────────────────
    "select_otp_action": {
        "en": "OTP Options:\n1. Enter OTP\n2. Request call me back",
        "nd": "Izinketho ze-OTP:\n1. Faka i-OTP\n2. Thumela imenyu nge-SMS",
        "sn": "Sarudzo dzeOTP:\n1. Isa OTP\n2. Tumira menyu ne-SMS",
    },
    "menu_sent_via_sms": {
        "en": "Call me back sent.",
        "nd": "Imenyu ithunyelwe ocingweni lwakho nge-SMS. Bheka imilayezo yakho.",
        "sn": "Menyu yatumirwa kufoni yako ne-SMS. Tarisa meseji yako.",
    },
    # ──────────────────────────────────────────────────────────────────────
    "enter_pin": {
        "en": "Enter your PIN:",
        "nd": "Faka i-PIN yakho:",
        "sn": "Isa PIN yako:",
    },
    "enter_otp": {
        "en": "Enter the OTP sent to your phone:",
        "nd": "Faka i-OTP ethunyelwe:",
        "sn": "Isa OTP yatumirwa kufoni:",
    },
    "invalid_pin": {
        "en": "Invalid PIN. Try again:",
        "nd": "I-PIN ayilungile. Zama futhi:",
        "sn": "PIN haina kunaka. Edza zvakare:",
    },
    "invalid_otp": {
        "en": "Invalid or expired OTP. Try again:",
        "nd": "OTP ayilungile noma iphelelwe isikhathi:",
        "sn": "OTP haina kunaka kana yaguma nguva:",
    },
    "otp_sent": {
        "en": "OTP sent to your phone.",
        "nd": "OTP ithunyelwe ocingweni lwakho.",
        "sn": "OTP yatumirwa kufoni yako.",
    },

    # ── Language selection ─────────────────────────────────────────────────
    "choose_language": {
        "en": "Choose Language:\n1. English\n2. Ndebele\n3. Shona",
        "nd": "Khetha Ulimi:\n1. English\n2. Ndebele\n3. Shona",
        "sn": "Sarudza Mutauro:\n1. English\n2. Ndebele\n3. Shona",
    },

    # ── Main menu ──────────────────────────────────────────────────────────
    "welcome": {
        "en": "Welcome",
        "nd": "Siyakwamukela",
        "sn": "Tinokugamuchirai",
    },
    "main_menu": {
        "en": "Main Menu:\n1. Wallet\n2. Support\n3. FAQ\n4. Account",
        "nd": "Menyu Enkulu:\n1. I-Wallet\n2. Usizo\n3. FAQ\n4. I-Akhawunti",
        "sn": "Menyu Huru:\n1. Wallet\n2. Rubatsiro\n3. FAQ\n4. Account",
    },

    # ── Wallet ─────────────────────────────────────────────────────────────
    "wallet_menu": {
        "en": "Wallet:\n1. Balance\n2. Send Money\n3. Mini Statement",
        "nd": "I-Wallet:\n1. Ibhalansi\n2. Thumela Imali\n3. Umlando",
        "sn": "Wallet:\n1. Balance\n2. Tumira Mari\n3. Nhoroondo",
    },
    "balance": {
        "en": "Your balance is",
        "nd": "Imali yakho ngu",
        "sn": "Mari yako i",
    },
    "enter_recipient": {
        "en": "Enter recipient phone number:",
        "nd": "Faka inombolo yomamukeli:",
        "sn": "Isa nhamba yeanogamuchira:",
    },
    "enter_amount": {
        "en": "Enter amount to send:",
        "nd": "Faka inani elizotshalwa:",
        "sn": "Isa huwandu yekutumira:",
    },
    "confirm_send": {
        "en": "Send {amount} to {recipient}?\n1. Confirm\n2. Cancel",
        "nd": "Thumela {amount} ku {recipient}?\n1. Qinisekisa\n2. Khansela",
        "sn": "Tumira {amount} ku {recipient}?\n1. Simbisa\n2. Kanzura",
    },
    "sent": {
        "en": "Successfully sent {amount} to {recipient}.",
        "nd": "Kuthunyelwe {amount} ku {recipient}.",
        "sn": "Watumira {amount} ku {recipient}.",
    },
    "insufficient": {
        "en": "Insufficient balance. Transaction cancelled.",
        "nd": "Imali ayanele. Umsebenzi ukhansele.",
        "sn": "Mari haina kukwana. Shanduko yakanzurwa.",
    },
    "mini_statement": {
        "en": "Last {n} transactions:",
        "nd": "Imisebenzi yokugcina {n}:",
        "sn": "Zvakaitwa {n} zvakapfuura:",
    },
    "no_transactions": {
        "en": "No transactions found.",
        "nd": "Ayikho imisebenzi.",
        "sn": "Hapana zvakaitwa.",
    },

    # ── Support ────────────────────────────────────────────────────────────
    "support_menu": {
        "en": "Support:\n1. Create Ticket\n2. Track Ticket\n3. Request Callback",
        "nd": "Usizo:\n1. Dala Ithikithi\n2. Landelela\n3. Cela Ukubizwa",
        "sn": "Rubatsiro:\n1. Gadzira Ticket\n2. Tarisa Ticket\n3. Kumbira Callback",
    },
    "enter_issue": {
        "en": "Describe your issue:",
        "nd": "Chaza inkinga yakho:",
        "sn": "Tsanangura dambudziko rako:",
    },
    "ticket_created": {
        "en": "Ticket created. Your ID: {tid}",
        "nd": "Ithikithi lidaliwe. I-ID yakho: {tid}",
        "sn": "Ticket yagadzirwa. ID yako: {tid}",
    },
    "enter_ticket_id": {
        "en": "Enter your ticket ID:",
        "nd": "Faka i-ID yethikithi:",
        "sn": "Isa ticket ID yako:",
    },
    "ticket_status": {
        "en": "Ticket {tid} status: {status}",
        "nd": "Isimo sethikithi {tid}: {status}",
        "sn": "Mamiriro eticket {tid}: {status}",
    },
    "ticket_not_found": {
        "en": "Ticket not found.",
        "nd": "Ithikithi alitholakali.",
        "sn": "Ticket haisi kuwanikwa.",
    },
    "callback_requested": {
        "en": "Callback requested. We will call you shortly.",
        "nd": "I-call back iceliwe. Sizobuya sikubize.",
        "sn": "Callback yakumbirwa. Tichadana newe munguva pfupi.",
    },

    # ── Account ────────────────────────────────────────────────────────────
    "account_menu": {
        "en": "Account:\n1. Change PIN\n2. Request OTP\n3. Verify OTP",
        "nd": "I-Akhawunti:\n1. Shintsha i-PIN\n2. Cela i-OTP\n3. Qinisekisa i-OTP",
        "sn": "Account:\n1. Chinja PIN\n2. Kumbira OTP\n3. Simbisa OTP",
    },
    "enter_new_pin": {
        "en": "Enter new PIN (4 digits):",
        "nd": "Faka i-PIN entsha (izinhlamvu ezi-4):",
        "sn": "Isa PIN nyowani (nhamba 4):",
    },
    "pin_updated": {
        "en": "PIN updated successfully.",
        "nd": "I-PIN iguquliwe ngempumelelo.",
        "sn": "PIN yashandurwa zvakanaka.",
    },
    "otp_verified": {
        "en": "OTP verified successfully.",
        "nd": "I-OTP iqinisekisiwe ngempumelelo.",
        "sn": "OTP yasimbiswa zvakanaka.",
    },

    # ── FAQ ────────────────────────────────────────────────────────────────
    "faq_menu": {
        "en": "FAQs (select a number to read):",
        "nd": "Imibuzo Evame Ukubuzwa:",
        "sn": "Mibvunzo Inowanzoburwa:",
    },

    # ── Generic ────────────────────────────────────────────────────────────
    "invalid_input": {
        "en": "Invalid input. Please try again.",
        "nd": "Okungavumelekile. Zama futhi.",
        "sn": "Zvisiri izvo. Edza zvakare.",
    },
    "invalid_choice": {
        "en": "Invalid choice.",
        "nd": "Ukhetho alulungile.",
        "sn": "Sarudzo haina kunaka.",
    },
    "session_error": {
        "en": "Session error. Please dial again.",
        "nd": "Iphutha leseshini. Zama futhi.",
        "sn": "Session error. Edza zvakare.",
    },
    "cancelled": {
        "en": "Cancelled.",
        "nd": "Khukhanyiwe.",
        "sn": "Yakanzurwa.",
    },
    "goodbye": {
        "en": "Thank you. Goodbye!",
        "nd": "Siyabonga. Hamba kahle!",
        "sn": "Mazvita. Chisarai zvakanaka!",
    },
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    """
    Return localised text for *key* in *lang*, falling back to English.
    Supports Python str.format() placeholders via **kwargs.

    Example:
        t("sent", "en", amount="5.00", recipient="0771234567")
        → "Successfully sent 5.00 to 0771234567."
    """
    bucket = TEXT.get(key, {})
    text = bucket.get(lang) or bucket.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # return unformatted rather than crash
    return text