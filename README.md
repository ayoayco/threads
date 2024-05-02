# Threads

Show off your favorite public threads and offer hand-picked, fine-grained, topical subscriptions!

These are streams of thought you decide to float to your personal site for being a bit more-effort than other small posts, but still yet to be refined as a blog.

How it works:
1. a featured status will be fetched on the server along with qualified "descendants", which are replies of the same author in a single thread.
2. clean HTML with some styling will be sent to the viewer's browser
3. it is therefore zero-JS as of yet
4. self-hostable with the app configuration in `threads.py` file -- we are working on a docker way and easy configuration

See it [in action](https://ayco.io/threads).

## Project setup

1. Set up your **Debian** (for other environments, search for counterpart instructions)

    ```bash
    # update repositories
    $ sudo apt update

    # install python stuff
    $ sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv
    ```

2. Install dependencies

    ```bash
    # clone the project 
    $ git clone git@git.sr.ht:~ayoayco/threads

    # go into the project directory
    $ cd threads

    # create python environment:
    $ python3 -m venv .venv

    # activate python env:
    $ . .venv/bin/activate

    # install dependencies
    (.venv)$ python -m pip install -r requirements.txt

    # rejoice!
    ```

3. To start development, run the following:
    ```bash
    (.venv)$ flask --debug run
    ```

    > Note: On a Mac, the default port 5000 is used by AirDrop & Handoff; you may have to turn those off

4. After development session, deactivate the python env
    ```bash
    (.venv)$ deactivate
    ```

## Deployment

For deployment, the recommended setup is with production server `gunicorn` and reverse proxy `nginx`. See the [DigitalOcean tutorial](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-20-04) (their website uses cookies).
