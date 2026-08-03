from datetime import timedelta

def init_app(app, url_prefix='/'):
    """Attach threads to a Flask app -- the standalone one, or a bigger site.

    Everything the blueprints need in order to work is set up here, so a host
    application only has to call this. Anything already in the app's config is
    left alone.
    """
    # imported here so `import threads` stays cheap and free of side effects
    from .auth import auth
    from .cache import cache
    from .threads import threads
    from . import db

    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(days=14))
    app.config.setdefault('CACHE_TYPE', 'SimpleCache')
    cache.init_app(app)
    db.init_app(app)
    app.register_blueprint(threads, url_prefix=url_prefix)
    app.register_blueprint(auth, url_prefix=url_prefix)
    return app
