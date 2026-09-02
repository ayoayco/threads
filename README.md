# Threads

![Uptime](https://up.ayo.run/api/badge/16/status)

Show off your favorite public threads and offer hand-picked, fine-grained, topical subscriptions!

These are streams of thought you decide to float to your personal site for being a bit more-effort than other small posts, but still yet to be refined as a blog.

How it works:

1. a featured status will be fetched on the server along with qualified "descendants", which are replies of the same author in a single thread.
2. the list of featured statuses lives in a small SQLite database, curated from the site itself after signing in with the Mastodon account it is built from -- see [Featured posts](#featured-posts)
3. clean HTML with some styling will be sent to the viewer's browser
4. bit of client-side JS for progressive enhancement:
   1. `<relative-time>` by GitHub: https://github.com/github/relative-time-element
   2. `<mastodon-content>`: https://www.npmjs.com/package/@ayo-run/mastodon-content -- rewrites hashtag links to point at this app's own tag pages, and styles a trailing hashtag-only line as a row of pills
5. self-hostable with the app configuration in `config.json` file -- we are working on a docker way and easy configuration

See it [in action](https://ayco.io/threads).

> The project is currently experimental. Some improvements need to be made with regards to app configuration, storing data, and easy deployment & usage.

## Project setup

1. Set up your **Debian** (for other environments, search for counterpart instructions)

   ```bash
   # update repositories
   $ sudo apt update

   # install python stuff
   $ sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv
   ```

> For MacOS: https://docs.python.org/3/using/mac.html

2. Install dependencies and set up the project

   ```bash
   # clone the project
   $ git clone git@git.sr.ht:~ayoayco/threads

   # go into the project directory
   $ cd threads

   # create app config from example
   $ cp example_config.json config.json

   # create python environment. I prefer conda
   $ conda create -n threads python=3.12

   # activate python env:
   $ conda activate threads

   # install dependencies
   (.venv)$ python -m pip install -r requirements.txt

   # create configuration from example config file
   (.venv)$ cp ./example_config.json ./config.json

   # set SECRET_KEY in config.json to a long random string, e.g.
   (.venv)$ python -c "import secrets; print(secrets.token_hex(32))"

   # create the database, with the posts that used to be hardcoded
   (.venv)$ flask --app app.py init-db

   # rejoice!
   ```

3. Install the browser-side dependencies

   ```bash
   $ pnpm install
   ```

   > There is no bundler here: the custom elements are installed from npm and served straight out of `node_modules` by the `/vendor/` route, with `templates/import-map.html` pointing each bare specifier at it. So `node_modules` has to be present wherever the app runs, deployments included -- `pnpm install --prod` is enough there.

4. To start development, run the following:

   ```bash
   (.venv)$ flask --debug run
   ```

   > Note: On a Mac, the default port 5000 is used by AirDrop & Handoff; you may have to turn those off

5. After development session, deactivate the python env
   ```bash
   (.venv)$ conda deactivate
   ```

## Featured posts

The featured statuses are rows in a SQLite database at `instance/threads.sqlite`
(set `DATABASE` in `config.json` to put it elsewhere). The tables are created on
startup if they are missing; `flask --app app.py init-db` also fills an empty
list with the posts that used to be hardcoded, and is safe to run again -- it
never drops what is already there.

To curate the list, go to `/login` and sign in on your Mastodon server. Only the
account in `APPS.threads.user_id` may add or remove posts; anyone else who signs
in is refused and their token is revoked. On the first sign in the app registers
itself with your server through the API, so there is nothing to paste in by
hand -- the credentials it gets back are kept in the database.

Once signed in, the home page grows a small form -- paste a status id or the URL
of a post to feature it -- and each post gets an "Unfeature" button. Visitors
see none of that.

The list is in the posts' own order, newest first, whenever each one was
featured -- so featuring a post from long ago slots it in down the page rather
than on top. `flask --app app.py list-featured` prints the list in that order,
with the date of each post, which is a quick way to check a deployment's
database from the host.

Two things this needs to work:

- `SECRET_KEY` in `config.json`, used to sign the session cookie. Without it
  `/login` refuses to start the flow. A sign-in lasts 14 days
  (`PERMANENT_SESSION_LIFETIME`); signing out clears the cookie and revokes the
  token with your server.
- the app has to know its own public URL to build the OAuth redirect. Behind a
  reverse proxy, either forward the `Host` and `X-Forwarded-Proto` headers, or
  set `SERVER_NAME` and `PREFERRED_URL_SCHEME` in `config.json`. The redirect
  URI is `<your site>/oauth/callback` -- plus the prefix, if threads is mounted
  under one.

## As a blueprint

`app.py` is the standalone site. To attach threads to a bigger Flask app
instead -- as [ayco.io-flask](https://ayco.io/sh/ayco.io-flask) does, with this
project checked out as a `threads` directory next to its `web.py`:

```python
import threads
threads.init_app(app, url_prefix='/threads')
```

That registers both blueprints, sets up the cache and the database, and adds the
`init-db` command to the host's CLI (`flask --app web.py init-db`). Config the
host has already set is left alone; what it has to provide is `SECRET_KEY`,
`APPS.threads` and `ATTRIBUTION`, same as `example_config.json` here.

The database, the cache and the SQL files stay inside this directory whatever
the host is, so `instance/threads.sqlite` is `threads/instance/threads.sqlite`
there, and the cache is `threads/instance/cache` (set `CACHE_DIR` to move it). The
redirect URI picks up the prefix: `<your site>/threads/oauth/callback`.

## Tests

```bash
(.venv)$ python -m unittest discover -s tests
```

## Deployment

For deployment, the recommended setup is with production server `gunicorn` and reverse proxy `nginx`. See the [DigitalOcean tutorial](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-20-04) (their website uses cookies).

The curated list is a file on disk, so keep `instance/` out of the deploy
directory that gets replaced on release -- mount it as a volume in Docker -- or
the featured posts go away with the old release.

Rendered pages are cached for five minutes. The cache lives on disk at
`instance/cache`, beside the database (`FileSystemCache`), so every `gunicorn`
worker on the host shares it and curating clears it for all of them at once --
persist `instance/` across releases (above) and the cache comes with it. To
drop it by hand, delete that directory and restart; the app recreates it.

### Behind a CDN

A CDN (Cloudflare, say) keeps its own copy of the public pages at the edge, and
two things keep the curator's view and the public's view from bleeding into each
other through it:

- **Responses carry cache headers.** A signed-in curator's page is
  `private, no-store`; a public page is `public, max-age=0, s-maxage=300`, so a
  shared cache may serve it for five minutes while the browser revalidates. The
  edge still keys a page on its URL alone, so add a rule to **bypass the cache
  for any request carrying the session cookie** (on Cloudflare: a Cache Rule,
  _Cookie contains `session=`_ -> Bypass cache). Without it the edge serves the
  anonymous page back to the curator right after they sign in.
- **Curating purges the edge.** Featuring or unfeaturing clears the server-side
  cache at once, but the edge would still serve its stale copy until `s-maxage`
  lapses. Set a `CLOUDFLARE` block in `config.json` -- `zone_id` and an API
  token scoped to _Zone -> Cache Purge_ only -- and each change purges the zone
  so the public sees it right away:

  ```json
  "CLOUDFLARE": { "zone_id": "…", "api_token": "…" }
  ```

  It is optional: leave the block out (or its fields blank) and nothing is
  purged -- a change then waits out the five-minute edge TTL. A purge that fails
  is logged and ignored, so the CDN being briefly unreachable never breaks
  curation.

### Moving an existing deployment to the database

Three things to do on the server, once:

1. **Seed the list.** The tables are created on startup, but they are created
   empty -- the home page has nothing to show until the seed is applied. In the
   deploy directory, with the app's environment active:

   ```bash
   $ flask --app app.py init-db
   ```

   It is safe to run again; it never drops what is already there.

2. **Add `SECRET_KEY`** to the server's `config.json`. That file is gitignored,
   so a deploy does not bring the new field with it. Until it is set the site
   serves fine and only `/login` refuses, so the order of these steps does not
   matter. Changing the key later signs you out and invalidates any form open in
   a tab; it is not shared with anything, so a new random value is always safe.

3. **Persist `instance/`** across releases, as above.

There is nothing new to install: the only third-party import this adds is
`click`, which Flask already pulls in -- it is spelled out in
`requirements.txt` now because the app imports it directly.
