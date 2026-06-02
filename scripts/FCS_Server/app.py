from pathlib import Path

from clarin.sru.server.wsgi import SRUServerApp
from clarin.sru.server.config import SRUServerConfigKey

from scripts.FCS_Server.zx_search_engine import ZXSearchEngine


BASE_DIR = Path(__file__).resolve().parent


def make_app():
    config_path = str(BASE_DIR / "sru-server-config.xml")

    return SRUServerApp(
        ZXSearchEngine,
        config_path,
        {
            SRUServerConfigKey.SRU_TRANSPORT: "http",
            SRUServerConfigKey.SRU_HOST: "127.0.0.1",
            SRUServerConfigKey.SRU_PORT: "8088",
            SRUServerConfigKey.SRU_DATABASE: "zxpress",
            SRUServerConfigKey.SRU_ECHO_REQUESTS: "true",
            SRUServerConfigKey.SRU_NUMBER_OF_RECORDS: 250,
            SRUServerConfigKey.SRU_MAXIMUM_RECORDS: 1000,
            SRUServerConfigKey.SRU_ALLOW_OVERRIDE_MAXIMUM_RECORDS: "true",
            SRUServerConfigKey.SRU_ALLOW_OVERRIDE_INDENT_RESPONSE: "true",
            #SRUServerConfigKey.SRU_LEGACY_NAMESPACE_MODE: "loc",

            # Versionen bewusst als Strings setzen
            SRUServerConfigKey.SRU_SUPPORTED_VERSION_MIN: "2.0",
            SRUServerConfigKey.SRU_SUPPORTED_VERSION_MAX: "2.0",
            SRUServerConfigKey.SRU_SUPPORTED_VERSION_DEFAULT: "2.0",
        },
    )

def main():
    app = make_app()
    app.run()

if __name__ == "__main__":
    main()