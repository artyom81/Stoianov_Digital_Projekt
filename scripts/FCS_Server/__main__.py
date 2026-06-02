from werkzeug.serving import run_simple
from .app import make_app

if __name__ == "__main__":
    app = make_app()
    run_simple("127.0.0.1", 8088, app, use_debugger=True, use_reloader=False)