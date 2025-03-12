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

---

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
```

### 2. Obtain Credentials

#### a. Telegram Bot Token
1. Open Telegram and start a chat with **@BotFather**.  
2. Send `/newbot` and follow prompts to name your bot.  
3. **BotFather** will reply with a token like:
   ```
   123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```
4. Keep this token safe. In `docker-compose.yml`, set `TELEGRAM_BOT_TOKEN` to this value (without quotes if possible).  

#### b. Telegram Chat ID
1. Use **@userinfobot** or **@RawDataBot** to retrieve your user ID.  
2. Start your newly created bot in a private chat.  
3. Your ID might look like `556793657`. In `docker-compose.yml`, set `TELEGRAM_CHAT_ID` to that ID. If using a group chat, it typically starts with `-100`.  

#### c. Plex Token
1. Open Plex in your browser (e.g., `http://localhost:32400/web`).  
2. Open Developer Tools (`F12`), watch the Network tab as you navigate.  
3. Look for `X-Plex-Token=...` in the request headers or query params.  
4. Copy that token and place it in `docker-compose.yml` under `PLEX_TOKEN`. Example:
   ```yaml
   PLEX_TOKEN='BJgw6LoCZrUz_58fS4Cf3&X'
   ```

### 3. Configure Docker Compose
Replace placeholders (`<YOUR_PLEX_TOKEN>`, `<YOUR_TELEGRAM_BOT_TOKEN>`, `<YOUR_CHAT_ID>`) with your actual values:

```yaml
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
      - "8080:8080"
      - "8999:8999/tcp"
      - "8999:8999/udp"
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
      - PLEX_TOKEN='<YOUR_PLEX_TOKEN>'
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
```

---

## Build & Run

```bash
docker-compose up -d --build
```

- `-d` runs in detached mode.  
- `--build` ensures the automation container is rebuilt.  

Check logs:

```bash
docker-compose logs -f automation
```

---

## Usage

### qBittorrent Web UI
- Go to `http://localhost:8080` in your browser.  
- Default credentials: `admin/adminadmin` (refer to linuxserver/qbittorrent docs).  

### Plex
- Access at `http://localhost:32401/web`.  
- Automation script triggers a Plex library refresh when a torrent finishes.  

### Flask Dashboard
- Visit `http://localhost:5001` for real-time logs, torrent statuses, and download history.  

### Telegram Commands
- `/status` – Quick status of active torrents.  
- `/summary` – Inline menu with Pause, Resume, Delete options.  
- `/addtorrent <link>` – Add a new torrent via magnet or URL.  
- `/stop` – Stop the automation container.  

---

## Contributing

1. Fork this repo and create a **feature branch**.  
2. Commit your changes and open a **Pull Request**.  

---

## License

```text
MIT License
```

Enjoy ZynkStream! 🚀
