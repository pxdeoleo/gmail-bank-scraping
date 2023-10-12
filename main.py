import os
import re
import datetime
from datetime import date
from enum import Enum

from bs4 import BeautifulSoup
from gmail_api_handler import GmailAPIHandler

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class TransactionStatus(Enum):
    APPROVED = 1
    REJECTED = 2
    REVERSED = 3


class Transaction:
    date_time: datetime.datetime
    ccy: str
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


def get_monday_date(day: date) -> date:
    """
    Returns the date of the Monday of the week of the given date.
    """
    monday = day - datetime.timedelta(days=date.weekday(day))
    return monday


def parse_html_table(html_string: str) -> Transaction:
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


def save_transactions_as_csv(transactions_list: list[Transaction], date_format: str = '%m/%d/%Y',
                             directory: str = 'transactions', file_name: str = 'transactions.csv'):
    # Check if the directory exists
    # If it doesn't, create it
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Check if filename has .csv extension
    if not file_name.endswith('.csv'):
        file_name += '.csv'

    with open(os.path.join(directory, file_name), 'w') as f:
        f.write('date_time,currency,amount,description,status\n')
        for transaction in transactions_list:
            f.write(f'{transaction.date_time.strftime(date_format)},{transaction.currency},{transaction.amount},'
                    f'{transaction.description},{transaction.status.name}\n')


if __name__ == '__main__':
    gmail_api_handler = GmailAPIHandler(scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                                        credentials_path='credentials.json',
                                        token_path='token.json')
    gmail_api_handler.authenticate()

    monday_date = get_monday_date(date.today()).strftime('%Y/%m/%d')
    gmail_query: str = f'label:bancos-bhd-notificacion after:{monday_date}'

    messages = gmail_api_handler.get_messages(query=gmail_query)

    transactions = []

    for message in messages:
        transactions.append(parse_html_table(message['body']))

    # Use a folder structure of [Card]/[Currency]/[Transactions].csv
    # Every .csv file will contain transactions of the same card, currency and day

    # Split transactions by Card
    cards = set([transaction.card_number for transaction in transactions])
    for card in cards:
        # Split transactions by Currency
        currencies = set([transaction.currency for transaction in transactions if transaction.card_number == card])
        for ccy in currencies:
            # Split transactions by day
            days = set([transaction.date_time.date() for transaction in transactions if transaction.card_number == card
                        and transaction.currency == ccy])
            for day in days:
                # Save transactions as .csv
                save_transactions_as_csv([transaction for transaction in transactions if transaction.card_number == card
                                          and transaction.currency == ccy
                                          and transaction.date_time.date() == day], '%d/%m/%Y',
                                         f'{BASE_DIR}/transactions/{card}/{ccy}', f'{day}_{card}_{ccy}.csv')

