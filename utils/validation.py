"""Validation utilities for user input."""

import re
from datetime import datetime
from typing import Optional, Tuple, Union

from utils.date_utils import parse_date_to_datetime
from utils.logging import logger


def validate_currency_code(code: str) -> Tuple[bool, str]:
    """
    Validate a currency code.

    Args:
        code: The currency code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code:
        return False, "Currency code cannot be empty"

    code = code.strip().upper()

    # Check if it's exactly 3 alphabetical characters
    if len(code) != 3:
        return False, "Currency code must be exactly 3 letters (e.g., USD, EUR)"

    if not code.isalpha():
        return False, "Currency code must contain only letters (e.g., USD, EUR)"

    return True, ""


def validate_amount(amount_str: str) -> Tuple[bool, Union[float, str]]:
    """
    Validate an amount string and convert to float if valid.

    Args:
        amount_str: The amount string to validate

    Returns:
        Tuple of (is_valid, amount_or_error_message)
    """
    if not amount_str:
        return False, "Amount cannot be empty"

    # Remove any whitespace
    amount_str = amount_str.strip()

    # Allow commas as decimal separators and replace them
    amount_str = amount_str.replace(",", ".")

    # Check for basic format (allow negative amounts)
    if not re.match(r"^-?\d+(\.\d+)?$", amount_str):
        return False, "Amount must be a valid number (e.g., 10, 10.50)"

    try:
        amount = float(amount_str)

        # Check for reasonable amount range
        if abs(amount) > 1000000000:  # Billion
            return False, "Amount seems too large. Please enter a reasonable value."

        return True, amount
    except ValueError:
        return False, "Unable to convert amount to a number"


def validate_date(date_str: str) -> Tuple[bool, Union[datetime, str]]:
    """
    Validate a date string and convert to datetime if valid.

    Args:
        date_str: The date string to validate

    Returns:
        Tuple of (is_valid, datetime_or_error_message)
    """
    if not date_str:
        return False, "Date cannot be empty"

    date_str = date_str.strip()

    # Handle "today" case
    if date_str.lower() == "today":
        return True, datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        date_obj = parse_date_to_datetime(date_str)

        # Check if date is in the far future (potential typo)
        if date_obj.year > datetime.now().year + 10:
            return False, f"Date {date_str} seems far in the future. Please check for typos."

        # Check if date is in the far past (potential typo)
        if date_obj.year < datetime.now().year - 100:
            return False, f"Date {date_str} seems far in the past. Please check for typos."

        return True, date_obj
    except ValueError as e:
        return False, str(e)


def validate_category(category: str) -> Tuple[bool, str]:
    """
    Validate a category name.

    Args:
        category: The category to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not category:
        return False, "Category cannot be empty"

    category = category.strip()

    if len(category) > 50:
        return False, "Category name too long (maximum 50 characters)"

    return True, ""


def validate_description(description: str, max_length: int = 200) -> Tuple[bool, str]:
    """
    Validate a spending description.

    Args:
        description: The description to validate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Description can be empty, so no check for that

    if description and len(description) > max_length:
        return False, f"Description too long (maximum {max_length} characters)"

    return True, ""
