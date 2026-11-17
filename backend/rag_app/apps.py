import os
import sys

from django.apps import AppConfig


class RagAppConfig(AppConfig):
    name = "rag_app"

    def ready(self):
        # Kick off the incremental background ingest once, only for the real server process
        # (runserver's autoreloader spawns a parent + child; RUN_MAIN marks the child).
        cmd = sys.argv[1] if len(sys.argv) > 1 else ""
        is_server = cmd == "runserver" or any(x in sys.argv[0] for x in ("gunicorn", "uwsgi", "daphne", "waitress"))
        if is_server and (cmd != "runserver" or os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv):
            from . import services
            services.start_background_ingest()
