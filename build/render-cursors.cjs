// Build-time only: node render-cursors.cjs --source PATH --sharp PATH --manifest PATH --output PATH
const fs = require('node:fs/promises');
const path = require('node:path');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => {
  if (i % 2 === 0) a.push([v.replace(/^--/, ''), all[i + 1]]);
  return a;
}, []));
const sharp = require(args.sharp);
async function svgText(file) {
  const text = await fs.readFile(file, 'utf8');
  if (text.includes('<svg')) return text;
  // Windows ZIP/checkouts represent upstream symlinks as relative path text.
  return svgText(path.resolve(path.dirname(file), text.trim()));
}
async function svgFiles(dir) {
  const files = [];
  for (const entry of await fs.readdir(dir, {withFileTypes: true})) {
    const file = path.join(dir, entry.name);
    if ((await fs.stat(file)).isDirectory()) files.push(...await svgFiles(file));
    else if (entry.name.endsWith('.svg')) files.push(file);
    else {
      const target = path.resolve(dir, (await fs.readFile(file, 'utf8')).trim());
      files.push(...await svgFiles(target));
    }
  }
  return files.sort((a, b) => path.basename(a).localeCompare(path.basename(b)));
}
async function main() {
  const presets = JSON.parse(await fs.readFile(args.manifest, 'utf8'));
  for (const style of presets.styles) {
    const dir = path.join(args.source, 'svg', style.id.toLowerCase());
    const files = await svgFiles(dir);
    for (const color of presets.colors) {
      const out = path.join(args.output, `CursorGlow-${style.id}-${color.id}`);
      await fs.mkdir(out, {recursive: true});
      for (let start = 0; start < files.length; start += 8) {
        await Promise.all(files.slice(start, start + 8).map(async file => {
          const svg = (await svgText(file))
            .replace(/#00ff00/ig, color.hex).replace(/#0000ff/ig, color.outline)
            .replace(/#ff0000/ig, color.hex);
          await sharp(Buffer.from(svg)).resize(256, 256).png()
            .toFile(path.join(out, path.basename(file).replace(/\.svg$/, '.png')));
        }));
      }
      process.stdout.write(`Rendered ${style.id} ${color.id}: ${files.length} SVGs\n`);
    }
  }
}
main().catch(error => {console.error(error); process.exitCode = 1;});
