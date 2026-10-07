"""Exercise install preflight and file effects using real Bash, unzip and cp.

The GNOME command doubles are only for this Windows host. They do not prove
GNOME schema compilation or extension execution on Ubuntu.
"""

import os
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def shell_path(path):
    return subprocess.check_output(
        [str(BASH), "-c", 'cygpath -u "$1"', "test", str(path)], text=True
    ).strip()


@unittest.skipUnless(BASH.is_file(), "Windows installer checks require existing Git Bash")
class InstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = PROJECT / "artifacts/installer-fixtures" / uuid.uuid4().hex
        cls.fixture.mkdir(parents=True)
        cls.fake_bin = cls.fixture / "bin"
        cls.fake_bin.mkdir()
        cls.package = cls.fixture / "package"
        cls.package.mkdir()
        shutil.copy2(PROJECT / "install.sh", cls.package / "install.sh")
        shutil.copy2(PROJECT / "artifacts/themes.zip", cls.package / "themes.zip")
        shutil.copytree(PROJECT / "extension", cls.package / "extension")
        for name, content in {
            "gnome-shell": '#!/bin/bash\nprintf "GNOME Shell %s\\n" "$TEST_GNOME_VERSION"\n',
            "gnome-extensions": "#!/bin/bash\nexit 0\n",
            "glib-compile-schemas": "#!/bin/bash\nexit 0\n",
        }.items():
            (cls.fake_bin / name).write_text(content, encoding="utf-8", newline="\n")
        subprocess.run(
            [str(BASH), "-c", 'chmod +x "$1"/*', "test", shell_path(cls.fake_bin)],
            check=True,
        )

    def install(self, name, version="50.0", session="wayland", prepare=None):
        data = self.fixture / name
        if prepare:
            prepare(data)
        env = dict(os.environ)
        env.update(
            XDG_DATA_HOME=shell_path(data), XDG_SESSION_TYPE=session,
            TEST_GNOME_VERSION=version, TEST_BIN=shell_path(self.fake_bin),
        )
        result = subprocess.run(
            [str(BASH), "-c", 'export PATH="$TEST_BIN:$PATH"; bash "$1"',
             "test", shell_path(self.package / "install.sh")],
            env=env, text=True, capture_output=True,
        )
        return result, data

    def test_wrong_gnome_version_leaves_no_installation(self):
        result, data = self.install("wrong-version", version="49.5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires GNOME Shell 50", result.stderr)
        self.assertFalse(data.exists())

    def test_wrong_session_leaves_no_installation(self):
        result, data = self.install("wrong-session", session="x11")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Wayland", result.stderr)
        self.assertFalse(data.exists())

    def test_existing_theme_is_preserved_before_extension_copy(self):
        def prepare(data):
            target = data / "icons/CursorGlow-Modern-blue"
            target.mkdir(parents=True)
            (target / "sentinel").write_text("keep me", encoding="utf-8")

        result, data = self.install("collision", prepare=prepare)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Target already exists", result.stderr)
        self.assertEqual((data / "icons/CursorGlow-Modern-blue/sentinel").read_text(), "keep me")
        self.assertFalse((data / "gnome-shell").exists())
        self.assertEqual(len(list((data / "icons").iterdir())), 1)

    def test_fresh_install_copies_extension_and_all_24_themes(self):
        result, data = self.install("fresh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        extension = data / "gnome-shell/extensions/cursor-glow@local"
        self.assertTrue((extension / "prefs.js").is_file())
        self.assertTrue((extension / "metadata.json").is_file())
        self.assertEqual(len(list((data / "icons").glob("CursorGlow-*/index.theme"))), 24)
        self.assertTrue((data / "icons/CursorGlow-Modern-blue/cursors/left_ptr").is_file())
        self.assertIn("Log out and back in", result.stdout)


if __name__ == "__main__":
    unittest.main()
