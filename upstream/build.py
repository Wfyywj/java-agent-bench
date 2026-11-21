"""Build the website case index and standalone GitHub issue toolkit."""
import json
from pathlib import Path
import zipfile

from bench import read_tasks


def main():
    root = Path(__file__).resolve().parents[1]
    dist = root / "dist"
    packages = dist / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    cases = read_tasks().values()
    cards = [{key: value for key, value in case.items() if key not in ("sources", "dependencies")}
             for case in cases]
    (dist / "upstream.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")

    files = {"README.md": root / "upstream/README.md", "LICENSE": root / "LICENSE",
             "upstream/bench.py": root / "upstream/bench.py"}
    for case in cases:
        for name in ("task.json", "Probe.java"):
            path = Path("upstream", case["id"], name)
            files[path.as_posix()] = root / path
    with zipfile.ZipFile(packages / "github-issues.zip", "w") as archive:
        for name, path in files.items():
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.external_attr = 0o644 << 16
            archive.writestr(member, path.read_bytes())
    print(f"Built {len(cards)} GitHub issue cards and packages/github-issues.zip")


if __name__ == "__main__":
    main()
