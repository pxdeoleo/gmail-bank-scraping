import datetime
from enum import Enum


class TransactionStatus(Enum):
    APPROVED = 1
    REJECTED = 2
    REVERSED = 3


class Transaction:
    date_time: datetime.datetime
    currency: str
    amount: float
    description: str
    status: TransactionStatus
    card_number: str

    def __init__(self, description: str, date_time: datetime.datetime, currency: str, amount: float,
                 status: TransactionStatus, card_number: str):
        self.description = description
        self.date_time = date_time
        self.currency = currency
        self.amount = amount
        self.status = status
        self.card_number = card_number
