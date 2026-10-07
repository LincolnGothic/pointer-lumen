"""Package the Ubuntu release without changing or deleting its sources."""

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path


def add_file(archive, path, target, executable=False):
    info = zipfile.ZipInfo(target)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bibata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    theme_bundle = project / "artifacts/themes.zip"
    if not theme_bundle.is_file():
        raise SystemExit("Build and validate artifacts/themes.zip before packaging.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prefix = "cursor-glow-v1/"
    with zipfile.ZipFile(args.output, "w") as archive:
        for name in ("extension", "build", "tests", "docs"):
            for path in sorted((project / name).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    add_file(archive, path, prefix + path.relative_to(project).as_posix())
        for name in ("README.md", "LICENSE", "install.sh", "package.json"):
            add_file(archive, project / name, prefix + name, name == "install.sh")
        add_file(archive, theme_bundle, prefix + "themes.zip")
        preview = project / "artifacts/color-preview.png"
        if preview.is_file():
            add_file(archive, preview, prefix + "color-preview.png")
        for name in ("svg/groups", "svg/modern", "svg/original", "configs/normal"):
            for path in sorted((args.bibata / name).rglob("*")):
                if path.is_file():
                    add_file(archive, path, prefix + "source/bibata/" + path.relative_to(args.bibata).as_posix())
        add_file(archive, args.bibata / "LICENSE", prefix + "source/bibata/LICENSE")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    report = {"file": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest}
    args.output.with_suffix(".sha256").write_text(digest + "  " + args.output.name + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
