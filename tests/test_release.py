"""Check the actual release contents and its rebuildable shared SVG sources."""

import io
import json
import os
import posixpath
import stat
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RELEASE = Path(os.environ.get("CURSOR_GLOW_RELEASE", PROJECT / "artifacts/cursor-glow-v1-ubuntu.zip"))


class ReleaseTests(unittest.TestCase):
    def test_release_contains_installable_extension_and_rebuildable_themes(self):
        self.assertTrue(RELEASE.is_file(), "Build the release ZIP before checking its contents")
        prefix = "cursor-glow-v1/"
        with zipfile.ZipFile(RELEASE) as archive:
            names = set(archive.namelist())
            self.assertEqual(len(names), len(archive.namelist()))
            self.assertTrue(all(name.startswith(prefix) and ".." not in name.split("/") for name in names))
            metadata = json.loads(archive.read(prefix + "extension/metadata.json"))
            self.assertEqual(metadata["uuid"], "cursor-glow@local")
            self.assertEqual(metadata["shell-version"], ["50"])
            schema = ET.fromstring(archive.read(prefix + "extension/schemas/org.gnome.shell.extensions.hati.gschema.xml")).find("schema")
            self.assertEqual(schema.attrib["id"], metadata["settings-schema"])
            installer = archive.getinfo(prefix + "install.sh")
            self.assertTrue(stat.S_IMODE(installer.external_attr >> 16) & 0o111)
            self.assertIn(prefix + "LICENSE", names)
            self.assertIn(prefix + "source/bibata/LICENSE", names)
            source_prefix = prefix + "source/bibata/"
            for name in names:
                if not name.startswith(source_prefix + "svg/"):
                    continue
                text = archive.read(name).decode("utf-8").strip()
                if "<svg" in text:
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), text))
                # Windows Git represents both SVG and directory symlinks as text.
                self.assertTrue(target in names or any(n.startswith(target + "/") for n in names), f"Missing source target: {name} -> {target}")
            with zipfile.ZipFile(io.BytesIO(archive.read(prefix + "themes.zip"))) as themes:
                indexes = [n for n in themes.namelist() if n.endswith("/index.theme")]
                self.assertEqual(len(indexes), 24)
                self.assertTrue(themes.read("CursorGlow-Modern-blue/cursors/left_ptr").startswith(b"Xcur"))
                self.assertTrue(stat.S_ISLNK(themes.getinfo("CursorGlow-Modern-blue/cursors/default").external_attr >> 16))


if __name__ == "__main__":
    unittest.main()
