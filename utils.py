"""
utils.py
--------
Pure-utility functions used across the application.
No imports from other app modules here – keeps the dependency graph clean.
"""

import re


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def is_valid_phone(phone: str) -> bool:
    """
    Accept phone numbers that are 7-15 digits, optionally prefixed with +.
    Examples: +263771234567, 0771234567, 771234567
    """
    return bool(re.fullmatch(r"\+?\d{7,15}", (phone or "").strip()))


def is_valid_account(account: str) -> bool:
    """
    Accept account numbers that are 6-20 alphanumeric characters.
    Adjust the pattern to match your platform's account number format.
    Examples: ACC001234, 123456, ZW00998877
    """
    return bool(re.fullmatch(r"[A-Za-z0-9]{6,20}", (account or "").strip()))


def is_valid_amount(value: str) -> bool:
    """Return True if *value* is a positive numeric string."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def is_valid_pin(pin: str) -> bool:
    """PIN must be exactly 4 digits."""
    return bool(re.fullmatch(r"\d{4}", (pin or "").strip()))


def is_valid_otp(otp: str) -> bool:
    """OTP is a 4-digit code."""
    return bool(re.fullmatch(r"\d{4}", (otp or "").strip()))


# ---------------------------------------------------------------------------
# Safe type coercion
# ---------------------------------------------------------------------------

def safe_float(val, default: float = 0.0) -> float:
    """Convert *val* to float or return *default* on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_int(val, default: int = 0) -> int:
    """Convert *val* to int or return *default* on failure."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt_amount(amount: float) -> str:
    """Format a float as a currency string with 2 decimal places."""
    return f"{amount:,.2f}"