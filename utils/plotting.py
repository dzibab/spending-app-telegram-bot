import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from io import BytesIO


def plot_bar_chart(data: pd.DataFrame, main_currency: str, month: int, year: int):
    # Sort data by total spending in descending order
    data = data.sort_values(by='total', ascending=False)

    # Plot the bar chart
    plt.figure(figsize=(12, 8))
    bars = plt.bar(data['category'], data['total'], color=plt.cm.Paired(range(len(data))))

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
    plt.title(f"Spending by Category for {datetime(year, month, 1).strftime('%B %Y')}\nTotal: {total_spending:.2f} {main_currency}", fontsize=14)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.tight_layout()


def plot_pie_chart(data: pd.DataFrame, main_currency: str, month: int, year: int):
    # Calculate total spending
    total_spending = data['total'].sum()

    # Plot the pie chart
    plt.figure(figsize=(10, 8))
    wedges, texts, autotexts = plt.pie(
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

    plt.title(f"Spending Distribution for {datetime(year, month, 1).strftime('%B %Y')}\nTotal: {total_spending:.2f} {main_currency}", fontsize=14)
    plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular


def generate_plot(data: pd.DataFrame, main_currency: str, month: int, year: int, chart_type: str = "bar") -> BytesIO:
    if chart_type == "bar":
        plot_bar_chart(data, main_currency, month, year)
    elif chart_type == "pie":
        plot_pie_chart(data, main_currency, month, year)

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
