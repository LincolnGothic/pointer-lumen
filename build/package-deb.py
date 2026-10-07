"""Build a Debian 2.0 package from the extension and validated prebuilt themes."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    content = io.BytesIO()
    installed_bytes = 0
    directories = set()
    with tarfile.open(fileobj=content, mode="w:gz", format=tarfile.GNU_FORMAT) as archive:
        def add(name, payload, symlink=False):
            nonlocal installed_bytes
            parent = Path(name).parent
            parents = []
            while len(parent.parts) > 2:
                parents.append(parent.as_posix())
                parent = parent.parent
            for directory in reversed(parents):
                if directory not in directories:
                    info = tarfile.TarInfo(directory)
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    archive.addfile(info)
                    directories.add(directory)
            info = tarfile.TarInfo(name)
            info.mode = 0o777 if symlink else 0o644
            if symlink:
                info.type = tarfile.SYMTYPE
                info.linkname = payload.decode("utf-8")
                archive.addfile(info)
            else:
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
                installed_bytes += len(payload)

        extension = project / "extension"
        for path in sorted(extension.rglob("*")):
            relative = path.relative_to(extension)
            if path.is_file() and "schemas" not in relative.parts and "__pycache__" not in relative.parts:
                add("usr/share/gnome-shell/extensions/cursor-glow@local/" + relative.as_posix(), path.read_bytes())
        schema = extension / "schemas/org.gnome.shell.extensions.hati.gschema.xml"
        add("usr/share/glib-2.0/schemas/org.gnome.shell.extensions.cursor-glow.gschema.xml", schema.read_bytes())
        with zipfile.ZipFile(project / "artifacts/themes.zip") as themes:
            for entry in themes.infolist():
                if entry.is_dir():
                    continue
                if entry.filename.startswith("CursorGlow-"):
                    add("usr/share/icons/" + entry.filename, themes.read(entry), stat.S_ISLNK(entry.external_attr >> 16))
                else:
                    add("usr/share/doc/pointer-lumen/theme-notices/" + entry.filename, themes.read(entry))
        add("usr/share/doc/pointer-lumen/README.md", (project / "README.md").read_bytes())
        attribution = b"Pointer Lumen: https://github.com/LincolnGothic/pointer-lumen\nDerived from Hati and Bibata. GPL-3.0-or-later; see README.md and theme-notices.\n\n"
        add("usr/share/doc/pointer-lumen/copyright", attribution + (project / "LICENSE").read_bytes())

    control_text = f"""Package: pointer-lumen
Version: 0.1.0-1
Section: gnome
Priority: optional
Architecture: all
Maintainer: LincolnGothic <127757595+LincolnGothic@users.noreply.github.com>
Installed-Size: {(installed_bytes + 1023) // 1024}
Depends: gnome-shell (>= 50~), gnome-shell (<< 51~), gnome-shell-extension-prefs, libglib2.0-bin
Homepage: https://github.com/LincolnGothic/pointer-lumen
Description: pointer colors and following glow for GNOME demonstrations
 Twelve prebuilt cursor colors, two shapes, three sizes and configurable glow.
 Requires GNOME Shell 50 with Wayland. Enable the extension after logging in.
 Preview release; live GNOME desktop validation remains pending.
""".encode("utf-8")
    control = io.BytesIO()
    with tarfile.open(fileobj=control, mode="w:gz", format=tarfile.GNU_FORMAT) as archive:
        info = tarfile.TarInfo("control")
        info.mode = 0o644
        info.size = len(control_text)
        archive.addfile(info, io.BytesIO(control_text))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as package:
        package.write(b"!<arch>\n")
        for name, payload in (("debian-binary", b"2.0\n"), ("control.tar.gz", control.getvalue()), ("data.tar.gz", content.getvalue())):
            header = f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(payload):<10}`\n"
            package.write(header.encode("ascii"))
            package.write(payload)
            if len(payload) % 2:
                package.write(b"\n")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".sha256").write_text(digest + "  " + args.output.name + "\n", encoding="utf-8")
    print(json.dumps({"file": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
