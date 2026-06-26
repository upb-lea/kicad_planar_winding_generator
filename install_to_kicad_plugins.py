"""
Interactive installer for KiCad pcbnew action plugins.

Installs two plugin packages:
- winding plugin package  (planar_winding_plugin)
- via plugin package (via_plugin)

Each package is copied or symlinked into KiCad's scripting/plugins directory.
Assets such as icons and diagrams are expected to live inside their package.
"""

import argparse
import json
import os
import platform
import shutil
from pathlib import Path

# --- defaults you may change ---
DEFAULT_MAIN_PLUGIN = "planar_winding_plugin"
DEFAULT_VIA_PLUGIN  = "via_plugin"
CONFIG_FILE = Path.home() / ".kicad_plugin_installer.json"
CONFIG_KEY = "plugins_dir"
# --------------------------------

def load_saved_plugins_dir() -> Path | None:
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            p = Path(data.get(CONFIG_KEY, ""))
            if p.exists():
                return p
        except Exception:
            pass
    return None

def save_plugins_dir(p: Path) -> None:
    try:
        CONFIG_FILE.write_text(json.dumps({CONFIG_KEY: str(p)}, indent=2), encoding="utf-8")
    except Exception:
        pass

def guess_plugins_dir(major="9") -> list[Path]:
    home = Path.home()
    sys = platform.system()
    c = []
    if sys == "Windows":
        c += [
            home / f"AppData/Roaming/KiCad/{major}.0/scripting/plugins",
            home / f"Documents/KiCad/{major}.0/scripting/plugins",
            home / f"OneDrive/Documents/KiCad/{major}.0/scripting/plugins",
            home / f"OneDrive/Dokumente/KiCad/{major}.0/scripting/plugins",
        ]
    elif sys == "Darwin":
        c += [
            home / f"Library/Preferences/kicad/{major}.0/scripting/plugins",
            home / f"Library/Preferences/kicad/{int(major)-1}.0/scripting/plugins",
        ]
    else:  # Linux
        c += [
            home / f".local/share/kicad/{major}.0/scripting/plugins",
            home / f".local/share/kicad/{int(major)-1}.0/scripting/plugins",
        ]
    return [p for p in c if p.exists()]

def pick_folder_gui(initial_dir: str | None = None) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        path = filedialog.askdirectory(
            initialdir=initial_dir or str(Path.home()),
            title="Select KiCad 'plugins' directory (Tools → External Plugins → Open Plugin Directory)"
        )
        root.destroy()
        return Path(path) if path else None
    except Exception:
        print("\nPlease paste your KiCad plugins directory path")
        print("(In KiCad PCB Editor: Tools → External Plugins → Open Plugin Directory)")
        path = input("Plugins folder path (leave empty to cancel): ").strip()
        return Path(path) if path else None

def _remove_if_exists(dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        try:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        except Exception:
            pass

def _install_package(repo_root: Path, package_name: str, dst_dir: Path, link: bool):
    src = (repo_root / package_name).resolve()

    if not src.is_dir():
        print(f"⚠ Skipping package (not found): {src}")
        return

    dst = (dst_dir / package_name).resolve()

    print(f"Installing package: {src.name} → {dst.name} "
          f"({'symlink' if link else 'copy'})")

    _remove_if_exists(dst)
    dst_dir.mkdir(parents=True, exist_ok=True)

    if link:
        try:
            os.symlink(src, dst, target_is_directory=True)
            print(f"✔ Symlink created: {dst} → {src}")
            return
        except OSError as e:
            print(f"⚠ Symlink failed ({e}). Falling back to copy.")

    shutil.copytree(src, dst)
    print(f"✔ Copied package: {src.name} → {dst.name}")

def main():
    ap = argparse.ArgumentParser(description="Install/Update KiCad plugins (asks for plugins folder first).")

    # Main spiral plugin
    ap.add_argument("--main-source", default=DEFAULT_MAIN_PLUGIN,
                    help=f"Main plugin file in this repo (default: {DEFAULT_MAIN_PLUGIN})")
    ap.add_argument("--main-link", action="store_true",
                    help="Symlink the main plugin instead of copying")

    # Via plugin
    ap.add_argument("--via-source", default=DEFAULT_VIA_PLUGIN,
                    help=f"Via plugin file in this repo (default: {DEFAULT_VIA_PLUGIN})")
    ap.add_argument("--via-link", action="store_true",
                    help="Symlink the via plugin instead of copying")
    ap.add_argument("--no-via", action="store_true",
                    help="Do not install the via plugin")

    # Common / assets
    ap.add_argument("--reset", action="store_true",
                    help="Ignore saved folder and ask again")
    ap.add_argument("--kicad-major", default="9",
                    help="KiCad major version for guesses (default: 9)")

    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent

    # Resolve plugins dir
    plugins_dir = None if args.reset else load_saved_plugins_dir()
    if not plugins_dir:
        plugins_dir = pick_folder_gui()
        if not plugins_dir:
            guesses = guess_plugins_dir(args.kicad_major)
            if guesses:
                print("\nNo folder chosen. Using detected path:", guesses[0])
                plugins_dir = guesses[0]
            else:
                raise SystemExit("\nNo folder chosen and nothing detected. Run again and pick the folder.")

    save_plugins_dir(plugins_dir)

    print(f"\nKiCad plugins dir : {plugins_dir}")

    # Install main plugin
    _install_package(repo_root, args.main_source, plugins_dir, args.main_link)
    # Install via plugin (optional)
    if not args.no_via:
        _install_package(repo_root, args.via_source, plugins_dir, args.via_link)

    print("\nDone. In KiCad PCB Editor use: Tools → External Plugins → Refresh Plugins.")
    # print(f"Plugins expect {ICON_TARGET_NAME}, {DIAGRAM_TARGET_NAME} and {VIA_ICON_TARGET_NAME} next to them.")

if __name__ == "__main__":
    main()
