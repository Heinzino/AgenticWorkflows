#!/usr/bin/env python3
"""
Google Sheets and Drive helper functions.
Handles authentication and common operations.
"""

import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes needed for Sheets, Drive, and Docs
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents.readonly'
]

def get_credentials():
    """Get or refresh Google API credentials."""
    creds = None
    base_path = Path(__file__).parent.parent
    token_path = base_path / 'token.json'
    creds_path = base_path / 'credentials.json'

    # Load existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save for next time
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds


def read_sheet(spreadsheet_id, range_name='Sheet1'):
    """Read data from a Google Sheet."""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    return result.get('values', [])


def list_drive_folder(folder_id):
    """List all items in a Google Drive folder."""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType)",
        pageSize=1000
    ).execute()

    return results.get('files', [])


def download_drive_file(file_id, destination_path):
    """Download a file from Google Drive to local path."""
    from googleapiclient.http import MediaIoBaseDownload
    import io

    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    request = service.files().get_media(fileId=file_id)

    # Ensure destination directory exists
    Path(destination_path).parent.mkdir(parents=True, exist_ok=True)

    with open(destination_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")

    return destination_path


def read_google_doc(document_id):
    """Read content from a Google Doc and return as plain text."""
    creds = get_credentials()
    service = build('docs', 'v1', credentials=creds)

    doc = service.documents().get(documentId=document_id).execute()

    # Extract all text from the document
    full_text = ''
    content = doc.get('body', {}).get('content', [])

    for element in content:
        if 'paragraph' in element:
            for para_element in element['paragraph'].get('elements', []):
                if 'textRun' in para_element:
                    full_text += para_element['textRun'].get('content', '')

    return full_text


def upload_to_drive(local_path, folder_id, filename=None):
    """Upload a file to Google Drive folder."""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    if filename is None:
        filename = Path(local_path).name

    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }

    media = MediaFileUpload(local_path, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()

    return file


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python google_helpers.py sheet <spreadsheet_id> [range]")
        print("  python google_helpers.py folder <folder_id>")
        print("  python google_helpers.py download <file_id> <destination_path>")
        print("  python google_helpers.py doc <document_id>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'sheet':
        sheet_id = sys.argv[2]
        range_name = sys.argv[3] if len(sys.argv) > 3 else 'Sheet1'
        data = read_sheet(sheet_id, range_name)
        for row in data[:20]:  # Show first 20 rows
            print(row)
        print(f"\nTotal rows: {len(data)}")

    elif cmd == 'folder':
        folder_id = sys.argv[2]
        files = list_drive_folder(folder_id)
        for f in files:
            print(f"{f['name']}: {f['id']} ({f['mimeType']})")
        print(f"\nTotal items: {len(files)}")

    elif cmd == 'download':
        file_id = sys.argv[2]
        dest_path = sys.argv[3]
        result = download_drive_file(file_id, dest_path)
        print(f"Downloaded to: {result}")

    elif cmd == 'doc':
        doc_id = sys.argv[2]
        text = read_google_doc(doc_id)
        # Strip non-ASCII for Windows console display
        safe_text = text[:2000].encode('ascii', errors='replace').decode('ascii')
        print(safe_text)
        print(f"\n... Total length: {len(text)} characters")
