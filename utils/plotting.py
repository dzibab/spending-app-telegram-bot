from datetime import datetime
from io import BytesIO

import matplotlib.figure
import matplotlib.pyplot as plt
import pandas as pd

from utils.logging import logger


class ChartError(ValueError):
    """Custom exception for chart-related errors."""

    def __init__(self, message: str = None, original_error: Exception = None):
        """Initialize a chart error.

        Args:
            message: Optional error message
            original_error: Original exception that caused this error
        """
        if message is None:
            message = "An error occurred in chart generation"
        super().__init__(message)
        self.original_error = original_error

    @classmethod
    def no_chart_created(cls):
        """Create an error for when no chart was created."""
        return cls("No chart has been created yet")

    @classmethod
    def unsupported_chart_type(cls, chart_type: str):
        """Create an error for unsupported chart type.

        Args:
            chart_type: The invalid chart type that was provided
        """
        return cls(f"Unsupported chart type: {chart_type}")

    @classmethod
    def from_exception(cls, error: Exception):
        """Create a chart error from another exception.

        Args:
            error: The original exception
        """
        return cls(f"Failed to generate chart: {error!s}", error)


class ChartGenerator:
    """Class for generating spending data visualizations."""

    def __init__(
        self,
        data: pd.DataFrame,
        main_currency: str,
        month: int,
        year: int,
        figsize: None | tuple[float, float] = None,
        dpi: int = 300,
    ):
        """Initialize chart generator.

        Args:
            data: DataFrame with columns 'category' and 'total'
            main_currency: Currency code to display in labels
            month: Month number (1-12)
            year: Year number
            figsize: Optional figure size as (width, height) in inches
            dpi: Resolution for saved images
        """
        self.data = data.sort_values(by="total", ascending=False).copy()
        self.main_currency = main_currency
        self.month = month
        self.year = year
        self.total_spending = data["total"].sum()
        self.date_str = datetime(year, month, 1).strftime("%B %Y")
        self.figsize = figsize
        self.dpi = dpi
        self.figure = None

    def _setup_figure(self, chart_type: str) -> matplotlib.figure.Figure:
        """Set up the matplotlib figure.

        Args:
            chart_type: Type of chart being created

        Returns:
            The created figure
        """
        # Use default figure sizes if none provided
        if self.figsize is None:
            if chart_type == "bar":
                self.figsize = (12, 8)
            elif chart_type == "pie":
                self.figsize = (10, 8)

        self.figure = plt.figure(figsize=self.figsize)
        return self.figure

    def create_bar_chart(self) -> matplotlib.figure.Figure:
        """Create a bar chart visualization of spending data.

        Returns:
            Matplotlib figure with the rendered chart
        """
        logger.debug(f"Creating bar chart for {self.month}/{self.year} in {self.main_currency}")

        self._setup_figure("bar")

        # Plot the bar chart
        bars = plt.bar(
            self.data["category"], self.data["total"], color=plt.cm.Paired(range(len(self.data)))
        )

        # Add percentage labels and total spending on top of each bar
        for bar, (_, total) in zip(bars, self.data.itertuples(index=False), strict=False):
            percentage = (total / self.total_spending) * 100
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{total:.2f} {self.main_currency}\n({percentage:.1f}%)",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        # Add gridlines for better readability
        plt.grid(axis="y", linestyle="--", alpha=0.7)

        # Set labels and title
        plt.xlabel("Category", fontsize=12)
        plt.ylabel(f"Total Spending ({self.main_currency})", fontsize=12)
        plt.title(
            f"Spending by Category for {self.date_str}\nTotal: {self.total_spending:.2f} {self.main_currency}",
            fontsize=14,
        )
        plt.xticks(rotation=45, ha="right", fontsize=10)
        plt.tight_layout()

        return self.figure

    def create_pie_chart(self) -> matplotlib.figure.Figure:
        """Create a pie chart visualization of spending data.

        Returns:
            Matplotlib figure with the rendered chart
        """
        logger.debug(f"Creating pie chart for {self.month}/{self.year} in {self.main_currency}")

        self._setup_figure("pie")

        # Plot the pie chart
        _, texts, autotexts = plt.pie(
            self.data["total"],
            labels=self.data["category"],
            autopct=lambda p: f"{p:.1f}%\n({(p * self.total_spending / 100):.2f} {self.main_currency})",
            startangle=140,
            colors=plt.cm.Paired(range(len(self.data))),
        )

        # Style the text
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(9)

        plt.title(
            f"Spending Distribution for {self.date_str}\nTotal: {self.total_spending:.2f} {self.main_currency}",
            fontsize=14,
        )
        plt.axis("equal")  # Equal aspect ratio ensures the pie chart is circular

        return self.figure

    def save_chart_to_buffer(self) -> BytesIO:
        """Save the current figure to a BytesIO buffer.

        Returns:
            BytesIO object containing the image in PNG format

        Raises:
            ChartError: If no chart has been created yet
        """
        if self.figure is None:
            raise ChartError.no_chart_created()

        buf = BytesIO()
        self.figure.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight")
        buf.seek(0)
        return buf

    def close(self) -> None:
        """Close the current figure to free memory."""
        if self.figure is not None:
            plt.close(self.figure)
            self.figure = None


def _validate_chart_type(chart_type: str) -> None:
    """Validate the chart type.

    Args:
        chart_type: Type of chart to validate

    Raises:
        ChartError: If chart_type is not supported
    """
    if chart_type not in ("bar", "pie"):
        raise ChartError.unsupported_chart_type(chart_type)


def generate_plot(
    data: pd.DataFrame,
    main_currency: str,
    month: int,
    year: int,
    chart_type: str = "bar",
    figsize: None | tuple[float, float] = None,
    dpi: int = 300,
) -> BytesIO:
    """Generate a plot visualization of spending data.

    Args:
        data: DataFrame with columns 'category' and 'total'
        main_currency: Currency code to display in labels
        month: Month number (1-12)
        year: Year number
        chart_type: Type of chart to generate ('bar' or 'pie')
        figsize: Optional figure size as (width, height) in inches
        dpi: Resolution for saved images

    Returns:
        BytesIO object containing the plot image in PNG format

    Raises:
        ChartError: If chart_type is not 'bar' or 'pie' or if an error occurs
    """
    logger.info(f"Generating {chart_type} chart for {month}/{year} in {main_currency}")

    chart_generator = ChartGenerator(
        data=data, main_currency=main_currency, month=month, year=year, figsize=figsize, dpi=dpi
    )

    try:
        _validate_chart_type(chart_type)
        if chart_type == "bar":
            chart_generator.create_bar_chart()
        else:  # chart_type == "pie"
            chart_generator.create_pie_chart()
    except ChartError:
        # Re-raise ChartError exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error generating {chart_type} chart: {e}")
        # Wrap other exceptions in a ChartError
        raise ChartError.from_exception(e) from e
    else:
        buf = chart_generator.save_chart_to_buffer()
        logger.debug("Successfully generated and saved plot")
        return buf
    finally:
        chart_generator.close()
