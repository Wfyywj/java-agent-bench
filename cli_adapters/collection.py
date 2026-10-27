"""Read-only, bounded before/after submission collection; never executes source."""
import difflib
import os
import stat
from .common import AdapterError, MAX_FILE_BYTES, canonical, checked_path, sha256

MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_FILES = 2000
MAX_DEPTH = 32


def snapshot(root):
    """Collect all regular files under an explicitly selected submission directory.

    Every component is opened relative to an already opened directory with
    O_NOFOLLOW; there is no symlink traversal, git invocation, or home discovery.
    Empty directories and timestamps are intentionally not part of source hashes.
    """
    root = checked_path(root)
    # Walk ancestors with descriptors too: a swapped parent cannot redirect reads.
    fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            new_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new_fd
        contents = {}
        total = 0

        def walk(directory_fd, prefix, depth):
            nonlocal total
            if depth > MAX_DEPTH:
                raise AdapterError("directory depth limit exceeded")
            initial = os.fstat(directory_fd)
            for name in sorted(os.listdir(directory_fd)):
                relative = prefix + name
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    raise AdapterError("symlink forbidden: " + relative)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
                    try:
                        walk(child, relative + "/", depth + 1)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    if len(contents) >= MAX_FILES or info.st_size > MAX_FILE_BYTES:
                        raise AdapterError("file count/size limit exceeded")
                    child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
                    try:
                        before = os.fstat(child)
                        if not stat.S_ISREG(before.st_mode):
                            raise AdapterError("file type changed")
                        with os.fdopen(child, "rb", closefd=False) as stream:
                            data = stream.read(MAX_FILE_BYTES + 1)
                        after = os.fstat(child)
                        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                        attrs = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                        if attrs(before) != attrs(after) or attrs(after) != attrs(current):
                            raise AdapterError("file changed during snapshot: " + relative)
                        total += len(data)
                        if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                            raise AdapterError("file/total size limit exceeded")
                        contents[relative] = data
                    finally:
                        os.close(child)
                else:
                    raise AdapterError("special file forbidden: " + relative)
            final = os.fstat(directory_fd)
            if (initial.st_mtime_ns, initial.st_ctime_ns) != (final.st_mtime_ns, final.st_ctime_ns):
                raise AdapterError("directory changed during snapshot")
        walk(fd, "", 0)
    finally:
        os.close(fd)
    files = [{"path": name, "bytes": len(data), "sha256": sha256(data)} for name, data in sorted(contents.items())]
    manifest = {"files": files, "source_sha256": sha256(canonical(files)), "total_bytes": total}
    return manifest, contents


def collect(before_root, after_root):
    before_path, after_path = checked_path(before_root), checked_path(after_root)
    if before_path == after_path or before_path in after_path.parents or after_path in before_path.parents:
        raise AdapterError("before/after must be independent non-nested directories")
    before, old = snapshot(before_path)
    after, new = snapshot(after_path)
    changes = []
    for name in sorted(old.keys() | new.keys()):
        if old.get(name) == new.get(name):
            continue
        kind = "added" if name not in old else "deleted" if name not in new else "modified"
        diff = None
        try:
            left, right = old.get(name, b"").decode("utf-8"), new.get(name, b"").decode("utf-8")
            if "\x00" not in left + right and len(left) + len(right) <= 200000 and left.count("\n") + right.count("\n") <= 10000:
                # splitlines(keepends=True) preserves content; hashes remain authoritative.
                lines = difflib.unified_diff(left.splitlines(True), right.splitlines(True), fromfile="before/" + name, tofile="after/" + name)
                diff = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)
        except UnicodeDecodeError:
            pass
        changes.append({"path": name, "kind": kind, "before_sha256": sha256(old[name]) if name in old else None,
                        "after_sha256": sha256(new[name]) if name in new else None, "text_diff": diff,
                        "diff_sha256": sha256(diff.encode("utf-8")) if diff is not None else None,
                        "text_diff_unavailable_reason": "binary/non-UTF8 or text diff size/line limit" if diff is None else None})
    return {"schema_version": 1, "run_kind": "offline_submission_collection", "business_status": "not_evaluated",
            "before": before, "after": after, "changes": changes, "changes_sha256": sha256(canonical(changes)),
            "uploaded": False, "atomic_snapshot_guaranteed": False}
