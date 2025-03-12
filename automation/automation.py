import sys
import atexit
atexit.register(lambda: sys.stdout.flush())

import os
import time
import shutil
import threading
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import InvalidToken
from flask import Flask, render_template_string, Response
from threading import Thread

# Environment Variables
PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400")
PLEX_SECTION_ID = os.environ.get("PLEX_SECTION_ID", "1")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "your_plex_token")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "your_telegram_chat_id")
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", "/downloads")
PLEX_MEDIA_DIR = os.environ.get("PLEX_MEDIA_DIR", "/plex/movies")

# Global status variables and counters
status_message = "No downloads in progress."
successful_downloads = 0
failed_downloads = 0

# Track completed & active torrents
completed_torrents = set()
previous_torrent_status = {}
torrent_hash_map = {}  # Maps torrent hash to name for interactive actions

# Logging arrays (for demonstration)
download_history = []
error_logs = []

# ------------- Utility Functions -------------
def progress_bar(progress, bar_length=20):
    filled_length = int(round(bar_length * progress))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    return f"|{bar}| {int(progress * 100)}%"

def refresh_plex():
    try:
        url = f"{PLEX_URL}/library/sections/{PLEX_SECTION_ID}/refresh?X-Plex-Token={PLEX_TOKEN}"
        response = requests.get(url)
        if response.ok:
            print("Plex library refreshed.")
            return "Plex library refreshed."
        else:
            err_msg = f"Failed to refresh Plex library: {response.text}"
            error_logs.append(err_msg)
            return err_msg
    except Exception as e:
        err_msg = f"Error refreshing Plex: {e}"
        error_logs.append(err_msg)
        return err_msg

def send_telegram(message):
    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(telegram_url, data=payload)
        if response.ok:
            print("Telegram notification sent:", message)
        else:
            err_msg = f"Telegram notification failed: {response.text}"
            error_logs.append(err_msg)
            print(err_msg)
    except Exception as e:
        err_msg = f"Error sending Telegram notification: {e}"
        error_logs.append(err_msg)
        print(err_msg)

# ------------- File Monitoring -------------
def process_new_file(src_path):
    global status_message, successful_downloads, failed_downloads
    filename = os.path.basename(src_path)
    try:
        time.sleep(1)
        dest_path = os.path.join(PLEX_MEDIA_DIR, filename)
        status_message = f"Download finished: {filename}"
        send_telegram(f"Download finished for: {filename}")
        print(f"Moving {src_path} to {dest_path}")
        shutil.move(src_path, dest_path)
        refresh_msg = refresh_plex()
        send_telegram(f"New movie '{filename}' added to Plex library.\n{refresh_msg}")
        status_message = f"Download completed & Plex refreshed: {filename}"
        successful_downloads += 1

        # Log to download_history
        download_history.append({"file": filename, "time": time.ctime(), "status": "Completed"})
    except Exception as e:
        err_msg = f"Error processing file {filename}: {e}"
        status_message = err_msg
        failed_downloads += 1
        error_logs.append(err_msg)

class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            print(f"Detected new file: {event.src_path}")
            send_telegram(f"New file detected: {os.path.basename(event.src_path)}")
            time.sleep(5)  # ensure file is completely written
            process_new_file(event.src_path)

def start_monitoring():
    event_handler = DownloadHandler()
    observer = Observer()
    observer.schedule(event_handler, DOWNLOADS_DIR, recursive=False)
    observer.start()
    print("Monitoring for new files in:", DOWNLOADS_DIR)
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# ------------- qBittorrent API Integration -------------
def qb_request(endpoint, method="GET", data=None, **kwargs):
    session = requests.Session()
    session.post("http://qbittorrent:8080/api/v2/auth/login", data={"username": "admin", "password": "admin123"})
    url = f"http://qbittorrent:8080/api/v2/{endpoint}"
    if method == "POST":
        return session.post(url, data=data, **kwargs)
    return session.get(url, **kwargs)

def poll_qbittorrent_status():
    global previous_torrent_status, completed_torrents, torrent_hash_map
    try:
        response = qb_request("torrents/info", timeout=5)
        if response.ok:
            torrents = response.json()
            if not torrents:
                previous_torrent_status.clear()
                return "No torrents in progress."
            statuses = []
            for t in torrents:
                name = t.get("name", "Unknown")
                progress = t.get("progress", 0.0)
                state = t.get("state", "unknown")
                torrent_hash = t.get("hash", "")
                torrent_hash_map[torrent_hash] = name
                bar = progress_bar(progress)
                statuses.append(f"{name}: {bar} ({state})")

                # If new
                if name not in previous_torrent_status:
                    send_telegram(f"Torrent started: {name} {bar}")
                previous_torrent_status[name] = progress

                # If completed
                if progress >= 1.0 and name not in completed_torrents:
                    completed_torrents.add(name)
                    send_telegram(f"Torrent completed: {name}")
            return "\n".join(statuses)
        else:
            err_msg = f"Failed to fetch torrent status: {response.text}"
            error_logs.append(err_msg)
            return err_msg
    except Exception as e:
        err_msg = f"Error fetching torrents: {e}"
        error_logs.append(err_msg)
        return err_msg

def update_status_loop():
    global status_message
    while True:
        status_message = poll_qbittorrent_status()
        print("Status updated:", status_message)
        time.sleep(30)

# ------------- Telegram Bot Handlers -------------
def summary_cmd(update, context):
    try:
        response = qb_request("torrents/info", timeout=5)
        if not response.ok:
            update.message.reply_text("Error fetching torrents info.")
            return
        torrents = response.json()
        if not torrents:
            update.message.reply_text("No torrents found.")
            return

        keyboard = []
        for idx, t in enumerate(torrents, start=1):
            torrent_hash = t.get("hash", "")
            name = t.get("name", "Unknown")
            label = f"[{idx}] {name}"

            keyboard.append([
                InlineKeyboardButton(f"Pause {label}", callback_data=f"pause:{torrent_hash}"),
                InlineKeyboardButton(f"Resume {label}", callback_data=f"resume:{torrent_hash}"),
                InlineKeyboardButton(f"Delete {label}", callback_data=f"delete:{torrent_hash}")
            ])
        keyboard.append([InlineKeyboardButton("Stop Automation", callback_data="stop")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Summary of torrents:", reply_markup=reply_markup)
    except Exception as e:
        update.message.reply_text(f"Error in summary command: {e}")
        error_logs.append(f"Summary command error: {e}")

def status_cmd(update, context):
    st = poll_qbittorrent_status()
    update.message.reply_text(f"Current status:\n{st}")

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if ":" in data:
        command, torrent_hash = data.split(":")
    else:
        command, torrent_hash = data, None

    if command == "pause":
        qb_request("torrents/pause", "POST", data={"hashes": torrent_hash})
        query.edit_message_text(text=f"Paused: {torrent_hash_map.get(torrent_hash,'Unknown')}")
    elif command == "resume":
        qb_request("torrents/resume", "POST", data={"hashes": torrent_hash})
        query.edit_message_text(text=f"Resumed: {torrent_hash_map.get(torrent_hash,'Unknown')}")
    elif command == "delete":
        qb_request("torrents/delete", "POST", data={"hashes": torrent_hash, "deleteFiles": "true"})
        query.edit_message_text(text=f"Deleted: {torrent_hash_map.get(torrent_hash,'Unknown')}")
    elif command == "stop":
        query.edit_message_text(text="Stopping ZynkStream automation...")
        os._exit(0)
    else:
        query.edit_message_text(text="Unknown command.")

def add_torrent_command(update, context):
    if not context.args:
        update.message.reply_text("Usage: /addtorrent <torrent_link>")
        return
    torrent_link = context.args[0]
    r = qb_request("torrents/add", "POST", data={"urls": torrent_link}, timeout=5)
    if r.ok:
        update.message.reply_text("Torrent added successfully.")
    else:
        update.message.reply_text("Failed to add torrent.")

def stop_bot_command(update, context):
    update.message.reply_text("Stopping ZynkStream automation...")
    os._exit(0)

# ------------- Modified start_bot() with Try/Except -------------
def start_bot():
    from telegram.error import InvalidToken

    try:
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("status", status_cmd))
        dp.add_handler(CommandHandler("summary", summary_cmd))
        dp.add_handler(CommandHandler("addtorrent", add_torrent_command))
        dp.add_handler(CommandHandler("stop", stop_bot_command))
        dp.add_handler(CallbackQueryHandler(button_handler))

        updater.start_polling(drop_pending_updates=True)
        updater.idle()

    except InvalidToken:
        error_logs.append("====================================")
        error_logs.append("ERROR: Telegram Bot token is invalid.")
        error_logs.append("Skipping Telegram initialization; no Telegram commands will work.")
        error_logs.append("====================================")
        print("\n".join(error_logs))
        # Instead of exiting, we simply pass, so the rest of the script runs:
        # If you prefer to exit, use `sys.exit(1)` here.
        pass

# ------------- Flask Web UI -------------
app = Flask("ZynkStream")

@app.route("/")
def index():
    qb_stat = poll_qbittorrent_status()
    html = """
    <html>
      <head>
        <title>ZynkStream Dashboard</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
          h1 { color: #333; }
          .section { margin-bottom: 30px; padding: 15px; background: #fff; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
          .title { font-size: 1.3em; margin-bottom: 10px; color: #555; }
          .status-item { margin: 5px 0; }
          .ok { color: green; }
          .error { color: red; }
          pre { background: #eee; padding: 10px; border-radius: 5px; }
        </style>
      </head>
      <body>
        <h1>ZynkStream Dashboard</h1>

        <div class="section">
          <div class="title">Overall Services</div>
          <div class="status-item"><strong>Automation:</strong> <span class="ok">🟢 Online</span></div>
          <div class="status-item"><strong>Telegram Bot:</strong> 
            {% if "ERROR: Telegram Bot token is invalid." in error_logs %}
              <span class="error">🔴 Invalid Token</span>
            {% else %}
              <span class="ok">🟢 Online (If token was valid)</span>
            {% endif %}
          </div>
          <div class="status-item"><strong>Plex:</strong> <span class="ok">🟢 Online</span></div>
        </div>

        <div class="section">
          <div class="title">Torrent / Download Status</div>
          <div class="status-item"><strong>qBittorrent:</strong></div>
          <pre>{{ qb_status }}</pre>
          <div class="status-item"><strong>Automation Detail:</strong> {{ automation_status }}</div>
        </div>

        <div class="section">
          <div class="title">Download Statistics</div>
          <div class="status-item"><strong>Successful Downloads:</strong> {{ success_count }}</div>
          <div class="status-item"><strong>Failed Downloads:</strong> {{ fail_count }}</div>
        </div>

        <div class="section">
          <div class="title">Download History</div>
          {% if download_history %}
            <ul>
              {% for item in download_history %}
                <li>{{ item.file }} ({{ item.time }}) - {{ item.status }}</li>
              {% endfor %}
            </ul>
          {% else %}
            <p>No downloads recorded yet.</p>
          {% endif %}
        </div>

        <div class="section">
          <div class="title">Error Logs</div>
          {% if error_logs %}
            <ul>
              {% for err in error_logs %}
                <li><span class="error">{{ err }}</span></li>
              {% endfor %}
            </ul>
          {% else %}
            <p>No errors logged yet.</p>
          {% endif %}
        </div>
      </body>
    </html>
    """
    return render_template_string(
        html,
        qb_status=qb_stat,
        automation_status=status_message,
        success_count=successful_downloads,
        fail_count=failed_downloads,
        download_history=download_history,
        error_logs=error_logs
    )

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ------------- Main -------------
if __name__ == "__main__":
    # Start file monitoring
    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()

    # Start torrent polling
    status_thread = threading.Thread(target=update_status_loop, daemon=True)
    status_thread.start()

    # Start Flask
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Telegram Bot (wrapped in try/except)
    start_bot()

    # Keep main thread alive
    while True:
        time.sleep(1)
