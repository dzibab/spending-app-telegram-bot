"""Utility functions for date handling."""

import re
from datetime import datetime


def parse_date(date_str: str) -> str:
    """Parse date string in different formats and return YYYY-MM-DD format.

    Supported formats:
    - YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    - DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY

    Args:
        date_str: Date string in one of the supported formats

    Returns:
        Date string in YYYY-MM-DD format

    Raises:
        ValueError: If date string format is not recognized or is invalid
    """
    # Clean the date string
    date_str = date_str.strip()

    # Replace all delimiters with hyphen for consistency in regex matching
    normalized = re.sub(r"[/.]", "-", date_str)

    # Try to match YYYY-MM-DD format
    if re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", normalized):
        year, month, day = map(int, normalized.split("-"))

    # Try to match DD-MM-YYYY format
    elif re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", normalized):
        day, month, year = map(int, normalized.split("-"))

    else:
        raise ValueError(
            f"Date format not recognized: {date_str}. Use YYYY-MM-DD or DD-MM-YYYY with delimiter -, / or ."
        )

    # Validate the date components
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month in date: {date_str}")

    if not (1 <= day <= 31):
        raise ValueError(f"Invalid day in date: {date_str}")

    # Check specific month lengths and leap year for February
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Adjust February for leap years
    if year % 400 == 0 or (year % 100 != 0 and year % 4 == 0):
        days_in_month[2] = 29

    if day > days_in_month[month]:
        raise ValueError(f"Invalid day for the given month and year in date: {date_str}")

    # Create datetime object to ensure date is valid and to get formatted string
    date_obj = datetime(year, month, day)
    return date_obj.strftime("%Y-%m-%d")


def parse_date_to_datetime(date_str: str) -> datetime:
    """Parse date string in different formats and return a datetime object.

    This uses parse_date internally but returns a datetime object instead of a string.

    Args:
        date_str: Date string in one of the supported formats

    Returns:
        datetime object representing the parsed date

    Raises:
        ValueError: If date string format is not recognized or is invalid
    """
    formatted_date = parse_date(date_str)
    return datetime.strptime(formatted_date, "%Y-%m-%d")
