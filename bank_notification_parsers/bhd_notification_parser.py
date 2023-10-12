import datetime
import re

from bs4 import BeautifulSoup

from bank_notification_parsers.bank_notification_parser import BankNotificationParser
from transaction.Transaction import Transaction, TransactionStatus


class BhdNotificationParser(BankNotificationParser):

    def parse_html(self, html_string: str) -> Transaction:
        # Create a BeautifulSoup object
        soup = BeautifulSoup(html_string, 'html.parser')

        # Initialize variables to store extracted data
        transaction_data = {
            "date_time": None,
            "currency": None,
            "amount": None,
            "description": None,
            "status": None,
            "card_number": None
        }

        # Get the card number
        # Find the element containing the credit/debit card number (assuming it's in a 'p' element with class 'justify')
        card_element = soup.find('p', class_='justify')

        if card_element:
            # Extract the text from the element
            card_text = card_element.get_text()

            # Search for the last 4 digits of the card number using regular expressions
            card_number_match = re.search(r'\b(\d{4})\b', card_text)

            if card_number_match:
                last_4_digits = card_number_match.group(1)
                transaction_data["card_number"] = last_4_digits
            else:
                transaction_data["card_number"] = "Not found"
        else:
            transaction_data["card_number"] = "Not found"

        # Find the table containing transaction details
        transaction_table = soup.find('tbody', class_='table_trans_body')

        # Check if the transaction table is found
        if transaction_table:
            # Extract data from the table
            tds = transaction_table.find_all('td')
            if len(tds) == 7:
                # Value must be converted to datetime in format '08/10/23 20:22'
                transaction_data["date_time"] = datetime.datetime.strptime(tds[0].text.strip(), '%d/%m/%y %H:%M')
                transaction_data["currency"] = "DOP" if tds[1].text.strip() == "RD" else tds[1].text.strip()
                transaction_data["description"] = tds[3].text.strip()
                status = TransactionStatus.APPROVED if tds[4].text.strip().lower() == "aprobada" \
                    else TransactionStatus.REJECTED if tds[4].text.strip().lower() == "rechazada" \
                    else TransactionStatus.REVERSED if tds[4].text.strip().lower() == "reversada" \
                    else None
                transaction_data["status"] = status

                amount = (
                    float(tds[2].text.strip())) if transaction_data["status"] == TransactionStatus.APPROVED \
                    else 0 if transaction_data["status"] == TransactionStatus.REJECTED \
                    else -float(tds[2].text.strip()) if transaction_data["status"] == TransactionStatus.REVERSED \
                    else None
                transaction_data["amount"] = amount

        # Print the extracted data as a dictionary
        return Transaction(**transaction_data)
