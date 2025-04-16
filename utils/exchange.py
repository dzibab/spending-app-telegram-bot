from datetime import datetime, timezone

import requests

from config import EXCHANGE_API_KEY
from utils.logging import logger


_rates_cache = {}


def fetch_rates(from_currency: str) -> dict:
    today = datetime.now(tz=timezone.utc).date()
    cache_entry = _rates_cache.get(from_currency.upper())

    if cache_entry and cache_entry["date"] == today:
        logger.debug(f"Using cached exchange rates for {from_currency}")
        return cache_entry["rates"]

    logger.info(f"Fetching fresh exchange rates for {from_currency}")
    url = "https://api.exchangerate.host/live"
    params = {
        "access_key": EXCHANGE_API_KEY,
        "source": from_currency.upper()
    }
    try:
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
        logger.debug(f"Successfully cached exchange rates for {from_currency}")
        return data["quotes"]
    except requests.RequestException as e:
        logger.error(f"Network error fetching exchange rates: {e}")
        raise
    except ValueError as e:
        logger.error(f"Invalid response from exchange rate API: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching exchange rates: {e}")
        raise


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    if from_currency == to_currency:
        logger.debug(f"Same currency conversion requested: {from_currency}")
        return round(amount, 4)

    logger.debug(f"Converting {amount} from {from_currency} to {to_currency}")
    try:
        rates = fetch_rates(from_currency)
        key = f"{from_currency.upper()}{to_currency.upper()}"
        rate = rates.get(key)
        if rate is None:
            msg = f"Conversion rate not found for {key}"
            logger.error(msg)
            raise ValueError(msg)

        result = round(amount * rate, 4)
        logger.debug(f"Converted amount: {result} {to_currency}")
        return result
    except Exception as e:
        logger.error(f"Error during currency conversion: {e}")
        raise
