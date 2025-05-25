# Bluesky Webhook Forwarder 

Monitor specific Bluesky users for new posts and comments, and forward them to a Discord channel via webhook.


Tracks both top-level posts and replies
Caches seen posts to avoid duplicates
Resolves DIDs to handles for valid links


## Quickstart

```bash
git clone https://github.com/YOUR_USERNAME/bluesky-webhook-forwarder.git
cd bluesky-webhook-forwarder
cp stack.env .env
docker-compose up -d --build
