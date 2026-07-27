import os
import sys

from core.google_auth import GoogleAuthManager
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.message import EmailMessage


class GmailReadTool:
    def __init__(self):
        self.ToolName = "ReadRecentEmails"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Membaca email terbaru dari akun Gmail pengguna (termasuk folder spam, kotak masuk, dll).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Pencarian spesifik, misalnya 'in:spam' untuk folder spam, 'is:unread', 'from:budi', atau dibiarkan kosong untuk kotak masuk umum.",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
        self.auth_manager = GoogleAuthManager()

    def Execute(self, Arguments):
        query = Arguments.get("query", "")
        creds = self.auth_manager.GetCredentials()

        if not creds:
            return "Error: Kredensial Google belum diatur. Tolong jalankan tools/login_google.py."

        try:
            service = build("gmail", "v1", credentials=creds)
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=5)
                .execute()
            )
            messages = results.get("messages", [])

            if not messages:
                return "Tidak ada email yang ditemukan."

            output = []
            for msg in messages:
                msg_data = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg["id"],
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    )
                    .execute()
                )
                headers = msg_data.get("payload", {}).get("headers", [])

                subject = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"].lower() == "subject"
                    ),
                    "Tanpa Subjek",
                )
                sender = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"].lower() == "from"
                    ),
                    "Tidak Diketahui",
                )
                date = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"].lower() == "date"
                    ),
                    "Waktu Tidak Diketahui",
                )
                snippet = msg_data.get("snippet", "")

                output.append(
                    f"Dari: {sender}\nSubjek: {subject}\nTanggal: {date}\nIsi Singkat: {snippet}\n---"
                )

            return "\n".join(output)

        except HttpError as error:
            return f"Terjadi kesalahan pada API Gmail: {error}"


class GmailSendTool:
    def __init__(self):
        self.ToolName = "SendEmail"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Mengirim sebuah email menggunakan akun Gmail pengguna.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Alamat email penerima.",
                        },
                        "subject": {"type": "string", "description": "Subjek email."},
                        "body": {"type": "string", "description": "Isi pesan email."},
                    },
                    "required": ["to", "subject", "body"],
                },
            },
        }
        self.auth_manager = GoogleAuthManager()

    def Execute(self, Arguments):
        to = Arguments.get("to")
        subject = Arguments.get("subject")
        body = Arguments.get("body")

        creds = self.auth_manager.GetCredentials()

        if not creds:
            return "Error: Kredensial Google belum diatur. Tolong jalankan tools/login_google.py."

        try:
            service = build("gmail", "v1", credentials=creds)

            profile = service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "me")

            message = EmailMessage()
            message.set_content(body)
            message["To"] = to
            message["From"] = user_email
            message["Subject"] = subject

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            return f"Email sukses dikirim! Message Id: {send_message['id']}"

        except HttpError as error:
            return f"Terjadi kesalahan pada API Gmail saat mengirim: {error}"
