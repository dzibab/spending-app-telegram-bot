from datetime import datetime
from io import BytesIO
from typing import Optional, List

import matplotlib.pyplot as plt
import pandas as pd
from telegram import InlineKeyboardButton

from utils.logging import logger


def plot_bar_chart(data: pd.DataFrame, main_currency: str, month: int, year: int) -> None:
    """Create a bar chart visualization of spending data.

    Args:
        data: DataFrame with columns 'category' and 'total'
        main_currency: Currency code to display in labels
        month: Month number (1-12)
        year: Year number
    """
    logger.debug(f"Creating bar chart for {month}/{year} in {main_currency}")

    # Sort data by total spending in descending order
    data = data.sort_values(by='total', ascending=False)

    # Plot the bar chart
    plt.figure(figsize=(12, 8))
    bars = plt.bar(data['category'], data['total'],
                   color=plt.cm.Paired(range(len(data))))

    # Add percentage labels and total spending on top of each bar
    total_spending = data['total'].sum()
    for bar, (category, total) in zip(bars, data.itertuples(index=False)):
        percentage = (total / total_spending) * 100
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f'{total:.2f} {main_currency}\n({percentage:.1f}%)',
            ha='center',
            va='bottom',
            fontsize=10
        )

    # Add gridlines for better readability
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Set labels and title
    plt.xlabel('Category', fontsize=12)
    plt.ylabel(f'Total Spending ({main_currency})', fontsize=12)
    plt.title(
        f"Spending by Category for {datetime(year, month, 1).strftime('%B %Y')}\n"
        f"Total: {total_spending:.2f} {main_currency}",
        fontsize=14
    )
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.tight_layout()


def plot_pie_chart(data: pd.DataFrame, main_currency: str, month: int, year: int) -> None:
    """Create a pie chart visualization of spending data.

    Args:
        data: DataFrame with columns 'category' and 'total'
        main_currency: Currency code to display in labels
        month: Month number (1-12)
        year: Year number
    """
    logger.debug(f"Creating pie chart for {month}/{year} in {main_currency}")

    # Calculate total spending
    total_spending = data['total'].sum()

    # Plot the pie chart
    plt.figure(figsize=(10, 8))
    _, texts, autotexts = plt.pie(
        data['total'],
        labels=data['category'],
        autopct=lambda p: f'{p:.1f}%\n({(p * total_spending / 100):.2f} {main_currency})',
        startangle=140,
        colors=plt.cm.Paired(range(len(data)))
    )

    # Style the text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(9)

    plt.title(
        f"Spending Distribution for {datetime(year, month, 1).strftime('%B %Y')}\n"
        f"Total: {total_spending:.2f} {main_currency}",
        fontsize=14
    )
    plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular


def generate_plot(
    data: pd.DataFrame,
    main_currency: str,
    month: int,
    year: int,
    chart_type: str = "bar"
) -> Optional[BytesIO]:
    """Generate a plot visualization of spending data.

    Args:
        data: DataFrame with columns 'category' and 'total'
        main_currency: Currency code to display in labels
        month: Month number (1-12)
        year: Year number
        chart_type: Type of chart to generate ('bar' or 'pie')

    Returns:
        BytesIO object containing the plot image in PNG format

    Raises:
        ValueError: If chart_type is not 'bar' or 'pie'
    """
    logger.info(f"Generating {chart_type} chart for {month}/{year} in {main_currency}")
    try:
        if chart_type == "bar":
            plot_bar_chart(data, main_currency, month, year)
        elif chart_type == "pie":
            plot_pie_chart(data, main_currency, month, year)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        # Save the plot to a BytesIO object
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        logger.debug("Successfully generated and saved plot")
        return buf
    except Exception as e:
        logger.error(f"Error generating {chart_type} chart: {e}")
        plt.close()  # Ensure figure is closed even on error
        raise


def create_pagination_buttons(current_page: int, total_pages: int, callback_prefix: str) -> List[InlineKeyboardButton]:
    """Create pagination buttons with first and last pages always visible.
    Current page is highlighted with dashes and is non-clickable.
    This function works with ITEMS_PER_PAGE constant from constants.py
    which defines how many items are shown per page.

    Args:
        current_page: Current page number (0-based)
        total_pages: Total number of pages based on ITEMS_PER_PAGE constant
        callback_prefix: Prefix for the callback data (e.g., 'list_page' or 'remove_page')

    Returns:
        List of InlineKeyboardButton objects with formatted pagination
    """
    buttons = []

    # If there's only one page, show just that page highlighted
    if total_pages <= 1:
        buttons.append(InlineKeyboardButton("-1-", callback_data="noop"))
        return buttons

    # First page handling (current or regular)
    if current_page == 0:
        buttons.append(InlineKeyboardButton("-1-", callback_data="noop"))
    else:
        buttons.append(InlineKeyboardButton("1", callback_data=f"{callback_prefix}:0"))

    # Show ellipsis if there are hidden pages at the start
    if current_page > 2:
        buttons.append(InlineKeyboardButton("...", callback_data="noop"))

    # Show surrounding pages (excluding first and last page)
    for page in range(max(1, current_page - 1), min(total_pages - 1, current_page + 2)):
        # Skip if this is the first or last page (they're handled separately)
        if page == 0 or page == total_pages - 1:
            continue
        button_text = f"-{page + 1}-" if page == current_page else str(page + 1)
        # Make current page non-clickable
        callback_data = "noop" if page == current_page else f"{callback_prefix}:{page}"
        buttons.append(InlineKeyboardButton(
            button_text,
            callback_data=callback_data
        ))

    # Show ellipsis if there are hidden pages at the end
    if current_page < total_pages - 3:
        buttons.append(InlineKeyboardButton("...", callback_data="noop"))

    # Last page handling (current or regular)
    if total_pages > 1:  # Only show last page button if there is more than one page
        if current_page == total_pages - 1:
            buttons.append(InlineKeyboardButton(f"-{total_pages}-", callback_data="noop"))
        else:
            buttons.append(InlineKeyboardButton(str(total_pages), callback_data=f"{callback_prefix}:{total_pages - 1}"))

    return buttons
