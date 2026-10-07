"""Acceptance checks for the installable Debian artifact, independent of its builder."""

import io
import json
import os
from pathlib import Path
import posixpath
import tarfile
import unittest
import xml.etree.ElementTree as ET

PROJECT = Path(__file__).resolve().parents[1]
DEB = Path(os.environ.get("POINTER_LUMEN_DEB", PROJECT / "artifacts/pointer-lumen_0.1.0-1_all.deb"))


class DebianArtifactTests(unittest.TestCase):
    def test_debian_archive_can_install_extension_themes_and_global_schema(self):
        self.assertTrue(DEB.is_file(), "Build the Debian package before checking installation contents")
        raw = DEB.read_bytes()
        self.assertEqual(raw[:8], b"!<arch>\n")
        members = {}
        offset = 8
        while offset < len(raw):
            header = raw[offset:offset + 60]
            self.assertEqual(header[58:], b"`\n")
            name = header[:16].decode().strip().rstrip("/")
            size = int(header[48:58])
            self.assertNotIn(name, members)
            members[name] = raw[offset + 60:offset + 60 + size]
            offset += 60 + size + size % 2
        self.assertEqual(offset, len(raw))
        self.assertEqual(list(members), ["debian-binary", "control.tar.gz", "data.tar.gz"])
        self.assertEqual(members["debian-binary"], b"2.0\n")
        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as control:
            fields = control.extractfile("control").read().decode()
            self.assertIn("Package: pointer-lumen\n", fields)
            self.assertIn("Architecture: all\n", fields)
            self.assertIn("gnome-shell (>= 50~)", fields)
            self.assertIn("gnome-shell (<< 51~)", fields)
            self.assertIn("gnome-shell-extension-prefs", fields)
            self.assertFalse(any(m.name in {"preinst", "postinst", "prerm", "postrm"} for m in control))
        with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as data:
            entries = data.getmembers()
            names = {m.name for m in entries}
            self.assertEqual(len(names), len(entries))
            self.assertTrue(all(n.startswith("usr/share/") and ".." not in n.split("/") for n in names))
            self.assertTrue(all(m.uid == 0 and m.gid == 0 for m in entries))
            extension = "usr/share/gnome-shell/extensions/cursor-glow@local/"
            metadata = json.load(data.extractfile(extension + "metadata.json"))
            self.assertEqual(metadata["uuid"], "cursor-glow@local")
            self.assertEqual(metadata["shell-version"], ["50"])
            self.assertIn(extension + "prefs.js", names)
            self.assertFalse(any(n.startswith(extension + "schemas/") for n in names))
            schema_path = "usr/share/glib-2.0/schemas/org.gnome.shell.extensions.cursor-glow.gschema.xml"
            schema = ET.fromstring(data.extractfile(schema_path).read()).find("schema")
            self.assertEqual(schema.attrib["id"], metadata["settings-schema"])
            themes = [n for n in names if n.startswith("usr/share/icons/CursorGlow-") and n.endswith("/index.theme")]
            self.assertEqual(len(themes), 24)
            left_ptr = "usr/share/icons/CursorGlow-Modern-blue/cursors/left_ptr"
            self.assertTrue(data.extractfile(left_ptr).read().startswith(b"Xcur"))
            aliases = [m for m in entries if m.issym()]
            self.assertEqual(len(aliases), 24 * 89)
            for alias in aliases:
                self.assertFalse(posixpath.isabs(alias.linkname))
                target = posixpath.normpath(posixpath.join(posixpath.dirname(alias.name), alias.linkname))
                self.assertIn(target, names)
            self.assertIn("usr/share/doc/pointer-lumen/copyright", names)
            self.assertIn("usr/share/doc/pointer-lumen/README.md", names)


if __name__ == "__main__":
    unittest.main()
