<div align="center">

# 🔐 Bruteforcer

**[English](#english) · [Русский](#russian)**

Графический инструмент для восстановления потерянных паролей из зашифрованных файлов.  
Создан на Python 3 и PySide6. Поддерживает многоядерное ускорение, три режима атаки и дюжину форматов файлов.

</div>

---

<a name="russian"></a>

<img width="1204" height="783" alt="{554C7066-5AB8-410D-8933-8C9A8D683266}" src="https://github.com/user-attachments/assets/4e3a2e87-0708-4602-9cb9-ff842efff3b3" />

## Русский

Bruteforcer — десктопный GUI-инструмент для восстановления забытого пароля от файла. Поддерживает атаку по словарю, полный перебор и атаку по маске. Тёмный интерфейс, статистика в реальном времени, многоядерное ускорение.

### Поддерживаемые форматы

| Категория | Форматы |
|---|---|
| Архивы | ZIP, RAR, 7Z |
| Microsoft Office | XLSX, XLS, XLSM, DOCX, DOC, PPTX, PPT, ACCDB, MDB |
| PDF | PDF |

### Режимы атаки

**По словарю** — перебирает пароли из текстового файла. При первом запуске автоматически скачивается `rockyou.txt`. Любой `.txt`-файл, помещённый в папку `passwords/`, сразу появляется в выпадающем списке.

**Перебор (Brute-force)** — генерирует все возможные комбинации для заданного набора символов и диапазона длин. Доступные наборы: строчные, заглавные, цифры, буквы+цифры, все печатные, hex (нижний/верхний регистр), произвольный набор.

**По маске** — атака по шаблону в стиле hashcat:

| Токен | Значение |
|---|---|
| `?l` | строчные a–z |
| `?u` | заглавные A–Z |
| `?d` | цифры 0–9 |
| `?s` | специальные символы |
| `?a` | все печатные |
| `?h` / `?H` | hex нижний / верхний регистр |

Пример маски: `?u?l?l?l?d?d` → перебирает строки вида `Hello42`.

### Возможности

- **Многоядерный режим** — распределяет задачу по всем потокам CPU через `multiprocessing`. На современных машинах даёт ускорение в 4–16 раз по сравнению с однопоточным режимом.
- **Статистика в реальном времени** — паролей/сек, прошедшее время, оставшееся время, текущий проверяемый пароль.
- **Журнал результатов** — каждый найденный пароль фиксируется во вкладке «Результаты» с временем, именем файла, типом и длительностью атаки. По желанию автоматически сохраняется в `Results.txt`.
- **Интерфейс EN / RU** — переключение языка прямо из заголовка окна без перезапуска.
- **Сохранение настроек** — последний файл, выбранный метод атаки и опции сохраняются в `settings.ini` и восстанавливаются при следующем запуске.

### Требования

Python 3.9 или новее. Установка зависимостей:

```bash
pip install PySide6 msoffcrypto-tool PyPDF2 rarfile py7zr pyzipper
```

> **Поддержка RAR** требует наличия `unrar` в PATH:
> - Windows — скачать с [rarlab.com](https://www.rarlab.com/rar_add.htm)
> - Linux — `sudo apt install unrar`
> - macOS — `brew install rar`

### Запуск

```bash
python Bruteforcer.py
```

1. Нажать **Обзор** и выбрать защищённый файл
2. Выбрать метод атаки и настроить параметры
3. Нажать **Начать**

Индикатор в правом верхнем углу показывает **ГОТОВ** / **РАБОТАЕТ**. Прогресс-бар, счётчик скорости и ETA обновляются в реальном времени.

### Структура проекта

```
Bruteforcer.py     ядро — движок атак, рабочий поток, главное окно
Design.py          весь UI — виджеты, стили, переводы
passwords/         папка для словарей (rockyou.txt скачивается при первом запуске)
Results.txt        создаётся автоматически при включённой опции сохранения
settings.ini       создаётся при первом запуске, хранит настройки
icon.ico           опционально — иконка окна и панели задач
```

### Как работает многоядерный режим

При включённом многоядерном режиме приложение запускает `multiprocessing.Pool` через контекст `spawn` (обязательно для Windows). Пространство паролей делится на чанки и раздаётся воркерам через `imap_unordered` — как только любой воркер находит пароль, пул немедленно завершается. При нажатии «Стоп» воркеры принудительно завершаются, чтобы не оставлять зависших процессов.

Словари читаются в кодировке `latin-1`, а не UTF-8. Это сделано намеренно: latin-1 — строгое однобайтовое отображение, которое никогда не теряет байты. UTF-8 с `errors='ignore'` молча удаляет невалидные последовательности, сдвигает границы чанков и приводит к тому, что часть паролей вообще не проверяется.

### ⚠️ Правовое уведомление

Инструмент предназначен **исключительно** для восстановления паролей от файлов, которыми вы владеете или на доступ к которым имеете явное письменное разрешение. Несанкционированное использование против чужих файлов может нарушать законодательство об информационной безопасности вашей страны. Автор не несёт ответственности за неправомерное использование.

### ⚠️ Это ЕДИНСТВЕННОЕ место где публикуется данная программа, если вы видите её в каких-либо youtube роликах, на подозрительных сайтах или вам кто-то присылает её в виде exe файла - это 100% ВИРУС или у вас пытаются украсть данные. Качайте программу ТОЛЬКО отсюда!


---

<a name="english"></a>

<div align="center">

# 🔐 Bruteforcer

A desktop GUI tool for recovering lost passwords from encrypted files.  
Built with Python 3 and PySide6. Supports multi-core acceleration, three attack modes, and a dozen file formats.

</div>

<img width="1205" height="785" alt="{DBC66F1B-5FF8-4917-8E0A-61D7389D74BF}" src="https://github.com/user-attachments/assets/65b422b2-1111-44b2-9dfb-4e70f4013e94" />

## English

Bruteforcer helps you recover a forgotten password from a file you own. It supports dictionary attacks, exhaustive brute-force, and mask-based pattern attacks — all from a clean dark-themed interface with real-time statistics.

### Supported formats

| Category | Formats |
|---|---|
| Archives | ZIP, RAR, 7Z |
| Microsoft Office | XLSX, XLS, XLSM, DOCX, DOC, PPTX, PPT, ACCDB, MDB |
| PDF | PDF |

### Attack modes

**Dictionary** — tries every password in a wordlist. `rockyou.txt` is downloaded automatically on first launch. Any `.txt` file placed in the `passwords/` folder appears in the dropdown instantly.

**Brute-force** — generates every possible combination for a given charset and length range. Charsets available: lowercase, uppercase, digits, alphanumeric, all printable, hex (lower/upper), or a fully custom set.

**Mask** — pattern-based attack using hashcat-style tokens:

| Token | Meaning |
|---|---|
| `?l` | lowercase a–z |
| `?u` | uppercase A–Z |
| `?d` | digits 0–9 |
| `?s` | special characters |
| `?a` | all printable |
| `?h` / `?H` | hex lowercase / uppercase |

Example mask: `?u?l?l?l?d?d` → tries all 6-char strings like `Hello42`.

### Features

- **Multi-core mode** — distributes work across all CPU threads using `multiprocessing`. On modern machines this gives a 4–16× speedup over single-threaded mode.
- **Live statistics** — passwords/sec, elapsed time, estimated time remaining, currently tested password.
- **Results log** — every found password is shown in the Results tab with timestamp, file name, type, and duration. Optionally auto-saved to `Results.txt`.
- **EN / RU interface** — switch language from the titlebar toggle at any time without restarting.
- **Persistent settings** — last opened file, selected attack method, and options are saved in `settings.ini` and restored on next launch.

### Requirements

Python 3.9 or newer. Install dependencies:

```bash
pip install PySide6 msoffcrypto-tool PyPDF2 rarfile py7zr pyzipper
```

> **RAR support** requires the `unrar` binary in PATH:
> - Windows — download from [rarlab.com](https://www.rarlab.com/rar_add.htm)
> - Linux — `sudo apt install unrar`
> - macOS — `brew install rar`

### Running

```bash
python Bruteforcer.py
```

1. Click **Browse** and select your protected file
2. Choose the attack method and configure options
3. Press **Start**

The status badge in the top-right corner shows **READY** / **RUNNING**. The progress bar, speed counter, and ETA update in real time.

### Project structure

```
Bruteforcer.py     core logic — attack engine, worker thread, main window
Design.py          all UI layout, custom widgets, styles, translations
passwords/         wordlist directory (rockyou.txt downloaded on first run)
Results.txt        auto-created when "Save results" is enabled
settings.ini       auto-created on first launch, stores preferences
icon.ico           optional — window and taskbar icon
```

### How multi-core works

When multi-core mode is on, the app spawns a `multiprocessing.Pool` using the `spawn` context (required for Windows). The password space is split into chunks and distributed with `imap_unordered` — as soon as any worker finds the password, the pool is terminated immediately. Workers are hard-killed on Stop/Cancel to avoid zombie processes.

Wordlists are read in `latin-1` encoding rather than UTF-8. This is intentional: latin-1 is a strict 1-byte mapping that never drops bytes. UTF-8 with `errors='ignore'` silently deletes invalid byte sequences, shifts chunk boundaries, and causes passwords to be missed entirely.

### ⚠️ Legal notice

This tool is intended **solely** for recovering passwords from files you own or have explicit written permission to access. Unauthorized use against files belonging to others may violate computer crime laws in your jurisdiction. The author assumes no liability for misuse.

### ⚠️ This is the ONLY place where this program is published, if you see it in any YouTube videos, on suspicious sites, or someone sends it to you as an exe file, it's a 100% VIRUS or you're trying to steal data. Download the program ONLY from here!

---

<div align="center">

[⬆ Back to top / Наверх](#-bruteforcer)

</div>
