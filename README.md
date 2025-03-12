Part 1 – Project Introduction & Features

# ZynkStream

ZynkStream is a **Dockerized** automation solution that integrates **qBittorrent**, **Plex**, and a **Telegram bot** to streamline torrent downloads and automatically refresh Plex. It also provides a **Flask-based dashboard** on port `5001` for real-time monitoring.

---

## Table of Contents

1. [Features](#features)  
2. [Prerequisites](#prerequisites)  
3. [Installation & Setup](#installation--setup)  
   - [1. Clone the Repository](#1-clone-the-repository)  
   - [2. Obtain Credentials](#2-obtain-credentials)  
     - [a. Telegram Bot Token](#a-telegram-bot-token)  
     - [b. Telegram Chat ID](#b-telegram-chat-id)  
     - [c. Plex Token](#c-plex-token)  
   - [3. Configure Docker Compose](#3-configure-docker-compose)  
   - [4. Build & Run](#4-build--run)  
4. [Usage](#usage)  
   - [qBittorrent Web UI](#qbittorrent-web-ui)  
   - [Plex](#plex)  
   - [Flask Dashboard](#flask-dashboard)  
   - [Telegram Commands](#telegram-commands)  
5. [Additional Notes](#additional-notes)  
   - [A. Ports & Firewall](#a-ports--firewall)  
   - [B. Ampersand in Plex Token](#b-ampersand-in-plex-token)  
   - [C. Common Troubleshooting](#c-common-troubleshooting)  
6. [Contributing](#contributing)  
7. [License](#license)

---

## Features

- **Automated File Monitoring**: Monitors qBittorrent’s completed downloads, then moves them into Plex’s media folder.  
- **Telegram Bot Integration**: Add/pause/resume/delete torrents, get status updates, and `/stop` automation – all via Telegram.  
- **Real-Time Flask Dashboard**: Access logs, torrent progress, and download history at `http://localhost:5001`.  
- **Plex Library Refresh**: Automatically refreshes Plex each time a new download is moved.  
- **Easy Docker Compose Setup**: Spin up qBittorrent, Plex, and the automation container with a single command.


Part 2 – Prerequisites, Installation & Setup

## Prerequisites

- **Docker** and **Docker Compose** installed on your host machine.  
- **Telegram account** to create a bot (via [@BotFather](https://t.me/botfather)).  
- **Plex** setup if you want library refreshes (not strictly required if you only want torrent + Telegram features).

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/ZynkStream.git
cd ZynkStream

In this folder, you should find:

automation/ (Dockerfile + Python scripts)
docker-compose.yml
(Optionally) .gitignore, LICENSE, README.md


2. Obtain Credentials
a. Telegram Bot Token
1. Open Telegram and start a chat with @BotFather.
2. Send /newbot and follow prompts to name your bot.
3. BotFather will reply with a token like:

123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

4. Keep this token safe. In docker-compose.yml, set TELEGRAM_BOT_TOKEN to this value (without quotes if possible).

b. Telegram Chat ID
Use @userinfobot or @RawDataBot to retrieve your user ID.
Then /start your newly created bot in a private chat.
Your ID might look like 556793657.
In docker-compose.yml, set TELEGRAM_CHAT_ID to that ID. If using a group chat, it typically starts with -100.

c. Plex Token
If you want Plex to refresh automatically:

Open Plex in your browser (e.g., http://localhost:32400/web).
Open Developer Tools (F12), watch the Network tab as you navigate.
Look for X-Plex-Token=... in the request headers or query params.
Copy that token, e.g. BJgw5LocZrUz_5284Cf3&X.
Place it in docker-compose.yml under PLEX_TOKEN, e.g. PLEX_TOKEN='BJgw5LocZrUz_5284Cf3&X'.

3. Configure Docker Compose
Below is an example docker-compose.yml. Replace <YOUR_PLEX_TOKEN>, <YOUR_TELEGRAM_BOT_TOKEN>, <YOUR_CHAT_ID> with your own:

services:
  qbittorrent:
    image: linuxserver/qbittorrent
    container_name: qbittorrent
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/London
    volumes:
      - /mnt/d/DownloadedMovies/config/qbittorrent:/config
      - /mnt/d/DownloadedMovies/torrent-files:/watch
      - /mnt/d/DownloadedMovies/torrent-downloaded-files:/downloads
    ports:
      - "8080:8080"         # Web UI
      - "8999:8999/tcp"     # Torrent traffic (TCP)
      - "8999:8999/udp"     # Torrent traffic (UDP)
    restart: unless-stopped

  plex:
    image: linuxserver/plex
    container_name: plex
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/London
    volumes:
      - /mnt/d/DownloadedMovies/plex-config:/config
      - /mnt/d/DownloadedMovies/downloads:/movies
    ports:
      - "32401:32400"
    restart: unless-stopped

  automation:
    build: ./automation
    container_name: automation
    environment:
      - DOWNLOADS_DIR=/downloads
      - PLEX_MEDIA_DIR=/plex/movies
      - PLEX_URL=http://plex:32400
      - PLEX_SECTION_ID=1
      - PLEX_TOKEN='<YOUR_PLEX_TOKEN>'         # e.g., 'BJgw5LocZrUz_5284Cf3&X'
      - TELEGRAM_BOT_TOKEN=<YOUR_TELEGRAM_BOT_TOKEN>
      - TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
    volumes:
      - /mnt/d/DownloadedMovies/torrent-downloaded-files:/downloads
      - /mnt/d/DownloadedMovies/downloads:/plex/movies
    depends_on:
      - qbittorrent
      - plex
    ports:
      - "5001:5000"
    restart: unless-stopped

</details>

---

## **Part 3** – Build & Run, Usage, Additional Notes

<details>
<summary>Click to Expand Part 3</summary>

```markdown
### 4. Build & Run

```bash
docker-compose up -d --build


-d runs in detached mode.
--build ensures the automation container is rebuilt.
Then check logs:

docker-compose logs -f automation


Usage
qBittorrent Web UI
Go to http://localhost:8080 in your browser.
Default creds might be admin/adminadmin (see linuxserver/qbittorrent docs).
Plex
Access at http://localhost:32401/web.
When a torrent finishes, the automation script triggers a Plex library refresh.
Flask Dashboard
Visit http://localhost:5001.
Real-time view of torrent statuses, logs, error messages, and completed download history.
Telegram Commands
/status – Quick textual status of active torrents.
/summary – Inline menu with Pause, Resume, Delete options.
/addtorrent <link> – Add a new torrent from a magnet or .torrent URL.
/stop – Stop the automation container.
(Make sure you /start your bot in Telegram so it can message you.)

Additional Notes
A. Ports & Firewall
qBittorrent: UI at 8080, torrent port 8999 (TCP+UDP).
Plex: Mapped to 32401:32400.
Automation: Flask UI at 5001:5000.
If running behind a firewall or NAT, you might need to open or forward these ports. If you see “stalled” torrents, confirm both TCP and UDP are mapped for your chosen port.

B. Ampersand in Plex Token
If your Plex token includes &, put it in single quotes: PLEX_TOKEN='BJgw5LocZrUz_5284Cf3&X'.

C. Common Troubleshooting
“Invalid Token”: Usually means your Telegram bot token is typed incorrectly or you included extra quotes.
“Bad Request: chat not found”: You might have an incorrect chat ID. Use @userinfobot to verify.
Stalled Torrents: Ensure 8999:8999/tcp and 8999:8999/udp are mapped, so inbound connections are allowed.

</details>

---

## **Part 4** – Contributing & License

<details>
<summary>Click to Expand Part 4</summary>

```markdown
## Contributing

1. Fork this repo and create a **feature branch** in your fork.  
2. Commit your changes and open a **Pull Request** against the main repo.  
3. Describe what your changes do (fix a bug, add a feature, etc.).

---

## License

```text
MIT License

Copyright (c) 2025 

Permission is hereby granted, free of charge, to any person obtaining ...
[Full MIT License text]


Enjoy ZynkStream! This solution should help you effortlessly automate torrent downloads with qBittorrent, auto-move them to Plex, and manage everything via a Telegram bot. If you have issues or suggestions, feel free to open a GitHub issue or create a Pull Request.