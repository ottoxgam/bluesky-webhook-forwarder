import asyncio
import json
import os
import logging
from atproto import Client
import requests

# === CONFIG ===
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
WATCH_HANDLES = os.getenv('WATCH_HANDLES', '').split(',')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 60))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

CACHE_DIR = 'cache'
POSTED_FILE = os.path.join(CACHE_DIR, 'posted_cache.json')
DID_FILE = os.path.join(CACHE_DIR, 'did_cache.json')

# === LOGGING ===
logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
)

# === INIT CLIENT ===
client = Client()
try:
    client.login(USERNAME, PASSWORD)
    logging.info(f"Logged in as {USERNAME}")
except Exception as e:
    logging.error(f"Failed to authenticate: {e}")
    exit(1)

# === CACHE HANDLING ===
def load_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    posted = set()
    did_cache = {}

    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, 'r') as f:
                posted = set(json.load(f))
        except Exception as e:
            logging.warning(f"Failed to load posted_cache.json: {e}")

    if os.path.exists(DID_FILE):
        try:
            with open(DID_FILE, 'r') as f:
                did_cache = json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load did_cache.json: {e}")

    return posted, did_cache

def save_cache(posted, did_cache):
    with open(POSTED_FILE, 'w') as f:
        json.dump(list(posted), f)
    with open(DID_FILE, 'w') as f:
        json.dump(did_cache, f)

# === DISCORD POSTING ===
def send_to_discord(content):
    response = requests.post(DISCORD_WEBHOOK_URL, json={'content': content})
    if response.ok:
        logging.debug("Message sent to Discord")
    else:
        logging.error(f"Discord webhook failed: {response.status_code} - {response.text}")

# === MAIN LOOP ===
async def poll_profiles():
    posted_cache, did_cache = load_cache()

    while True:
        for handle in WATCH_HANDLES:
            logging.info(f"Checking posts for {handle}")
            try:
                feed = client.app.bsky.feed.get_author_feed({'actor': handle, 'limit': 10})
                for item in feed.feed:
                    post = item.post
                    uri = post.uri
                    if uri in posted_cache:
                        continue

                    record = post.record
                    text = getattr(record, 'text', '[No Text]')
                    post_id = uri.split('/')[-1]
                    author_profile = f"https://bsky.app/profile/{handle}/post/{post_id}"

                    is_comment = (
                        hasattr(record, 'reply') and
                        record.reply is not None and
                        record.reply.root.uri.split('/')[2] != handle
                    )

                    if is_comment:
                        target_uri = record.reply.root.uri
                        target_post = target_uri.split('/')[-1]
                        target_did = target_uri.split('/')[2]

                        if target_did in did_cache:
                            target_handle = did_cache[target_did]
                        else:
                            try:
                                target_profile = client.app.bsky.actor.get_profile({'actor': target_did})
                                target_handle = target_profile.handle
                                did_cache[target_did] = target_handle
                            except Exception as e:
                                logging.warning(f"Failed to resolve handle for DID {target_did}: {e}")
                                target_handle = target_did

                        target_link = f"https://bsky.app/profile/{target_handle}/post/{target_post}"
                        message = (
                            f"💬 **{handle} commented on {target_handle}**\n"
                            f"{text}\n"
                            f"🧵 Original: {target_link}\n"
                            f"💬 Comment: {author_profile}"
                        )
                        logging.debug(f"Detected new comment by {handle} on {target_handle}")
                    else:
                        message = (
                            f"📝 **New post by {handle}**\n"
                            f"{text}\n"
                            f"{author_profile}"
                        )
                        logging.debug(f"Detected new post by {handle}")

                    send_to_discord(message)
                    posted_cache.add(uri)

            except Exception as e:
                logging.error(f"Failed to process {handle}: {e}")

        save_cache(posted_cache, did_cache)
        await asyncio.sleep(POLL_INTERVAL)

# === ENTRY POINT ===
if __name__ == '__main__':
    logging.info("Bluesky webhook forwarder started.")
    asyncio.run(poll_profiles())
