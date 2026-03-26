import sys
import os
import time
import string
import itertools
from datetime import datetime
from pathlib import Path
import concurrent.futures
import threading
import multiprocessing
import urllib.request
import configparser

def _mp_check_password(file_path, password, file_type):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if file_type == "zip" or ext == ".zip":
            import zipfile
            with zipfile.ZipFile(file_path, 'r') as zf:
                names = zf.namelist()
                if not names:
                    return False
                pwd_bytes = password.encode('utf-8') if isinstance(password, str) else password
                zf.read(names[0], pwd=pwd_bytes)
                return True
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


def _pool_dispatch(args):
    fn, fn_args = args
    return fn(*fn_args)


def _read_wordlist(path):
    try:
        with open(path, 'r', encoding='latin-1') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        pass
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return None


# GUI
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QTableWidgetItem
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

# Design module
from Design import (
    build_ui, build_palette, MAIN_STYLESHEET,
    FILE_LABEL_SELECTED_STYLE, FILE_LABEL_EMPTY_STYLE,
    STATUS_READY_STYLE, STATUS_ACTIVE_STYLE,
    tr, set_language, TRANSLATIONS,
)

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

SETTINGS_FILE = "settings.ini"

DEFAULT_SETTINGS = {
    "general": {
        "language":      "en",
        "last_file":     "",
        "attack_method": "0",
    },
    "options": {
        "multicore":     "true",
        "save_results":  "true",
    },
}

def load_settings() -> configparser.ConfigParser:
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
        if not ZIP_SUPPORT:
            return False
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                names = zf.namelist()
                if not names:
                    return False
                pwd_bytes = password.encode('utf-8') if isinstance(password, str) else password
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

class DictionaryManager:
    DEFAULT_WORDLISTS = {
        "rockyou.txt": (
            "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt"
        ),
        "10k_most_common.txt": (
            "https://raw.githubusercontent.com/danielmiessler/SecLists/master/"
            "Passwords/Common-Credentials/10-million-password-list-top-10000.txt"
        ),
    }

    @staticmethod
    def get_available_wordlists():
        wordlists = {}
        passwords_dir = Path("passwords")
        passwords_dir.mkdir(exist_ok=True)
        for file in passwords_dir.glob("*.txt"):
            wordlists[file.name] = str(file)
        if "rockyou.txt" not in wordlists:
            DictionaryManager.download_default_wordlists()
            fp = passwords_dir / "rockyou.txt"
            if fp.exists():
                wordlists["rockyou.txt"] = str(fp)
        return wordlists

    @staticmethod
    def download_default_wordlists():
        passwords_dir = Path("passwords")
        passwords_dir.mkdir(exist_ok=True)
        for name, url in DictionaryManager.DEFAULT_WORDLISTS.items():
            fp = passwords_dir / name
            if not fp.exists():
                try:
                    print(f"Downloading {name}...")
                    urllib.request.urlretrieve(url, fp)
                    print(f"Downloaded {name}")
                except Exception as e:
                    print(f"Error downloading {name}: {e}")


class PasswordWorker(QThread):
    progress         = Signal(int)
    password_found   = Signal(str, str)
    status_update    = Signal(str, str)
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

    def set_parameters(self, file_path, file_type, mode, charset,
                       min_len, max_len, wordlist_path=None, mask=None,
                       custom_charset="", performant_mode=False):
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

            if self.performant_mode:
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
        num_procs = multiprocessing.cpu_count()
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

        num_procs = multiprocessing.cpu_count()
        ctx  = multiprocessing.get_context('spawn')
        pool = ctx.Pool(processes=num_procs)
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
            "hex_lower":    string.hexdigits.lower(),
            "hex_upper":    string.hexdigits.upper(),
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
        self.selected_file      = ""
        self.selected_file_type = ""
        self.default_wordlists  = {}
        self.current_stats      = {}
        self._attack_start_time = None   # for duration column

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
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon.ico"),
            os.path.join(os.getcwd(), "icon.ico"),
            "icon.ico",
        ]:
            if os.path.exists(ico_path):
                wicon = QIcon(ico_path)
                if not wicon.isNull():
                    self.setWindowIcon(wicon)
                break
        self.load_wordlists()
        self.setStyleSheet(MAIN_STYLESHEET)

        # Apply saved settings to UI
        self._apply_settings_to_ui()

    def init_ui(self):
        refs = build_ui(self)
        self.status_badge          = refs["status_badge"]
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
        self.performant_checkbox   = refs["performant_checkbox"]
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
        self._perf_hint_lbl = refs.get("perf_hint")
        self._save_hint_lbl = refs.get("save_hint")

        self.update_attack_method()

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

        save_res = self.cfg.getboolean("options", "save_results", fallback=True)
        self.save_checkbox.setChecked(save_res)

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
        self.cfg.set("options", "save_results", str(self.save_checkbox.isChecked()).lower())
        save_settings(self.cfg)

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
            tr("col_time"), tr("col_file"), tr("col_type"),
            tr("col_password"), tr("col_duration"), tr("col_status"),
        ])

        # Settings checkboxes
        self.performant_checkbox.setText(tr("perf_checkbox"))
        self.save_checkbox.setText(tr("save_checkbox"))

        # Settings hints
        perf_hint = getattr(self, "_perf_hint_lbl", None)
        save_hint = getattr(self, "_save_hint_lbl", None)
        if perf_hint:
            perf_hint.setText(tr("perf_hint"))
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
                label = f"{name}{tr('default_label')}" if name == "rockyou.txt" else name
                self.dict_combo.addItem(label)
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
                pp = Path("passwords") / raw
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
            with open("Results.txt", "a", encoding="utf-8") as f:
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


def main():
    multiprocessing.freeze_support()
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
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon.ico"),
        os.path.join(os.getcwd(), "icon.ico"),
        "icon.ico",
    ]
    for path in candidates:
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                app.setWindowIcon(icon)
            return


if __name__ == "__main__":
    main()
