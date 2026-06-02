from korp_endpoint.app import make_app

if __name__ == "__main__":
    import contextvars
    import logging

    from werkzeug.serving import WSGIRequestHandler
    from werkzeug.serving import run_simple

    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname).1s][%(request_id)s][%(name)s:%(lineno)s] %(message)s",
    )

    REQUEST_ID = contextvars.ContextVar("request_id", default="-")

    class RequestFilter(logging.Filter):
        def filter(self, record):
            record.request_id = REQUEST_ID.get("-")
            return record

    handler = logging.root.handlers[0]
    handler.addFilter(RequestFilter())

    class MyWSGIRequestHandler(WSGIRequestHandler):
        counter = 1  # not thread-safe I think, see contextvars/threading stuff

        def handle_one_request(self) -> None:
            MyWSGIRequestHandler.counter += 1
            token = REQUEST_ID.set(f"{MyWSGIRequestHandler.counter:04x}")
            # uuid.uuid4().hex[:4])
            try:
                return super().handle_one_request()
            finally:
                REQUEST_ID.reset(token)

    app = make_app()

    run_simple(
        "localhost", 8080, app, use_reloader=True, request_handler=MyWSGIRequestHandler
    )

    # tests:
    # - explain:
    #   curl 'http://localhost:8080/?operation=explain&x-fcs-endpoint-description=true&x-indent-response=1'
    # - cql/basic
    #   curl 'http://localhost:8080/?operation=searchRetrieve&query=Katze&x-indent-response=1'
    # - fcq/adv
    #   curl 'http://localhost:8080/?operation=searchRetrieve&queryType=fcs&query=%5bword%3d%22dina%22%5d&x-indent-response=1'