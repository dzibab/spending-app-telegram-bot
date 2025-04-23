"""Utility functions for date handling."""

import calendar
import re
from datetime import datetime

from utils.logging import logger


def get_month_name(month_num: int or str) -> str:
    """Get month name from its number.

    Args:
        month_num: Month number (1-12) as integer or string

    Returns:
        Full month name (e.g., 'January' for 1)

    Raises:
        ValueError: If month number is invalid
    """
    logger.debug(f"Getting month name for number: {month_num}")
    try:
        # Convert string to int if needed
        month = int(month_num)
        if 1 <= month <= 12:
            month_name = calendar.month_name[month]
            logger.debug(f"Converted month number {month} to name: {month_name}")
            return month_name
        else:
            logger.warning(f"Invalid month number {month} (must be 1-12)")
            raise ValueError(f"Month number must be between 1 and 12, got {month}")
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to convert month number '{month_num}': {e}")
        raise ValueError(f"Invalid month number: {month_num}. {e}")


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
    logger.debug(f"Parsing date string: '{date_str}'")

    # Clean the date string
    date_str = date_str.strip()

    # Replace all delimiters with hyphen for consistency in regex matching
    normalized = re.sub(r"[/.]", "-", date_str)
    logger.debug(f"Normalized date format: '{normalized}'")

    # Try to match YYYY-MM-DD format
    if re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", normalized):
        logger.debug(f"Detected YYYY-MM-DD format: '{normalized}'")
        year, month, day = map(int, normalized.split("-"))

    # Try to match DD-MM-YYYY format
    elif re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", normalized):
        logger.debug(f"Detected DD-MM-YYYY format: '{normalized}'")
        day, month, year = map(int, normalized.split("-"))

    else:
        logger.warning(f"Unrecognized date format: '{date_str}'")
        raise ValueError(
            f"Date format not recognized: {date_str}. Use YYYY-MM-DD or DD-MM-YYYY with delimiter -, / or ."
        )

    logger.debug(f"Extracted components: year={year}, month={month}, day={day}")

    # Validate the date components
    if not (1 <= month <= 12):
        logger.warning(f"Invalid month {month} in date: '{date_str}'")
        raise ValueError(f"Invalid month in date: {date_str}")

    if not (1 <= day <= 31):
        logger.warning(f"Invalid day {day} in date: '{date_str}'")
        raise ValueError(f"Invalid day in date: {date_str}")

    # Check specific month lengths and leap year for February
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Adjust February for leap years
    is_leap_year = year % 400 == 0 or (year % 100 != 0 and year % 4 == 0)
    if is_leap_year:
        logger.debug(f"Year {year} is a leap year")
        days_in_month[2] = 29

    if day > days_in_month[month]:
        logger.warning(f"Invalid day {day} for month {month} in year {year}")
        raise ValueError(f"Invalid day for the given month and year in date: {date_str}")

    # Create datetime object to ensure date is valid and to get formatted string
    try:
        date_obj = datetime(year, month, day)
        formatted_date = date_obj.strftime("%Y-%m-%d")
        logger.debug(f"Successfully parsed date: '{date_str}' -> '{formatted_date}'")
        return formatted_date
    except ValueError as e:
        logger.error(f"Failed to create datetime object with y={year}, m={month}, d={day}: {e}")
        raise


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
    logger.debug(f"Converting date string to datetime object: '{date_str}'")
    formatted_date = parse_date(date_str)
    try:
        date_obj = datetime.strptime(formatted_date, "%Y-%m-%d")
        logger.debug(f"Created datetime object: {date_obj.isoformat()}")
        return date_obj
    except ValueError as e:
        logger.error(f"Failed to convert formatted date '{formatted_date}' to datetime: {e}")
        raise
