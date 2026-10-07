#!/usr/bin/env bash
set -euo pipefail

package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
uuid='cursor-glow@local'

for tool in gnome-shell gnome-extensions glib-compile-schemas unzip; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Missing prerequisite: %s\n' "$tool" >&2
        exit 1
    fi
done

shell_version="$(gnome-shell --version)"
if [[ ! "$shell_version" =~ ^GNOME\ Shell\ 50([.[:space:]]|$) ]]; then
    printf 'Pointer Lumen v1 requires GNOME Shell 50. Found: %s\n' "$shell_version" >&2
    exit 1
fi
if [[ "${XDG_SESSION_TYPE:-}" != 'wayland' ]]; then
    printf 'Run this installer in your Ubuntu GNOME Wayland desktop session.\n' >&2
    exit 1
fi

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
extension_dir="$data_dir/gnome-shell/extensions/$uuid"
icons_dir="$data_dir/icons"
mapfile -t themes < <(unzip -Z -1 "$package_dir/themes.zip" | sed -n 's#^\(CursorGlow-[^/]*\)/index.theme$#\1#p')
if [[ "${#themes[@]}" -ne 24 ]]; then
    printf 'The package must contain all 24 Pointer Lumen themes.\n' >&2
    exit 1
fi

# Check every target before writing anything. Never overwrite or delete.
for target in "$extension_dir" "${themes[@]/#/$icons_dir/}"; do
    if [[ -e "$target" || -L "$target" ]]; then
        printf 'Target already exists; no files were changed: %s\n' "$target" >&2
        exit 1
    fi
done
unzip -tq "$package_dir/themes.zip" >/dev/null
glib-compile-schemas --strict --dry-run "$package_dir/extension/schemas"

mkdir -p -- "$extension_dir" "$icons_dir"
cp -R -- "$package_dir/extension/." "$extension_dir/"
glib-compile-schemas --strict "$extension_dir/schemas"
for theme in "${themes[@]}"; do
    unzip -q "$package_dir/themes.zip" "$theme/index.theme" "$theme/cursors/*" -d "$icons_dir"
done

printf '\nInstalled Pointer Lumen and 24 themes for the current user.\n'
printf 'Log out and back in, then run:\n\n'
printf '  gnome-extensions enable %s\n' "$uuid"
printf '  gnome-extensions prefs %s\n\n' "$uuid"
printf 'Apply a cursor in the settings window. Restore original cursor returns your previous theme and size.\n'
