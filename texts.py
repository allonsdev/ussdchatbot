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

# ---------------------------------------------------------------------------
# Hardcoded FAQs in all three languages (no database needed)
# ---------------------------------------------------------------------------
FAQS = {
    "en": [
        {"id": 1, "question": "How do I check my balance?",        "answer": "Go to Wallet > Balance."},
        {"id": 2, "question": "How do I send money?",              "answer": "Go to Wallet > Send Money, enter the recipient and amount."},
        {"id": 3, "question": "How do I reset my PIN?",            "answer": "Go to Account > Change PIN and follow the prompts."},
        {"id": 4, "question": "What do I do if my OTP expires?",   "answer": "Go to Account > Request OTP to get a new one."},
        {"id": 5, "question": "How do I contact support?",         "answer": "Go to Support > Create Ticket or Request Callback."},
    ],
    "nd": [
        {"id": 1, "question": "Ngiyihlola kanjani ibhalansi yami?",           "answer": "Yiya ku Isikhwama > Ibhalansi."},
        {"id": 2, "question": "Ngithumela kanjani imali?",                    "answer": "Yiya ku Isikhwama > Thumela Imali, faka inombolo nomamukeli nenani."},
        {"id": 3, "question": "Ngishintsha kanjani inombolo yemfihlo yami?",  "answer": "Yiya ku I-Akhawunti > Shintsha Inombolo Yemfihlo ulandele imiyalelo."},
        {"id": 4, "question": "Ngenzeni uma inombolo yesikhathi sami iphelelwe?", "answer": "Yiya ku I-Akhawunti > Cela Inombolo Yesikhathi ukuthola entsha."},
        {"id": 5, "question": "Ngithintana kanjani nabo usizo?",              "answer": "Yiya ku Usizo > Dala Ithikithi noma Cela Ukubizwa."},
    ],
    "sn": [
        {"id": 1, "question": "Ndinoona sei mari iripo?",                     "answer": "Enda kuSigaba Semari > Mari Iripo."},
        {"id": 2, "question": "Ndinotumira sei mari?",                        "answer": "Enda kuSigaba Semari > Tumira Mari, isa nhamba yeanogamuchira nehuwandu."},
        {"id": 3, "question": "Ndinochinja sei nhamba yangu yechinyel'ano?",  "answer": "Enda kuHesapu > Chinja Nhamba Yechinyel'ano utevedze mirayiro."},
        {"id": 4, "question": "Ndinoitei kana nhamba yangu yenguva yaguma?",  "answer": "Enda kuHesapu > Kumbira Nhamba Yenguva kuti uwane imwe."},
        {"id": 5, "question": "Ndinosvika sei rubatsiro?",                    "answer": "Enda kuRubatsiro > Gadzira Tiketi kana Kumbira Kufonerwa."},
    ],
}


TEXT: dict[str, dict[str, str]] = {

    # ── Auth / Login ───────────────────────────────────────────────────────
    "enter_phone": {
        "en": "Enter your phone or account number:",
        "nd": "Faka inombolo yocingo noma ye-akhawunti:",
        "sn": "Isa nhamba yefoni kana yehesapu:",
    },
    "select_id_type": {
        "en": "Identify yourself via:\n1. Phone number\n2. Account number",
        "nd": "Ziveze nge:\n1. Inombolo yocingo\n2. Inombolo ye-akhawunti",
        "sn": "Zivonese ne:\n1. Nhamba yefoni\n2. Nhamba yehesapu",
    },
    "enter_account": {
        "en": "Enter your account number:",
        "nd": "Faka inombolo ye-akhawunti yakho:",
        "sn": "Isa nhamba yehesapu yako:",
    },
    "account_not_found": {
        "en": "Account not found. Please try again:",
        "nd": "I-akhawunti ayitholakali. Zama futhi:",
        "sn": "Hesapu haisi kuwanikwa. Edza zvakare:",
    },
    "select_auth": {
        "en": "Login via:\n1. PIN\n2. OTP",
        "nd": "Ngena nge:\n1. Inombolo Yemfihlo\n2. Inombolo Yesikhathi",
        "sn": "Pinda ne:\n1. Nhamba Yechinyel'ano\n2. Nhamba Yenguva",
    },
    # ── OTP sub-menu ──────────────────────────────────────────────────────
    "select_otp_action": {
        "en": "OTP Options:\n1. Enter OTP\n2. Request call me back",
        "nd": "Izinketho Zenombolo Yesikhathi:\n1. Faka Inombolo Yesikhathi\n2. Cela ukubizwa",
        "sn": "Sarudzo dzeNhamba Yenguva:\n1. Isa Nhamba Yenguva\n2. Kumbira kufonerwa",
    },
    "menu_sent_via_sms": {
        "en": "Call me back request sent.",
        "nd": "Isicelo sokubizwa sithunyelwe.",
        "sn": "Chikumbiro chekufonerwa chatumirwa.",
    },
    # ─────────────────────────────────────────────────────────────────────
    "enter_pin": {
        "en": "Enter your PIN:",
        "nd": "Faka Inombolo Yakho Yemfihlo:",
        "sn": "Isa Nhamba Yako Yechinyel'ano:",
    },
    "enter_otp": {
        "en": "Enter the OTP sent to your phone:",
        "nd": "Faka Inombolo Yesikhathi ethunyelwe ocingweni lwakho:",
        "sn": "Isa Nhamba Yenguva yatumirwa kufoni yako:",
    },
    "invalid_pin": {
        "en": "Invalid PIN. Try again:",
        "nd": "Inombolo Yemfihlo ayilungile. Zama futhi:",
        "sn": "Nhamba Yechinyel'ano haina kunaka. Edza zvakare:",
    },
    "invalid_otp": {
        "en": "Invalid or expired OTP. Try again:",
        "nd": "Inombolo Yesikhathi ayilungile noma iphelelwe. Zama futhi:",
        "sn": "Nhamba Yenguva haina kunaka kana yaguma. Edza zvakare:",
    },
    "otp_sent": {
        "en": "OTP sent to your phone.",
        "nd": "Inombolo Yesikhathi ithunyelwe ocingweni lwakho.",
        "sn": "Nhamba Yenguva yatumirwa kufoni yako.",
    },

    # ── Language selection ────────────────────────────────────────────────
    "choose_language": {
        "en": "Choose Language:\n1. English\n2. Ndebele\n3. Shona",
        "nd": "Khetha Ulimi:\n1. IsiNgisi\n2. IsiNdebele\n3. IsiShona",
        "sn": "Sarudza Mutauro:\n1. Chirungu\n2. Sindebele\n3. Chishona",
    },

    # ── Main menu — Wallet REMOVED ────────────────────────────────────────
    "welcome": {
        "en": "Welcome",
        "nd": "Siyakwamukela",
        "sn": "Tinokugamuchirai",
    },
    "main_menu": {
        "en": "Main Menu:\n1. Support\n2. FAQ\n3. Account",
        "nd": "Menyu Enkulu:\n1. Usizo\n2. Imibuzo Evamile\n3. I-Akhawunti",
        "sn": "Menyu Huru:\n1. Rubatsiro\n2. Mibvunzo Inowanzo\n3. Hesapu",
    },

    # ── Support ───────────────────────────────────────────────────────────
    "support_menu": {
        "en": "Support:\n1. Create Ticket\n2. Track Ticket\n3. Request Callback",
        "nd": "Usizo:\n1. Dala Ithikithi\n2. Landelela Ithikithi\n3. Cela Ukubizwa",
        "sn": "Rubatsiro:\n1. Gadzira Tiketi\n2. Tevera Tiketi\n3. Kumbira Kufonerwa",
    },
    "enter_issue": {
        "en": "Describe your issue:",
        "nd": "Chaza inkinga yakho:",
        "sn": "Tsanangura dambudziko rako:",
    },
    "ticket_created": {
        "en": "Ticket created. Your ID: {tid}",
        "nd": "Ithikithi lidaliwe. Inombolo yakho: {tid}",
        "sn": "Tiketi ragadzirwa. Nhamba yako: {tid}",
    },
    "enter_ticket_id": {
        "en": "Enter your ticket ID:",
        "nd": "Faka inombolo yethikithi:",
        "sn": "Isa nhamba yetiketi yako:",
    },
    "ticket_status": {
        "en": "Ticket {tid} status: {status}",
        "nd": "Isimo sethikithi {tid}: {status}",
        "sn": "Mamiriro etiketi {tid}: {status}",
    },
    "ticket_not_found": {
        "en": "Ticket not found.",
        "nd": "Ithikithi alitholakali.",
        "sn": "Tiketi haisi kuwanikwa.",
    },
    "callback_requested": {
        "en": "Callback requested. We will call you shortly.",
        "nd": "Isicelo sokubizwa samukelwe. Sizobuya sikubize.",
        "sn": "Chikumbiro chekufonerwa chagamuchirwa. Tichadana newe munguva pfupi.",
    },

    # ── Account ───────────────────────────────────────────────────────────
    "account_menu": {
        "en": "Account:\n1. Change PIN\n2. Request OTP\n3. Verify OTP",
        "nd": "I-Akhawunti:\n1. Shintsha Inombolo Yemfihlo\n2. Cela Inombolo Yesikhathi\n3. Qinisekisa Inombolo Yesikhathi",
        "sn": "Hesapu:\n1. Chinja Nhamba Yechinyel'ano\n2. Kumbira Nhamba Yenguva\n3. Simbisa Nhamba Yenguva",
    },
    "enter_new_pin": {
        "en": "Enter new PIN (4 digits):",
        "nd": "Faka Inombolo Entsha Yemfihlo (izinhlamvu ezi-4):",
        "sn": "Isa Nhamba Nyowani Yechinyel'ano (nhamba 4):",
    },
    "pin_updated": {
        "en": "PIN updated successfully.",
        "nd": "Inombolo Yemfihlo iguquliwe ngempumelelo.",
        "sn": "Nhamba Yechinyel'ano yashandurwa zvakanaka.",
    },
    "otp_verified": {
        "en": "OTP verified successfully.",
        "nd": "Inombolo Yesikhathi iqinisekisiwe ngempumelelo.",
        "sn": "Nhamba Yenguva yasimbiswa zvakanaka.",
    },

    # ── FAQ ───────────────────────────────────────────────────────────────
    "faq_menu": {
        "en": "FAQs – select a number to read:",
        "nd": "Imibuzo Evamile – khetha inombolo ukufunda:",
        "sn": "Mibvunzo Inowanzo – sarudza nhamba kuverenga:",
    },
    "faq_not_found": {
        "en": "FAQ not found.",
        "nd": "Umbuzo awutholakali.",
        "sn": "Mubvunzo hauwanikwi.",
    },

    # ── Generic ───────────────────────────────────────────────────────────
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
        "nd": "Iphutha lesikhathi. Zama futhi.",
        "sn": "Nguva yakanganisika. Edza zvakare.",
    },
    "cancelled": {
        "en": "Cancelled.",
        "nd": "Kukhanselwe.",
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
        t("ticket_created", "sn", tid="TKT001")
        → "Tiketi ragadzirwa. Nhamba yako: TKT001"
    """
    bucket = TEXT.get(key, {})
    text = bucket.get(lang) or bucket.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # return unformatted rather than crash
    return text


def get_faqs(lang: str = "en") -> list:
    """Return the FAQ list for the given language, falling back to English."""
    return FAQS.get(lang) or FAQS["en"]