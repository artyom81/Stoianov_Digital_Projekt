FCS Korp Endpoint
=================

The Korp FCS 2.0 reference endpoint implementation.

This is the Python version of [`clarin-eric/fcs-korp-endpoint`](https://github.com/clarin-eric/fcs-korp-endpoint)! It is a manual translation from Java to Python and should functionally be the same. Its main purpose is to be a demonstrator and prototype for new FCS 2.0 endpoints using the SRU+FCS Python libraries.

## Information

- Requires: Python 3.8+
- Dependencies:
  - [FCS Simple Endpoint](https://github.com/Querela/fcs-simple-endpoint-python)
  - [FCS SRU Server](https://github.com/Querela/fcs-sru-server-python/)

## Installation

The project does not really require an installation. Simply copy the project anywhere, install required dependencies and it should work out-of-the-box.

```bash
git clone https://github.com/Querela/fcs-korp-endpoint-python
cd fcs-korp-endpoint-python

# optional (but will also install all dependencies)
pip install -e .
```

## Run

To just run the application:
```bash
python3 -m korp_endpoint
```

### Run with Docker

First build the docker image:
```bash
docker build --progress=plain -t korpy .
```

Then run (default port specified in envvar `PORT` is 5000):
```bash
docker run --rm -it -p 5000:5000 korpy
```

## Configuration & Modification

The file [`src/korp_endpoint/app.py`](src/korp_endpoint/app.py) describes how to set or overwrite SRU/FCS configuration parameters. It also shows how to expose the `app` object for [WSGI](https://wsgi.readthedocs.io/en/latest/index.html).

The file [`src/korp_endpoint/__main__.py`](src/korp_endpoint/__main__.py) is the module entrypoint for the above run command. It shows how to use the `werkzeug.serving.run_simple` function to run the app instance for debugging. If you want to deploy for production take a look at the [`werkzeug` deployment docs](https://werkzeug.palletsprojects.com/en/2.2.x/deployment/).

The configuration files [`src/korp_endpoint/sru-server-config.xml`](src/korp_endpoint/sru-server-config.xml) and [`src/korp_endpoint/endpoint-description.xml`](src/korp_endpoint/endpoint-description.xml) are bundled and need to be adjusted for your own endpoint, too.

## Endpoint implementation

[`src/korp_endpoint/endpoint.py`](src/korp_endpoint/endpoint.py) is the implementation of the endpoint! It ([_`KorpEndpointSearchEngine`_](src/korp_endpoint/endpoint.py)) is the core of the endpoint and handles requests for FCS 2.0 `explain` and `searchRetrieve` requests.

This implementation translates incoming CQL/FCS-QL queries into CQP using [`src/korp_endpoint/query_converter.py`](src/korp_endpoint/query_converter.py), forwards the query to the Korp search engine in [`src/korp_endpoint/korp.py`](src/korp_endpoint/korp.py) and wraps the result in a SRU/FCS response ([_`KorpSearchResultSet`_](src/korp_endpoint/endpoint.py)).

## Development

Run style checks:
```bash
# general style checks
python3 -m pip install -e .[style]

black --check .
flake8 . --show-source --statistics
isort --check --diff .
mypy .
```
