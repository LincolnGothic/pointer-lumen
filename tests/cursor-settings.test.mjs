import test from 'node:test';
import assert from 'node:assert/strict';
import { applyCursor, restoreCursor } from '../extension/modules/cursor-settings.js';

// Separate instances share a persistent backend, like reopened Gio.Settings.
class Settings {
  constructor(values) { this.values = values; this.pending = null; }
  get_string(key) { return this.values[key]; }
  get_int(key) { return this.values[key]; }
  get_boolean(key) { return this.values[key]; }
  set_string(key, value) { (this.pending ?? this.values)[key] = value; return true; }
  set_int(key, value) { (this.pending ?? this.values)[key] = value; return true; }
  set_boolean(key, value) { (this.pending ?? this.values)[key] = value; return true; }
  delay() { this.pending = {}; }
  apply() { Object.assign(this.values, this.pending); this.pending = {}; }
}
function fixture() {
  const desktop = {'cursor-theme': 'Yaru', 'cursor-size': 32};
  const backup = {'original-cursor-theme': '', 'original-cursor-size': 24,
    'original-cursor-captured': false, enabled: true};
  return {desktop, backup, interfaceSettings: new Settings(desktop), settings: new Settings(backup)};
}
test('first apply captures original theme and size and applies requested cursor', () => {
  const f = fixture();
  applyCursor(f.interfaceSettings, f.settings, 'CursorGlow-Modern-cyan', 48);
  assert.deepEqual(f.desktop, {'cursor-theme': 'CursorGlow-Modern-cyan', 'cursor-size': 48});
  assert.equal(f.backup['original-cursor-theme'], 'Yaru');
  assert.equal(f.backup['original-cursor-size'], 32);
  assert.equal(f.backup['original-cursor-captured'], true);
});
test('reopened preferences preserve original settings across repeated apply', () => {
  const f = fixture();
  applyCursor(f.interfaceSettings, f.settings, 'CursorGlow-Modern-cyan', 48);
  applyCursor(new Settings(f.desktop), new Settings(f.backup), 'CursorGlow-Original-red', 24);
  assert.deepEqual(f.desktop, {'cursor-theme': 'CursorGlow-Original-red', 'cursor-size': 24});
  restoreCursor(new Settings(f.desktop), new Settings(f.backup));
  assert.deepEqual(f.desktop, {'cursor-theme': 'Yaru', 'cursor-size': 32});
  assert.equal(f.backup['original-cursor-captured'], false);
  assert.equal(f.backup.enabled, false);
});
test('restore without capture preserves current theme and size and disables glow', () => {
  const f = fixture();
  restoreCursor(f.interfaceSettings, f.settings);
  assert.deepEqual(f.desktop, {'cursor-theme': 'Yaru', 'cursor-size': 32});
  assert.equal(f.backup.enabled, false);
});
test('after restore a later apply captures the newly selected user cursor', () => {
  const f = fixture();
  applyCursor(f.interfaceSettings, f.settings, 'CursorGlow-Modern-cyan', 48);
  restoreCursor(f.interfaceSettings, f.settings);
  f.desktop['cursor-theme'] = 'Adwaita';
  f.desktop['cursor-size'] = 24;
  applyCursor(new Settings(f.desktop), new Settings(f.backup), 'CursorGlow-Original-blue', 32);
  assert.equal(f.backup['original-cursor-theme'], 'Adwaita');
  assert.equal(f.backup['original-cursor-size'], 24);
  assert.equal(f.backup['original-cursor-captured'], true);
  assert.deepEqual(f.desktop, {'cursor-theme': 'CursorGlow-Original-blue', 'cursor-size': 32});
  restoreCursor(new Settings(f.desktop), new Settings(f.backup));
  assert.deepEqual(f.desktop, {'cursor-theme': 'Adwaita', 'cursor-size': 24});
});

test('locked desktop settings report a readable error and retain backup for retry', () => {
  const f = fixture();
  applyCursor(f.interfaceSettings, f.settings, 'CursorGlow-Modern-cyan', 48);
  const locked = new Settings(f.desktop);
  locked.set_string = () => false;
  assert.throws(() => restoreCursor(locked, f.settings), /Could not save cursor-theme/);
  assert.equal(f.backup['original-cursor-captured'], true);
  assert.equal(f.backup['original-cursor-theme'], 'Yaru');
  restoreCursor(f.interfaceSettings, f.settings);
  assert.deepEqual(f.desktop, {'cursor-theme': 'Yaru', 'cursor-size': 32});
});
