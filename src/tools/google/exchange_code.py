import os
import sys

from config import paths

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def main(code):
    import dotenv
    dotenv.load_dotenv(paths.get_env_file())
    
    data_dir = paths.get_data_dir()
    token_path = os.path.join(data_dir, "token.json")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing from .env")
        return None

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

    flow = InstalledAppFlow.from_client_config(
        client_config, SCOPES, redirect_uri="http://localhost:8080/"
    )
    flow.fetch_token(code=code)

    creds = flow.credentials
    with open(token_path, "w") as token:
        token.write(creds.to_json())
        print(f"Success! Credentials saved to {token_path}")


if __name__ == "__main__":
    main(sys.argv[1])
