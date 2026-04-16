import io
import json
import os
import re
import runpy
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import platform
import shutil
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

try:
    import certifi
except ImportError:
    certifi = None


APP_DIR = Path.home() / "Bruteforcer"
LIB_DIR = APP_DIR / "lib"
PYTHON_LIB_DIR = LIB_DIR / "python"
HASHCAT_VERSION = "7.1.2"
HASHCAT_ARCHIVE_NAME = f"hashcat-{HASHCAT_VERSION}.7z"
HASHCAT_DOWNLOAD_URL = (
    f"https://github.com/hashcat/hashcat/releases/download/v{HASHCAT_VERSION}/"
    f"{HASHCAT_ARCHIVE_NAME}"
)
HASHCAT_ARCHIVE_SIZE_BYTES = 19_682_772
HASHCAT_EXTRACTED_SIZE_BYTES = 85_000_000
TOOLS_DIR = LIB_DIR / "tools"
OFFICE2JOHN_URL = "https://raw.githubusercontent.com/openwall/john/bleeding-jumbo/run/office2john.py"
OFFICE2JOHN_PATH = TOOLS_DIR / "office2john.py"
PDF2JOHN_URL = "https://raw.githubusercontent.com/openwall/john/bleeding-jumbo/run/pdf2john.py"
PDF2JOHN_PATH = TOOLS_DIR / "pdf2john.py"
JOHN_ARCHIVE_NAME = "john-1.9.0-jumbo-1-win64.zip"
JOHN_ARCHIVE_URL = "https://www.openwall.com/john/k/john-1.9.0-jumbo-1-win64.zip"
JOHN_ARCHIVE_SIZE_BYTES = 65_376_163
JOHN_ROOT = TOOLS_DIR / "john-1.9.0-jumbo-1-win64"
ZIP2JOHN_EXE = JOHN_ROOT / "run" / "zip2john.exe"
RAR2JOHN_EXE = JOHN_ROOT / "run" / "rar2john.exe"
SEVENZIP2HASHCAT_ARCHIVE_NAME = "7z2hashcat64-2.0.zip"
SEVENZIP2HASHCAT_URL = "https://github.com/philsmd/7z2hashcat/releases/download/2.0/7z2hashcat64-2.0.zip"
SEVENZIP2HASHCAT_ROOT = TOOLS_DIR / "7z2hashcat64-2.0"
SEVENZIP2HASHCAT_EXE = SEVENZIP2HASHCAT_ROOT / "7z2hashcat64-2.0.exe"
SEVENZIP_VERSION = "26.00"
SEVENZIP_INSTALLER_NAME = "7z2600-x64.exe"
SEVENZIP_INSTALLER_URL = f"https://www.7-zip.org/a/{SEVENZIP_INSTALLER_NAME}"
SEVENZIP_INSTALLER_SIZE_BYTES = 1_655_627


class GPUBackendError(RuntimeError):
    pass


def _hidden_subprocess_kwargs():
    if os.name != "nt":
        return {}

    kwargs = {}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags

    startupinfo_cls = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_cls is not None:
        startupinfo = startupinfo_cls()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo

    return kwargs


def _run_python_script_in_process(script_path, args):
    script_path = Path(script_path)
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    original_argv = sys.argv[:]
    original_path = list(sys.path)

    try:
        extra_paths = [str(script_path.parent), str(PYTHON_LIB_DIR)]
        for entry in reversed(extra_paths):
            if entry and entry not in sys.path:
                sys.path.insert(0, entry)

        sys.argv = [str(script_path), *[str(arg) for arg in args]]
        returncode = 0

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            try:
                runpy.run_path(str(script_path), run_name="__main__")
            except SystemExit as exc:
                code = exc.code
                if code is None:
                    returncode = 0
                elif isinstance(code, int):
                    returncode = code
                else:
                    returncode = 1
                    if code:
                        print(code, file=sys.stderr)

        return subprocess.CompletedProcess(
            [str(script_path), *[str(arg) for arg in args]],
            returncode,
            stdout_buffer.getvalue(),
            stderr_buffer.getvalue(),
        )
    finally:
        sys.argv = original_argv
        sys.path[:] = original_path


def _resolve_python_executable():
    candidates = []
    for attr_name in ("_base_executable", "executable"):
        value = getattr(sys, attr_name, None)
        if value:
            candidates.append(value)

    for command in ("python", "py"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(resolved)

    seen = set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.abspath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)

        name = Path(candidate).name.lower()
        if getattr(sys, "frozen", False) and name == Path(sys.executable).name.lower():
            continue
        if name.startswith("python") or name == "py.exe":
            return candidate

    if not getattr(sys, "frozen", False):
        return sys.executable
    return None


def _download_file(url, destination, progress_callback=None, label=None, fallback_total=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Fall back to the OS certificate store when certifi is unavailable.
    cafile = certifi.where() if certifi is not None else None
    context = ssl.create_default_context(cafile=cafile)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    request = urllib.request.Request(url, headers={"User-Agent": "Bruteforcer/1.0"})

    try:
        with opener.open(request, timeout=120) as response, open(destination, "wb") as output:
            total_size = response.headers.get("Content-Length")
            try:
                total_size = int(total_size) if total_size else None
            except Exception:
                total_size = None
            total_size = total_size or fallback_total

            downloaded = 0
            if progress_callback and label:
                progress_callback(label, 0)

            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if progress_callback and label and total_size and total_size > 0:
                    percent = min(100, int((downloaded / total_size) * 100))
                    progress_callback(label, percent)
    except Exception:
        try:
            destination.unlink(missing_ok=True)
        except Exception:
            pass
        raise


class HashcatRuntimeManager:
    def __init__(self, lib_dir=None):
        self.lib_dir = Path(lib_dir) if lib_dir else LIB_DIR
        self.runtime_root = self.lib_dir / f"hashcat-{HASHCAT_VERSION}"
        self.archive_path = self.lib_dir / HASHCAT_ARCHIVE_NAME
        self.exe_path = self.runtime_root / "hashcat.exe"
        self.work_root = Path(tempfile.gettempdir()) / "Bruteforcer" / f"hashcat-{HASHCAT_VERSION}"
        self.sevenzip_root = self.lib_dir / "7zip"
        self.sevenzip_installer_path = self.lib_dir / SEVENZIP_INSTALLER_NAME
        self.sevenzip_exe_path = self.sevenzip_root / "7z.exe"

    @staticmethod
    def get_runtime_info():
        return {
            "name": "Hashcat",
            "version": HASHCAT_VERSION,
            "download_url": HASHCAT_DOWNLOAD_URL,
            "download_bytes": HASHCAT_ARCHIVE_SIZE_BYTES,
            "installed_bytes": HASHCAT_EXTRACTED_SIZE_BYTES,
            "install_dir": str(LIB_DIR / f"hashcat-{HASHCAT_VERSION}"),
        }

    def is_installed(self):
        return self.exe_path.exists()

    def ensure_installed(self, progress_callback=None):
        if self.is_installed():
            return self.exe_path

        self.lib_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback("Preparing archive extractor…", None)
        self._ensure_7zip_installed(progress_callback)

        if progress_callback:
            progress_callback("Downloading GPU backend package…", 0)
        self._download_archive(progress_callback)

        if progress_callback:
            progress_callback("Extracting GPU backend package…", None)
        self._extract_archive()

        if not self.exe_path.exists():
            raise GPUBackendError(
                f"GPU backend installation finished, but {self.exe_path.name} was not found."
            )

        try:
            self.archive_path.unlink(missing_ok=True)
        except Exception:
            pass

        return self.exe_path

    def probe_devices(self):
        if not self.is_installed():
            raise GPUBackendError("GPU backend is not installed.")
        workdir = self.prepare_workdir()

        try:
            result = subprocess.run(
                [str(workdir / "hashcat.exe"), "-I"],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=60,
                **_hidden_subprocess_kwargs(),
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to query GPU devices: {exc}") from exc

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        devices = GPUBackend._parse_backend_devices(output)
        has_gpu = bool(
            devices
        )
        return {
            "returncode": result.returncode,
            "output": output.strip(),
            "has_gpu": has_gpu,
            "devices": devices,
        }

    def prepare_workdir(self):
        self._sync_work_runtime()
        return self.work_root

    def _download_archive(self, progress_callback=None):
        def _report(block_num, block_size, total_size):
            if not progress_callback:
                return
            total = total_size if total_size and total_size > 0 else HASHCAT_ARCHIVE_SIZE_BYTES
            downloaded = min(block_num * block_size, total)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            progress_callback("Downloading GPU backend…", percent)

        try:
            _download_file(
                HASHCAT_DOWNLOAD_URL,
                self.archive_path,
                progress_callback=progress_callback,
                label="Downloading GPU backend...",
                fallback_total=HASHCAT_ARCHIVE_SIZE_BYTES,
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to download GPU backend: {exc}") from exc

    def _extract_archive(self):
        try:
            if self.runtime_root.exists():
                for item in self.runtime_root.iterdir():
                    if item.is_dir():
                        for nested in sorted(item.rglob("*"), reverse=True):
                            if nested.is_file():
                                nested.unlink(missing_ok=True)
                            elif nested.is_dir():
                                nested.rmdir()
                        item.rmdir()
                    else:
                        item.unlink(missing_ok=True)
            result = subprocess.run(
                [str(self.sevenzip_exe_path), "x", str(self.archive_path), f"-o{self.lib_dir}", "-y"],
                capture_output=True,
                text=True,
                timeout=300,
                **_hidden_subprocess_kwargs(),
            )
            if result.returncode != 0:
                output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
                raise GPUBackendError(output or "7-Zip extraction failed.")
        except Exception as exc:
            if isinstance(exc, GPUBackendError):
                raise
            raise GPUBackendError(f"Failed to extract GPU backend: {exc}") from exc

    def _ensure_7zip_installed(self, progress_callback=None):
        if self.sevenzip_exe_path.exists():
            return self.sevenzip_exe_path
        if platform.system().lower() != "windows":
            raise GPUBackendError("Automatic Hashcat extraction is currently implemented for Windows only.")

        if progress_callback:
            progress_callback("Downloading 7-Zip extractor…", 0)
        self._download_7zip_installer(progress_callback)

        self.sevenzip_root.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.sevenzip_installer_path),
            "/S",
            f"/D={self.sevenzip_root}",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                **_hidden_subprocess_kwargs(),
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to install 7-Zip extractor: {exc}") from exc

        if result.returncode != 0 or not self.sevenzip_exe_path.exists():
            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
            raise GPUBackendError(
                "Failed to install 7-Zip extractor.\n"
                f"{output or '7-Zip installer did not complete successfully.'}"
            )

        try:
            self.sevenzip_installer_path.unlink(missing_ok=True)
        except Exception:
            pass
        return self.sevenzip_exe_path

    def _sync_work_runtime(self):
        if not self.runtime_root.exists():
            raise GPUBackendError(f"Hashcat runtime folder is missing: {self.runtime_root}")

        try:
            self.work_root.mkdir(parents=True, exist_ok=True)
            marker = self.work_root / ".runtime_version"
            current_version = f"{HASHCAT_VERSION}|{self.runtime_root.stat().st_mtime_ns}"
            needs_sync = True
            if marker.exists():
                try:
                    needs_sync = marker.read_text(encoding="utf-8") != current_version
                except Exception:
                    needs_sync = True
            if not needs_sync and (self.work_root / "hashcat.exe").exists():
                return

            for item in list(self.work_root.iterdir()):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

            for item in self.runtime_root.iterdir():
                target = self.work_root / item.name
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)

            marker.write_text(current_version, encoding="utf-8")
        except Exception as exc:
            raise GPUBackendError(
                f"Failed to prepare writable Hashcat work runtime: {exc}"
            ) from exc

    def _download_7zip_installer(self, progress_callback=None):
        def _report(block_num, block_size, total_size):
            if not progress_callback:
                return
            total = total_size if total_size and total_size > 0 else SEVENZIP_INSTALLER_SIZE_BYTES
            downloaded = min(block_num * block_size, total)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            progress_callback("Downloading 7-Zip extractor…", percent)

        try:
            _download_file(
                SEVENZIP_INSTALLER_URL,
                self.sevenzip_installer_path,
                progress_callback=progress_callback,
                label="Downloading 7-Zip extractor...",
                fallback_total=SEVENZIP_INSTALLER_SIZE_BYTES,
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to download 7-Zip extractor: {exc}") from exc


class GPUBackend:
    def __init__(self, lib_dir=None):
        self.runtime = HashcatRuntimeManager(lib_dir=lib_dir)

    @staticmethod
    def get_runtime_info():
        return HashcatRuntimeManager.get_runtime_info()

    def ensure_installed(self, progress_callback=None):
        return self.runtime.ensure_installed(progress_callback=progress_callback)

    def probe_devices(self):
        return self.runtime.probe_devices()

    def ensure_office_support(self, progress_callback=None):
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        if OFFICE2JOHN_PATH.exists():
            return OFFICE2JOHN_PATH
        if progress_callback:
            progress_callback("Downloading office2john extractor…", 0)
        try:
            _download_file(
                OFFICE2JOHN_URL,
                OFFICE2JOHN_PATH,
                progress_callback=progress_callback,
                label="Downloading office2john extractor...",
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to download office2john.py: {exc}") from exc
        return OFFICE2JOHN_PATH

    def ensure_pdf_support(self, progress_callback=None):
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        PYTHON_LIB_DIR.mkdir(parents=True, exist_ok=True)
        if PDF2JOHN_PATH.exists():
            self._ensure_python_package("pyhanko", "pyhanko", progress_callback)
            return PDF2JOHN_PATH
        if progress_callback:
            progress_callback("Downloading PDF extractor…", 0)
        try:
            _download_file(
                PDF2JOHN_URL,
                PDF2JOHN_PATH,
                progress_callback=progress_callback,
                label="Downloading PDF extractor...",
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to download pdf2john.py: {exc}") from exc
        self._ensure_python_package("pyhanko", "pyhanko", progress_callback)
        return PDF2JOHN_PATH

    def ensure_filetype_support(self, file_type, progress_callback=None):
        file_type = (file_type or "").lower()
        if file_type in ("excel", "word", "powerpoint", "access"):
            return self.ensure_office_support(progress_callback)
        if file_type == "pdf":
            return self.ensure_pdf_support(progress_callback)
        return self.ensure_archive_support(file_type, progress_callback)

    def ensure_archive_support(self, file_type, progress_callback=None):
        file_type = (file_type or "").lower()
        if file_type == "zip":
            self._ensure_john_tools(progress_callback)
            return ZIP2JOHN_EXE
        if file_type == "rar":
            self._ensure_john_tools(progress_callback)
            return RAR2JOHN_EXE
        if file_type == "7z":
            self._ensure_7z2hashcat_tool(progress_callback)
            return SEVENZIP2HASHCAT_EXE
        raise GPUBackendError(f"Unsupported archive type for GPU extractor: {file_type}")

    def extract_office_hash(self, file_path):
        extractor_path = self.ensure_office_support()
        try:
            result = _run_python_script_in_process(extractor_path, [file_path])
        except Exception as exc:
            raise GPUBackendError(f"Failed to extract Office hash: {exc}") from exc

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode != 0 or not stdout:
            raise GPUBackendError(
                "Office hash extraction failed.\n"
                f"{stderr or stdout or 'No output from office2john.py'}"
            )

        hash_line = stdout.splitlines()[-1].strip()
        if ":" in hash_line:
            hash_line = hash_line.split(":", 1)[1].strip()
        mode = self._detect_office_hash_mode(hash_line)
        if mode is None:
            raise GPUBackendError(
                f"Unsupported Office hash format returned by office2john.py: {hash_line[:80]}"
            )
        return {
            "hash": hash_line,
            "mode": mode,
            "stdout": stdout,
            "stderr": stderr,
        }

    def extract_archive_hash(self, file_path, file_type):
        file_type = (file_type or "").lower()
        self.ensure_archive_support(file_type)

        if file_type == "zip":
            cmd = [str(ZIP2JOHN_EXE), str(file_path)]
        elif file_type == "rar":
            cmd = [str(RAR2JOHN_EXE), str(file_path)]
        elif file_type == "7z":
            cmd = [str(SEVENZIP2HASHCAT_EXE), str(file_path)]
        else:
            raise GPUBackendError(f"Unsupported archive type for hash extraction: {file_type}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                **_hidden_subprocess_kwargs(),
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to extract {file_type.upper()} hash: {exc}") from exc

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode != 0 or not stdout:
            raise GPUBackendError(
                f"{file_type.upper()} hash extraction failed.\n"
                f"{stderr or stdout or 'No output from extractor'}"
            )

        hash_line = self._normalize_extracted_archive_hash(stdout, file_type)
        if not hash_line:
            raise GPUBackendError(
                f"Unsupported or unreadable {file_type.upper()} archive hash format."
            )

        return {
            "hash": hash_line,
            "mode": None,
            "stdout": stdout,
            "stderr": stderr,
        }

    def extract_pdf_hash(self, file_path):
        extractor_path = self.ensure_pdf_support()
        try:
            result = _run_python_script_in_process(extractor_path, [file_path])
        except Exception as exc:
            raise GPUBackendError(f"Failed to extract PDF hash: {exc}") from exc

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode != 0 or not stdout:
            raise GPUBackendError(
                "PDF hash extraction failed.\n"
                f"{stderr or stdout or 'No output from pdf2john.py'}"
            )

        hash_line = stdout.splitlines()[-1].strip()
        if ":" in hash_line:
            hash_line = hash_line.split(":", 1)[1].strip()
        modes = self._detect_hash_modes("pdf", hash_line)
        if not modes:
            raise GPUBackendError(
                f"Unsupported PDF hash format returned by pdf2john.py: {hash_line[:80]}"
            )
        return {
            "hash": hash_line,
            "modes": modes,
            "stdout": stdout,
            "stderr": stderr,
        }

    def build_hashcat_attack_plan(self, attack_mode, office_hash, wordlist_path=None,
                                  charset=None, min_len=None, max_len=None, mask=None,
                                  device_id=None, hash_modes=None):
        workdir = self.runtime.prepare_workdir()
        hash_file = self._write_temp_hash(office_hash)
        outfile = Path(tempfile.mkstemp(prefix="bf_hashcat_out_", suffix=".txt")[1])
        potfile = Path(tempfile.mkstemp(prefix="bf_hashcat_pot_", suffix=".pot")[1])
        base_common = [
            str(workdir / "hashcat.exe"),
            "--status",
            "--status-timer", "1",
            "--potfile-path", str(potfile),
            "--outfile", str(outfile),
            "--outfile-autohex-disable",
            "--outfile-format", "2",
        ]
        if device_id:
            base_common.extend(["-d", str(device_id)])

        modes = list(hash_modes or [])
        if not modes:
            identified_modes = self.identify_hash_modes(office_hash, workdir)
            modes = identified_modes
        if not modes:
            raise GPUBackendError("No hashcat mode was detected for this GPU target.")

        commands = []
        for mode in modes:
            common = list(base_common) + ["-m", str(mode)]
            if attack_mode == "dictionary":
                commands.append(common + ["-a", "0", str(hash_file), str(wordlist_path)])
            elif attack_mode == "mask":
                commands.append(common + ["-a", "3", str(hash_file), str(mask)])
            elif attack_mode == "bruteforce":
                charset_args, mask_template = self._build_charset_args(charset)
                for length in range(min_len, max_len + 1):
                    commands.append(common + charset_args + ["-a", "3", str(hash_file), mask_template * length])
            else:
                raise GPUBackendError(f"Unsupported GPU attack mode: {attack_mode}")

        return {
            "commands": commands,
            "hash_file": hash_file,
            "outfile": outfile,
            "potfile": potfile,
            "workdir": workdir,
        }

    def read_cracked_password(self, outfile):
        try:
            if not Path(outfile).exists():
                return None
            content = Path(outfile).read_text(encoding="utf-8", errors="replace").splitlines()
            for line in content:
                candidate = line.strip()
                if candidate:
                    return candidate
        except Exception:
            return None
        return None

    def supports_attack(self, file_type, mode):
        if file_type in ("excel", "word", "powerpoint", "access", "zip", "rar", "7z", "pdf"):
            return {"supported": True, "reason": ""}
        return {
            "supported": False,
            "reason": (
                f"GPU backend is installed, but direct {file_type.upper()} {mode} attacks "
                f"still use CPU-based file validators in this build."
            ),
        }

    def as_json(self):
        return json.dumps(self.get_runtime_info(), ensure_ascii=False, indent=2)

    @staticmethod
    def _detect_office_hash_mode(hash_line):
        if hash_line.startswith("$office$*2007*"):
            return 9400
        if hash_line.startswith("$office$*2010*"):
            return 9500
        if hash_line.startswith("$office$*2013*"):
            return 9600
        if hash_line.startswith("$oldoffice$0*") or hash_line.startswith("$oldoffice$1*"):
            return 9700
        if hash_line.startswith("$oldoffice$3*") or hash_line.startswith("$oldoffice$4*"):
            return 9800
        return None

    @classmethod
    def _detect_hash_modes(cls, file_type, hash_line):
        file_type = (file_type or "").lower()
        if file_type in ("excel", "word", "powerpoint", "access"):
            mode = cls._detect_office_hash_mode(hash_line)
            return [mode] if mode is not None else []

        if file_type == "7z":
            return [11600] if hash_line.startswith("$7z$") else []

        if file_type == "zip":
            if hash_line.startswith("$pkzip2$8*"):
                return [17230]
            if hash_line.startswith("$pkzip2$3*"):
                return [17220, 17225]
            if hash_line.startswith("$pkzip2$1*"):
                return [17210]
            if hash_line.startswith("$pkzip$"):
                return [13600]
            return []

        if file_type == "rar":
            lowered = hash_line.lower()
            if lowered.startswith("$rar5$"):
                return [13000]
            if lowered.startswith("$rar3$*0*"):
                return [12500]
            if lowered.startswith("$rar3$*1*"):
                return [23700, 23800]
            return []

        if file_type == "pdf":
            if hash_line.startswith("$pdf$1*2*"):
                return [10400]
            if hash_line.startswith("$pdf$2*3*"):
                return [10500]
            if hash_line.startswith("$pdf$1*3*"):
                return [10510]
            if hash_line.startswith("$pdf$5*5*"):
                return [10600]
            if hash_line.startswith("$pdf$5*6*"):
                return [10700]
            return []

        return []

    @staticmethod
    def _write_temp_hash(hash_line):
        fd, path = tempfile.mkstemp(prefix="bf_office_hash_", suffix=".txt")
        os.close(fd)
        Path(path).write_text(hash_line + "\n", encoding="utf-8")
        return Path(path)

    @staticmethod
    def _build_charset_args(charset):
        builtins = {
            "lowercase": ([], "?l"),
            "uppercase": ([], "?u"),
            "digits": ([], "?d"),
            "hex_lower": ([], "?h"),
            "hex_upper": ([], "?H"),
        }
        if charset in builtins:
            return builtins[charset]
        custom_map = {
            "alphanumeric": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            "all": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
        }
        if charset in custom_map:
            return (["-1", custom_map[charset]], "?1")
        if charset:
            return (["-1", charset], "?1")
        raise GPUBackendError("Cannot build GPU brute-force charset.")

    def _ensure_john_tools(self, progress_callback=None):
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        if ZIP2JOHN_EXE.exists() and RAR2JOHN_EXE.exists():
            return JOHN_ROOT

        archive_path = TOOLS_DIR / JOHN_ARCHIVE_NAME
        if progress_callback:
            progress_callback("Downloading ZIP/RAR GPU extractors…", 0)

        def _report(block_num, block_size, total_size):
            if not progress_callback:
                return
            total = total_size if total_size and total_size > 0 else JOHN_ARCHIVE_SIZE_BYTES
            downloaded = min(block_num * block_size, total)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            progress_callback("Downloading ZIP/RAR GPU extractors…", percent)

        try:
            _download_file(
                JOHN_ARCHIVE_URL,
                archive_path,
                progress_callback=progress_callback,
                label="Downloading ZIP/RAR GPU extractors...",
                fallback_total=JOHN_ARCHIVE_SIZE_BYTES,
            )
            self.runtime._ensure_7zip_installed(progress_callback)
            result = subprocess.run(
                [str(self.runtime.sevenzip_exe_path), "x", str(archive_path), f"-o{TOOLS_DIR}", "-y"],
                capture_output=True,
                text=True,
                timeout=600,
                **_hidden_subprocess_kwargs(),
            )
            if result.returncode != 0:
                output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
                raise GPUBackendError(output or "Failed to extract John tools.")
        except Exception as exc:
            if isinstance(exc, GPUBackendError):
                raise
            raise GPUBackendError(f"Failed to prepare ZIP/RAR GPU extractors: {exc}") from exc
        finally:
            try:
                archive_path.unlink(missing_ok=True)
            except Exception:
                pass

        if not ZIP2JOHN_EXE.exists() or not RAR2JOHN_EXE.exists():
            raise GPUBackendError("ZIP/RAR extractor tools were installed, but required executables were not found.")
        return JOHN_ROOT

    def _ensure_python_package(self, package_name, module_name, progress_callback=None):
        try:
            __import__(module_name)
            return
        except Exception:
            pass

        try:
            if PYTHON_LIB_DIR.exists():
                sys.path.insert(0, str(PYTHON_LIB_DIR))
                __import__(module_name)
                return
        except Exception:
            pass

        if progress_callback:
            progress_callback(f"Installing Python package {package_name}…", None)

        python_executable = _resolve_python_executable()
        if not python_executable:
            raise GPUBackendError(
                f"Python dependency {package_name} is missing, and no external Python interpreter "
                "was found to install it from the packaged application."
            )

        cmd = [
            python_executable, "-m", "pip", "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--target", str(PYTHON_LIB_DIR),
            package_name,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,
                **_hidden_subprocess_kwargs(),
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to install Python dependency {package_name}: {exc}") from exc

        if result.returncode != 0:
            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
            raise GPUBackendError(
                f"Failed to install Python dependency {package_name}.\n"
                f"{output or 'pip returned a non-zero exit code.'}"
            )

    def identify_hash_modes(self, hash_line, workdir=None):
        workdir = Path(workdir) if workdir else self.runtime.prepare_workdir()
        try:
            result = subprocess.run(
                [str(workdir / "hashcat.exe"), "--identify", hash_line],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=60,
                **_hidden_subprocess_kwargs(),
            )
        except Exception as exc:
            raise GPUBackendError(f"Failed to identify hash mode: {exc}") from exc

        output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        modes = []
        for line in output.splitlines():
            match = re.match(r"\s*([0-9]{4,6})\s+\|", line)
            if match:
                modes.append(int(match.group(1)))
        return modes

    def _ensure_7z2hashcat_tool(self, progress_callback=None):
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        if SEVENZIP2HASHCAT_EXE.exists():
            return SEVENZIP2HASHCAT_EXE

        archive_path = TOOLS_DIR / SEVENZIP2HASHCAT_ARCHIVE_NAME
        if progress_callback:
            progress_callback("Downloading 7Z GPU extractor…", 0)

        def _report(block_num, block_size, total_size):
            if not progress_callback:
                return
            total = total_size if total_size and total_size > 0 else 5_000_000
            downloaded = min(block_num * block_size, total)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            progress_callback("Downloading 7Z GPU extractor…", percent)

        try:
            _download_file(
                SEVENZIP2HASHCAT_URL,
                archive_path,
                progress_callback=progress_callback,
                label="Downloading 7Z GPU extractor...",
                fallback_total=5_000_000,
            )
            self.runtime._ensure_7zip_installed(progress_callback)
            result = subprocess.run(
                [str(self.runtime.sevenzip_exe_path), "x", str(archive_path), f"-o{TOOLS_DIR}", "-y"],
                capture_output=True,
                text=True,
                timeout=300,
                **_hidden_subprocess_kwargs(),
            )
            if result.returncode != 0:
                output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
                raise GPUBackendError(output or "Failed to extract 7Z extractor.")
        except Exception as exc:
            if isinstance(exc, GPUBackendError):
                raise
            raise GPUBackendError(f"Failed to prepare 7Z GPU extractor: {exc}") from exc
        finally:
            try:
                archive_path.unlink(missing_ok=True)
            except Exception:
                pass

        if not SEVENZIP2HASHCAT_EXE.exists():
            raise GPUBackendError("7Z extractor tool was installed, but the executable was not found.")
        return SEVENZIP2HASHCAT_EXE

    @staticmethod
    def _normalize_extracted_archive_hash(output, file_type):
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return None

        if file_type == "7z":
            for line in reversed(lines):
                if line.startswith("$7z$"):
                    return line
            return None

        if file_type == "zip":
            for line in reversed(lines):
                match = re.search(r"(\$(?:pkzip2?)\$.*?\$/(?:pkzip2?)\$)", line, re.IGNORECASE)
                if match:
                    return match.group(1)
            return None

        if file_type == "rar":
            for line in reversed(lines):
                for prefix in ("$rar5$", "$rar3$", "$RAR3$"):
                    idx = line.find(prefix)
                    if idx >= 0:
                        candidate = line[idx:]
                        if prefix in ("$rar3$", "$RAR3$") and ":" in candidate:
                            candidate = candidate.split(":", 1)[0]
                        return candidate
            return None

        return None

    @staticmethod
    def _parse_backend_devices(output):
        devices = []
        current = None
        for raw_line in output.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                continue
            m = re.match(r"\s*Backend Device ID\s*#0*([0-9]+)", line, re.IGNORECASE)
            if m:
                if current and current.get("type", "").upper() == "GPU":
                    devices.append(current)
                current = {"backend_id": m.group(1), "name": "", "vendor": "", "type": ""}
                continue
            if current is None:
                continue
            type_match = re.match(r"\s*Type\.*:\s*(.+)", line, re.IGNORECASE)
            if type_match:
                current["type"] = type_match.group(1).strip()
                continue
            vendor_match = re.match(r"\s*Vendor\.*:\s*(.+)", line, re.IGNORECASE)
            if vendor_match:
                current["vendor"] = vendor_match.group(1).strip()
                continue
            name_match = re.match(r"\s*Name\.*:\s*(.+)", line, re.IGNORECASE)
            if name_match:
                current["name"] = name_match.group(1).strip()
                continue
        if current and current.get("type", "").upper() == "GPU":
            devices.append(current)
        return devices
