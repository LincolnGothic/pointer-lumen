"""Independent binary acceptance checks; BIBATA_SOURCE selects the pinned checkout."""
import json
import os
from pathlib import Path
import stat
import struct
import tomllib
import unittest
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('BIBATA_SOURCE', r'D:\Codex_skill\source_repos\cursor-glow-bibata-v2.0.7'))
COLORS = 'black white amber red orange yellow green cyan blue purple pink gray'.split()
SIZES = {24, 32, 48, 64, 96}

class ThemeArtifactTests(unittest.TestCase):
    def test_preset_arrow_colors(self):
        from PIL import Image, ImageColor
        presets = json.loads((ROOT / 'extension/cursor-presets.json').read_text())
        self.assertEqual([c['id'] for c in presets['colors']], COLORS)
        self.assertEqual(presets['sizes'], [24, 32, 48])
        self.assertEqual([s['id'] for s in presets['styles']], ['Modern', 'Original'])
        for style in presets['styles']:
            for color in presets['colors']:
                image = Image.open(ROOT / f"artifacts/build-cache/CursorGlow-{style['id']}-{color['id']}/left_ptr.png").convert('RGBA')
                pixels = np.asarray(image)
                for field in ['hex', 'outline']:
                    rgb = ImageColor.getrgb(color[field])
                    self.assertGreater(np.count_nonzero(np.all(pixels == (*rgb, 255), axis=2)), 100, f"{style['id']} {color['id']} {field}")

    def test_bundle(self):
        archive = ROOT / 'artifacts/themes.zip'
        self.assertTrue(archive.is_file(), 'Expected artifacts/themes.zip is absent')
        config = tomllib.loads((SOURCE / 'configs/normal/x.build.toml').read_text())['cursors']
        fallback = config['fallback_settings']
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertEqual(len(names), len(set(names)))
            expected = set()
            for style in ['Modern', 'Original']:
                for color in COLORS:
                    theme = f'CursorGlow-{style}-{color}'
                    expected.add(theme)
                    self.assertIn('[Icon Theme]', z.read(theme + '/index.theme').decode())
                    for key, state in config.items():
                        if key == 'fallback_settings':
                            continue
                        name = theme + '/cursors/' + state['x11_name']
                        data = z.read(name)
                        self.assertFalse(stat.S_ISLNK(z.getinfo(name).external_attr >> 16))
                        pattern = state['png'].replace('.png', '.svg')
                        source_dir = SOURCE / 'svg' / style.lower()
                        if '*' in pattern:
                            source_dir = source_dir / pattern.split('-*')[0]
                            if source_dir.is_file():
                                source_dir = (source_dir.parent / source_dir.read_text().strip()).resolve()
                        frames = sorted(source_dir.glob(pattern))
                        self.assertTrue(frames)
                        magic, header, version, count = struct.unpack_from('<4sIII', data)
                        self.assertEqual((magic, header, version), (b'Xcur', 16, 65536))
                        self.assertEqual(count, len(frames) * len(SIZES))
                        seen = {size: [] for size in SIZES}
                        end = 16 + count * 12
                        for i in range(count):
                            typ, size, offset = struct.unpack_from('<III', data, 16 + i * 12)
                            self.assertEqual(offset, end, name)
                            self.assertEqual(typ, 0xfffd0002)
                            h, t, s, v, w, ht, x, y, delay = struct.unpack_from('<9I', data, offset)
                            self.assertEqual((h, t, s, v, w, ht), (36, typ, size, 1, size, size))
                            self.assertIn(size, SIZES)
                            self.assertEqual((x, y), tuple(int(state.get(k, fallback[k]) * size / 256) for k in ['x_hotspot', 'y_hotspot']))
                            self.assertLess(x, w)
                            self.assertLess(y, ht)
                            self.assertEqual(delay, state.get('x11_delay', fallback['x11_delay']))
                            end = offset + 36 + w * ht * 4
                            self.assertLessEqual(end, len(data))
                            pixels = data[offset + 36:end]
                            alpha = pixels[3::4]
                            self.assertIn(0, alpha)
                            self.assertTrue(any(alpha))
                            bgra = np.frombuffer(pixels, dtype=np.uint8).reshape(-1, 4)
                            self.assertTrue(np.all(bgra[:, :3] <= bgra[:, 3:4]))
                            seen[size].append(pixels)
                        self.assertEqual(end, len(data))
                        for size, sequence in seen.items():
                            self.assertEqual(len(sequence), len(frames))
                            # Compare each decoded frame to independently resized rendered PNGs.
                            from PIL import Image
                            for frame, pixels in zip(frames, sequence):
                                png = ROOT / 'artifacts/build-cache' / theme / (frame.stem + '.png')
                                image = Image.open(png).convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)
                                rgba = np.asarray(image, dtype=np.float64)
                                expected_pixels = rgba[:, :, [2, 1, 0, 3]].copy()
                                expected_pixels[:, :, :3] *= rgba[:, :, 3:4] / 255
                                expected_pixels = expected_pixels.astype(np.uint8).tobytes()
                                self.assertEqual(pixels, expected_pixels, f'{name}: frame {frame.name}, size {size}')
                        for alias in state.get('x11_symlinks', []):
                            path = theme + '/cursors/' + alias
                            info = z.getinfo(path)
                            self.assertEqual(info.create_system, 3)
                            self.assertTrue(stat.S_ISLNK(info.external_attr >> 16))
                            self.assertEqual(z.read(path).decode(), state['x11_name'])
                            self.assertIn(theme + '/cursors/' + z.read(path).decode(), names)
            actual = {n.split('/')[0] for n in names if n.startswith('CursorGlow-')}
            self.assertEqual(actual, expected)
            self.assertIn('licenses/Bibata-GPL-3.0.txt', names)
            self.assertIn('licenses/Clickgen-LICENSE.txt', names)

if __name__ == '__main__':
    unittest.main()
