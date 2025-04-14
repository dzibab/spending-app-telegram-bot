from datetime import date

from pydantic.dataclasses import dataclass


@dataclass
class Spending:
    id: int | None
    user_id: int
    description: str
    amount: float
    currency: str
    category: str
    date: date
