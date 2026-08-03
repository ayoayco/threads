CREATE TABLE IF NOT EXISTS statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_id TEXT NOT NULL,
    host TEXT
);

-- a status is only featured once
CREATE UNIQUE INDEX IF NOT EXISTS statuses_status_id ON statuses (status_id);

-- OAuth client credentials, registered with the Mastodon server on first login
CREATE TABLE IF NOT EXISTS oauth_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    host TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS oauth_clients_host_redirect
    ON oauth_clients (host, redirect_uri);
