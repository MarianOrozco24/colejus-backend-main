from flask import jsonify, request
from datetime import datetime
import math

class InterestPeriod:
    def __init__(self, start_date: datetime, end_date: datetime, rate: float):
        self.start_date = start_date
        self.end_date = end_date
        self.rate = rate
        self.days = (end_date - start_date).days

    def calculate_interest(self, capital: float) -> float:
        yearly_rate = self.rate / 100
        daily_rate = yearly_rate / 365
        return capital * daily_rate * self.days

    def to_string(self) -> str:
        return f"{self.start_date.strftime('%d-%m-%Y')}: {self.rate}% / 365 * {self.days} dias = %{(self.rate * self.days / 365):.4f}"

