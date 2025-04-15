from datetime import datetime, timezone

import requests

from config import EXCHANGE_API_KEY
from utils.logging import logger


_rates_cache = {}


def fetch_rates(from_currency: str) -> dict:
    today = datetime.now(tz=timezone.utc).date()
    cache_entry = _rates_cache.get(from_currency.upper())

    if cache_entry and cache_entry["date"] == today:
        return cache_entry["rates"]

    url = "https://api.exchangerate.host/live"
    params = {
        "access_key": EXCHANGE_API_KEY,
        "source": from_currency.upper()
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data["success"]:
        logger.error(f"API request failed: {data}")
        raise ValueError("Failed to fetch exchange rates")

    _rates_cache[from_currency.upper()] = {
        "date": today,
        "rates": data["quotes"]
    }

    return data["quotes"]


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    if from_currency == to_currency:
        return round(amount, 4)
    rates = fetch_rates(from_currency)
    key = f"{from_currency.upper()}{to_currency.upper()}"
    rate = rates.get(key)
    if rate is None:
        msg = f"Conversion rate not found for {key}"
        logger.error(msg)
        raise ValueError(msg)
    return round(amount * rate, 4)
