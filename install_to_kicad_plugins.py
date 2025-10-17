"""
Interactive installer for a KiCad pcbnew action plugin.

What it does:
1) Asks the user to pick KiCad's "plugins" directory (GUI folder picker).
   - If you leave it blank, it will try to guess common locations.
2) Remembers that directory in a small config file for next time.
3) Copies (or symlinks with --link) the plugin file into that directory.
4) Also copies 'icon.png' next to the plugin, so the toolbar icon works.

Defaults assume your plugin file is 'winding_generator.py' and the icon is 'icon.png'.
"""

import argparse
import json
import os
import platform
import shutil
from pathlib import Path

# --- settings you might change ---
DEFAULT_PLUGIN = "winding_generator.py"
EXTRA_ASSETS = ["icon.png"]  # always copied
CONFIG_FILE = Path.home() / ".kicad_plugin_installer.json"
CONFIG_KEY = "plugins_dir"
# ---------------------------------

def load_saved_plugins_dir() -> Path | None:
    """
    Load the previously saved KiCad plugin directory path.

    :return: Path to the saved KiCad plugins folder, or None if not found.
    :rtype: Path | None
    """
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
    """
    Save the chosen KiCad plugin directory path for next time.

    :param p: Path to the KiCad plugins directory.
    :type p: Path
    """
    try:
        CONFIG_FILE.write_text(json.dumps({CONFIG_KEY: str(p)}, indent=2), encoding="utf-8")
    except Exception:
        pass

def guess_plugins_dir(major="9") -> list[Path]:
    """
    Guess likely plugin directory locations for KiCad across platforms.

    :param major: KiCad major version to search for (default: "9").
    :type major: str
    :return: List of possible existing plugin directories.
    :rtype: list[Path]
    """
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
    """
    Open a native folder picker (falls back to console input if GUI fails).

    :param initial_dir: Optional start directory for dialog.
    :type initial_dir: str | None
    :return: The path selected by the user or None if canceled.
    :rtype: Path | None
    """
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
        # fallback: terminal input
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
    """
    Copy or symlink a single file into the KiCad plugins directory.

    :param src: Source file path.
    :param dst_dir: Destination directory.
    :param target_name: Output filename at destination.
    :param link: If True, try to create a symlink (ignored if force_copy is True).
    :param force_copy: If True, always copy (used for assets like icon.png).
    """
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
    print(f"✔ Copied: {src} → {dst}")

def main():
    """
    Main function: orchestrates the plugin installation process.

    Steps:
    1) Parse command-line arguments.
    2) Locate the plugin directory (saved → user pick → guessed).
    3) Save directory path for next time.
    4) Copy/symlink the plugin Python file and copy the icon.
    5) Notify user and show next steps.
    """
    import argparse
    ap = argparse.ArgumentParser(description="Install/Update KiCad plugin (asks for plugins folder first).")
    ap.add_argument("--source", default=DEFAULT_PLUGIN, help="Plugin file in this repo (default: winding_generator.py)")
    ap.add_argument("--name", default=None, help="Target filename in KiCad (default: same as source)")
    ap.add_argument("--link", action="store_true", help="Create a symbolic link for the Python file instead of copying")
    ap.add_argument("--reset", action="store_true", help="Ignore saved folder and ask again")
    ap.add_argument("--kicad-major", default="9", help="KiCad major version for guesses (default: 9)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent
    src_py = (repo_root / args.source).resolve()
    if not src_py.is_file():
        raise SystemExit(f"ERROR: source plugin not found: {src_py}")

    # 1) Find plugins dir: saved → ask user → guess
    plugins_dir = None if args.reset else load_saved_plugins_dir()
    if not plugins_dir:
        plugins_dir = pick_folder_gui()
        if not plugins_dir:
            guesses = guess_plugins_dir(args.kicad_major)
            if guesses:
                print("\nNo folder chosen. Using detected path:", guesses[0])
                plugins_dir = guesses[0]
            else:
                raise SystemExit("\nNo folder chosen and nothing detected. Please run again and pick the folder.")

    # 2) Remember it
    save_plugins_dir(plugins_dir)

    # 3) Install Python file
    target_py = args.name or src_py.name
    print(f"\nKiCad plugins dir : {plugins_dir}")
    print(f"Installing Python : {src_py.name} → {target_py} ({'symlink' if args.link else 'copy'})")
    install_file(src_py, plugins_dir, target_py, link=args.link, force_copy=False)

    # 4) Install extra assets (always copied)
    for asset in EXTRA_ASSETS:
        src_asset = (repo_root / asset).resolve()
        if src_asset.exists():
            print(f"Installing asset  : {asset} → {asset} (copy)")
            install_file(src_asset, plugins_dir, asset, link=False, force_copy=True)
        else:
            print(f"⚠ Asset not found : {src_asset}")

    print("\nDone. In KiCad PCB Editor use: Tools → External Plugins → Refresh Plugins.")
    print("If you don’t see the toolbar icon, ensure 'icon.png' is next to the plugin file.")

if __name__ == "__main__":
    main()
