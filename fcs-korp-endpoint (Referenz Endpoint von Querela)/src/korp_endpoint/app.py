import os

from clarin.sru.constants import SRUVersion
from clarin.sru.server.config import SRUServerConfigKey
from clarin.sru.server.wsgi import SRUServerApp

from korp_endpoint.endpoint import API_BASE_URL_KEY
from korp_endpoint.endpoint import RESOURCE_INVENTORY_URL_KEY
from korp_endpoint.endpoint import KorpEndpointSearchEngine
from korp_endpoint.korp import API_BASE_URL

# ---------------------------------------------------------------------------


def make_app():
    here = os.path.dirname(__file__)
    config_file = os.path.join(here, "sru-server-config.xml")
    ed_file = os.path.join(here, "endpoint-description.xml")

    app = SRUServerApp(
        KorpEndpointSearchEngine,
        config_file,
        {
            RESOURCE_INVENTORY_URL_KEY: ed_file,  # comment out to use bundled
            # API_BASE_URL_KEY: API_BASE_URL,
            #
            # SRUServerConfigKey.SRU_TRANSPORT: "http",
            # SRUServerConfigKey.SRU_HOST: "127.0.0.1",
            # SRUServerConfigKey.SRU_PORT: "8080",
            # required information
            SRUServerConfigKey.SRU_DATABASE: "korp",
            #
            SRUServerConfigKey.SRU_ECHO_REQUESTS: "true",
            SRUServerConfigKey.SRU_NUMBER_OF_RECORDS: 250,
            SRUServerConfigKey.SRU_MAXIMUM_RECORDS: 1000,
            SRUServerConfigKey.SRU_ALLOW_OVERRIDE_MAXIMUM_RECORDS: "true",
            SRUServerConfigKey.SRU_ALLOW_OVERRIDE_INDENT_RESPONSE: "true",
            # To enable SRU 2.0 for FCS 2.0
            SRUServerConfigKey.SRU_SUPPORTED_VERSION_MAX: SRUVersion.VERSION_2_0,
            # SRUServerConfigKey.SRU_SUPPORTED_VERSION_DEFAULT: SRUVersion.VERSION_2_0,
            SRUServerConfigKey.SRU_LEGACY_NAMESPACE_MODE: "loc",
        },
        develop=True,
    )
    return app


def make_gunicorn_app():
    """Setup logging to display on stdout with gunicorn logging level."""

    import logging

    # https://trstringer.com/logging-flask-gunicorn-the-manageable-way/

    gunicorn_logger = logging.getLogger("gunicorn.error")

    logging.basicConfig(
        level=gunicorn_logger.level,
        format="[%(levelname).1s][%(name)s:%(lineno)s] %(message)s",
    )

    return make_app()


# ---------------------------------------------------------------------------
