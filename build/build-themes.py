"""Build all themes from Bibata v2.0.7 using Clickgen v2.2.5 (build time only).

python build/build-themes.py --bibata-source PATH --clickgen-source PATH
    --node PATH --sharp PATH [--python-packages PATH]
All generation intermediates remain under artifacts/build-cache; no cleanup occurs.
"""
import argparse
import json
from pathlib import Path
import stat
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ['bibata-source', 'clickgen-source', 'node', 'sharp']:
        parser.add_argument('--' + arg, required=True, type=Path)
    parser.add_argument('--python-packages', type=Path)
    args = parser.parse_args()
    if args.python_packages:
        sys.path.insert(0, str(args.python_packages))
    sys.path.insert(0, str(args.clickgen_source / 'src'))
    from clickgen.parser import open_blob
    from clickgen.writer import to_x11
    from PIL import Image, ImageDraw
    presets_file = ROOT / 'extension/cursor-presets.json'
    presets = json.loads(presets_file.read_text())
    artifacts = ROOT / 'artifacts'
    cache = artifacts / 'build-cache'
    cache.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(args.node), str(ROOT / 'build/render-cursors.cjs'),
                    '--source', str(args.bibata_source), '--sharp', str(args.sharp),
                    '--manifest', str(presets_file), '--output', str(cache)], check=True)
    config = tomllib.loads((args.bibata_source / 'configs/normal/x.build.toml').read_text())['cursors']
    fallback = config['fallback_settings']
    sizes = sorted(set(presets['sizes'] + [s * 2 for s in presets['sizes']]))
    report = {'bibata_version': '2.0.7', 'clickgen_version': '2.2.5', 'sizes': sizes, 'themes': []}
    with zipfile.ZipFile(artifacts / 'themes.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for style in presets['styles']:
            for color in presets['colors']:
                theme = f"CursorGlow-{style['id']}-{color['id']}"
                z.writestr(theme + '/index.theme', f"[Icon Theme]\nName={theme}\nComment=Recolored Bibata 2.0.7; GPL-3.0\nInherits=Adwaita\n")
                states = 0
                for key, state in config.items():
                    if key == 'fallback_settings':
                        continue
                    frames = sorted((cache / theme).glob(state['png']))
                    if not frames:
                        raise FileNotFoundError(f"{theme}: no frames for {state['png']}")
                    hotspot = tuple(state.get(k, fallback[k]) for k in ['x_hotspot', 'y_hotspot'])
                    cursor = open_blob([f.read_bytes() for f in frames], hotspot, sizes,
                                       state.get('x11_delay', fallback['x11_delay']))
                    z.writestr(theme + '/cursors/' + state['x11_name'], to_x11(cursor.frames))
                    for alias in state.get('x11_symlinks', []):
                        info = zipfile.ZipInfo(theme + '/cursors/' + alias)
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        info.compress_type = zipfile.ZIP_DEFLATED
                        z.writestr(info, state['x11_name'])
                    states += 1
                report['themes'].append({'name': theme, 'states': states})
                print(f'Built {theme}: {states} states', flush=True)
        z.write(args.bibata_source / 'LICENSE', 'licenses/Bibata-GPL-3.0.txt')
        z.write(args.clickgen_source / 'LICENSE', 'licenses/Clickgen-LICENSE.txt')
        z.writestr('licenses/NOTICE.txt', 'Cursor Glow themes derived from Bibata 2.0.7 by ful1e5 and contributors.\nBuilt using Clickgen 2.2.5. Recoloring only; upstream geometry and cursor metadata preserved.\nSources: https://github.com/ful1e5/Bibata_Cursor/releases/tag/v2.0.7\nhttps://github.com/ful1e5/clickgen/releases/tag/v2.2.5\n')
    preview = Image.new('RGB', (1080, 400), '#F0F2F5')
    draw = ImageDraw.Draw(preview)
    draw.text((20, 12), 'Cursor Glow | twelve colors | Modern and Original', fill='#171717')
    for row, style in enumerate(presets['styles']):
        draw.text((20, 45 + row * 170), style['label'], fill='#171717')
        for col, color in enumerate(presets['colors']):
            theme = f"CursorGlow-{style['id']}-{color['id']}"
            arrow = Image.open(cache / theme / 'left_ptr.png').convert('RGBA').resize((72, 72), Image.Resampling.LANCZOS)
            x, y = 12 + col * 88, 70 + row * 170
            preview.paste(arrow, (x, y), arrow)
            draw.text((x, y + 86), color['label'], fill='#171717')
    preview.save(artifacts / 'color-preview.png')
    report['zip_bytes'] = (artifacts / 'themes.zip').stat().st_size
    (artifacts / 'theme-build-report.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
