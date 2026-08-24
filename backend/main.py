"""Canonical production entrypoint for the Sistema DM API.

All extensions are registered on the same FastAPI application. Render must
start this module so the deployed service cannot accidentally expose a partial
API from a different entrypoint.
"""

import server

# Register the specialized routes on the already initialized server.app.
import appointments  # noqa: F401,E402
import deadlines  # noqa: F401,E402
from routes import processes  # noqa: F401,E402
import gridfs_app  # noqa: F401,E402

app = gridfs_app.app

__all__ = ["app"]
