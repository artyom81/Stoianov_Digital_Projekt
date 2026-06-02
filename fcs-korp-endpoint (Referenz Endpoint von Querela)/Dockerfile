FROM python:3.12.0-slim-bookworm

ENV PIP_ROOT_USER_ACTION ignore
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app /logs

# create user for webapp
RUN useradd sru --no-create-home --user-group

# app working dir
WORKDIR /app

# create enviroment
RUN python3 -m pip install --no-cache-dir -U pip setuptools wheel
RUN python3 -m pip install --no-cache-dir -U gunicorn

# install requirements/dependencies
COPY --chown=sru:sru requirements.txt /app/
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# copy sources
COPY --chown=sru:sru setup.py setup.cfg pyproject.toml README.md /app/
COPY --chown=sru:sru src /app/src/

# install application
RUN python3 -m pip install --no-cache-dir -e .

# fix permissions (?)
RUN chown -R sru:sru /app /logs


ENV GUNICORN_NUM_WORKERS 2
ENV PORT 5000

# public port
EXPOSE $PORT

# change to user
USER sru

# run
ENTRYPOINT [ \
    "gunicorn", \
    "--access-logfile", "/logs/access.log", \
    "--error-logfile", "/logs/errors.log", \
    "--log-level", "debug", \
    "korp_endpoint.app:make_gunicorn_app()" ]

