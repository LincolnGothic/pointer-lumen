// SPDX-License-Identifier: GPL-3.0-or-later

function write(settings, type, key, value) {
  if (!settings[`set_${type}`](key, value))
    throw new Error(`Could not save ${key}. Check whether desktop settings are locked.`);
}

export function applyCursor(interfaceSettings, settings, themeName, size) {
  if (!settings.get_boolean("original-cursor-captured")) {
    write(settings, "string", "original-cursor-theme", interfaceSettings.get_string("cursor-theme"));
    write(settings, "int", "original-cursor-size", interfaceSettings.get_int("cursor-size"));
    write(settings, "boolean", "original-cursor-captured", true);
  }
  write(interfaceSettings, "string", "cursor-theme", themeName);
  write(interfaceSettings, "int", "cursor-size", size);
}

export function restoreCursor(interfaceSettings, settings) {
  if (settings.get_boolean("original-cursor-captured")) {
    write(interfaceSettings, "string", "cursor-theme", settings.get_string("original-cursor-theme"));
    write(interfaceSettings, "int", "cursor-size", settings.get_int("original-cursor-size"));
    write(settings, "boolean", "original-cursor-captured", false);
  }
  write(settings, "boolean", "enabled", false);
}
