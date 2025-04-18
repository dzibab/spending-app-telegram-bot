from datetime import date, datetime, timezone

import requests

from config import EXCHANGE_API_KEY
from utils.logging import logger


class ExchangeRateCache:
    """Cache for exchange rates to minimize API calls."""

    def __init__(self):
        self._cache: dict[str, dict[str, any]] = {}

    def get_rates(self, currency: str, current_date: date) -> dict[str, float] | None:
        """Get cached exchange rates for a currency if they exist and are from today."""
        cache_entry = self._cache.get(currency.upper())
        if cache_entry and cache_entry["date"] == current_date:
            logger.debug(f"Using cached exchange rates for {currency}")
            return cache_entry["rates"]
        return None

    def set_rates(self, currency: str, rates: dict[str, float], current_date: date) -> None:
        """Cache exchange rates for a currency."""
        self._cache[currency.upper()] = {"date": current_date, "rates": rates}
        logger.debug(f"Cached exchange rates for {currency}")


# Create global cache instance
_rates_cache = ExchangeRateCache()


def fetch_rates(main_currency: str) -> dict[str, float]:
    """Fetch current exchange rates for a currency.

    Args:
        main_currency: Base currency code (e.g., 'USD')

    Returns:
        Dictionary mapping currency pairs to exchange rates

    Raises:
        ValueError: If the API request fails
        requests.RequestException: If there's a network error
    """
    today = datetime.now(tz=timezone.utc).date()
    cached_rates = _rates_cache.get_rates(main_currency, today)

    if cached_rates:
        return cached_rates

    logger.info(f"Fetching fresh exchange rates for {main_currency}")
    url = "https://api.exchangerate.host/live"
    params = {"access_key": EXCHANGE_API_KEY, "source": main_currency.upper()}

    try:
        response = requests.get(url, params=params, timeout=10)  # Add timeout
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            error_msg = data.get("error", {}).get("info", "Unknown error")
            logger.error(f"API request failed: {error_msg}")
            raise ValueError(f"Failed to fetch exchange rates: {error_msg}")

        rates = data["quotes"]
        _rates_cache.set_rates(main_currency, rates, today)
        return rates

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
    """Convert an amount between currencies using optimal conversion path.

    The conversion is done by first converting to the user's main currency and then
    to the target currency if needed. This minimizes API calls as we only need to
    fetch exchange rates once for the main currency.

    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code

    Returns:
        Converted amount rounded to 4 decimal places

    Raises:
        ValueError: If the conversion rate is not available
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        logger.debug(f"Same currency conversion requested: {from_currency}")
        return round(amount, 4)

    logger.debug(f"Converting {amount} from {from_currency} to {to_currency}")
    try:
        rates = fetch_rates(to_currency)  # We fetch rates using the target currency as base
        direct_key = f"{to_currency}{from_currency}"  # e.g., PLNUSD if converting from USD to PLN

        if direct_key in rates:
            # Convert using the inverse of the rate since we have target->source rate
            rate = 1 / rates[direct_key]
            result = round(amount * rate, 4)
            logger.debug(f"Converted amount: {result} {to_currency}")
            return result

        msg = f"Conversion rate not found for {direct_key}"
        logger.error(msg)
        raise ValueError(msg)

    except Exception as e:
        logger.error(f"Error during currency conversion: {e}")
        raise
