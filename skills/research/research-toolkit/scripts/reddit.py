#!/usr/bin/env python3
"""Read Reddit without a browser: listings, search, threads with comments, user pages.

Two backends, chosen automatically:

* **OAuth API** (preferred when ``REDDIT_CLIENT_ID`` + ``REDDIT_CLIENT_SECRET`` are set):
  app-only ``client_credentials`` grant for a free "script" app registered at
  https://www.reddit.com/prefs/apps. No username, password or cookie is ever used and
  the script never acts as a user. ~100 requests/minute, full JSON including scores
  and nested comments.
* **Anonymous Atom feeds** (``.rss`` endpoints): the only unauthenticated path Reddit
  still serves to server IPs (``.json`` and old.reddit return 403 / an empty shell).
  Roughly ONE request per minute per IP; the script sleeps until the window resets
  when it hits a 429 and retries once.
