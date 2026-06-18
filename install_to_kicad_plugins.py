"""
Interactive installer for KiCad pcbnew action plugins.

Now installs TWO plugins:
- main plugin  (default: winding_generator.py)
- via plugin   (default: place_vias.py)

Also installs two explicit assets next to the plugins:
- icon    -> 'icon.png'
- diagram -> 'parameter_sketch.png'
"""

import argparse
import json
import os
import platform
import shutil
from pathlib import Path

# --- defaults you may change ---
DEFAULT_MAIN_PLUGIN = ["action_plugin.py", "gui.py", "geometry.py",
                             "drawing.py", "rectangular_windings.py", "rounded_windings.py"]
#DEFAULT_MAIN_PLUGIN = "winding_generator.py"
DEFAULT_VIA_PLUGIN  = "place_vias.py"
ICON_TARGET_NAME = "icon.png"
VIA_ICON_TARGET_NAME = "vias_icon.png"
DIAGRAM_TARGET_NAME = "parameter_sketch.png"
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

def install_file(src: Path, dst_dir: Path, target_name: str, link: bool, force_copy: bool = False):
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / target_name
    _remove_if_exists(dst)
    if link and not force_copy:
        try:
            os.symlink(src, dst)
            print(f"✔ Symlink created: {dst} → {src}")
            return
        except OSError as e:
            print(f"⚠ Symlink failed ({e}). Falling back to copy.")
    shutil.copy2(src, dst)
    print(f"✔ Copied: {src.name} → {dst.name}")

def _install_plugin(repo_root: Path, src_name: str, dst_dir: Path, target_name: str | None, link: bool):
    src = (repo_root / src_name).resolve()
    if not src.is_file():
        print(f"⚠ Skipping (not found): {src}")
        return
    final_name = target_name or src.name
    print(f"Installing Python : {src.name} → {final_name} ({'symlink' if link else 'copy'})")
    install_file(src, dst_dir, final_name, link=link, force_copy=False)

def main():
    ap = argparse.ArgumentParser(description="Install/Update KiCad plugins (asks for plugins folder first).")

    # Main spiral plugin
    ap.add_argument("--main-source", default=DEFAULT_MAIN_PLUGIN,
                    help=f"Main plugin file in this repo (default: {DEFAULT_MAIN_PLUGIN})")
    ap.add_argument("--main-name", default=None,
                    help="Target filename for main plugin in KiCad (default: same as source)")
    ap.add_argument("--main-link", action="store_true",
                    help="Symlink the main plugin instead of copying")

    # Via plugin
    ap.add_argument("--via-source", default=DEFAULT_VIA_PLUGIN,
                    help=f"Via plugin file in this repo (default: {DEFAULT_VIA_PLUGIN})")
    ap.add_argument("--via-name", default=None,
                    help="Target filename for via plugin in KiCad (default: same as source)")
    ap.add_argument("--via-link", action="store_true",
                    help="Symlink the via plugin instead of copying")
    ap.add_argument("--no-via", action="store_true",
                    help="Do not install the via plugin")

    # Common / assets
    ap.add_argument("--reset", action="store_true",
                    help="Ignore saved folder and ask again")
    ap.add_argument("--kicad-major", default="9",
                    help="KiCad major version for guesses (default: 9)")
    ap.add_argument("--icon-src", default="icon.png",
                    help=f"Path to icon image to install as {ICON_TARGET_NAME} (default: icon.png)")
    ap.add_argument("--diagram-src", default="parameter_sketch.png",
                    help=f"Path to diagram image to install as {DIAGRAM_TARGET_NAME} (default: parameter_sketch.png)")
    ap.add_argument("--via-icon-src", default="vias_icon.png",  # <— NEW
                    help=f"Path to via icon image to install as {VIA_ICON_TARGET_NAME} (default: vias_icon.png)")

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
    for args.main_source in DEFAULT_MAIN_PLUGIN:
        _install_plugin(repo_root, args.main_source, plugins_dir, args.main_name, args.main_link)

    # Install via plugin (optional)
    if not args.no_via:
        _install_plugin(repo_root, args.via_source, plugins_dir, args.via_name, args.via_link)

    # Install icon → icon.png
    icon_src = (repo_root / args.icon_src).resolve()
    if icon_src.exists():
        print(f"Installing icon    : {icon_src.name} → {ICON_TARGET_NAME} (copy)")
        install_file(icon_src, plugins_dir, ICON_TARGET_NAME, link=False, force_copy=True)
    else:
        print(f"⚠ Icon not found   : {icon_src}")

    # Install diagram → parameter_sketch.png
    diagram_src = (repo_root / args.diagram_src).resolve()
    if diagram_src.exists():
        print(f"Installing diagram : {diagram_src.name} → {DIAGRAM_TARGET_NAME} (copy)")
        install_file(diagram_src, plugins_dir, DIAGRAM_TARGET_NAME, link=False, force_copy=True)
    else:
        print(f"⚠ Diagram not found: {diagram_src}")

    # Install via icon → vias_icon.png   (NEW)
    via_icon_src = (repo_root / args.via_icon_src).resolve()
    if via_icon_src.exists():
        print(f"Installing via icon: {via_icon_src.name} → {VIA_ICON_TARGET_NAME} (copy)")
        install_file(via_icon_src, plugins_dir, VIA_ICON_TARGET_NAME, link=False, force_copy=True)
    else:
        print(f"⚠ Via icon not found: {via_icon_src}")

    print("\nDone. In KiCad PCB Editor use: Tools → External Plugins → Refresh Plugins.")
    print(f"Plugins expect {ICON_TARGET_NAME}, {DIAGRAM_TARGET_NAME} and {VIA_ICON_TARGET_NAME} next to them.")

if __name__ == "__main__":
    main()
