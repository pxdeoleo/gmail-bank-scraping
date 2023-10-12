import argparse
import datetime
import os
from datetime import date

from bank_notification_parsers.bank_notification_parser import BankNotificationParser
from bank_notification_parsers.bhd_notification_parser import BhdNotificationParser
from gmail_api.gmail_api_handler import GmailAPIHandler
from transaction import Transaction

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_monday_date(weekday: date) -> date:
    """
    Returns the date of the Monday of the week of the given date.
    """
    monday = weekday - datetime.timedelta(days=date.weekday(weekday))
    return monday


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
    args_parser = argparse.ArgumentParser(description="Just an example",
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    args_parser.add_argument('label', type=str, help='Gmail label to search for')
    args_parser.add_argument("bank", type=str, help="Bank to parse notifications from", choices=['bhd'])
    args_parser.add_argument('--before', type=str, help='Date before which to search for emails. '
                                                        'Format: YYYY/MM/DD')
    args_parser.add_argument('--after', type=str, help='Date after which to search for emails. '
                                                       'Format: YYYY/MM/DD')
    args_parser.add_argument("--credentials", type=str, help="Path to credentials.json file")
    args_parser.add_argument("--token", type=str, help="Path to token.json file",
                             default=os.path.join(BASE_DIR, 'token.json'))
    args_parser.add_argument("--output", type=str, help="Path to output directory")

    args = args_parser.parse_args()

    parser: BankNotificationParser

    label = args.label
    date_before: str = ''
    date_after: str = get_monday_date(date.today()).strftime('%Y/%m/%d')
    credentials_path = args.credentials if args.credentials else os.path.join(BASE_DIR, 'credentials.json')
    token_path = args.token if args.token else os.path.join(BASE_DIR, 'token.json')
    output_dir = args.output if args.output else os.path.join(BASE_DIR, 'transactions')

    if args.bank == 'bhd':
        parser = BhdNotificationParser()
    else:
        raise NotImplementedError(f'Bank {args.bank} is not supported yet')

    if args.before:
        # Check if date is valid
        try:
            datetime.datetime.strptime(args.before, '%Y/%m/%d')
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY/MM/DD")
        date_before: str = args.before
    if args.after:
        # Check if date is valid
        try:
            datetime.datetime.strptime(args.after, '%Y/%m/%d')
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY/MM/DD")
        date_after: str = args.after

    gmail_api_handler = GmailAPIHandler(scopes=SCOPES,
                                        credentials_path=credentials_path,
                                        token_path=token_path)
    gmail_api_handler.authenticate()

    # label = 'bancos-bhd-notificacion'

    gmail_query: str = ''

    gmail_query += f'label:{label} '
    gmail_query += f'after:{date_after} '
    if date_before:
        gmail_query += f'before:{date_before} '

    messages = gmail_api_handler.get_messages(query=gmail_query)

    transactions = []

    for message in messages:
        transactions.append(parser.parse_html(message['body']))

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
                                         f'{output_dir}/{card}/{ccy}', f'{day}_{card}_{ccy}.csv')
