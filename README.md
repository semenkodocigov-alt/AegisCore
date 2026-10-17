# Aegis Core

Aegis Core is a local-first Windows desktop workspace. The React interface is
hosted in a frameless PyWebView window and calls the Python scanner, account
store, and quarantine manager through a local native bridge.

## Features

- Email registration and sign-in, guest sessions, and editable account details
- Zinc, slate, near-black, and warm-light themes
- On-demand single-file, quick-folder, and bounded extended scans
- Local quarantine with restore and permanent-delete actions
- Local SQLite account storage with salted PBKDF2 password hashes

Aegis Core does not continuously monitor files. File contents are not uploaded;
if VirusTotal credentials are configured, file hashes may be sent for an
external lookup. The default configuration does not include an API key. Scan
results are produced by the local scanner and should not be treated as a
guarantee that a file is safe.

## Requirements

- Windows 10 or later
- Python 3.10 or later
- Node.js 18 or later (to build the frontend)

## Install and run

Install the Python dependencies from the repository root:

```powershell
pip install -r requirements.txt
```

Build the desktop interface:

```powershell
Set-Location frontend
npm install
npm run build
Set-Location ..
```

Launch Aegis Core from the repository root:

```powershell
python main.py
```

If `frontend/dist/index.html` is missing, launching the source checkout runs
`npm install` and `npm run build` automatically. Node.js 18 or later must be
installed. A standard Windows Node.js installation is detected even when its
directory has not yet been added to the current process's `PATH`. Packaged
builds must include the frontend assets and cannot build them at runtime.

## Accounts and sessions

Registration creates a local account in `aegis_users.db`. Passwords are stored
as salted PBKDF2 hashes. “Remember Me” stores the session on this device;
otherwise the session lasts only until the app closes. Guest mode is available
without registration. Guest profile details remain local to the selected
browser storage session.

## Scanning and quarantine

- **Quick scan** checks available temporary, Downloads, and Desktop folders
  with per-folder limits.
- **Extended scan** checks the home folder and selected Windows system folders,
  also with file and directory-depth limits.
- **Choose a file** lets you inspect a selected file.
- Threats reported by the local scanner can be moved to quarantine. Quarantined
  files can be restored or permanently deleted from the Quarantine tab.

## Packaging

Build the frontend first, then install PyInstaller if it is not already
available and run the project spec:

```powershell
pip install pyinstaller
pyinstaller main.spec
```

## Project entry points

- `main.py` — desktop application entry point
- `desktop_app.py` — PyWebView window and native API bridge
- `frontend/` — React and TypeScript interface
- `scanner.py` — local file scanner
- `backend/` — local account database and authentication helpers
- `quarantine.py` — local quarantine manager
- `gui_app.py` and `gui/` — legacy Tkinter interface code
