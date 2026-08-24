"""Purging the CDN edge cache when the featured list changes.

The server-side view cache is cleared in-process the moment a post is featured
or unfeatured, but a CDN in front of the site keeps its own copy of the public
pages for as long as their `s-maxage`. Until that lapses the public keeps seeing
the old list. Purging the edge closes that window.

This is optional and configured: with no `CLOUDFLARE` block in `config.json`
(or one whose `zone_id`/`api_token` is blank) it is a no-op, so a deployment
that isn't fronted by Cloudflare -- or hasn't set it up yet -- behaves exactly
as before and simply waits out the edge TTL.
"""
import requests
from flask import current_app

# someone is waiting on their curation request while this runs, so never hang
TIMEOUT = 10

def purge():
    """Purge the whole configured Cloudflare zone, if one is configured.

    Failure is logged and swallowed on purpose: the change has already landed in
    the database and the server-side cache, so curating must not fail because
    the CDN was briefly unreachable. The edge TTL is the backstop -- a missed
    purge means the change shows up in a few minutes rather than at once.
    """
    config = current_app.config.get('CLOUDFLARE')
    if not config:
        return
    zone, token = config.get('zone_id'), config.get('api_token')
    if not zone or not token:
        return

    url = f'https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache'
    try:
        response = requests.post(
            url,
            headers={'Authorization': f'Bearer {token}'},
            json={'purge_everything': True},
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            current_app.logger.error(
                f'Cloudflare purge returned {response.status_code} for {url}: '
                f'{response.text[:200]}')
    except requests.RequestException as error:
        current_app.logger.error(f'could not purge the Cloudflare cache: {error}')
