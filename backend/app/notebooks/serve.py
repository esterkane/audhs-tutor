"""Notebook-environment entry point for authenticated listener ownership checks."""

import hashlib
import hmac
import os
import sys

from jupyterlab.labapp import main
from tornado.web import RequestHandler

# Jupyter loads a configured extra service by module name. Register this exact file, even
# when the notebook environment has no tutor package on sys.path.
_KEY = bytes.fromhex(os.environ.pop("AUDHS_NOTEBOOK_PROOF_KEY"))


class ListenerProof(RequestHandler):  # type: ignore[misc]  # Tornado is installed in the notebook environment.
    def get(self, challenge: str) -> None:
        self.set_header("Cache-Control", "no-store")
        self.set_header(
            "X-AuDHS-Listener-Proof",
            hmac.new(_KEY, challenge.encode("ascii"), hashlib.sha256).hexdigest(),
        )
        self.set_status(204)


default_handlers = [(r"/audhs-listener-proof/([0-9a-f]{64})", ListenerProof)]

if __name__ == "__main__":
    sys.modules["audhs_notebook_listener"] = sys.modules[__name__]
    main(argv=[*sys.argv[1:], "--ServerApp.extra_services=audhs_notebook_listener"])
