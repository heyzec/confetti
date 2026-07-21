from __future__ import annotations

import datetime
from dataclasses import dataclass

from .block import Block

DATE_FORMAT = "%Y-%m-%d"


@dataclass
class Date(Block):
    """Custom inline element to represent Confluence's time."""

    date: datetime.date

    @classmethod
    def parse(cls, s: str):
        return cls(date=datetime.datetime.strptime(s, DATE_FORMAT))

    def format(self):
        return self.date.strftime(DATE_FORMAT)
