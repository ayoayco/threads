# Threads

Show off your favorite public threads and offer hand-picked, fine-grained, topical subscriptions!

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
    (.venv)$ python -m pip install flask requests markdown

    # rejoice!
    ```

3. To start development, run the following:
    ```bash
    (.venv)$ flask --app app.py --debug run
    ```

    > Note: On a Mac, the default port 5000 is used by AirDrop & Handoff; you may have to turn those off

4. After development session, deactivate the python env
    ```bash
    (.venv)$ deactivate
    ```

## Deployment

For deployment, the recommended setup is with production server `gunicorn` and reverse proxy `nginx`. See the [DigitalOcean tutorial](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-20-04) (their website uses cookies).
