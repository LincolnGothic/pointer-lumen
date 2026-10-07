import test from 'node:test';
import assert from 'node:assert/strict';
import { renderHighlight } from '../extension/modules/highlight-renderer.js';
import { Glow } from '../extension/modules/glow.js';

// Record the source alpha used for strokes, preserving Cairo save/restore state.
class Cairo {
  constructor() { this.alpha = 1; this.stack = []; this.strokes = []; }
  save() { this.stack.push(this.alpha); }
  restore() { this.alpha = this.stack.pop(); }
  setSourceRGBA(r, g, b, alpha) { this.alpha = alpha; }
  stroke() { this.strokes.push(this.alpha); }
  setOperator() {}
  paint() {}
  fill() {}
  translate() {}
  scale() {}
  rotate() {}
  newPath() {}
  arc() {}
  rectangle() {}
  closePath() {}
  setLineWidth() {}
  setDash() {}
  $dispose() {}
}
function draw(alpha, opacity) {
  const cr = new Cairo();
  const settings = {
    get_boolean: key => key === 'glow',
    get_int: key => ({'glow-radius': 10, 'glow-spread': 4})[key],
  };
  const glow = new Glow(settings);
  let glowAlpha;
  const realDraw = glow.draw.bind(glow);
  glow.draw = (context, params, path) => {
    glowAlpha = params.drawColor.a;
    realDraw(context, params, path);
  };
  renderHighlight({get_context: () => cr, get_surface_size: () => [200, 200]}, {
    drawSettings: {size: 125, borderWeight: 4, color: {red: 0, green: 180, blue: 255, alpha},
      radiusPx: 62.5, rotation: 0, gap: 1, opacity, clickAnimations: false,
      dashedBorder: false, dashGapSize: 1.5},
    clickState: null, glow, settings,
  });
  return {strokes: cr.strokes, glowAlpha};
}
test('zero overall opacity leaves no nontransparent ring or glow stroke', () => {
  const result = draw(1, 0);
  assert.ok(result.strokes.length >= 2);
  assert.ok(result.strokes.every(alpha => alpha === 0), JSON.stringify(result.strokes));
});
test('zero color alpha leaves no nontransparent ring or glow stroke', () => {
  const result = draw(0, 0.7);
  assert.ok(result.strokes.every(alpha => alpha === 0), JSON.stringify(result.strokes));
});
test('color alpha times opacity reaches both ring strokes and glow input', () => {
  const result = draw(0.5, 0.6);
  assert.deepEqual(result.strokes.slice(-2), [0.3, 0.3]);
  assert.equal(result.glowAlpha, 0.3);
  assert.ok(result.strokes.slice(0, -2).every(alpha => alpha > 0 && alpha <= 0.3));
});
