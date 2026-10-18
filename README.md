# Aegis Core

Aegis Core is a local-first Windows desktop workspace. The React interface is
hosted in a frameless PyWebView window and calls the Python scanner, account
store, and quarantine manager through a local native bridge.

## Features

- Email registration and sign-in, guest sessions, and editable account details
- Russian and English interface, with the selected language saved on this device
- Zinc, slate, near-black, and warm-light themes
- On-demand single-file, quick-folder, and bounded extended scans
- Full system scans across fixed drives and critical Windows locations, with
  live progress, pause/resume, cancellation, and inaccessible-path skipping
- Windows UAC elevation request at startup, with the current privilege level
  shown in the workspace
- Optional VirusTotal API v3 hash lookups, with separately enabled uploads
- Optional native C++17 acceleration for file hashing, signature lookups,
  entropy calculation, and directory traversal
- Local quarantine with restore and permanent-delete actions
- Local SQLite account storage with salted PBKDF2 password hashes

Aegis Core does not continuously monitor files. File contents are not uploaded;
if VirusTotal is enabled, file hashes are sent for an external lookup. Unknown
files are not uploaded unless the separate upload option is enabled; that
option only uploads files smaller than 32 MB and sends their contents to
VirusTotal. The API key is protected with Windows DPAPI and saved in the local
SQLite settings table. Scan results are not a guarantee that a file is safe.

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

On Windows, Aegis Core requests administrator access through UAC at startup.
If elevation is declined or unavailable, the app continues with standard
privileges and may skip protected files during a full system scan.

If `frontend/dist/index.html` is missing, launching the source checkout runs
`npm install` and `npm run build` automatically. Node.js 18 or later must be
installed. A standard Windows Node.js installation is detected even when its
directory has not yet been added to the current process's `PATH`. Packaged
builds must include the frontend assets and cannot build them at runtime.

On Windows, the scanner lazily compiles `native_scanner.cpp` on the first scan
when `g++` or `clang++` is available, caching the DLL under the system
temporary directory. If compilation or native loading fails, hashing,
signature matching, entropy calculation, and directory traversal fall back to
Python implementations without blocking application startup.

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
- **Full system scan** walks all available fixed drives and critical Windows
  paths, skips inaccessible files and reparse points, and can be paused,
  resumed, or stopped. The total file count is discovered as the scan runs.
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

The Windows executable is written to `dist/AegisCore.exe`.

## Project entry points

- `main.py` — desktop application entry point
- `desktop_app.py` — PyWebView window and native API bridge
- `frontend/` — React and TypeScript interface
- `scanner.py` — local file scanner
- `backend/` — local account database and authentication helpers
- `quarantine.py` — local quarantine manager
- `gui_app.py` and `gui/` — legacy Tkinter interface code
