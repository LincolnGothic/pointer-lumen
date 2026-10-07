// SPDX-License-Identifier: GPL-3.0-or-later

import Adw from "gi://Adw";
import Gio from "gi://Gio";
import Gdk from "gi://Gdk";
import Gtk from "gi://Gtk";
import { ExtensionPreferences } from "resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js";
import { applyCursor, restoreCursor } from "./modules/cursor-settings.js";

export default class CursorGlowPreferences extends ExtensionPreferences {
  fillPreferencesWindow(window) {
    const settings = this.getSettings();
    const interfaceSettings = new Gio.Settings({ schema_id: "org.gnome.desktop.interface" });
    const [, contents] = this.dir.get_child("cursor-presets.json").load_contents(null);
    const presets = JSON.parse(new TextDecoder().decode(contents));
    const page = new Adw.PreferencesPage({ title: "Pointer Lumen", icon_name: "preferences-desktop-appearance-symbolic" });
    window.add(page);

    const arrow = new Adw.PreferencesGroup({ title: "Arrow", description: "Choose a preset, then Apply. Your original cursor is saved until Restore." });
    page.add(arrow);
    const combo = (group, title, labels, selected = 0) => {
      const row = new Adw.ComboRow({ title, model: Gtk.StringList.new(labels), selected });
      group.add(row);
      return row;
    };
    const currentTheme = interfaceSettings.get_string("cursor-theme");
    const colorIndex = presets.colors.findIndex(color => currentTheme.endsWith(`-${color.id}`));
    const styleIndex = presets.styles.findIndex(style => currentTheme.startsWith(`CursorGlow-${style.id}-`));
    const sizeIndex = presets.sizes.indexOf(interfaceSettings.get_int("cursor-size"));
    const colors = combo(arrow, "Color", presets.colors.map(color => color.label), Math.max(0, colorIndex));
    const styles = combo(arrow, "Style", presets.styles.map(style => style.label), Math.max(0, styleIndex));
    const sizes = combo(arrow, "Size", presets.sizes.map(String), Math.max(0, sizeIndex));
    const actions = new Adw.ActionRow({ title: "Cursor settings" });
    const apply = new Gtk.Button({ label: "Apply", valign: Gtk.Align.CENTER, css_classes: ["suggested-action"] });
    const restore = new Gtk.Button({ label: "Restore", valign: Gtk.Align.CENTER });
    actions.add_suffix(apply);
    actions.add_suffix(restore);
    arrow.add(actions);
    const status = new Adw.ActionRow({ title: "", visible: false });
    arrow.add(status);
    const run = (action, message) => {
      try {
        action();
        status.title = message;
      } catch (error) {
        status.title = "Cursor settings could not be changed";
        status.subtitle = error.message;
        status.visible = true;
        return;
      }
      status.subtitle = "";
      status.visible = true;
    };
    apply.connect("clicked", () => run(() => {
      const theme = `CursorGlow-${presets.styles[styles.selected].id}-${presets.colors[colors.selected].id}`;
      applyCursor(interfaceSettings, settings, theme, presets.sizes[sizes.selected]);
    }, "Cursor applied"));
    restore.connect("clicked", () => run(() => restoreCursor(interfaceSettings, settings), "Original cursor restored; glow disabled"));

    const glow = new Adw.PreferencesGroup({ title: "Glow", description: "Changes take effect immediately." });
    page.add(glow);
    const enabled = new Adw.SwitchRow({ title: "Enable glow" });
    settings.bind("enabled", enabled, "active", Gio.SettingsBindFlags.DEFAULT);
    glow.add(enabled);
    const colorRow = new Adw.ActionRow({ title: "Glow color", subtitle: "Includes color transparency" });
    const dialog = new Gtk.ColorDialog({ with_alpha: true });
    const rgba = new Gdk.RGBA();
    rgba.parse(settings.get_string("color"));
    const colorButton = new Gtk.ColorDialogButton({ dialog, rgba, valign: Gtk.Align.CENTER });
    colorButton.connect("notify::rgba", () => settings.set_string("color", colorButton.rgba.to_string()));
    colorRow.add_suffix(colorButton);
    glow.add(colorRow);
    const spin = (title, key, min, max, step, digits = 0) => {
      const row = new Adw.SpinRow({ title, digits, adjustment: new Gtk.Adjustment({ lower: min, upper: max, step_increment: step, page_increment: step * 5 }) });
      settings.bind(key, row, "value", Gio.SettingsBindFlags.DEFAULT);
      glow.add(row);
    };
    spin("Blur radius", "glow-radius", 0, 100, 1);
    spin("Spread", "glow-spread", 0, 50, 1);
    spin("Opacity", "opacity", 0, 1, 0.05, 2);
    spin("Ring diameter", "size", 40, 200, 1);
    const shapeIds = ["circle", "squircle", "square"];
    const shapes = combo(glow, "Ring shape", ["Circle", "Squircle", "Square"], Math.max(0, shapeIds.indexOf(settings.get_string("shape"))));
    shapes.connect("notify::selected", () => {
      settings.set_string("shape", shapeIds[shapes.selected]);
      settings.set_int("corner-radius", [50, 25, 0][shapes.selected]);
    });
  }
}
