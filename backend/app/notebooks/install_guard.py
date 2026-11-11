"""Keep a POSIX notebook installation and its helpers bound to the backend lifetime."""

import os
import select
import signal
import subprocess
import sys
import time


def main() -> int:
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    child = subprocess.Popen(sys.argv[1:], stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        while child.poll() is None and not stopping:
            if select.select([sys.stdin], [], [], 0.1)[0] and not os.read(0, 1):
                break
        return child.returncode if child.returncode is not None else 1
    finally:
        # A build helper can outlive uv, including after uv exits successfully.
        try:
            os.killpg(child.pid, signal.SIGTERM)
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                child.poll()
                os.killpg(child.pid, 0)
                time.sleep(0.05)
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()


if __name__ == "__main__":
    sys.exit(main())
