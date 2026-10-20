import threading
from collections.abc import Callable
from typing import Any


def run_in_background(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> threading.Thread:
    """Start a short-lived background task without tying it to a request session."""
    thread = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread
