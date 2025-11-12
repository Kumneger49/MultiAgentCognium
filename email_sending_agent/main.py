




# import base64
# from email.message import EmailMessage

# import google.auth
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError


# def gmail_send_message():
#   """Create and send an email message
#   Print the returned  message id
#   Returns: Message object, including message id

#   Load pre-authorized user credentials from the environment.
#   TODO(developer) - See https://developers.google.com/identity
#   for guides on implementing OAuth2 for the application.
#   """
#   creds, _ = google.auth.default()

#   try:
#     service = build("gmail", "v1", credentials=creds)
#     message = EmailMessage()

#     message.set_content("This is automated draft mail")

#     message["To"] = "kmm9570@nyu.edu"
#     message["From"] = "kmm9570@nyu.edu"
#     message["Subject"] = "Automated draft"

#     # encoded message
#     encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

#     create_message = {"raw": encoded_message}
#     # pylint: disable=E1101
#     send_message = (
#         service.users()
#         .messages()
#         .send(userId="me", body=create_message)
#         .execute()
#     )
#     print(f'Message Id: {send_message["id"]}')
#   except HttpError as error:
#     print(f"An error occurred: {error}")
#     send_message = None
#   return send_message


# if __name__ == "__main__":
#   gmail_send_message()


import os.path
import base64
from pathlib import Path
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Use gmail.send so you can send messages
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Get the directory where this script is located
EMAIL_AGENT_DIR = Path(__file__).resolve().parent

def gmail_send_message(emailto, subject, body):
    # Use absolute paths based on script location
    token_path = EMAIL_AGENT_DIR / "token.json"
    credentials_path = EMAIL_AGENT_DIR / "credentials.json"
    
    creds = None
    # Load saved credentials if they exist
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {credentials_path}. "
                    "Please ensure the Google OAuth credentials file is in the email_sending_agent directory."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    # Build the Gmail API service
    service = build("gmail", "v1", credentials=creds)

    # Create the email
    message = EmailMessage()
    message.set_content(body)

    message["To"] = emailto
    message["From"] = "kmm9570@nyu.edu"  # Must match logged-in account
    message["Subject"] = subject

    # Encode and send
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}

    send_message = (
        service.users().messages().send(userId="me", body=create_message).execute()
    )
    print(f'Message sent! Message Id: {send_message["id"]}')

if __name__ == "__main__":
    gmail_send_message(
        "kmm9570@nyu.edu",
        "Test: Cognium Email Agent",
        "This is a test email sent from the email_sending_agent.",
    )
