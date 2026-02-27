# Ghost Browser (Lab Edition)

Privacy-focused ephemeral browser shell for cybersecurity labs on Windows and Linux, built with Python + PyQt WebEngine.

## Highlights

- Ephemeral per-run browser profile (cleanup on exit)
- Default startup page is `about:blank`
- Tabs, popup-to-tab handling, and download manager panel
- Session controls: new session, clear data, reopen closed tab
- Settings dialog (persisted): startup URL, download folder/mode, proxy mode, custom proxy, user-agent
- Privacy status chips: `Proxy`, `Tor endpoint`, `Session`
- Startup proxy diagnostics with retry UX (`Retry Check`, `Continue Anyway`, `Exit`)
- Permission hardening: deny camera/mic/geolocation/notifications/clipboard requests
- Download modes: `prompt`, `auto`, `ephemeral` (auto-cleaned with session profile)

This project is for legitimate privacy/lab use, not anti-forensics/evasion.

## Requirements

- Python 3.9+
- PyQt5
- PyQtWebEngine

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Run

From repo root:

```bash
python ghost_browser.py
```

Or as module:

```bash
python -m ghost_browser
```

## CLI

```bash
python -m ghost_browser --help
```

Examples:

```bash
# Start with Tor SOCKS proxy
python -m ghost_browser --tor

# Custom proxy + strict startup check
python -m ghost_browser --proxy socks5://127.0.0.1:9050 --strict-proxy

# Skip startup proxy check
python -m ghost_browser --proxy socks5://127.0.0.1:9050 --skip-proxy-check

# Override download mode
python -m ghost_browser --download-mode auto

# Use a RAM-disk profile location
python -m ghost_browser --profile-root /mnt/ramdisk
```

Windows PowerShell:

```powershell
python -m ghost_browser --tor --strict-proxy
python -m ghost_browser --start-url about:blank
```

## Settings UI

Open `Settings -> Preferences` (or `Ctrl+,`) to configure:

- Startup URL
- Download folder
- Download mode (`prompt`, `auto`, `ephemeral`)
- Proxy mode (`off`, `tor`, `custom`)
- Custom proxy URL
- User-agent override

Notes:

- Proxy changes are saved and applied on next launch.
- Download mode and user-agent updates apply immediately.

## UI shortcuts

- `Ctrl+T`: New tab
- `Ctrl+W`: Close current tab
- `Ctrl+Shift+T`: Reopen closed tab
- `Ctrl+Shift+N`: Start new session
- `Ctrl+,`: Open settings
- Right-click tab: duplicate/reload/copy URL/close others/close right/reopen

## Tests

```bash
python -m pytest -q tests -p no:cacheprovider
```

## Packaging (Windows)

Build script with icon/version metadata:

```powershell
# One-file EXE (default)
.\scripts\build.ps1 -Mode onefile -Name ghost_browser

# One-dir build (faster startup)
.\scripts\build.ps1 -Mode onedir -Name ghost_browser
```

Artifacts:

- `dist\ghost_browser.exe` for `onefile`
- `dist\ghost_browser\ghost_browser.exe` for `onedir`

### Optional code signing

If you have a signing certificate:

```powershell
.\scripts\build.ps1 -Mode onefile -Name ghost_browser -Sign -CertPath C:\path\to\cert.pfx -CertPassword "your-password"
```

If no certificate is available, signing is skipped.
