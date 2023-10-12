from __future__ import print_function

import base64
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailAPIHandler:
    def __init__(self, scopes, credentials_path, token_path):
        self.scopes = scopes
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.creds = None

    def authenticate(self):
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())

    def get_labels(self):
        try:
            # Call the Gmail API
            self.service = build('gmail', 'v1', credentials=self.creds)
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            return labels

        except HttpError as error:
            # TODO(developer) - Handle errors from gmail API.
            print(f'An error occurred: {error}')

    def get_messages(self, query):
        try:
            # Call the Gmail API
            self.service = build('gmail', 'v1', credentials=self.creds)
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])

            msgs = []

            for message in messages:
                msg = self.service.users().messages().get(userId="me", id=message["id"]).execute()
                new_message = {}
                email_data = msg["payload"]["headers"]
                for values in email_data:
                    name = values["name"]
                    if name == "From":
                        from_name = values["value"]
                        new_message["from"] = from_name
                        subject = [j["value"] for j in email_data if j["name"] == "Subject"]
                        new_message["subject"] = subject.pop()

                # I added the below script.
                for p in msg["payload"]["parts"]:
                    if p["mimeType"] in ["text/plain", "text/html"]:
                        data = base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8")
                        new_message["body"] = data

                msgs.append(new_message)
            return msgs

        except HttpError as error:
            # TODO(developer) - Handle errors from gmail API.
            print(f'An error occurred: {error}')
