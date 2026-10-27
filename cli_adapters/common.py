"""Shared strict JSON and bounded local-file utilities (stdlib only)."""
import hashlib
import json
import math
import os
import stat
from pathlib import Path

MAX_FILE_BYTES = 1024 * 1024
MAX_TRACE_BYTES = 16 * 1024 * 1024


class AdapterError(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdapterError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _finite_float(text):
    value = float(text)
    if (isinstance(value, float) and not math.isfinite(value)):
        raise AdapterError("nonfinite JSON number")
    return value


def strict_json(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_float=_finite_float,
                          parse_constant=lambda x: (_ for _ in ()).throw(AdapterError("nonfinite JSON: " + x)))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AdapterError("invalid JSON: " + str(exc)) from exc


def checked_path(path):
    """Reject symlinks in every existing component, including the root itself."""
    path = Path(os.path.abspath(path))
    for component in [*reversed(path.parents), path]:
        if component.is_symlink():
            raise AdapterError("symlink forbidden: " + str(component))
    return path


def read_regular(path, limit=MAX_FILE_BYTES):
    path = checked_path(path)
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        initial = os.fstat(fd)
        if not stat.S_ISREG(initial.st_mode) or initial.st_size > limit:
            raise AdapterError("not a regular bounded file: " + str(path))
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        final = os.fstat(fd)
        if len(data) > limit or (initial.st_size, initial.st_mtime_ns, initial.st_ctime_ns) != (final.st_size, final.st_mtime_ns, final.st_ctime_ns):
            raise AdapterError("file too large or changed while reading: " + str(path))
        return data
    finally:
        os.close(fd)


def nonnegative(value, label, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)) or value < 0 or (integer and not isinstance(value, int)):
        raise AdapterError("invalid nonnegative " + label)
    return value
