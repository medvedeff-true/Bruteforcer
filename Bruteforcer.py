import sys
import os
import time
import string
import itertools
import csv
import json
from html import escape
from datetime import datetime
from pathlib import Path
import concurrent.futures
import threading
import multiprocessing
import configparser
import shutil
import subprocess
import re

SYSTEM_RESERVED_LOGICAL_CPUS = 2
POOL_MAX_TASKS_PER_CHILD = 200
DICTIONARY_CHUNK_SIZE = 2000
BRUTEFORCE_TASK_FACTOR = 8


def _get_safe_process_count():
    total = multiprocessing.cpu_count()
    if total <= 1:
        return 1
    reserved = 1 if total <= 2 else SYSTEM_RESERVED_LOGICAL_CPUS
    return max(1, total - reserved)


def _iter_wordlist_lines(path):
    for encoding, kwargs in (
        ("latin-1", {}),
        ("utf-8", {"errors": "replace"}),
    ):
        try:
            with open(path, "r", encoding=encoding, **kwargs) as f:
                for line in f:
                    password = line.strip()
                    if password:
                        yield password
            return
        except Exception:
            continue


def _count_wordlist_entries(path):
    count = 0
    for _ in _iter_wordlist_lines(path):
        count += 1
    return count


def _chunked_iterable(iterable, chunk_size):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _set_low_priority_for_current_process():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def _mp_pool_initializer():
    _set_low_priority_for_current_process()

def _mp_check_password(file_path, password, file_type):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if file_type == "zip" or ext == ".zip":
            return PasswordChecker.check_zip_password(file_path, password)
        elif file_type in ("excel", "word", "powerpoint", "access"):
            import msoffcrypto, io
            with open(file_path, 'rb') as f:
                of = msoffcrypto.OfficeFile(f)
                if not of.is_encrypted():
                    return False
                of.load_key(password=password)
                of.decrypt(io.BytesIO())
                return True
        elif file_type == "pdf":
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    return reader.decrypt(password) > 0
                return False
        elif file_type == "rar":
            import rarfile
            with rarfile.RarFile(file_path, 'r') as rf:
                names = rf.namelist()
                if not names:
                    return False
                rf.read(names[0], pwd=password)
                return True
        elif file_type == "7z":
            import py7zr
            with py7zr.SevenZipFile(file_path, mode='r', password=password) as archive:
                return len(archive.getnames()) > 0
    except Exception:
        return False
    return False


def _mp_bruteforce_chunk(file_path, file_type, chars, length, start_idx, end_idx):
    chars = list(chars)
    base = len(chars)
    count = 0

    def idx_to_combo(n):
        result = []
        for _ in range(length):
            result.append(chars[n % base])
            n //= base
        return ''.join(reversed(result))

    for idx in range(start_idx, end_idx):
        count += 1
        password = idx_to_combo(idx)
        if _mp_check_password(file_path, password, file_type):
            return (password, count)
    return (None, count)


def _mp_dictionary_chunk(file_path, file_type, passwords_chunk):
    count = 0
    for password in passwords_chunk:
        count += 1
        if _mp_check_password(file_path, password, file_type):
            return (password, count)
    return (None, count)


def _mp_mask_chunk(file_path, file_type, positions, start_idx, end_idx):
    count = 0
    choices = []
    radices = []
    for pos in positions:
        current = [pos] if isinstance(pos, str) else list(pos)
        choices.append(current)
        radices.append(len(current))

    for idx in range(start_idx, end_idx):
        count += 1
        value = idx
        chars = [""] * len(choices)
        for offset in range(len(choices) - 1, -1, -1):
            base = radices[offset]
            chars[offset] = choices[offset][value % base]
            value //= base
        password = ''.join(chars)
        if _mp_check_password(file_path, password, file_type):
            return (password, count)
    return (None, count)


def _pool_dispatch(args):
    fn, fn_args = args
    return fn(*fn_args)


def _read_wordlist(path):
    try:
        return list(_iter_wordlist_lines(path))
    except Exception:
        return None


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


# GUI
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QTableWidgetItem,
    QFrame, QLabel, QVBoxLayout, QProgressBar,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QTextDocument, QPdfWriter

# Design module
from Design import (
    build_ui, build_palette, MAIN_STYLESHEET,
    FILE_LABEL_SELECTED_STYLE, FILE_LABEL_EMPTY_STYLE,
    STATUS_READY_STYLE, STATUS_ACTIVE_STYLE,
    tr, set_language, TRANSLATIONS,
)
from gpu_backend import GPUBackend, GPUBackendError

try:
    import msoffcrypto
    OFFICE_SUPPORT = True
except ImportError:
    OFFICE_SUPPORT = False

try:
    import zipfile
    ZIP_SUPPORT = True
except ImportError:
    ZIP_SUPPORT = False

try:
    import pyzipper
    AES_ZIP_SUPPORT = True
except ImportError:
    AES_ZIP_SUPPORT = False

try:
    import rarfile
    RAR_SUPPORT = True
except ImportError:
    RAR_SUPPORT = False

try:
    import py7zr
    SEVENZIP_SUPPORT = True
except ImportError:
    SEVENZIP_SUPPORT = False

APP_DIR = Path.home() / "Bruteforcer"
USER_PASSWORDS_DIR = APP_DIR / "Passwords"
SETTINGS_FILE = APP_DIR / "settings.ini"
RESULTS_FILE = APP_DIR / "Results.txt"
INFO_FILE = APP_DIR / "Bruteforcer_links.txt"

INFO_FILE_TEXT = (
    "https://github.com/medvedeff-true/Bruteforcer\n"
    "Пароли взяты из - https://github.com/danielmiessler/SecLists\n"
)


def resource_path(*parts):
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(base_path).joinpath(*parts)


def ensure_app_storage():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    USER_PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
    if not INFO_FILE.exists():
        INFO_FILE.write_text(INFO_FILE_TEXT, encoding="utf-8")

    bundled_passwords_dir = resource_path("passwords")
    if bundled_passwords_dir.exists():
        for source_file in bundled_passwords_dir.glob("*.txt"):
            if source_file.name.lower() == "rockyou.txt" or _is_lfs_pointer(source_file):
                continue
            target_file = USER_PASSWORDS_DIR / source_file.name
            if not target_file.exists():
                shutil.copy2(source_file, target_file)

    stale_rockyou = USER_PASSWORDS_DIR / "rockyou.txt"
    if _is_lfs_pointer(stale_rockyou):
        stale_rockyou.unlink()


def _is_lfs_pointer(path):
    try:
        if not Path(path).exists() or Path(path).stat().st_size > 1024:
            return False
        with open(path, "rb") as f:
            head = f.read(256)
        return b"version https://git-lfs.github.com/spec/v1" in head
    except Exception:
        return False


DEFAULT_SETTINGS = {
    "general": {
        "language":      "en",
        "last_file":     "",
        "attack_method": "0",
    },
    "options": {
        "multicore":     "true",
        "compute_backend": "cpu",
        "gpu_device":    "",
        "save_results":  "true",
    },
}

def load_settings() -> configparser.ConfigParser:
    ensure_app_storage()
    cfg = configparser.ConfigParser()
    if os.path.exists(SETTINGS_FILE):
        try:
            cfg.read(SETTINGS_FILE, encoding="utf-8")
            for section, values in DEFAULT_SETTINGS.items():
                if not cfg.has_section(section):
                    cfg.add_section(section)
                    for k, v in values.items():
                        cfg.set(section, k, v)
        except Exception:
            cfg = _build_default_config()
    else:
        cfg = _build_default_config()
        _save_settings(cfg)
    return cfg

def _build_default_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    for section, values in DEFAULT_SETTINGS.items():
        cfg.add_section(section)
        for k, v in values.items():
            cfg.set(section, k, v)
    return cfg

def _save_settings(cfg: configparser.ConfigParser):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            cfg.write(f)
    except Exception:
        pass

def save_settings(cfg: configparser.ConfigParser):
    _save_settings(cfg)

class PasswordChecker:

    @staticmethod
    def check_password(file_path, password, file_type=None):
        if not os.path.exists(file_path):
            return False
        if file_type is None:
            file_type = PasswordChecker.detect_file_type(file_path)
        try:
            if file_type == "zip":
                return PasswordChecker.check_zip_password(file_path, password)
            elif file_type == "rar":
                return PasswordChecker.check_rar_password(file_path, password)
            elif file_type == "7z":
                return PasswordChecker.check_7z_password(file_path, password)
            elif file_type in ["excel", "word", "powerpoint", "access"]:
                return PasswordChecker.check_office_password(file_path, password, file_type)
            elif file_type == "pdf":
                return PasswordChecker.check_pdf_password(file_path, password)
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def detect_file_type(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.zip']:                               return 'zip'
        elif ext in ['.rar']:                             return 'rar'
        elif ext in ['.7z', '.7zip']:                     return '7z'
        elif ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']: return 'excel'
        elif ext in ['.docx', '.doc', '.docm']:           return 'word'
        elif ext in ['.pptx', '.ppt', '.pptm']:           return 'powerpoint'
        elif ext in ['.accdb', '.mdb']:                   return 'access'
        elif ext in ['.pdf']:                             return 'pdf'
        else:                                             return 'unknown'

    @staticmethod
    def check_zip_password(file_path, password):
        pwd_bytes = password.encode('utf-8') if isinstance(password, str) else password
        if AES_ZIP_SUPPORT:
            try:
                with pyzipper.AESZipFile(file_path, 'r') as zf:
                    names = zf.namelist()
                    if not names:
                        return False
                    zf.pwd = pwd_bytes
                    zf.read(names[0])
                    return True
            except Exception:
                pass
        if not ZIP_SUPPORT:
            return False
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                names = zf.namelist()
                if not names:
                    return False
                zf.read(names[0], pwd=pwd_bytes)
                return True
        except Exception:
            return False

    @staticmethod
    def check_rar_password(file_path, password):
        if not RAR_SUPPORT:
            return False
        try:
            with rarfile.RarFile(file_path, 'r') as rar_file:
                file_list = rar_file.namelist()
                if not file_list:
                    return False
                try:
                    rar_file.read(file_list[0], pwd=password)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    @staticmethod
    def check_7z_password(file_path, password):
        if not SEVENZIP_SUPPORT:
            return False
        try:
            with py7zr.SevenZipFile(file_path, mode='r', password=password) as archive:
                return len(archive.getnames()) > 0
        except Exception:
            return False

    @staticmethod
    def check_office_password(file_path, password, file_type):
        if not OFFICE_SUPPORT:
            return False
        try:
            with open(file_path, 'rb') as f:
                office_file = msoffcrypto.OfficeFile(f)
                if not office_file.is_encrypted():
                    return False if password else True
                import io
                office_file.load_key(password=password)
                office_file.decrypt(io.BytesIO())
                return True
        except Exception:
            return False

    @staticmethod
    def check_pdf_password(file_path, password):
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    return reader.decrypt(password) > 0
                else:
                    return False if password else True
        except Exception:
            return False

    @staticmethod
    def is_protected(file_path):
        try:
            file_type = PasswordChecker.detect_file_type(file_path)
            if file_type == "zip":
                try:
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        for fi in zf.infolist():
                            if fi.flag_bits & 0x1:
                                return True
                        return False
                except RuntimeError as e:
                    return "encrypted" in str(e).lower()
                except Exception:
                    return True
            elif file_type in ["excel", "word", "powerpoint", "access"]:
                try:
                    with open(file_path, 'rb') as f:
                        return msoffcrypto.OfficeFile(f).is_encrypted()
                except Exception:
                    return True
            elif file_type == "pdf":
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        return PyPDF2.PdfReader(f).is_encrypted
                except Exception:
                    return True
            elif file_type == "rar":
                try:
                    with rarfile.RarFile(file_path, 'r') as rf:
                        return rf.needs_password()
                except Exception:
                    return True
            elif file_type == "7z":
                try:
                    with py7zr.SevenZipFile(file_path, mode='r') as archive:
                        return archive.password is not None
                except Exception as e:
                    return "password" in str(e).lower()
            return False
        except Exception:
            return True

    @staticmethod
    def describe_protection(file_path, file_type=None):
        file_type = file_type or PasswordChecker.detect_file_type(file_path)
        try:
            if file_type == "zip":
                return PasswordChecker._describe_zip_protection(file_path)
            if file_type == "rar":
                return PasswordChecker._describe_rar_protection(file_path)
            if file_type == "7z":
                return PasswordChecker._describe_7z_protection(file_path)
            if file_type == "pdf":
                return PasswordChecker._describe_pdf_protection(file_path)
            if file_type in ("excel", "word", "powerpoint", "access"):
                return PasswordChecker._describe_office_protection(file_path, file_type)
        except Exception:
            pass
        return "Protected" if PasswordChecker.is_protected(file_path) else "Not protected"

    @staticmethod
    def _describe_zip_protection(file_path):
        if not ZIP_SUPPORT:
            return "ZIP encrypted"
        with zipfile.ZipFile(file_path, "r") as zf:
            encrypted_entries = [fi for fi in zf.infolist() if fi.flag_bits & 0x1]
            if not encrypted_entries:
                return "Not protected"
            aes_bits = None
            for info in encrypted_entries:
                aes_bits = PasswordChecker._zip_aes_bits(info.extra)
                if aes_bits:
                    break
            return f"ZIP AES-{aes_bits}" if aes_bits else "ZIP ZipCrypto"

    @staticmethod
    def _zip_aes_bits(extra):
        extra = extra or b""
        idx = 0
        while idx + 4 <= len(extra):
            header_id = int.from_bytes(extra[idx:idx + 2], "little")
            data_size = int.from_bytes(extra[idx + 2:idx + 4], "little")
            data = extra[idx + 4:idx + 4 + data_size]
            if header_id == 0x9901 and len(data) >= 7:
                strength = data[4]
                return {1: 128, 2: 192, 3: 256}.get(strength, 256)
            idx += 4 + data_size
        return None

    @staticmethod
    def _describe_rar_protection(file_path):
        with open(file_path, "rb") as f:
            header = f.read(8)
        if header.startswith(b"Rar!\x1a\x07\x01\x00"):
            return "RAR5"
        if header.startswith(b"Rar!\x1a\x07\x00"):
            return "RAR4"
        return "RAR encrypted"

    @staticmethod
    def _describe_7z_protection(file_path):
        return "7Z AES-256" if PasswordChecker.is_protected(file_path) else "Not protected"

    @staticmethod
    def _describe_pdf_protection(file_path):
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if not reader.is_encrypted:
                    return "Not protected"
                enc = reader.trailer.get("/Encrypt") or {}
                revision = enc.get("/R")
                bits = enc.get("/Length")
                parts = ["PDF encrypted"]
                if revision is not None:
                    parts.append(f"R={revision}")
                if bits is not None:
                    parts.append(f"{bits}-bit")
                return ", ".join(parts)
        except Exception:
            pass
        return "PDF encrypted"

    @staticmethod
    def _describe_office_protection(file_path, file_type):
        ext = Path(file_path).suffix.lower()
        try:
            import olefile
            if olefile.isOleFile(file_path):
                with olefile.OleFileIO(file_path) as ole:
                    if ole.exists("EncryptionInfo"):
                        stream = ole.openstream("EncryptionInfo")
                        header = stream.read(8)
                        if len(header) >= 4:
                            major = int.from_bytes(header[0:2], "little")
                            minor = int.from_bytes(header[2:4], "little")
                            if (major, minor) == (4, 4):
                                return "Office Agile Encryption"
                            if (major, minor) == (4, 2):
                                return "Office Standard Encryption"
                        return "Office encrypted"
        except Exception:
            pass

        if ext in (".doc", ".xls", ".ppt", ".mdb"):
            return "Legacy Office encryption"
        if ext in (".docx", ".docm", ".xlsx", ".xlsm", ".xlsb", ".pptx", ".pptm", ".accdb"):
            return "Office OOXML encryption"
        return f"{file_type.upper()} encrypted"

class DictionaryManager:
    @staticmethod
    def get_available_wordlists():
        ensure_app_storage()
        wordlists = {}
        passwords_dir = USER_PASSWORDS_DIR
        passwords_dir.mkdir(exist_ok=True)
        for file in passwords_dir.glob("*.txt"):
            if _is_lfs_pointer(file):
                continue
            wordlists[file.name] = str(file)
        return dict(sorted(wordlists.items(), key=lambda item: item[0].lower()))


class PasswordWorker(QThread):
    progress         = Signal(int)
    password_found   = Signal(str, str)
    status_update    = Signal(str, str)
    engine_changed   = Signal(str)
    current_password = Signal(str)
    stats_update     = Signal(dict)
    estimated_time   = Signal(str)
    speed_update     = Signal(float)
    attack_finished  = Signal(bool)

    def __init__(self):
        super().__init__()
        self.file_path           = ""
        self.file_type           = ""
        self.running             = False
        self.passwords_tried     = 0
        self.start_time          = None
        self.end_time            = None       # set when attack stops
        self.total_passwords     = 0
        self.current_mode        = ""
        self.password_discovered = None
        self.performant_mode     = False
        self.found_event         = threading.Event()
        self._counter_lock       = threading.Lock()
        self._last_speed_emit_ts = 0.0
        self._active_pool        = None
        self._gpu_process        = None
        self.compute_backend     = "cpu"
        self.gpu_device_id       = ""
        self._gpu_runtime_broken = False
        self._gpu_failure_reason = ""

    def set_parameters(self, file_path, file_type, mode, charset,
                       min_len, max_len, wordlist_path=None, mask=None,
                       custom_charset="", performant_mode=False,
                       compute_backend="cpu", gpu_device_id=""):
        self.file_path       = file_path
        self.file_type       = file_type
        self.mode            = mode
        self.charset         = charset
        self.min_len         = min_len
        self.max_len         = max_len
        self.wordlist_path   = wordlist_path
        self.mask            = mask
        self.custom_charset  = custom_charset
        self.current_mode    = mode
        self.performant_mode = performant_mode
        self.compute_backend = compute_backend
        self.gpu_device_id   = gpu_device_id

    def run(self):
        self.running = True
        self.passwords_tried = 0
        self.start_time = datetime.now()
        self.end_time = None
        self._last_speed_emit_ts = 0.0
        self.password_discovered = None
        self.found_event.clear()

        try:
            if not PasswordChecker.is_protected(self.file_path):
                self.status_update.emit("⚠️ File is not password-protected", "#ff9900")
                self.running = False
                self.end_time = datetime.now()
                self.attack_finished.emit(False)
                return

            self.status_update.emit(
                f"🚀 Starting attack on {self.file_type.upper()} file…", "#007acc")

            if self.compute_backend == "gpu" and self.file_type in ("excel", "word", "powerpoint", "access", "zip", "rar", "7z", "pdf"):
                self.run_gpu_attack()
            elif self.performant_mode:
                self.run_performant_attack()
            else:
                if self.mode == "dictionary":   self.run_dictionary_attack()
                elif self.mode == "bruteforce": self.run_bruteforce_attack()
                elif self.mode == "mask":       self.run_mask_attack()

            if self.password_discovered:
                self.status_update.emit("✅ Attack completed successfully!", "#00cc00")
                self.attack_finished.emit(True)
            else:
                if self.running:
                    self.status_update.emit(
                        "❌ Attack finished. Password not found.", "#ff3333")
                    self.attack_finished.emit(False)

        except Exception as e:
            self.status_update.emit(f"❌ Error: {str(e)}", "#ff3333")
            self.attack_finished.emit(False)
        finally:
            self.running = False
            if self.end_time is None:
                self.end_time = datetime.now()

    def get_elapsed_seconds(self):
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()

    def run_performant_attack(self):
        num_procs = _get_safe_process_count()
        if self.mode == "dictionary":   self.run_performant_dictionary(num_procs)
        elif self.mode == "bruteforce": self.run_performant_bruteforce(num_procs)
        elif self.mode == "mask":       self.run_performant_mask(num_procs)

    def run_performant_dictionary(self, num_procs):
        if not os.path.exists(self.wordlist_path):
            self.status_update.emit("❌ Wordlist file not found!", "#ff3333")
            return

        all_passwords = _read_wordlist(self.wordlist_path)
        if all_passwords is None:
            self.status_update.emit("❌ Cannot read wordlist!", "#ff3333")
            return

        total = len(all_passwords)
        self.total_passwords = total
        if total == 0:
            self.status_update.emit("❌ Wordlist is empty!", "#ff3333")
            return

        chunk_size = max(1, min(2000, total // (num_procs * 4)))
        chunks = [all_passwords[i:i + chunk_size] for i in range(0, total, chunk_size)]

        file_path = self.file_path
        file_type = self.file_type
        tasks     = [(file_path, file_type, chunk) for chunk in chunks]

        self._run_pool(_mp_dictionary_chunk, tasks, total)

    def run_performant_bruteforce(self, num_procs):
        chars = self.get_charset()
        if not chars:
            self.status_update.emit("❌ Character set is empty!", "#ff3333")
            return

        chars_list = list(chars)
        base       = len(chars_list)

        total = 0
        length_ranges = []
        for length in range(self.min_len, self.max_len + 1):
            cnt = base ** length
            length_ranges.append((length, cnt))
            total += cnt
        self.total_passwords = total
        if total == 0:
            self.status_update.emit("❌ No combinations to try!", "#ff3333")
            return

        file_path = self.file_path
        file_type = self.file_type

        target_chunk = max(1, total // (num_procs * 8))
        tasks = []
        for length, cnt in length_ranges:
            chunk = max(1, min(target_chunk, cnt // num_procs))
            for start in range(0, cnt, chunk):
                end = min(start + chunk, cnt)
                tasks.append((file_path, file_type, chars_list, length, start, end))

        self._run_pool(_mp_bruteforce_chunk, tasks, total)

    def run_performant_mask(self, num_procs):
        mask = self.mask
        if not mask:
            self.status_update.emit("❌ No mask specified!", "#ff3333")
            return

        chars_map = self._get_chars_map()
        positions = self._parse_mask(mask, chars_map)

        char_sets = []
        for p in positions:
            char_sets.append([p] if isinstance(p, str) else list(p))
        all_passwords = [''.join(c) for c in itertools.product(*char_sets)]

        total = len(all_passwords)
        self.total_passwords = total
        if total == 0:
            self.status_update.emit("❌ No combinations for this mask!", "#ff3333")
            return

        chunk_size = max(1, min(2000, total // (num_procs * 4)))
        chunks = [all_passwords[i:i + chunk_size] for i in range(0, total, chunk_size)]

        file_path = self.file_path
        file_type = self.file_type
        tasks     = [(file_path, file_type, chunk) for chunk in chunks]

        self._run_pool(_mp_dictionary_chunk, tasks, total)

    def _kill_pool(self):
        pool = self._active_pool
        if pool is None:
            return
        self._active_pool = None

        procs = []
        try:
            if hasattr(pool, '_pool'):
                procs = list(pool._pool)
        except Exception:
            pass

        try:
            pool.terminate()
        except Exception:
            pass

        for p in procs:
            try:
                p.kill()
            except Exception:
                pass

        for p in procs:
            try:
                p.join(timeout=0.5)
            except Exception:
                pass

        if sys.platform == 'win32':
            import ctypes
            k32 = ctypes.windll.kernel32
            PROCESS_TERMINATE = 1
            for p in procs:
                try:
                    if p.is_alive():
                        h = k32.OpenProcess(PROCESS_TERMINATE, False, p.pid)
                        if h:
                            k32.TerminateProcess(h, 1)
                            k32.CloseHandle(h)
                except Exception:
                    pass

    def _run_pool(self, worker_fn, tasks, total):
        import atexit

        num_procs = _get_safe_process_count()
        ctx  = multiprocessing.get_context('spawn')
        pool = ctx.Pool(
            processes=num_procs,
            initializer=_mp_pool_initializer,
            maxtasksperchild=POOL_MAX_TASKS_PER_CHILD,
        )
        self._active_pool = pool

        def _emergency_cleanup():
            p = self._active_pool
            if p is not None:
                try: p.terminate()
                except Exception: pass
        atexit.register(_emergency_cleanup)

        async_iter = pool.imap_unordered(
            _pool_dispatch, [(worker_fn, args) for args in tasks], chunksize=1)

        def _monitor():
            while self.running and not self.found_event.is_set():
                elapsed = (datetime.now() - self.start_time).total_seconds() \
                    if self.start_time else 0
                tried = self.passwords_tried
                if elapsed > 0 and tried > 0:
                    speed = tried / elapsed
                    self.speed_update.emit(speed)
                    if total > 0 and speed > 0:
                        remaining = (total - tried) / speed
                        self.estimated_time.emit(f"ETA: ~{self._fmt_time(remaining)}")
                    pct = int(min(tried / total * 100, 100)) if total > 0 else 0
                    self.progress.emit(pct)
                time.sleep(0.5)

        mon = threading.Thread(target=_monitor, daemon=True)
        mon.start()

        try:
            for result in async_iter:
                if not self.running or self.found_event.is_set():
                    break
                try:
                    found, count = result
                except Exception:
                    continue
                self.passwords_tried += count
                if found is not None and not self.password_discovered:
                    self.password_discovered = found
                    self.found_event.set()   # stop monitor thread first
                    self.password_found.emit(found, self.file_type)
                    break                    # stop consuming results
        finally:
            self.found_event.set()
            self._kill_pool()
            atexit.unregister(_emergency_cleanup)

    def run_dictionary_attack(self):
        if not os.path.exists(self.wordlist_path):
            self.status_update.emit("❌ Wordlist file not found!", "#ff3333")
            return

        # Use _read_wordlist for correct encoding (latin-1 fallback).
        passwords = _read_wordlist(self.wordlist_path)
        if passwords is None:
            self.status_update.emit("❌ Cannot read wordlist!", "#ff3333")
            return

        total_lines = len(passwords)
        if total_lines == 0:
            self.status_update.emit("❌ Wordlist is empty!", "#ff3333")
            return

        processed = 0
        start_time = self.start_time.timestamp() if self.start_time else time.time()
        last_speed_update = start_time

        for password in passwords:
            if not self.running:
                break
            if not password:
                continue
            self.current_password.emit(password)
            self.passwords_tried += 1
            processed += 1
            if total_lines > 0 and processed % 100 == 0:
                self.progress.emit(int((processed / total_lines) * 100))
                current_time = time.time()
                if current_time - last_speed_update >= 1.0:
                    elapsed = current_time - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    self.speed_update.emit(speed)
                    last_speed_update = current_time
                    if processed > 100 and speed > 0:
                        remaining = (total_lines - processed) / speed
                        if remaining > 0:
                            self.estimated_time.emit(
                                f"ETA: ~{self._fmt_time(remaining)}")
            if self.passwords_tried % 1000 == 0:
                self.update_stats()
            if PasswordChecker.check_password(self.file_path, password, self.file_type):
                self.password_discovered = password
                self.password_found.emit(password, self.file_type)
                return

    def run_bruteforce_attack(self):
        chars = self.get_charset()
        if not chars:
            self.status_update.emit("❌ Character set is empty!", "#ff3333")
            return
        self.total_passwords = sum(len(chars) ** i for i in range(self.min_len, self.max_len + 1))
        if self.total_passwords == 0:
            self.status_update.emit("❌ No combinations to try!", "#ff3333")
            return

        processed = 0
        start_time = time.time()
        last_speed_update = start_time

        for length in range(self.min_len, self.max_len + 1):
            if not self.running:
                break
            for combo in itertools.product(chars, repeat=length):
                if not self.running:
                    break
                password = ''.join(combo)
                self.current_password.emit(password)
                self.passwords_tried += 1
                processed += 1
                current_time = time.time()
                if current_time - last_speed_update >= 1.0:
                    elapsed = current_time - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    self.speed_update.emit(speed)
                    last_speed_update = current_time
                    if processed > 100 and speed > 0:
                        remaining = (self.total_passwords - processed) / speed
                        if remaining > 0:
                            self.estimated_time.emit(
                                f"ETA: ~{self._fmt_time(remaining)}")
                    self.update_stats()
                if PasswordChecker.check_password(self.file_path, password, self.file_type):
                    self.password_discovered = password
                    self.password_found.emit(password, self.file_type)
                    return

    def run_mask_attack(self):
        mask = self.mask
        if not mask:
            self.status_update.emit("❌ No mask specified!", "#ff3333")
            return
        chars_map = self._get_chars_map()
        positions = self._parse_mask(mask, chars_map)
        total_combinations = 1
        for pos in positions:
            total_combinations *= 1 if isinstance(pos, str) else len(pos)
        if total_combinations == 0:
            self.status_update.emit("❌ No combinations for this mask!", "#ff3333")
            return

        processed = 0
        start_time = self.start_time.timestamp() if self.start_time else time.time()
        last_speed_update = start_time

        def generate_combinations(pos_list, current=""):
            if not pos_list:
                yield current
            else:
                first, rest = pos_list[0], pos_list[1:]
                if isinstance(first, str):
                    yield from generate_combinations(rest, current + first)
                else:
                    for char in first:
                        yield from generate_combinations(rest, current + char)

        for password in generate_combinations(positions):
            if not self.running:
                break
            self.current_password.emit(password)
            self.passwords_tried += 1
            processed += 1
            current_time = time.time()
            if current_time - last_speed_update >= 1.0:
                elapsed = current_time - start_time
                speed = processed / elapsed if elapsed > 0 else 0
                self.speed_update.emit(speed)
                last_speed_update = current_time
                if total_combinations > 0:
                    self.progress.emit(int((processed / total_combinations) * 100))
                if processed > 100 and speed > 0:
                    remaining = (total_combinations - processed) / speed
                    if remaining > 0:
                        self.estimated_time.emit(
                            f"ETA: ~{self._fmt_time(remaining)}")
                self.update_stats()
            if PasswordChecker.check_password(self.file_path, password, self.file_type):
                self.password_discovered = password
                self.password_found.emit(password, self.file_type)
                return

    def process_password_chunk(self, passwords):
        EMIT_EVERY = 200
        for password in passwords:
            if not self.running or self.found_event.is_set():
                return None
            with self._counter_lock:
                self.passwords_tried += 1
                tried = self.passwords_tried
            if tried % EMIT_EVERY == 0:
                self.current_password.emit(password)
            now_ts = time.time()
            if now_ts - self._last_speed_emit_ts >= 1.0:
                self._last_speed_emit_ts = now_ts
                elapsed = (datetime.now() - self.start_time).total_seconds() \
                    if self.start_time else 0.0
                if elapsed > 0:
                    speed = tried / elapsed
                    self.speed_update.emit(speed)
                    if self.total_passwords > 0 and speed > 0 and tried > 100:
                        remaining = (self.total_passwords - tried) / speed
                        self.estimated_time.emit(f"ETA: ~{self._fmt_time(remaining)}")
            if tried % 1000 == 0:
                self.update_stats()
            if PasswordChecker.check_password(self.file_path, password, self.file_type):
                self.password_found.emit(password, self.file_type)
                return password
        return None

    def process_length_range(self, chars, length):
        EMIT_EVERY = 200
        for combo in itertools.product(chars, repeat=length):
            if not self.running or self.found_event.is_set():
                return None
            password = ''.join(combo)
            with self._counter_lock:
                self.passwords_tried += 1
                tried = self.passwords_tried
            if tried % EMIT_EVERY == 0:
                self.current_password.emit(password)
            now_ts = time.time()
            if now_ts - self._last_speed_emit_ts >= 1.0:
                self._last_speed_emit_ts = now_ts
                elapsed = (datetime.now() - self.start_time).total_seconds() \
                    if self.start_time else 0.0
                if elapsed > 0:
                    self.speed_update.emit(tried / elapsed)
            if tried % 1000 == 0:
                self.update_stats()
            if PasswordChecker.check_password(self.file_path, password, self.file_type):
                self.password_found.emit(password, self.file_type)
                return password
        return None

    def get_charset(self):
        mapping = {
            "lowercase":    string.ascii_lowercase,
            "uppercase":    string.ascii_uppercase,
            "digits":       string.digits,
            "alphanumeric": string.ascii_letters + string.digits,
            "all":          string.ascii_letters + string.digits + string.punctuation,
            "hex_lower":    string.digits + "abcdef",
            "hex_upper":    string.digits + "ABCDEF",
        }
        if self.charset in mapping:
            return mapping[self.charset]
        if self.charset == "custom":
            return self.custom_charset if self.custom_charset \
                else string.ascii_lowercase + string.digits
        return string.ascii_lowercase + string.digits

    def update_stats(self):
        if self.start_time:
            elapsed = self.get_elapsed_seconds()
            if elapsed > 0:
                speed = self.passwords_tried / elapsed
                self.stats_update.emit({
                    'passwords_tried': self.passwords_tried,
                    'speed':   f"{speed:.1f} pwd/sec",
                    'elapsed': f"{elapsed:.1f} sec",
                    'total':   self.total_passwords if self.current_mode == "bruteforce" else 0,
                })

    def stop(self):
        self.running = False
        self.found_event.set()
        if self.end_time is None:
            self.end_time = datetime.now()
        proc = self._gpu_process
        self._gpu_process = None
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
        self._kill_pool()

    # ── Private utilities ──────────────────────────────────────────────

    @staticmethod
    def _fmt_time(seconds):
        if seconds > 86400:  return f"{seconds / 86400:.1f} days"
        elif seconds > 3600: return f"{seconds / 3600:.1f} h"
        elif seconds > 60:   return f"{seconds / 60:.1f} min"
        else:                return f"{seconds:.0f} s"

    @staticmethod
    def _get_chars_map():
        return {
            '?l': string.ascii_lowercase,
            '?u': string.ascii_uppercase,
            '?d': string.digits,
            '?s': string.punctuation,
            '?a': string.ascii_letters + string.digits + string.punctuation,
            '?h': string.hexdigits.lower(),
            '?H': string.hexdigits.upper(),
        }

    @staticmethod
    def _parse_mask(mask, chars_map):
        positions = []
        i = 0
        while i < len(mask):
            token = mask[i:i + 2]
            if i + 1 < len(mask) and token in chars_map:
                positions.append(chars_map[token])
                i += 2
            else:
                positions.append(mask[i])
                i += 1
        return positions

    def generate_mask_passwords(self, mask):
        positions = self._parse_mask(mask, self._get_chars_map())

        def generate_recursive(pos_list, current=""):
            if not pos_list:
                yield current
            else:
                first, rest = pos_list[0], pos_list[1:]
                if isinstance(first, str):
                    yield from generate_recursive(rest, current + first)
                else:
                    for char in first:
                        yield from generate_recursive(rest, current + char)

        return generate_recursive(positions)

class ZetaUniversalBruteforcer(QMainWindow):

    def __init__(self):
        super().__init__()
        self.worker             = None
        self.gpu_backend        = GPUBackend()
        self.active_engine_key  = "engine_cpu"
        self.selected_file      = ""
        self.selected_file_type = ""
        self.default_wordlists  = {}
        self.current_stats      = {}
        self._attack_start_time = None   # for duration column
        self._selected_engine_key = "engine_cpu"
        self._last_log_message = None
        self._last_log_ts = 0.0

        # Load settings.ini first (before building UI)
        self.cfg = load_settings()
        lang = self.cfg.get("general", "language", fallback="en")
        set_language(lang)

        self.init_ui()
        self.setWindowTitle("Bruteforcer")
        self.setFixedSize(1200, 750)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)

        from PySide6.QtGui import QIcon
        for ico_path in [
            resource_path("icon.ico"),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon.ico"),
            os.path.join(os.getcwd(), "icon.ico"),
        ]:
            if os.path.exists(ico_path):
                wicon = QIcon(str(ico_path))
                if not wicon.isNull():
                    self.setWindowIcon(wicon)
                break
        self.load_wordlists()
        self.setStyleSheet(MAIN_STYLESHEET)
        self._init_loading_overlay()

        # Apply saved settings to UI
        self._apply_settings_to_ui()

    def init_ui(self):
        refs = build_ui(self)
        self.status_badge          = refs["status_badge"]
        self.engine_label          = refs["engine_label"]
        self.file_label            = refs["file_label"]
        self.file_info_label       = refs["file_info_label"]
        self.attack_combo          = refs["attack_combo"]
        self.dict_combo            = refs["dict_combo"]
        self.dict_widget           = refs["dict_widget"]
        self.bruteforce_widget     = refs["bruteforce_widget"]
        self.min_length            = refs["min_length"]
        self.max_length            = refs["max_length"]
        self.charset_combo         = refs["charset_combo"]
        self.custom_charset_edit   = refs["custom_charset_edit"]
        self.custom_charset_widget = refs["custom_charset_widget"]
        self.mask_edit             = refs["mask_edit"]
        self.mask_widget           = refs["mask_widget"]
        self.stats_labels          = refs["stats_labels"]
        self.stats_key_labels      = refs["stats_key_labels"]
        self.progress_bar          = refs["progress_bar"]
        self.start_btn             = refs["start_btn"]
        self.stop_btn              = refs["stop_btn"]
        self.tab_widget            = refs["tab_widget"]
        self.terminal              = refs["terminal"]
        self.results_table         = refs["results_table"]
        self.clear_log_btn         = refs["clear_log_btn"]
        self.export_results_btn    = refs["export_results_btn"]
        self.restore_results_btn   = refs["restore_results_btn"]
        self.performant_checkbox   = refs["performant_checkbox"]
        self.backend_combo         = refs["backend_combo"]
        self.gpu_device_combo      = refs["gpu_device_combo"]
        self.save_checkbox         = refs["save_checkbox"]
        self.ui_timer              = refs["ui_timer"]
        self.lang_toggle           = refs["lang_toggle"]
        self.browse_btn            = refs["browse_btn"]

        # For retranslation
        self.dict_lbl      = refs.get("dict_lbl")
        self.len_lbl       = refs.get("len_lbl")
        self.cs_lbl        = refs.get("cs_lbl")
        self.cc_lbl        = refs.get("cc_lbl")
        self.mask_lbl      = refs.get("mask_lbl")
        self.file_card     = refs.get("file_card")
        self.method_card   = refs.get("method_card")
        self.stats_card    = refs.get("stats_card")
        self._perf_section = refs.get("perf_section")
        self._save_section = refs.get("save_section")
        self._backend_label = refs.get("backend_label")
        self._gpu_device_label = refs.get("gpu_device_label")
        self._perf_hint_lbl = refs.get("perf_hint")
        self._backend_hint_lbl = refs.get("backend_hint")
        self._save_hint_lbl = refs.get("save_hint")

        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        self.gpu_device_combo.currentIndexChanged.connect(lambda _=None: self._persist_settings())
        self.clear_log_btn.clicked.connect(self.terminal.clear)
        self.export_results_btn.clicked.connect(self.export_results)
        self.restore_results_btn.clicked.connect(self.restore_results)
        self.save_checkbox.connect_toggle(self._update_restore_button_state)

        self.update_attack_method()

    def _init_loading_overlay(self):
        overlay = QFrame(self)
        overlay.setStyleSheet("background-color: rgba(10, 10, 12, 180);")
        overlay.hide()

        panel = QFrame(overlay)
        panel.setFixedWidth(420)
        panel.setStyleSheet("""
QFrame {
    background-color: #1f1f22;
    border: 1px solid #323238;
    border-radius: 16px;
}
QLabel {
    background: transparent;
}
""")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("Installing GPU backend")
        title.setStyleSheet("color: #f2f2f2; font-size: 12pt; font-weight: 700;")
        message = QLabel("Preparing…")
        message.setWordWrap(True)
        message.setStyleSheet("color: #c9c9cf; font-size: 9.5pt; line-height: 145%;")
        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(True)
        progress.setFormat("Working…")
        progress.setFixedHeight(20)

        layout.addWidget(title)
        layout.addWidget(message)
        layout.addWidget(progress)

        self._loading_overlay = overlay
        self._loading_panel = panel
        self._loading_title = title
        self._loading_message = message
        self._loading_progress = progress
        self._position_loading_overlay()

    def _position_loading_overlay(self):
        if not hasattr(self, "_loading_overlay"):
            return
        self._loading_overlay.setGeometry(self.rect())
        if hasattr(self, "_loading_panel"):
            panel = self._loading_panel
            x = max(0, (self.width() - panel.width()) // 2)
            y = max(0, (self.height() - panel.sizeHint().height()) // 2)
            panel.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_loading_overlay()

    def _show_loading_overlay(self, title, message):
        self._loading_title.setText(title)
        self._loading_message.setText(message)
        self._loading_progress.setRange(0, 0)
        self._loading_progress.setFormat("Working…")
        self._position_loading_overlay()
        self._loading_overlay.show()
        self._loading_overlay.raise_()
        QApplication.processEvents()

    def _update_loading_overlay(self, message, percent=None):
        self._loading_message.setText(message)
        if percent is None:
            self._loading_progress.setRange(0, 0)
            self._loading_progress.setFormat("Working…")
        else:
            bounded = max(0, min(100, int(percent)))
            self._loading_progress.setRange(0, 100)
            self._loading_progress.setValue(bounded)
            self._loading_progress.setFormat(f"{bounded}%")
        QApplication.processEvents()

    def _hide_loading_overlay(self):
        if hasattr(self, "_loading_overlay"):
            self._loading_overlay.hide()
            QApplication.processEvents()

    def _apply_settings_to_ui(self):
        lang = self.cfg.get("general", "language", fallback="en")
        is_ru = (lang == "ru")
        self.lang_toggle.set_russian(is_ru)

        # Attack method
        method_idx = self.cfg.getint("general", "attack_method", fallback=0)
        if 0 <= method_idx < self.attack_combo.count():
            self.attack_combo.setCurrentIndex(method_idx)

        # Checkboxes
        multicore = self.cfg.getboolean("options", "multicore", fallback=True)
        self.performant_checkbox.setChecked(multicore)
        backend = self.cfg.get("options", "compute_backend", fallback="cpu").lower()
        self._set_backend_index_silently(1 if backend == "gpu" else 0)
        self._set_selected_engine()
        self._update_gpu_device_visibility()
        if backend == "gpu":
            self._refresh_gpu_devices()
        else:
            self._refresh_gpu_devices({"devices": []})

        save_res = self.cfg.getboolean("options", "save_results", fallback=True)
        self.save_checkbox.setChecked(save_res)
        self._update_restore_button_state(save_res)

        # Last file path
        last_file = self.cfg.get("general", "last_file", fallback="")
        if last_file and os.path.exists(last_file):
            self._load_file(last_file)

    def _persist_settings(self):
        lang = "ru" if self.lang_toggle.is_russian else "en"
        self.cfg.set("general", "language", lang)
        self.cfg.set("general", "last_file", self.selected_file)
        self.cfg.set("general", "attack_method", str(self.attack_combo.currentIndex()))
        self.cfg.set("options", "multicore", str(self.performant_checkbox.isChecked()).lower())
        self.cfg.set("options", "compute_backend", "gpu" if self.backend_combo.currentIndex() == 1 else "cpu")
        self.cfg.set("options", "gpu_device", str(self.gpu_device_combo.currentData() or ""))
        self.cfg.set("options", "save_results", str(self.save_checkbox.isChecked()).lower())
        save_settings(self.cfg)

    def _set_backend_index_silently(self, index):
        self.backend_combo.blockSignals(True)
        self.backend_combo.setCurrentIndex(index)
        self.backend_combo.blockSignals(False)

    def _set_active_engine(self, engine_key):
        self.active_engine_key = engine_key
        if hasattr(self, "engine_label") and self.engine_label:
            self.engine_label.setText(f"{tr('engine_label')} {tr(engine_key)}")

    def _set_selected_engine(self):
        self._selected_engine_key = "engine_gpu" if self.backend_combo.currentIndex() == 1 else "engine_cpu"
        if not (self.worker and self.worker.running):
            self._set_active_engine(self._selected_engine_key)

    def _log_line(self, message, color="#ffffff", dedupe_window=0.0):
        now = time.time()
        if dedupe_window and self._last_log_message == message and (now - self._last_log_ts) < dedupe_window:
            return
        self._last_log_message = message
        self._last_log_ts = now
        self.terminal.add_line(message, color)

    def _log_section(self, title, color="#2e2e30"):
        self.terminal.add_separator(color=color)
        self.terminal.add_line(title, color)
        self.terminal.add_separator(color=color)

    def _update_restore_button_state(self, enabled=None):
        active = self.save_checkbox.isChecked() if enabled is None else bool(enabled)
        self.restore_results_btn.setEnabled(True)
        self.restore_results_btn.setToolTip(
            "" if active else "Requires the 'Save results to Results.txt' option."
        )

    def _update_gpu_device_visibility(self):
        visible = self.backend_combo.currentIndex() == 1
        if self._gpu_device_label:
            self._gpu_device_label.setVisible(visible)
        self.gpu_device_combo.setVisible(visible)

    def _refresh_gpu_devices(self, probe=None):
        if probe is None:
            try:
                probe = self.gpu_backend.probe_devices()
            except Exception:
                probe = {"devices": []}

        selected = self.cfg.get("options", "gpu_device", fallback="")
        self.gpu_device_combo.blockSignals(True)
        self.gpu_device_combo.clear()
        devices = probe.get("devices", []) if probe else []
        if not devices:
            self.gpu_device_combo.addItem(tr("gpu_device_placeholder"), "")
            self.gpu_device_combo.setEnabled(False)
        else:
            self.gpu_device_combo.setEnabled(True)
            for device in devices:
                label = device.get("name") or f"GPU #{device.get('backend_id', '')}"
                vendor = device.get("vendor")
                if vendor:
                    label = f"{label} [{vendor}]"
                self.gpu_device_combo.addItem(label, device.get("backend_id", ""))
            if selected:
                for i in range(self.gpu_device_combo.count()):
                    if self.gpu_device_combo.itemData(i) == selected:
                        self.gpu_device_combo.setCurrentIndex(i)
                        break
        self.gpu_device_combo.blockSignals(False)

    @staticmethod
    def _format_size_mb(size_bytes):
        return f"{(size_bytes / (1024 * 1024)):.1f} MB"

    def _on_backend_changed(self, index):
        if index != 1:
            self._set_selected_engine()
            self._update_gpu_device_visibility()
            self._persist_settings()
            return
        if self._ensure_gpu_runtime_installed():
            self._set_selected_engine()
            self._update_gpu_device_visibility()
            self._persist_settings()
        else:
            self._update_gpu_device_visibility()
            self._persist_settings()

    def _ensure_gpu_runtime_installed(self):
        info = self.gpu_backend.get_runtime_info()
        install_dir = info["install_dir"]
        download_bytes = info["download_bytes"]
        if not self.gpu_backend.runtime.sevenzip_exe_path.exists():
            download_bytes += 1_655_627
        download_size = self._format_size_mb(download_bytes)
        extracted_size = self._format_size_mb(info["installed_bytes"])

        if not self.gpu_backend.runtime.is_installed():
            answer = QMessageBox.question(
                self,
                "Install GPU backend",
                (
                    "Для режима GPU будет скачан внешний backend в папку:\n"
                    f"{install_dir}\n\n"
                    f"Размер загрузки: ~{download_size}\n"
                    f"После распаковки: ~{extracted_size}\n\n"
                    "Продолжить установку?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False

            self._show_loading_overlay(
                "Installing GPU backend",
                "Downloading required components for GPU mode…",
            )
            try:
                self.gpu_backend.ensure_installed(
                    progress_callback=self._update_loading_overlay
                )
            except GPUBackendError as exc:
                QMessageBox.critical(self, "GPU backend", str(exc))
                return False
            finally:
                self._hide_loading_overlay()

        self._show_loading_overlay(
            "Checking GPU backend",
            "Detecting compatible GPU devices…",
        )
        try:
            probe = self.gpu_backend.probe_devices()
        except GPUBackendError as exc:
            QMessageBox.warning(self, "GPU backend", str(exc))
            self.terminal.add_line(f"GPU backend probe failed: {exc}", "#8a7040")
            return False
        finally:
            self._hide_loading_overlay()

        if not probe["has_gpu"]:
            QMessageBox.warning(
                self,
                "GPU backend",
                (
                    "Внешний GPU backend установлен, но совместимая видеокарта не обнаружена.\n\n"
                    "Приложение вернётся в CPU-режим."
                ),
            )
            self.terminal.add_line("No compatible GPU devices were detected by the GPU backend.", "#8a7040")
            return False

        self._refresh_gpu_devices(probe)
        self.terminal.add_line("GPU backend is installed and detected a compatible device.", "#5a8a6a")
        return True

    def load_wordlists(self):
        self.default_wordlists = DictionaryManager.get_available_wordlists()
        self.update_dict_combo()

    def _on_language_change(self, is_russian: bool):
        lang = "ru" if is_russian else "en"
        set_language(lang)
        self._retranslate_ui()
        self._persist_settings()

    def _retranslate_ui(self):
        if self.worker and self.worker.running:
            self.status_badge.setText(tr("status_running"))
        else:
            self.status_badge.setText(tr("status_ready"))
        self._set_active_engine(self.active_engine_key)

        # File card title
        for card_ref, key in [
            ("file_card", "card_target_file"),
            ("method_card", "card_attack_method"),
            ("stats_card", "card_statistics"),
        ]:
            widget = getattr(self, card_ref, None)
            if widget:
                widget.setTitle(tr(key))

        if not self.selected_file:
            self.file_label.setText(tr("no_file"))

        # Browse button
        self.browse_btn.setText(tr("browse"))

        # Attack combo
        idx = self.attack_combo.currentIndex()
        self.attack_combo.blockSignals(True)
        self.attack_combo.clear()
        self.attack_combo.addItems([
            tr("method_dictionary"), tr("method_bruteforce"), tr("method_mask")
        ])
        self.attack_combo.setCurrentIndex(idx)
        self.attack_combo.blockSignals(False)

        # Charset combo
        cs_idx = self.charset_combo.currentIndex()
        self.charset_combo.blockSignals(True)
        self.charset_combo.clear()
        self.charset_combo.addItems([
            tr("charset_lower"), tr("charset_upper"), tr("charset_digits"),
            tr("charset_alnum"), tr("charset_all"), tr("charset_hex_l"),
            tr("charset_hex_u"), tr("charset_custom"),
        ])
        self.charset_combo.setCurrentIndex(cs_idx)
        self.charset_combo.blockSignals(False)

        # Dict combo — preserve selection
        self.update_dict_combo()

        # Sub-widget labels
        for w, key in [
            (self.dict_lbl,  "lbl_wordlist"),
            (self.len_lbl,   "lbl_length"),
            (self.cs_lbl,    "lbl_charset"),
            (self.cc_lbl,    "lbl_chars"),
            (self.mask_lbl,  "lbl_mask"),
        ]:
            if w:
                w.setText(tr(key))

        self.mask_edit.setPlaceholderText(tr("mask_placeholder"))
        self.custom_charset_edit.setPlaceholderText(tr("custom_placeholder"))

        # Stats key labels
        stat_map = {
            "stat_attempts": "passwords_tried",
            "stat_speed":    "speed",
            "stat_elapsed":  "elapsed",
            "stat_current":  "current_password",
            "stat_eta":      "estimated_time",
        }
        for name_key, _ in stat_map.items():
            lbl = self.stats_key_labels.get(name_key)
            if lbl:
                lbl.setText(tr(name_key))

        # Buttons
        self.start_btn.setText(tr("btn_start"))
        self.stop_btn.setText(tr("btn_stop"))

        # Tabs
        self.tab_widget.setTabText(0, tr("tab_log"))
        self.tab_widget.setTabText(1, tr("tab_results"))
        self.tab_widget.setTabText(2, tr("tab_settings"))

        # Results table headers
        self.results_table.setHorizontalHeaderLabels([
            tr("col_time"), tr("col_file"), tr("col_type"), tr("col_protection"),
            tr("col_password"), tr("col_duration"), tr("col_status"),
        ])

        # Settings checkboxes
        self.performant_checkbox.setText(tr("perf_checkbox"))
        self.save_checkbox.setText(tr("save_checkbox"))
        self.clear_log_btn.setText(tr("btn_clear_log"))
        self.export_results_btn.setText(tr("btn_export"))
        self.restore_results_btn.setText(tr("btn_restore"))
        if self._backend_label:
            self._backend_label.setText(tr("backend_label"))
        if self._gpu_device_label:
            self._gpu_device_label.setText(tr("gpu_device_label"))

        backend_idx = self.backend_combo.currentIndex()
        self.backend_combo.blockSignals(True)
        self.backend_combo.clear()
        self.backend_combo.addItems([tr("backend_cpu"), tr("backend_gpu")])
        self.backend_combo.setCurrentIndex(backend_idx if backend_idx in (0, 1) else 0)
        self.backend_combo.blockSignals(False)
        self._refresh_gpu_devices()
        self._update_gpu_device_visibility()

        # Settings hints
        perf_hint = getattr(self, "_perf_hint_lbl", None)
        backend_hint = getattr(self, "_backend_hint_lbl", None)
        save_hint = getattr(self, "_save_hint_lbl", None)
        if perf_hint:
            perf_hint.setText(tr("perf_hint"))
        if backend_hint:
            backend_hint.setText(tr("backend_hint"))
        if save_hint:
            save_hint.setText(tr("save_hint"))

        # Section titles
        perf_section = getattr(self, "_perf_section", None)
        save_section = getattr(self, "_save_section", None)
        if perf_section:
            perf_section.setTitle(tr("card_performance"))
        if save_section:
            save_section.setTitle(tr("card_save"))

    def update_dict_combo(self):
        current_text = self.dict_combo.currentText()
        self.dict_combo.clear()
        if self.default_wordlists:
            self.dict_combo.addItem(tr("select_wordlist"))
            for name in sorted(self.default_wordlists.keys()):
                self.dict_combo.addItem(name)
            # Try to restore previous selection
            for i in range(self.dict_combo.count()):
                if current_text and current_text in self.dict_combo.itemText(i):
                    self.dict_combo.setCurrentIndex(i)
                    break
        else:
            self.dict_combo.addItem(tr("no_wordlists"))

    def update_attack_method(self):
        m = self.attack_combo.currentIndex()
        self.dict_widget.setVisible(m == 0)
        self.bruteforce_widget.setVisible(m == 1)
        self.mask_widget.setVisible(m == 2)

    def update_charset_widget(self):
        self.custom_charset_widget.setVisible(
            self.charset_combo.currentIndex() == 7)

    def _set_status(self, text_key, active=False):
        self.status_badge.setText(text_key)   # caller passes already-translated text
        self.status_badge.setStyleSheet(
            STATUS_ACTIVE_STYLE if active else STATUS_READY_STYLE)

    def select_file(self):
        file_filter = (
            "Supported files (*.zip *.rar *.7z *.xlsx *.xls *.xlsm "
            "*.docx *.doc *.pptx *.ppt *.pdf);;"
            "Archives (*.zip *.rar *.7z);;"
            "Excel (*.xlsx *.xls *.xlsm);;"
            "Word (*.docx *.doc);;"
            "PowerPoint (*.pptx *.ppt);;"
            "PDF (*.pdf);;"
            "All files (*.*)"
        )
        start_dir = os.path.dirname(self.selected_file) if self.selected_file else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select protected file", start_dir, file_filter)
        if file_path:
            self._load_file(file_path)
            self._persist_settings()

    def _load_file(self, file_path):
        self.selected_file      = file_path
        self.selected_file_type = PasswordChecker.detect_file_type(file_path)
        short = os.path.basename(file_path)
        if len(short) > 34:
            short = short[:31] + "…"
        self.file_label.setText(short)
        self.file_label.setStyleSheet(FILE_LABEL_SELECTED_STYLE)
        self.browse_btn.set_file_selected(True)
        self.analyze_file(file_path)
        self.start_btn.setEnabled(True)

    def analyze_file(self, file_path):
        try:
            size_kb   = os.path.getsize(file_path) / 1024
            ftype     = self.selected_file_type.upper()
            protected = PasswordChecker.is_protected(file_path)
            prot_str  = "Protected" if protected else "Not protected"
            self.file_info_label.setText(
                f"Type: {ftype}  |  {size_kb:.0f} KB  |  {prot_str}")
            color = "#5a8a6a" if protected else "#8a7040"
            self.terminal.add_line(
                f"File: {os.path.basename(file_path)}  [{ftype}  {size_kb:.0f} KB]")
            self.terminal.add_line(f"Protection: {prot_str}", color)
            if not protected:
                self.terminal.add_line(
                    "Warning: file has no password protection.", "#8a6030")
        except Exception as e:
            self.terminal.add_line(f"Error reading file: {str(e)}", "#8a4040")

    def browse_custom_dict(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Select wordlist", "",
            "Text files (*.txt);;All files (*.*)")
        if fp:
            name = os.path.basename(fp)
            self.dict_combo.addItem(name)
            self.dict_combo.setCurrentIndex(self.dict_combo.count() - 1)
            self.default_wordlists[name] = fp

    def start_attack(self):
        if not self.selected_file:
            self.terminal.add_line(tr("log_select_file"), "#8a4040")
            return

        if not PasswordChecker.is_protected(self.selected_file):
            reply = QMessageBox.question(
                self, tr("confirm_title"), tr("confirm_msg"),
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        method    = self.attack_combo.currentIndex()
        self.worker = PasswordWorker()
        mode      = ["dictionary", "bruteforce", "mask"][method]
        file_type = self.selected_file_type
        compute_backend = "gpu" if self.backend_combo.currentIndex() == 1 else "cpu"
        gpu_device_id = str(self.gpu_device_combo.currentData() or "")
        engine_key = "engine_gpu" if compute_backend == "gpu" else "engine_cpu"

        if compute_backend == "gpu":
            if not self._ensure_gpu_runtime_installed():
                compute_backend = "cpu"
                engine_key = "engine_gpu_fallback"
            else:
                support = self.gpu_backend.supports_attack(file_type, mode)
                if not support["supported"]:
                    QMessageBox.information(
                        self,
                        "GPU backend",
                        support["reason"] + "\n\nТекущая атака будет выполнена на CPU.",
                    )
                    self.terminal.add_line(support["reason"], "#8a7040")
                    compute_backend = "cpu"
                    engine_key = "engine_gpu_fallback"
                elif file_type in ("excel", "word", "powerpoint", "access"):
                    try:
                        self._show_loading_overlay(
                            "Preparing Office GPU mode",
                            "Downloading Office hash extractor…",
                        )
                        self.gpu_backend.ensure_office_support(
                            progress_callback=self._update_loading_overlay
                        )
                    except GPUBackendError as exc:
                        QMessageBox.warning(self, "GPU backend", str(exc))
                        self.terminal.add_line(f"GPU Office support install failed: {exc}", "#8a7040")
                        compute_backend = "cpu"
                        engine_key = "engine_gpu_fallback"
                    finally:
                        self._hide_loading_overlay()
                elif file_type in ("zip", "rar", "7z", "pdf"):
                    try:
                        self._show_loading_overlay(
                            "Preparing GPU mode",
                            "Downloading GPU extractors…",
                        )
                        self.gpu_backend.ensure_filetype_support(
                            file_type,
                            progress_callback=self._update_loading_overlay
                        )
                    except GPUBackendError as exc:
                        QMessageBox.warning(self, "GPU backend", str(exc))
                        self.terminal.add_line(f"GPU extractor install failed: {exc}", "#8a7040")
                        compute_backend = "cpu"
                        engine_key = "engine_gpu_fallback"
                    finally:
                        self._hide_loading_overlay()

        if method == 0:
            if self.dict_combo.currentIndex() <= 0:
                self.terminal.add_line(tr("log_select_wordlist"), "#8a4040")
                return
            raw = self.dict_combo.currentText()
            raw = raw.replace(tr("default_label"), "").strip()
            wordlist_path = None
            for name, path in self.default_wordlists.items():
                if name == raw or raw in name:
                    wordlist_path = path
                    break
            if not wordlist_path or not os.path.exists(wordlist_path):
                pp = USER_PASSWORDS_DIR / raw
                if pp.exists():
                    wordlist_path = str(pp)
                else:
                    self.terminal.add_line(tr("log_wordlist_not_found") + raw, "#8a4040")
                    return
            charset = "dictionary"
            mask = None
            custom_charset = ""

        elif method == 1:
            wordlist_path = None
            mask = None
            cm = {0: "lowercase", 1: "uppercase", 2: "digits", 3: "alphanumeric",
                  4: "all", 5: "hex_lower", 6: "hex_upper", 7: "custom"}
            charset = cm[self.charset_combo.currentIndex()]
            custom_charset = self.custom_charset_edit.text() if charset == "custom" else ""

        else:
            wordlist_path = None
            charset = "mask"
            mask = self.mask_edit.text()
            custom_charset = ""
            if not mask:
                self.terminal.add_line(tr("log_enter_mask"), "#8a4040")
                return

        self.worker.set_parameters(
            self.selected_file, file_type, mode, charset,
            self.min_length.value(), self.max_length.value(),
            wordlist_path, mask, custom_charset,
            self.performant_checkbox.isChecked(),
            compute_backend, gpu_device_id,
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.password_found.connect(self.on_password_found)
        self.worker.status_update.connect(self.on_status_update)
        self.worker.current_password.connect(self.on_current_password)
        self.worker.stats_update.connect(self.on_stats_update)
        self.worker.estimated_time.connect(self.on_estimated_time)
        self.worker.speed_update.connect(self.on_speed_update)
        self.worker.attack_finished.connect(self.on_attack_finished)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self._set_active_engine(engine_key)
        self._set_status(tr("status_running"), active=True)
        self._attack_start_time = datetime.now()

        sep = "─" * 52
        self.terminal.add_line(sep, "#2e2e30")
        self.terminal.add_line(
            f"{tr('log_attack_started')}  [{file_type.upper()}]  {self.attack_combo.currentText()}",
            "#7090b0")
        self.terminal.add_line(
            f"{tr('log_file')}{os.path.basename(self.selected_file)}", "#6080a0")
        if self.performant_checkbox.isChecked():
            self.terminal.add_line(tr("log_mode_multicore"), "#6080a0")
        self.terminal.add_line(
            f"{tr('backend_label')} {self.backend_combo.currentText()}", "#6080a0")
        self.terminal.add_line(sep, "#2e2e30")

        self._persist_settings()

        self.worker.start()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        self._persist_settings()
        event.accept()

    def stop_attack(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(3000)
            self.terminal.add_line(tr("log_stopped"), "#8a7040")
            self.on_attack_finished(False)

    def on_password_found(self, password, file_type):
        sep = "─" * 52
        self.terminal.add_line(sep, "#3a5a3a")
        self.terminal.add_line(tr("log_password_found"), "#5ab870")
        self.terminal.add_line(f"  {password}", "#78d090")
        self.terminal.add_line(sep, "#3a5a3a")
        self.add_to_results(password, file_type, True)

    def on_attack_finished(self, success):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_active_engine("engine_cpu")
        self._set_status(tr("status_ready"))
        if not success:
            if self.worker and not self.worker.password_discovered:
                self.terminal.add_line(tr("log_not_found"), "#6a4040")

    def on_status_update(self, message, color):
        self.terminal.add_line(message, color)

    def on_current_password(self, password):
        dp = password[:32] + "…" if len(password) > 32 else password
        self.stats_labels["current_password"].setText(dp)

    def on_stats_update(self, stats):
        self.current_stats = stats

    def on_estimated_time(self, time_str):
        self.stats_labels["estimated_time"].setText(time_str)

    def on_speed_update(self, speed):
        self.stats_labels["speed"].setText(f"{speed:.0f} pwd/s")

    def add_to_results(self, password, file_type, success=True):
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        ts = datetime.now().strftime("%H:%M:%S")
        fn = os.path.basename(self.selected_file)

        # Calculate duration
        if self._attack_start_time:
            dur_secs = (datetime.now() - self._attack_start_time).total_seconds()
            dur_str  = PasswordWorker._fmt_time(dur_secs)
        else:
            dur_str = "—"

        items = [
            QTableWidgetItem(ts),
            QTableWidgetItem(fn),
            QTableWidgetItem(file_type.upper()),
            QTableWidgetItem(password),
            QTableWidgetItem(dur_str),
            QTableWidgetItem(tr("status_found") if success else tr("status_not_found")),
        ]
        clr = QColor("#5ab870") if success else QColor("#a05050")
        items[5].setForeground(clr)
        if success:
            items[3].setForeground(QColor("#78c090"))
            items[4].setForeground(QColor("#a0c8a0"))

        for col, item in enumerate(items):
            self.results_table.setItem(row, col, item)
        self.results_table.resizeColumnsToContents()

        # Save to Results.txt if enabled
        if self.save_checkbox.isChecked() and success:
            self._write_result_to_file(ts, fn, file_type, password, dur_str)

    def _write_result_to_file(self, ts, filename, file_type, password, duration):
        try:
            line = (f"[{ts}] File: {filename} | Type: {file_type.upper()} | "
                    f"Password: {password} | Duration: {duration}\n")
            with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            self.terminal.add_line(f"⚠️ Could not write Results.txt: {e}", "#8a7040")

    def update_ui(self):
        """Update statistics panel. Elapsed freezes when attack is not running."""
        if self.worker and self.worker.running and self.worker.start_time:
            tried   = int(self.worker.passwords_tried)
            elapsed = self.worker.get_elapsed_seconds()
            speed   = tried / elapsed if elapsed > 0 else 0.0
            self.stats_labels["passwords_tried"].setText(f"{tried:,}")
            self.stats_labels["elapsed"].setText(f"{elapsed:.1f} s")
            self.stats_labels["speed"].setText(f"{speed:.0f} pwd/s")
            total = int(getattr(self.worker, "total_passwords", 0) or 0)
            if total > 0 and speed > 0 and tried <= total:
                rem = (total - tried) / speed
                self.stats_labels["estimated_time"].setText(
                    f"~{PasswordWorker._fmt_time(rem)}")
            return

        if self.worker and self.worker.start_time and self.worker.end_time:
            tried   = int(getattr(self.worker, "passwords_tried", 0))
            elapsed = self.worker.get_elapsed_seconds()   # frozen at end_time
            self.stats_labels["passwords_tried"].setText(f"{tried:,}")
            self.stats_labels["elapsed"].setText(f"{elapsed:.1f} s")
            if elapsed > 0 and tried > 0:
                approx = tried / elapsed
                if self.stats_labels["speed"].text().startswith("0"):
                    self.stats_labels["speed"].setText(f"{approx:.0f} pwd/s")
            return

        if hasattr(self, "current_stats"):
            st = self.current_stats
            if "passwords_tried" in st:
                self.stats_labels["passwords_tried"].setText(
                    f"{st['passwords_tried']:,}")
            if "elapsed" in st:
                self.stats_labels["elapsed"].setText(st["elapsed"])


def _pw_run_performant_dictionary(self, num_procs):
    if not os.path.exists(self.wordlist_path):
        self.status_update.emit("вќЊ Wordlist file not found!", "#ff3333")
        return

    total = _count_wordlist_entries(self.wordlist_path)
    self.total_passwords = total
    if total == 0:
        self.status_update.emit("вќЊ Wordlist is empty!", "#ff3333")
        return

    chunk_size = max(1, min(DICTIONARY_CHUNK_SIZE, total // max(1, num_procs * 4)))
    chunks = _chunked_iterable(_iter_wordlist_lines(self.wordlist_path), chunk_size)
    tasks = ((self.file_path, self.file_type, chunk) for chunk in chunks)
    self._run_pool(_mp_dictionary_chunk, tasks, total)


def _pw_run_dictionary_attack(self):
    if not os.path.exists(self.wordlist_path):
        self.status_update.emit("вќЊ Wordlist file not found!", "#ff3333")
        return

    total_lines = _count_wordlist_entries(self.wordlist_path)
    if total_lines == 0:
        self.status_update.emit("вќЊ Wordlist is empty!", "#ff3333")
        return

    self.total_passwords = total_lines
    processed = 0
    start_time = self.start_time.timestamp() if self.start_time else time.time()
    last_speed_update = start_time

    for password in _iter_wordlist_lines(self.wordlist_path):
        if not self.running:
            break
        self.current_password.emit(password)
        self.passwords_tried += 1
        processed += 1
        if total_lines > 0 and processed % 100 == 0:
            self.progress.emit(int((processed / total_lines) * 100))
            current_time = time.time()
            if current_time - last_speed_update >= 1.0:
                elapsed = current_time - start_time
                speed = processed / elapsed if elapsed > 0 else 0
                self.speed_update.emit(speed)
                last_speed_update = current_time
                if processed > 100 and speed > 0:
                    remaining = (total_lines - processed) / speed
                    if remaining > 0:
                        self.estimated_time.emit(
                            f"ETA: ~{self._fmt_time(remaining)}")
        if self.passwords_tried % 1000 == 0:
            self.update_stats()
        if PasswordChecker.check_password(self.file_path, password, self.file_type):
            self.password_discovered = password
            self.password_found.emit(password, self.file_type)
            return


def _pw_parse_hashcat_status(self, line):
    line = line.strip()
    if not line:
        return

    progress_match = re.search(r"Progress.*?:\s*([0-9]+)\/([0-9]+)\s+\(([\d\.]+)%\)", line)
    if progress_match:
        try:
            percent = int(float(progress_match.group(3)))
            self.progress.emit(max(0, min(100, percent)))
        except Exception:
            pass
        return

    speed_match = re.search(r"Speed.*?:\s*([\d\.]+)\s*([kMGT]?H/s)", line, re.IGNORECASE)
    if speed_match:
        value = float(speed_match.group(1))
        suffix = speed_match.group(2).lower()
        mult = {"h/s": 1, "kh/s": 1_000, "mh/s": 1_000_000, "gh/s": 1_000_000_000, "th/s": 1_000_000_000_000}
        self.speed_update.emit(value * mult.get(suffix, 1))
        return

    eta_match = re.search(r"Time\.Estimated.*?\((.*?)\)", line)
    if eta_match:
        self.estimated_time.emit(f"ETA: ~{eta_match.group(1)}")
        return

    candidate_match = re.search(r"Candidates.*?:\s*(.*?)\s*->", line)
    if candidate_match:
        candidate = candidate_match.group(1).strip()
        if candidate:
            self.current_password.emit(candidate)


def _pw_cleanup_gpu_plan(plan):
    for key in ("hash_file", "outfile", "potfile"):
        try:
            Path(plan[key]).unlink(missing_ok=True)
        except Exception:
            pass


def _pw_run_gpu_attack(self):
    backend = GPUBackend()
    try:
        backend.ensure_installed()
        hash_modes = []
        if self.file_type in ("excel", "word", "powerpoint", "access"):
            backend.ensure_office_support()
            self.status_update.emit("Preparing Office file for GPU attack…", "#6080a0")
            extracted = backend.extract_office_hash(self.file_path)
            hash_modes = [extracted["mode"]]
            self.status_update.emit("Office file is ready for GPU attack.", "#5a8a6a")
        elif self.file_type in ("zip", "rar", "7z"):
            backend.ensure_archive_support(self.file_type)
            self.status_update.emit(f"Preparing {self.file_type.upper()} archive for GPU attack…", "#6080a0")
            extracted = backend.extract_archive_hash(self.file_path, self.file_type)
            hash_modes = backend._detect_hash_modes(self.file_type, extracted["hash"])
            if self.file_type == "zip":
                hash_modes = []
            self.status_update.emit(f"{self.file_type.upper()} archive is ready for GPU attack.", "#5a8a6a")
        elif self.file_type == "pdf":
            backend.ensure_pdf_support()
            self.status_update.emit("Preparing PDF file for GPU attack…", "#6080a0")
            extracted = backend.extract_pdf_hash(self.file_path)
            hash_modes = list(extracted["modes"])
            self.status_update.emit("PDF file is ready for GPU attack.", "#5a8a6a")
        else:
            raise GPUBackendError(f"GPU attack is not supported for {self.file_type}.")

        charset_value = self.custom_charset if self.charset == "custom" else self.charset
        plan = backend.build_hashcat_attack_plan(
            self.mode,
            extracted["hash"],
            wordlist_path=self.wordlist_path,
            charset=charset_value,
            min_len=self.min_len,
            max_len=self.max_len,
            mask=self.mask,
            device_id=self.gpu_device_id,
            hash_modes=hash_modes,
        )
    except GPUBackendError as exc:
        self.status_update.emit(f"вќЊ GPU setup failed for this {self.file_type.upper()} target.", "#ff3333")
        return

    try:
        self.status_update.emit(f"Running {self.file_type.upper()} attack on GPU…", "#6080a0")
        for cmd in plan["commands"]:
            if not self.running:
                break
            proc = subprocess.Popen(
                cmd,
                cwd=str(plan["workdir"]),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                **_hidden_subprocess_kwargs(),
            )
            self._gpu_process = proc

            while self.running:
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    self._pw_parse_hashcat_status(line)
                if proc.poll() is not None:
                    break

            if not self.running and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

            proc.wait(timeout=30)
            self._gpu_process = None

            password = backend.read_cracked_password(plan["outfile"])
            if password:
                self.password_discovered = password
                self.password_found.emit(password, self.file_type)
                return
    except Exception as exc:
        self.status_update.emit(f"вќЊ GPU {self.file_type.upper()} attack failed.", "#ff3333")
    finally:
        self._gpu_process = None
        _pw_cleanup_gpu_plan(plan)


def _pw_run_performant_bruteforce(self, num_procs):
    chars = self.get_charset()
    if not chars:
        self.status_update.emit("вќЊ Character set is empty!", "#ff3333")
        return

    chars_list = list(chars)
    base = len(chars_list)

    total = 0
    length_ranges = []
    for length in range(self.min_len, self.max_len + 1):
        cnt = base ** length
        length_ranges.append((length, cnt))
        total += cnt
    self.total_passwords = total
    if total == 0:
        self.status_update.emit("вќЊ No combinations to try!", "#ff3333")
        return

    target_chunk = max(1, total // max(1, num_procs * BRUTEFORCE_TASK_FACTOR))

    def task_iter():
        for length, cnt in length_ranges:
            chunk = max(1, min(target_chunk, max(1, cnt // max(1, num_procs))))
            for start in range(0, cnt, chunk):
                end = min(start + chunk, cnt)
                yield (self.file_path, self.file_type, chars_list, length, start, end)

    self._run_pool(_mp_bruteforce_chunk, task_iter(), total)


def _pw_run_performant_mask(self, num_procs):
    mask = self.mask
    if not mask:
        self.status_update.emit("вќЊ No mask specified!", "#ff3333")
        return

    chars_map = self._get_chars_map()
    positions = self._parse_mask(mask, chars_map)

    total = 1
    for pos in positions:
        current = [pos] if isinstance(pos, str) else list(pos)
        if not current:
            self.status_update.emit("вќЊ No combinations for this mask!", "#ff3333")
            return
        total *= len(current)

    self.total_passwords = total
    if total == 0:
        self.status_update.emit("вќЊ No combinations for this mask!", "#ff3333")
        return

    chunk_size = max(1, min(DICTIONARY_CHUNK_SIZE, total // max(1, num_procs * 4)))

    def task_iter():
        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            yield (self.file_path, self.file_type, positions, start, end)

    self._run_pool(_mp_mask_chunk, task_iter(), total)


def _pw_run(self):
    self.running = True
    self.passwords_tried = 0
    self.start_time = datetime.now()
    self.end_time = None
    self._last_speed_emit_ts = 0.0
    self.password_discovered = None
    self._gpu_runtime_broken = False
    self._gpu_failure_reason = ""
    self.found_event.clear()

    try:
        if not PasswordChecker.is_protected(self.file_path):
            self.status_update.emit("File is not password-protected.", "#ff9900")
            self.running = False
            self.end_time = datetime.now()
            self.attack_finished.emit(False)
            return

        self.status_update.emit(f"Starting attack on {self.file_type.upper()} file...", "#007acc")

        if self.compute_backend == "gpu" and self.file_type in ("excel", "word", "powerpoint", "access", "zip", "rar", "7z", "pdf"):
            self.run_gpu_attack()
            if self.running and not self.password_discovered and self._gpu_runtime_broken:
                self.engine_changed.emit("engine_gpu_fallback")
                self.status_update.emit(
                    f"GPU attack failed unexpectedly. Current run continues on CPU. Reason: {self._gpu_failure_reason}",
                    "#c8872f",
                )
                if self.performant_mode:
                    self.run_performant_attack()
                else:
                    if self.mode == "dictionary":
                        self.run_dictionary_attack()
                    elif self.mode == "bruteforce":
                        self.run_bruteforce_attack()
                    elif self.mode == "mask":
                        self.run_mask_attack()
        elif self.performant_mode:
            self.run_performant_attack()
        else:
            if self.mode == "dictionary":
                self.run_dictionary_attack()
            elif self.mode == "bruteforce":
                self.run_bruteforce_attack()
            elif self.mode == "mask":
                self.run_mask_attack()

        if self.password_discovered:
            self.status_update.emit("Attack completed successfully.", "#00cc00")
            self.attack_finished.emit(True)
        elif self.running:
            self.status_update.emit("Attack finished. Password not found.", "#ff3333")
            self.attack_finished.emit(False)

    except Exception as e:
        self.status_update.emit(f"Error: {str(e)}", "#ff3333")
        self.attack_finished.emit(False)
    finally:
        self.running = False
        if self.end_time is None:
            self.end_time = datetime.now()


def _pw_run_gpu_attack_v2(self):
    backend = GPUBackend()
    plan = None
    saw_valid_completion = False
    last_error_code = None
    try:
        backend.ensure_installed()
        hash_modes = []
        if self.file_type in ("excel", "word", "powerpoint", "access"):
            backend.ensure_office_support()
            self.status_update.emit("Preparing Office file for GPU attack...", "#6080a0")
            extracted = backend.extract_office_hash(self.file_path)
            hash_modes = [extracted["mode"]]
            self.status_update.emit("Office file is ready for GPU attack.", "#5a8a6a")
        elif self.file_type in ("zip", "rar", "7z"):
            backend.ensure_archive_support(self.file_type)
            self.status_update.emit(f"Preparing {self.file_type.upper()} archive for GPU attack...", "#6080a0")
            extracted = backend.extract_archive_hash(self.file_path, self.file_type)
            hash_modes = backend._detect_hash_modes(self.file_type, extracted["hash"])
            if self.file_type == "zip":
                # ZIP was more reliable when hashcat picked the mode itself from the extracted hash.
                # Keep explicit mode detection for logging/debugging, but let hashcat auto-identify here.
                hash_modes = []
            self.status_update.emit(f"{self.file_type.upper()} archive is ready for GPU attack.", "#5a8a6a")
        elif self.file_type == "pdf":
            backend.ensure_pdf_support()
            self.status_update.emit("Preparing PDF file for GPU attack...", "#6080a0")
            extracted = backend.extract_pdf_hash(self.file_path)
            hash_modes = list(extracted["modes"])
            self.status_update.emit("PDF file is ready for GPU attack.", "#5a8a6a")
        else:
            raise GPUBackendError(f"GPU attack is not supported for {self.file_type}.")

        charset_value = self.custom_charset if self.charset == "custom" else self.charset
        plan = backend.build_hashcat_attack_plan(
            self.mode,
            extracted["hash"],
            wordlist_path=self.wordlist_path,
            charset=charset_value,
            min_len=self.min_len,
            max_len=self.max_len,
            mask=self.mask,
            device_id=self.gpu_device_id,
            hash_modes=hash_modes,
        )
    except GPUBackendError as exc:
        self._gpu_runtime_broken = True
        self._gpu_failure_reason = str(exc)
        return

    try:
        self.status_update.emit(f"Running {self.file_type.upper()} attack on GPU...", "#6080a0")
        for cmd in plan["commands"]:
            if not self.running:
                break
            proc = subprocess.Popen(
                cmd,
                cwd=str(plan["workdir"]),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                **_hidden_subprocess_kwargs(),
            )
            self._gpu_process = proc

            while self.running:
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    self._pw_parse_hashcat_status(line)
                if proc.poll() is not None:
                    break

            if not self.running and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

            proc.wait(timeout=30)
            self._gpu_process = None

            if proc.returncode in (0, 1):
                saw_valid_completion = True
            else:
                last_error_code = proc.returncode

            password = backend.read_cracked_password(plan["outfile"])
            if password:
                self.password_discovered = password
                self.password_found.emit(password, self.file_type)
                return
    except Exception as exc:
        self._gpu_runtime_broken = True
        self._gpu_failure_reason = str(exc)
    finally:
        self._gpu_process = None
        if plan:
            _pw_cleanup_gpu_plan(plan)

    if not self.password_discovered and not saw_valid_completion and last_error_code is not None:
        self._gpu_runtime_broken = True
        self._gpu_failure_reason = f"hashcat returned code {last_error_code}"


def _ui_collect_results(self):
    rows = []
    for row in range(self.results_table.rowCount()):
        values = []
        for col in range(self.results_table.columnCount()):
            item = self.results_table.item(row, col)
            values.append(item.text() if item else "")
        rows.append({
            "time": values[0],
            "file": values[1],
            "type": values[2],
            "protection": values[3],
            "password": values[4],
            "duration": values[5],
            "status": values[6],
        })
    return rows


def _ui_insert_result_row(self, entry, persist=False):
    row = self.results_table.rowCount()
    self.results_table.insertRow(row)
    items = [
        QTableWidgetItem(entry.get("time", "")),
        QTableWidgetItem(entry.get("file", "")),
        QTableWidgetItem(entry.get("type", "")),
        QTableWidgetItem(entry.get("protection", "")),
        QTableWidgetItem(entry.get("password", "")),
        QTableWidgetItem(entry.get("duration", "")),
        QTableWidgetItem(entry.get("status", "")),
    ]
    success = entry.get("status", "").lower() == tr("status_found").lower()
    status_color = QColor("#5ab870") if success else QColor("#a05050")
    items[6].setForeground(status_color)
    if success:
        items[4].setForeground(QColor("#78c090"))
        items[5].setForeground(QColor("#a0c8a0"))
        items[3].setForeground(QColor("#7fb0d8"))

    for col, item in enumerate(items):
        self.results_table.setItem(row, col, item)
    self.results_table.resizeColumnsToContents()

    if persist and success and self.save_checkbox.isChecked():
        self._write_result_to_file(
            entry.get("time", ""),
            entry.get("file", ""),
            entry.get("type", ""),
            entry.get("protection", ""),
            entry.get("password", ""),
            entry.get("duration", ""),
        )


def _ui_write_result_to_file(self, ts, filename, file_type, protection, password, duration):
    try:
        line = (
            f"[{ts}] File: {filename} | Type: {file_type} | Protection: {protection} | "
            f"Password: {password} | Duration: {duration}\n"
        )
        with open(RESULTS_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        self._log_line(f"Could not write Results.txt: {e}", "#8a7040")


def _ui_restore_results(self):
    if not self.save_checkbox.isChecked():
        QMessageBox.information(
            self,
            "Results restore",
            "Восстановление доступно только когда включена опция сохранения в Results.txt.",
        )
        return
    if not RESULTS_FILE.exists():
        QMessageBox.information(self, "Results restore", "Results.txt пока не найден.")
        return

    restored = 0
    pattern = re.compile(
        r"^\[(?P<time>[^\]]+)\]\s+File:\s+(?P<file>.+?)\s+\|\s+Type:\s+(?P<type>.+?)"
        r"(?:\s+\|\s+Protection:\s+(?P<protection>.+?))?\s+\|\s+Password:\s+(?P<password>.+?)\s+\|\s+Duration:\s+(?P<duration>.+?)$"
    )
    existing = {
        tuple(row.values())
        for row in self._collect_results()
    }

    for raw in RESULTS_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        entry = {
            "time": match.group("time") or "",
            "file": match.group("file") or "",
            "type": (match.group("type") or "").upper(),
            "protection": match.group("protection") or "Unknown",
            "password": match.group("password") or "",
            "duration": match.group("duration") or "",
            "status": tr("status_found"),
        }
        key = tuple(entry.values())
        if key in existing:
            continue
        existing.add(key)
        self._ui_insert_result_row(entry, persist=False)
        restored += 1

    self._log_line(f"Restored {restored} saved result(s) from Results.txt.", "#5a8a6a")


def _ui_export_results(self):
    rows = self._collect_results()
    if not rows:
        QMessageBox.information(self, "Export results", "Список результатов пока пуст.")
        return

    path, selected_filter = QFileDialog.getSaveFileName(
        self,
        "Export results",
        str(APP_DIR / "results_export.txt"),
        "Text (*.txt);;CSV (*.csv);;JSON (*.json);;Word Document (*.doc);;PDF (*.pdf)",
    )
    if not path:
        return

    suffix = Path(path).suffix.lower()
    if not suffix:
        filter_map = {
            "Text (*.txt)": ".txt",
            "CSV (*.csv)": ".csv",
            "JSON (*.json)": ".json",
            "Word Document (*.doc)": ".doc",
            "PDF (*.pdf)": ".pdf",
        }
        suffix = filter_map.get(selected_filter, ".txt")
        path += suffix
        suffix = suffix.lower()

    headers = ["Time", "File", "Type", "Protection", "Password", "Duration", "Status"]
    try:
        if suffix == ".txt":
            with open(path, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(
                        f"[{row['time']}] {row['file']} | {row['type']} | {row['protection']} | "
                        f"{row['password']} | {row['duration']} | {row['status']}\n"
                    )
        elif suffix == ".csv":
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[h.lower() for h in headers])
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        elif suffix == ".json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
        elif suffix in (".doc", ".pdf"):
            html_rows = []
            for row in rows:
                cols = "".join(f"<td>{escape(row[key.lower()])}</td>" for key in headers)
                html_rows.append(f"<tr>{cols}</tr>")
            html = (
                "<html><body style='font-family: Segoe UI; color: #202020;'>"
                "<h2>Bruteforcer Results</h2>"
                "<table border='1' cellspacing='0' cellpadding='4' style='border-collapse: collapse; width: 100%;'>"
                f"<tr>{''.join(f'<th>{escape(h)}</th>' for h in headers)}</tr>"
                f"{''.join(html_rows)}</table></body></html>"
            )
            if suffix == ".doc":
                Path(path).write_text(html, encoding="utf-8")
            else:
                writer = QPdfWriter(path)
                document = QTextDocument()
                document.setHtml(html)
                document.print(writer)
        else:
            raise ValueError("Unsupported export format.")
    except Exception as exc:
        QMessageBox.warning(self, "Export results", str(exc))
        return

    self._log_line(f"Results exported to: {path}", "#5a8a6a")


def _ui_on_engine_changed(self, engine_key):
    self._set_active_engine(engine_key)


def _ui_on_status_update(self, message, color):
    self._log_line(message, color, dedupe_window=1.2)


def _ui_on_password_found(self, password, file_type):
    self._log_section(tr("log_password_found"), "#3a5a3a")
    self._log_line(password, "#78d090")
    self.add_to_results(password, file_type, True)


def _ui_on_attack_finished(self, success):
    self.start_btn.setEnabled(True)
    self.stop_btn.setEnabled(False)
    self._set_active_engine(self._selected_engine_key)
    self._set_status(tr("status_ready"))


def _ui_add_to_results(self, password, file_type, success=True):
    ts = datetime.now().strftime("%H:%M:%S")
    filename = os.path.basename(self.selected_file)
    protection = getattr(self, "_current_protection", "") or PasswordChecker.describe_protection(self.selected_file, file_type)
    if self._attack_start_time:
        dur_secs = (datetime.now() - self._attack_start_time).total_seconds()
        duration = PasswordWorker._fmt_time(dur_secs)
    else:
        duration = "-"

    self._ui_insert_result_row({
        "time": ts,
        "file": filename,
        "type": file_type.upper(),
        "protection": protection,
        "password": password,
        "duration": duration,
        "status": tr("status_found") if success else tr("status_not_found"),
    }, persist=True)


def _ui_analyze_file(self, file_path):
    try:
        size_kb = os.path.getsize(file_path) / 1024
        ftype = self.selected_file_type.upper()
        protected = PasswordChecker.is_protected(file_path)
        protection = PasswordChecker.describe_protection(file_path, self.selected_file_type)
        self._current_protection = protection
        prot_state = "Protected" if protected else "Not protected"
        self.file_info_label.setText(
            f"Type: {ftype}  |  {size_kb:.0f} KB  |  Protection: {protection}"
        )
        color = "#5a8a6a" if protected else "#8a7040"
        self._log_section(f"Target file: {os.path.basename(file_path)}", "#2e2e30")
        self._log_line(f"Type: {ftype}  |  Size: {size_kb:.0f} KB", "#6080a0")
        self._log_line(f"Protection: {protection}", color)
        if not protected:
            self._log_line(f"Status: {prot_state}", "#8a6030")
    except Exception as e:
        self._log_line(f"Error reading file: {str(e)}", "#8a4040")


def _ui_start_attack(self):
    if not self.selected_file:
        self._log_line(tr("log_select_file"), "#8a4040")
        return

    if not PasswordChecker.is_protected(self.selected_file):
        reply = QMessageBox.question(
            self, tr("confirm_title"), tr("confirm_msg"),
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            return

    method = self.attack_combo.currentIndex()
    self.worker = PasswordWorker()
    mode = ["dictionary", "bruteforce", "mask"][method]
    file_type = self.selected_file_type
    compute_backend = "gpu" if self.backend_combo.currentIndex() == 1 else "cpu"
    gpu_device_id = str(self.gpu_device_combo.currentData() or "")
    engine_key = "engine_gpu" if compute_backend == "gpu" else "engine_cpu"

    if compute_backend == "gpu":
        if not self._ensure_gpu_runtime_installed():
            self._log_line("GPU mode is selected, but the backend is not ready. Attack was not started.", "#8a7040")
            self._set_selected_engine()
            return
        support = self.gpu_backend.supports_attack(file_type, mode)
        if not support["supported"]:
            QMessageBox.information(self, "GPU backend", support["reason"])
            self._log_line(support["reason"], "#8a7040")
            self._set_selected_engine()
            return
        try:
            if file_type in ("excel", "word", "powerpoint", "access"):
                self._show_loading_overlay("Preparing Office GPU mode", "Downloading Office hash extractor...")
                self.gpu_backend.ensure_office_support(progress_callback=self._update_loading_overlay)
            elif file_type in ("zip", "rar", "7z", "pdf"):
                self._show_loading_overlay("Preparing GPU mode", "Downloading GPU extractors...")
                self.gpu_backend.ensure_filetype_support(file_type, progress_callback=self._update_loading_overlay)
        except GPUBackendError as exc:
            QMessageBox.warning(self, "GPU backend", str(exc))
            self._log_line(f"GPU preparation failed: {exc}", "#8a7040")
            self._set_selected_engine()
            return
        finally:
            self._hide_loading_overlay()

    if method == 0:
        if self.dict_combo.currentIndex() <= 0:
            self._log_line(tr("log_select_wordlist"), "#8a4040")
            return
        raw = self.dict_combo.currentText().replace(tr("default_label"), "").strip()
        wordlist_path = None
        for name, source_path in self.default_wordlists.items():
            if name == raw or raw in name:
                wordlist_path = source_path
                break
        if not wordlist_path or not os.path.exists(wordlist_path):
            pp = USER_PASSWORDS_DIR / raw
            if pp.exists():
                wordlist_path = str(pp)
            else:
                self._log_line(tr("log_wordlist_not_found") + raw, "#8a4040")
                return
        charset = "dictionary"
        mask = None
        custom_charset = ""
    elif method == 1:
        wordlist_path = None
        mask = None
        cm = {
            0: "lowercase", 1: "uppercase", 2: "digits", 3: "alphanumeric",
            4: "all", 5: "hex_lower", 6: "hex_upper", 7: "custom",
        }
        charset = cm[self.charset_combo.currentIndex()]
        custom_charset = self.custom_charset_edit.text() if charset == "custom" else ""
    else:
        wordlist_path = None
        charset = "mask"
        mask = self.mask_edit.text()
        custom_charset = ""
        if not mask:
            self._log_line(tr("log_enter_mask"), "#8a4040")
            return

    self.worker.set_parameters(
        self.selected_file, file_type, mode, charset,
        self.min_length.value(), self.max_length.value(),
        wordlist_path, mask, custom_charset,
        self.performant_checkbox.isChecked(),
        compute_backend, gpu_device_id,
    )
    self.worker.progress.connect(self.progress_bar.setValue)
    self.worker.password_found.connect(self.on_password_found)
    self.worker.status_update.connect(self.on_status_update)
    self.worker.engine_changed.connect(self.on_engine_changed)
    self.worker.current_password.connect(self.on_current_password)
    self.worker.stats_update.connect(self.on_stats_update)
    self.worker.estimated_time.connect(self.on_estimated_time)
    self.worker.speed_update.connect(self.on_speed_update)
    self.worker.attack_finished.connect(self.on_attack_finished)

    self.start_btn.setEnabled(False)
    self.stop_btn.setEnabled(True)
    self.progress_bar.setValue(0)
    self._set_active_engine(engine_key)
    self._set_status(tr("status_running"), active=True)
    self._attack_start_time = datetime.now()

    protection = PasswordChecker.describe_protection(self.selected_file, file_type)
    self._current_protection = protection
    self._log_section(f"{tr('log_attack_started')}  [{file_type.upper()}]  {self.attack_combo.currentText()}", "#2e2e30")
    self._log_line(f"{tr('log_file')}{os.path.basename(self.selected_file)}", "#6080a0")
    self._log_line(f"Protection: {protection}", "#6080a0")
    if self.performant_checkbox.isChecked():
        self._log_line(tr("log_mode_multicore"), "#6080a0")
    self._log_line(f"{tr('backend_label')} {self.backend_combo.currentText()}", "#6080a0")

    self._persist_settings()
    self.worker.start()


PasswordWorker.run = _pw_run
PasswordWorker.run_dictionary_attack = _pw_run_dictionary_attack
PasswordWorker._pw_parse_hashcat_status = _pw_parse_hashcat_status
PasswordWorker.run_gpu_attack = _pw_run_gpu_attack_v2
PasswordWorker.run_performant_dictionary = _pw_run_performant_dictionary
PasswordWorker.run_performant_bruteforce = _pw_run_performant_bruteforce
PasswordWorker.run_performant_mask = _pw_run_performant_mask

ZetaUniversalBruteforcer.start_attack = _ui_start_attack
ZetaUniversalBruteforcer.analyze_file = _ui_analyze_file
ZetaUniversalBruteforcer.on_status_update = _ui_on_status_update
ZetaUniversalBruteforcer.on_engine_changed = _ui_on_engine_changed
ZetaUniversalBruteforcer.on_password_found = _ui_on_password_found
ZetaUniversalBruteforcer.on_attack_finished = _ui_on_attack_finished
ZetaUniversalBruteforcer.add_to_results = _ui_add_to_results
ZetaUniversalBruteforcer._write_result_to_file = _ui_write_result_to_file
ZetaUniversalBruteforcer._collect_results = _ui_collect_results
ZetaUniversalBruteforcer._ui_insert_result_row = _ui_insert_result_row
ZetaUniversalBruteforcer.export_results = _ui_export_results
ZetaUniversalBruteforcer.restore_results = _ui_restore_results


def main():
    multiprocessing.freeze_support()
    ensure_app_storage()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(build_palette())

    _apply_app_icon(app)

    window = ZetaUniversalBruteforcer()
    window.show()
    sys.exit(app.exec())


def _apply_app_icon(app):
    from PySide6.QtGui import QIcon
    candidates = [
        resource_path("icon.ico"),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon.ico"),
        os.path.join(os.getcwd(), "icon.ico"),
    ]
    for path in candidates:
        if os.path.exists(path):
            icon = QIcon(str(path))
            if not icon.isNull():
                app.setWindowIcon(icon)
            return


if __name__ == "__main__":
    main()
