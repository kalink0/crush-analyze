"""`json.dumps(..., default=json_safe.default)` fallback for values a
module's own business logic may return that aren't natively JSON-
serializable — parsed plist values in particular often come back as real
`datetime` objects. Never drops a value silently: anything not handled
explicitly falls back to `str(obj)` rather than raising, so one oddly-typed
field can't crash writing the whole contract v1 result — matches the
standing rule that a bad value degrades a row, it never fails the run.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    return str(obj)
