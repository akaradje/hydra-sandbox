"""
Deprecation warning helper.

Emits ``DeprecationWarning`` or ``FutureWarning`` for public API that
will be removed or changed in a future version.  Callers can use
``warnings.filterwarnings`` to turn these into errors during CI.
"""

from __future__ import annotations

import functools
import warnings
from typing import Any, Callable


def deprecated(
    since: str,
    removed_in: str,
    *,
    replacement: str = "",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: emit a ``DeprecationWarning`` when a function is called.

    Args:
        since: Version where deprecation was introduced (e.g. ``"0.2.0"``).
        removed_in: Version where the function will be removed.
        replacement: Suggestion for the replacement function (optional).

    Example::

        @deprecated(since="0.2.0", removed_in="0.4.0", replacement="new_func")
        def old_func():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            msg = (
                f"{func.__qualname__} is deprecated since v{since} "
                f"and will be removed in v{removed_in}."
            )
            if replacement:
                msg += f" Use {replacement} instead."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
