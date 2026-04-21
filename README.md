# ⚡ NexFetch v2.9
**Universal Media Downloader & Info Tool**
Author: fgradeartist · License: MIT · Python 3.10–3.13

---

## Quick Start — 3 Steps

1. Extract this ZIP anywhere (e.g. your Desktop)
2. Double-click **`START_NEXFETCH.bat`**
3. First launch installs everything automatically (1–3 min), then the login screen appears

> **If nothing happens:** Double-click **`START_DEBUG.bat`** instead — it shows the exact error

---

## Requirements

| Requirement | Notes |
|---|---|
| **Windows 10 or 11** | macOS/Linux: run `python NexFetch.py` directly |
| **Python 3.10–3.13** | Download from [python.org](https://www.python.org/downloads/) |
| **"Add Python to PATH"** | Must tick this box during Python install |
| Internet connection | For first-time setup and all downloads |

> Python 3.14 has a known UI bug. Use Python 3.13 for best results.

---

## Launcher Files

| File | Purpose |
|---|---|
| `START_NEXFETCH.bat` | Normal launch — no CMD window appears |
| `START_DEBUG.bat` | Shows all errors — use when something breaks |
| `RESET_SETUP.bat` | Deletes setup flag so setup runs again |
| `BUILD_EXE.bat` | Builds a standalone .exe with your logo |

---

## Using the Web UI

NexFetch includes a premium dark web interface (your uploaded design). Here is how to use it:

**Step 1** — Double-click `START_NEXFETCH.bat` and log in normally.

**Step 2** — Click the **🌐** button in the top-right of the app header (next to your username).

**Step 3** — Your browser opens automatically at `http://127.0.0.1:7432`.

**Step 4** — Use the browser UI — all downloads go to your real folder on disk.

The Python app must be running for the web UI to work. If the browser shows a blank or black screen, check that NexFetch.py is still open in the background. If the footer shows "Server offline", restart NexFetch and click 🌐 again.

The browser UI and the desktop app share the same download engine. Files are saved to the same folder regardless of which interface you use.

---

## Custom Logo

To use your own logo or icon:

1. Put your image in the `assets/` folder
2. Name it `logo.png` (PNG format, square is best)
3. Restart NexFetch — the header, login screen, and taskbar icon update automatically
4. GIF files work too — animated GIFs are supported for both logo and background

To get the logo on the EXE icon:
1. Place `logo.png` in `assets/` first
2. Run `BUILD_EXE.bat` — it converts to `.ico` automatically during build

---

## Build as Standalone EXE

1. Place your `logo.png` in `assets/` (optional but recommended)
2. Run `BUILD_EXE.bat`
3. Wait 1–2 minutes for the build to complete
4. Open `NexFetch_EXE\NexFetch\`
5. Right-click `NexFetch.exe` → Send to → Desktop (create shortcut)
6. Right-click the shortcut → Pin to taskbar

The EXE is a folder (`NexFetch_EXE\NexFetch\`), not a single file. Always move the entire folder together — never just the `.exe`.

---

## Account System

### Creating an Account
- Click CREATE ACCOUNT on the login screen
- Fill in: Full Name, Username, Email, Password, Invite Code
- Default invite code: `NEXFETCH2024`
- The first user registered becomes Admin automatically
- No location or phone number required

### Recovery Phrases
When you create an account, 12 random words are shown once. Write them down — they are never shown again. If you forget your password, click "Forgot password?", type your phrases, and set a new password.

### Quick Login
After logging in once, your username appears as a button on the login screen. Click your name, type password, done.

### Switch Accounts
Click **⇄ Switch** in the header. A login overlay appears over the current window — no blank screen, no restart.

---

## Feature Guide

### Download Tab
Paste one or more URLs (one per line). Supports 1000+ sites including YouTube, Instagram, TikTok, Twitter/X, Facebook, Reddit, Twitch, SoundCloud, Vimeo, and more.

Clip download: Enter start time and end time (e.g. 2:00 and 2:30) to download only that portion of a video. Select an aspect ratio (original, 16:9, 9:16, 1:1, 4:3) to crop the output.

The queue pauses and resumes — progress is saved between sessions. Duplicate URLs are detected and skipped automatically.

### Music Tab
Paste YouTube Music URLs, Spotify URLs, or type a song name like "Artist - Song Title". Full playlists are supported — paste the playlist URL.

Album art is embedded as 1:1 square directly into the audio file. No separate image file is created. Lyrics are saved as a `.lrc` sidecar file next to the MP3 — Apple Music, most media players, and streaming apps read this file automatically. Artist, album, year, and track number are all embedded in the file metadata.

Spotify links use spotdl as a fallback. YouTube Music is the primary source.

### Scraper Tab
Scrapes all video or post links from a channel or profile and saves them to a `.txt` file.

Supported platforms: YouTube channels and playlists, Instagram public profiles, Facebook pages, TikTok users, Reddit users and subreddits, Twitter/X users, and adult sites (Pornhub, xHamster, xnxx, RedTube, and others via yt-dlp).

If the primary scraping method fails, the tool automatically tries a fallback method.

### Images Tab
Downloads images from social media profiles. Instagram requires logging in via the login form in this tab. Supports Pinterest boards, Reddit, Twitter/X, and Tumblr. Auto-detect mode works for most platforms.

### Ecommerce Tab
Scrapes product listings from online stores. Works with AliExpress, Alibaba, Amazon, eBay, Daraz, Ramsha, Laam, and most other stores.

Extracts: product number, category, title, price, sale price, URL, image count, video count, and description. The CSV is sorted by category. When image download is enabled, product images are saved into per-product folders named after the product title.

### Account Tab
Profile photo (PNG, JPG, or animated GIF), display name, email, phone, date of birth, and bio. Notes and to-do list — shown as a reminder notification when the app opens. Save Photo saves your avatar immediately. Save Notes saves your notes immediately. Save All saves everything at once.

Admin users see an admin panel where they can reset or delete any account.

### Settings Tab
All users can change the download folder and run maintenance tasks (update yt-dlp, re-download ffmpeg, re-run setup, clear logs).

Admin users additionally control: tool name, author, version, license, invite codes (multiple codes supported — one per line, any valid code works for registration), access control, color theme, font family and size, logo, and background image.

---

## File Structure

```
NexFetch/
├── NexFetch.py              ← Main launcher
├── START_NEXFETCH.bat       ← Normal launch (no CMD window)
├── START_DEBUG.bat          ← Debug launch (shows errors)
├── START_SILENT.vbs         ← Used internally to hide CMD
├── BUILD_EXE.bat            ← Build standalone EXE
├── RESET_SETUP.bat          ← Reset first-time setup
├── README.md                ← This guide
├── core/
│   ├── app.py               ← Main app code
│   └── server.py            ← Local web server (port 7432)
├── web/
│   └── index.html           ← Web UI (opened by 🌐 button)
├── assets/
│   └── logo.png             ← Put your logo here
├── userdata/username/       ← Per-user saved data
├── ffmpeg_bin/              ← Auto-downloaded ffmpeg
├── users.json               ← User accounts (hashed passwords)
├── config.json              ← App settings
├── saved_logins.json        ← Quick-login list
└── .setup_complete          ← Setup skip flag
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| BAT closes instantly | Run START_DEBUG.bat — copy the error for support |
| TclError Layout not found | Python 3.14 bug — install Python 3.13 |
| Import Error on launch | Run RESET_SETUP.bat then START_NEXFETCH.bat |
| Web UI shows black screen | NexFetch.py must be running first — start it, then click 🌐 |
| Web UI shows "Server offline" | Python app is not running — start NexFetch first |
| Downloads not in folder | Check Settings → Download Folder path |
| CMD window appears | Use START_NEXFETCH.bat, not python NexFetch.py directly |
| EXE not found after build | Look in NexFetch_EXE\NexFetch\NexFetch.exe |
| Switch user goes black | Fixed in v2.9 — uses overlay, no blank screen |
| Spotify downloads fail | Paste song name directly — YouTube Music is more reliable |
| Instagram profile not found | Private profile — log in via the Images tab first |
| Instagram 2FA error | Temporarily disable 2FA in Instagram Security settings |
| Setup runs every launch | Check that .setup_complete file exists in the app folder |
| Music lyrics not working | The .lrc file must be in the same folder as the MP3 |
| Album art not embedding | ffmpeg required — Settings → Re-download ffmpeg |
| Ecommerce shows N/A | Some sites block scrapers — try a product listing page instead |
| Firewall blocking web UI | Allow port 7432 through Windows Firewall |

---

## How It Works

The desktop app (NexFetch.py) and web UI (index.html) both use the same download engine.

When you click Download in either interface, the app calls yt-dlp (a command-line tool that supports 1000+ video sites). yt-dlp fetches the content, ffmpeg merges audio and video if needed, and the file is saved to your chosen folder.

The web UI works by sending requests to a local server running at port 7432. The Python app receives these requests and runs yt-dlp. The browser never directly downloads or saves files — that is always handled by Python.

---

## Dependencies (installed automatically)

| Package | Purpose |
|---|---|
| yt-dlp | Core download engine |
| spotdl | Spotify downloads |
| instaloader | Instagram scraping |
| requests | HTTP for ecommerce scraper |
| Pillow | Image processing and GIF support |
| beautifulsoup4 | HTML parsing |
| lxml | Fast HTML parser |
| mutagen | Audio metadata |
| ffmpeg | Video/audio processing (downloaded separately) |

---

*NexFetch v2.9 · Python · yt-dlp · spotdl · instaloader · MIT License*
