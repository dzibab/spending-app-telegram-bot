VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "CNY", "SEK", "NZD",
    "PLN", "NOK", "DKK", "CZK", "HUF", "INR", "BRL", "MXN", "ZAR", "SGD",
    "HKD", "KRW", "RUB", "TRY", "UAH", "ILS", "THB", "MYR", "IDR", "PHP",
    "BYN",
    # Add more as needed
}


def is_valid_currency(code: str) -> bool:
    return code.upper() in VALID_CURRENCIES
