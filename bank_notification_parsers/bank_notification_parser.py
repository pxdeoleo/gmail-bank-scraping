from abc import ABC, abstractmethod

from transaction import Transaction


class BankNotificationParser(ABC):
    @abstractmethod
    def parse_html(self, html_code: str) -> Transaction:
        pass
