from django.core.exceptions import ValidationError

# Supported release currencies, not a default assumption that every currency has two decimals.
CURRENCY_EXPONENTS = {"INR": 2, "USD": 2, "JPY": 0, "KWD": 3}


def validate_currency(currency):
    if currency not in CURRENCY_EXPONENTS:
        raise ValidationError("Unsupported currency; configure its exponent before importing it.")


def format_minor(amount, currency):
    validate_currency(currency)
    exponent = CURRENCY_EXPONENTS[currency]
    sign = "-" if amount < 0 else ""
    whole, fraction = divmod(abs(amount), 10 ** exponent)
    return f"{currency} {sign}{whole}" + (f".{fraction:0{exponent}d}" if exponent else "")
