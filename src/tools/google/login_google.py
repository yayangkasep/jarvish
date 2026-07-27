import os
import sys

from config import paths

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
# We request full Gmail access and Calendar/Drive access if needed later.
# For now, just Gmail readonly and send.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/tasks",
]


def main():
    """Shows basic usage of the Gmail API.
    Logs the user in and saves the token.json file.
    """
    import dotenv
    dotenv.load_dotenv(paths.get_env_file())
    
    data_dir = paths.get_data_dir()
    token_path = os.path.join(data_dir, "token.json")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not set in .env")
        return

    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": "jarvish-google",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret
        }
    }

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"Warning: Could not load existing token.json (it might be missing a refresh_token): {e}")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("No valid token found. Please visit the URL below to authorize:")
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            # Run local server on port 8080 (must match what's allowed in Google Console)
            # prompt='consent' forces Google to issue a new refresh_token even if previously authorized
            creds = flow.run_local_server(port=8080, open_browser=False, prompt='consent')

        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())
            print(f"\nSuccess! Credentials saved to {token_path}")
            print("Jarvish can now access your Gmail securely!")
    else:
        print(f"Credentials are already valid and saved at {token_path}")


if __name__ == "__main__":
    main()
