# Daily Video Upload - NBA Picks

## Goal
Automatically download videos from Google Drive folders, match them with descriptions from a Google Doc, generate platform-specific captions, and upload to YouTube, Twitter/X, and Instagram.

## Schedule
Daily at 8:40 PM Mountain Time (America/Edmonton)

## Inputs
- **Google Drive Folder**: `1Rn6ueiZqoLg9NJSrBGOw0PoXANgnxN_8`
  - Contains subfolders: HANS, GRIFFIN, LANDON, NADIA (skip), DESCRIPTIONS
- **Google Doc (Descriptions)**: `1cBJM2vG9_X91o29OjLgzuJFIBzKkAiLJliZROum160s`
  - Format: Person name on its own line, followed by their caption text

## Account Mapping
| Folder Name | Account ID |
|-------------|------------|
| GRIFFIN | griffinSports |
| HANS | hansPicks |
| LANDON | landonBets |
| NADIA | SKIP (do not process) |

## Tools/Scripts
- `execution/daily_video_upload.py` - Main execution script
- `execution/google_helpers.py` - Google API helpers (Docs, Drive, Sheets)

## Workflow Steps

1. **Read Google Doc**
   - Fetch the descriptions document
   - Parse to extract person → caption mapping
   - Each section starts with the person's name (GRIFFIN, HANS, LANDON, NADIA)

2. **List Drive Folders**
   - Get all subfolders from the main folder
   - Filter out NADIA and DESCRIPTIONS

3. **For Each Folder (GRIFFIN, HANS, LANDON)**
   - List files in the folder
   - Find the video file (mp4, mov, etc.)
   - Download to `.tmp/`
   - Match folder name to caption from the doc
   - Map folder name to account ID

4. **Generate Platform Captions**
   - POST to `https://socialzap.app.n8n.cloud/webhook/caption-generator`
   - Body: `{"Caption": "<the raw caption from doc>"}`
   - Response contains: `YT_Title`, `TwitterCaption`, `Caption` (Instagram)

5. **Upload to Platforms**
   - POST multipart/form-data to `https://api.upload-post.com/api/upload`
   - Include video file and all platform-specific fields
   - See execution script for full field list

## Outputs
- Videos uploaded to YouTube, Twitter/X, Instagram for each account
- Upload results logged to console

## Environment Variables Required
```
UPLOAD_POST_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Edge Cases & Learnings
- Skip NADIA folder entirely
- Skip DESCRIPTIONS folder (it's a Google Doc, not a folder with videos)
- If no video found in a folder, log warning and continue
- If caption parsing fails for a person, use folder name as fallback caption
- Caption generator webhook may return array - handle `[0].output` format
- Google Doc parsing: sections are separated by the person's name on its own line

## Manual Run
```bash
python execution/daily_video_upload.py
```

## Scheduled Run
Use Windows Task Scheduler or cron:
```bash
# cron (Linux/Mac)
40 20 * * * cd /path/to/AgenticWorkflows && python execution/daily_video_upload.py

# Windows Task Scheduler
# Action: python
# Arguments: execution/daily_video_upload.py
# Start in: C:\Users\heinz\OneDrive\Desktop\REPO\AgenticWorkflows
# Trigger: Daily at 8:40 PM
```
