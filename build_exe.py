from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_DIR / "Bruteforcer.py"
ICON_FILE = PROJECT_DIR / "icon.ico"
VERSION_FILE = PROJECT_DIR / "version_info.txt"
PASSWORDS_DIR = PROJECT_DIR / "passwords"
BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"


def add_data_arg(source: Path, target: str) -> str:
    separator = ";" if sys.platform.startswith("win") else ":"
    return f"{source}{separator}{target}"


def is_excluded_password_file(path: Path) -> bool:
    if path.name.lower() in {"rockyou.txt"}:
        return True
    if not path.exists() or path.stat().st_size > 1024:
        return False
    return b"version https://git-lfs.github.com/spec/v1" in path.read_bytes()[:256]


def iter_password_data_files():
    if not PASSWORDS_DIR.exists():
        return
    for path in PASSWORDS_DIR.glob("*.txt"):
        if not is_excluded_password_file(path):
            yield path


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller")
        return 1

    if not ENTRY_SCRIPT.exists():
        print(f"Entry script not found: {ENTRY_SCRIPT}")
        return 1

    args = [
        str(ENTRY_SCRIPT),
        "--name=Bruteforcer",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
        "--hidden-import=msoffcrypto",
        "--hidden-import=PyPDF2",
        "--hidden-import=rarfile",
        "--hidden-import=py7zr",
        "--hidden-import=pyzipper",
        "--hidden-import=olefile",
        "--hidden-import=certifi",
    ]

    if ICON_FILE.exists():
        args.append(f"--icon={ICON_FILE}")
        args.append(f"--add-data={add_data_arg(ICON_FILE, '.')}")
    else:
        print(f"Warning: icon not found: {ICON_FILE}")

    if VERSION_FILE.exists():
        args.append(f"--version-file={VERSION_FILE}")
    else:
        print(f"Warning: version info not found: {VERSION_FILE}")

    password_files = list(iter_password_data_files() or [])
    if password_files:
        for password_file in password_files:
            args.append(f"--add-data={add_data_arg(password_file, 'passwords')}")
    else:
        print(f"Warning: passwords folder not found: {PASSWORDS_DIR}")

    PyInstaller.__main__.run(args)
    print(f"Build complete: {DIST_DIR / 'Bruteforcer.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
