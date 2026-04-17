<div align="center">

# 🔐 Bruteforcer

**[English](#english) · [Русский](#russian)**

Графический инструмент для восстановления паролей от защищенных файлов.  
Built with Python and PySide6, with CPU and optional GPU attack backends.

</div>

---

<a name="russian"></a>

<img width="1201" height="783" alt="{311366CF-0025-4FE7-B5F0-4386116E9E25}" src="https://github.com/user-attachments/assets/cd04fc88-ce47-413f-870e-a3293e1f3741" />

#

<details open>
<summary><strong><img width="19" height="20" alt="277031mbmmfoabln" src="https://github.com/user-attachments/assets/6161bda3-fa90-40be-8e71-c077bf96af9d" /> Последнее обновление</strong></summary>

#### Новые возможности

- **GPU-ускорение**: полная поддержка GPU для brute-force, dictionary и mask-атак на файлы ZIP, RAR, 7Z, PDF и Microsoft Office.
- **Интеграция GPU-инструментов**: используется связка Hashcat, John the Ripper, `office2john.py`, `pdf2john.py`, `zip2john`, `rar2john` и `7z2hashcat` для извлечения и перебора хэшей.
- **Автоматическая установка backend**: приложение само скачивает и подготавливает внешний runtime для GPU-режима:
  `Hashcat` около 19 MB, `John the Ripper` около 65 MB и `7-Zip` около 1.6 MB.
- **Выбор вычислительного backend**: в настройках добавлен переключатель `CPU / GPU` с определением совместимых GPU-устройств.
- **Автоопределение GPU**: поддерживается обнаружение совместимых устройств NVIDIA и AMD через Hashcat runtime.
- **Fallback на CPU**: если GPU backend недоступен, не поддерживает конкретный сценарий или завершается с ошибкой, атака автоматически продолжается на CPU.
- **Улучшенная поддержка форматов**:
  ZIP с AES-шифрованием через `pyzipper`;
  детальное определение типа защиты, например `ZIP AES-256`, `RAR5`, `7Z AES-256`, `PDF encrypted, R=6, 256-bit`, `Office Agile Encryption`.
- **Расширенные словари**: добавлены крупные словари `xato-net-10-million-passwords.txt` и `xato-net-10-million-passwords-1000000.txt`.
- **Управление словарями**: словари автоматически хранятся и используются из пользовательской папки `~/Bruteforcer/Passwords/`. Также автоматически подгружается дефолтный список `10k_most_common.txt`.
- **Экспорт и восстановление результатов**: результаты можно экспортировать в `TXT`, `CSV`, `JSON`, `DOC`, `PDF`, а также восстанавливать из `Results.txt`.
- **Улучшенный UI**: добавлены подсказки, индикаторы загрузки для подготовки GPU backend, выбор GPU-устройства, улучшенные секции настроек и полноценное переключение RU/EN.

#### Улучшения производительности

- **Оптимизация CPU-режима**: приложение оставляет часть логических ядер свободными для системы и использует до `CPU - 2` процессов.
- **Чанкинг задач**: словарные атаки режутся на чанки по `2000` паролей, brute-force и mask-режим распределяются пакетами для более равномерной загрузки ядер.
- **Реальное время статистики**: скорость, прогресс, ETA и текущий статус обновляются в реальном времени.
- **Безопасность процессов**: при остановке атаки дочерние процессы завершаются принудительно, а временные GPU/CPU-процессы корректно очищаются.
- **Приоритет процессов**: в Windows рабочие процессы понижают приоритет, чтобы интерфейс оставался отзывчивым на тяжелых задачах.

#### Технические изменения

- **Новая архитектура**:
  класс `GPUBackend` управляет установкой и использованием GPU runtime;
  `HashcatRuntimeManager` подготавливает рабочую директорию Hashcat;
  `DictionaryManager` отвечает за словари;
  `PasswordChecker` расширен методами `is_protected()` и `describe_protection()`.
- **Зависимости и модули**: используются `pyzipper`, `msoffcrypto-tool`, `PyPDF2`, `rarfile`, `py7zr`, `csv`, `json`, `subprocess`, `shutil`, `html.escape`.
- **Хранение данных**: настройки и служебные файлы перенесены в `~/Bruteforcer/`:
  `settings.ini`, `Results.txt`, `Bruteforcer_links.txt`, `Passwords/`, `lib/`.
- **Сборка**: добавлен `build_exe.py` для сборки standalone `Bruteforcer.exe` через PyInstaller с иконкой, версией и встроенными словарями.
- **Кодировки**: улучшено чтение словарей через `latin-1` с fallback на `utf-8` и `errors="replace"`.
- **Логирование**: терминал получил более детальные сообщения, цветовую индикацию и дедупликацию повторов.

#### Исправления и стабильность

- **Обработка ошибок**: ошибки GPU-подготовки, извлечения хэшей и записи результатов обрабатываются аккуратнее, без падения интерфейса.
- **Проверка файлов**: `is_protected()` точнее определяет, защищен файл или нет, еще до запуска атаки.
- **Маски**: поддерживаются hashcat-стиль токены `?l`, `?u`, `?d`, `?s`, `?a`, `?h`, `?H`.
- **Остановка атак**: на Windows остановка стала надежнее за счет `terminate` и принудительной очистки процессов.

#### Удаления и изменения поведения

- Для части GPU-проверок больше не используется прежний подход через локальные проверки форматов: при GPU-режиме приоритет отдан извлечению хэшей и внешним GPU-инструментам.
- Настройки, результаты и словари теперь хранятся в пользовательской папке, а не рядом с исполняемым файлом.

</details>

## Русский

Bruteforcer - это десктопное GUI-приложение для восстановления забытого пароля от файла, которым вы владеете. Проект поддерживает три режима атаки, CPU и GPU backend, автоматическую работу со словарями и живую статистику в процессе подбора.

### Поддерживаемые форматы

| Категория | Форматы |
|---|---|
| Архивы | `ZIP`, `RAR`, `7Z` |
| Microsoft Office | `XLSX`, `XLS`, `XLSM`, `XLSB`, `DOCX`, `DOC`, `DOCM`, `PPTX`, `PPT`, `PPTM`, `ACCDB`, `MDB` |
| PDF | `PDF` |

### Режимы атаки

- **По словарю** - перебирает пароли из текстового словаря.
- **Brute-force** - генерирует комбинации по выбранному набору символов и диапазону длины.
- **По маске** - использует шаблоны в стиле Hashcat, например `?u?l?l?l?d?d`.

Поддерживаемые токены масок:

| Токен | Значение |
|---|---|
| `?l` | строчные `a-z` |
| `?u` | заглавные `A-Z` |
| `?d` | цифры `0-9` |
| `?s` | спецсимволы |
| `?a` | все печатные символы |
| `?h` | hex в нижнем регистре |
| `?H` | hex в верхнем регистре |

### Ключевые возможности

- **CPU и GPU backend**: CPU-режим встроен в приложение, GPU-режим подключается отдельно и ставится по запросу.
- **Автоустановка GPU runtime**: при первом включении GPU-режима приложение скачивает нужные компоненты в `~/Bruteforcer/lib/`.
- **Обнаружение GPU-устройств**: после установки backend приложение проверяет наличие совместимой видеокарты и позволяет выбрать устройство.
- **Точное описание защиты**: интерфейс показывает не просто "защищен", а конкретный тип защиты файла.
- **Живая статистика**: скорость, прошедшее время, ETA, текущий пароль и статус движка обновляются во время атаки.
- **Результаты**: найденные пароли попадают во вкладку результатов и могут автоматически сохраняться в `~/Bruteforcer/Results.txt`.
- **Экспорт**: результаты можно выгрузить в `TXT`, `CSV`, `JSON`, `DOC` или `PDF`.
- **Восстановление истории**: сохраненные записи можно повторно загрузить из `Results.txt`.
- **RU / EN интерфейс**: язык меняется прямо в приложении без перезапуска.
- **Словари**: встроенные словари из сборки копируются в пользовательскую папку, а дополнительные `.txt`-файлы подхватываются автоматически.

### Где хранятся данные

После первого запуска приложение создает пользовательскую папку:

```text
~/Bruteforcer/
├── Passwords/
├── Results.txt
├── settings.ini
├── Bruteforcer_links.txt
└── lib/
```

Это значит, что настройки, результаты, словари и GPU runtime живут отдельно от папки проекта и от `EXE`.

### Словари

- Дефолтный словарь `10k_most_common.txt` скачивается автоматически при необходимости.
- В репозитории уже присутствуют дополнительные словари, включая `dates.txt`, `digits.txt`, `Lizard-Squad.txt`, `milw0rm-dictionary.txt`.
- В папке `heavy/` находятся крупные словари `xato-net-10-million-passwords.txt` и `xato-net-10-million-passwords-1000000.txt`.
- Все пользовательские словари должны лежать в `~/Bruteforcer/Passwords/`.

### Зависимости

Минимальный запуск из исходников:

```bash
pip install PySide6 msoffcrypto-tool PyPDF2 rarfile py7zr pyzipper olefile
```

Дополнительно для GPU-режима приложение при необходимости автоматически скачивает внешние инструменты и Python-зависимости в пользовательскую папку.

> Для `RAR` в CPU-режиме может понадобиться установленный `unrar` в `PATH`.

### Запуск

```bash
python Bruteforcer.py
```

1. Нажмите **Обзор** и выберите защищенный файл.
2. Выберите режим атаки.
3. При необходимости переключите backend на `GPU`.
4. Настройте словарь, диапазон длины или маску.
5. Нажмите **Начать**.

### Сборка EXE

```bash
python build_exe.py
```

Скрипт соберет standalone `Bruteforcer.exe` через PyInstaller, добавит иконку, версию и включит доступные словари из папки `passwords/`.

### Структура проекта

```text
Bruteforcer.py    основной GUI, логика атак, настройки, экспорт результатов
Design.py         интерфейс, стили, тексты и локализация
gpu_backend.py    установка GPU runtime, извлечение хэшей, запуск Hashcat
build_exe.py      сборка standalone EXE через PyInstaller
passwords/        словари, включаемые в сборку
heavy/            крупные словари для dictionary-атак
dist/             готовая сборка после PyInstaller
```

### Важные детали реализации

- В CPU-режиме приложение специально оставляет часть логических ядер свободными для системы.
- Словари читаются через `latin-1` с fallback на `utf-8`, чтобы не терять байты в проблемных файлах.
- Для GPU-режима используются внешние инструменты, а не прямой перебор форматов внутри Python.
- Если GPU-режим не готов или не подходит для конкретной атаки, приложение умеет безопасно откатиться на CPU.

### Правовое уведомление

Инструмент предназначен только для восстановления доступа к собственным файлам или к файлам, на которые у вас есть явное разрешение. Несанкционированное использование против чужих данных может нарушать закон.

### 🟥 Важно ‼️

🟥 Данная программа рапространяется *ТОЛЬКО* здесь, если вы видите её на случайных сайтах, в видео на YouTube, а котором вам предлагают скачать её не из этогго репозитория, скорее всего это вирусная копия. Избегайте мошенников и `качайте программу исключительно отсюда`!

---

<a name="english"></a>

<img width="1205" height="785" alt="Bruteforcer screenshot" src="https://github.com/user-attachments/assets/65b422b2-1111-44b2-9dfb-4e70f4013e94" />

#

<details>
<summary><strong><img width="19" height="20" alt="277031mbmmfoabln" src="https://github.com/user-attachments/assets/6161bda3-fa90-40be-8e71-c077bf96af9d" /> Latest Update</strong></summary>

### Additions and changes

- Added a full optional **GPU backend** for ZIP, RAR, 7Z, PDF, and Microsoft Office targets.
- Integrated **Hashcat**, **John the Ripper**, `office2john.py`, `pdf2john.py`, `zip2john`, `rar2john`, and `7z2hashcat`.
- Added automatic backend installation into `~/Bruteforcer/lib/`, including Hashcat, John the Ripper, and 7-Zip runtime components.
- Added **CPU / GPU backend selection**, GPU device detection, and CPU fallback on GPU failure.
- Improved format support and protection reporting, including values such as `ZIP AES-256`, `RAR5`, `7Z AES-256`, `PDF encrypted, R=6, 256-bit`, and `Office Agile Encryption`.
- Added larger wordlists, user-level dictionary storage, result export, saved-result restore, and a more informative bilingual UI.
- Improved CPU scheduling, chunked workloads, real-time stats, process cleanup, logging, and standalone EXE building.

</details>

## English

Bruteforcer is a desktop GUI application for recovering forgotten passwords from protected files you own. It supports three attack modes, a built-in CPU engine, an optional GPU backend, automatic dictionary management, and live progress statistics.

### Supported formats

| Category | Formats |
|---|---|
| Archives | `ZIP`, `RAR`, `7Z` |
| Microsoft Office | `XLSX`, `XLS`, `XLSM`, `XLSB`, `DOCX`, `DOC`, `DOCM`, `PPTX`, `PPT`, `PPTM`, `ACCDB`, `MDB` |
| PDF | `PDF` |

### Attack modes

- **Dictionary** - tries passwords from a text wordlist.
- **Brute-force** - generates combinations from a selected charset and length range.
- **Mask** - uses Hashcat-style masks such as `?u?l?l?l?d?d`.

Supported mask tokens:

| Token | Meaning |
|---|---|
| `?l` | lowercase `a-z` |
| `?u` | uppercase `A-Z` |
| `?d` | digits `0-9` |
| `?s` | special characters |
| `?a` | all printable characters |
| `?h` | lowercase hex |
| `?H` | uppercase hex |

### Highlights

- **CPU and GPU backends**: CPU mode is built in, while GPU mode is optional and installed on demand.
- **Automatic GPU runtime setup**: required external components are downloaded into `~/Bruteforcer/lib/`.
- **GPU device detection**: the app probes compatible devices and lets you choose one.
- **Protection details**: the UI reports the detected protection type instead of a generic protected/not protected label.
- **Live statistics**: speed, elapsed time, ETA, current password, and engine status update while the attack is running.
- **Results management**: found passwords appear in the results tab and can be auto-saved to `~/Bruteforcer/Results.txt`.
- **Export support**: results can be exported to `TXT`, `CSV`, `JSON`, `DOC`, and `PDF`.
- **Restore support**: previously saved entries can be restored from `Results.txt`.
- **RU / EN UI**: switch language directly in the app without restarting.
- **Dictionary workflow**: bundled wordlists are copied to the user folder, and any extra `.txt` files are picked up automatically.

### Data storage

On first launch, the application creates:

```text
~/Bruteforcer/
├── Passwords/
├── Results.txt
├── settings.ini
├── Bruteforcer_links.txt
└── lib/
```

This keeps settings, results, wordlists, and GPU runtime files outside the project folder and outside the EXE location.

### Wordlists

- `10k_most_common.txt` is downloaded automatically when needed.
- The repository also includes extra bundled lists such as `dates.txt`, `digits.txt`, `Lizard-Squad.txt`, and `milw0rm-dictionary.txt`.
- Large wordlists live in `heavy/`, including `xato-net-10-million-passwords.txt` and `xato-net-10-million-passwords-1000000.txt`.
- User wordlists should be placed in `~/Bruteforcer/Passwords/`.

### Requirements

To run from source:

```bash
pip install PySide6 msoffcrypto-tool PyPDF2 rarfile py7zr pyzipper olefile
```

For GPU mode, the application can automatically download the required external tools and Python support packages into the user directory.

> `RAR` support in CPU mode may require `unrar` to be available in `PATH`.

### Running

```bash
python Bruteforcer.py
```

1. Click **Browse** and choose a protected file.
2. Select the attack mode.
3. Switch to `GPU` if needed.
4. Configure the wordlist, length range, or mask.
5. Press **Start**.

### Building EXE

```bash
python build_exe.py
```

This builds a standalone `Bruteforcer.exe` with PyInstaller, includes the icon, version metadata, and bundled wordlists from `passwords/`.

### Project structure

```text
Bruteforcer.py    main GUI, attack logic, settings, results export
Design.py         UI layout, styles, text resources, localization
gpu_backend.py    GPU runtime setup, hash extraction, Hashcat launch flow
build_exe.py      standalone EXE build script
passwords/        bundled wordlists included in builds
heavy/            large dictionary files for dictionary attacks
dist/             generated build output
```

### Implementation notes

- CPU mode intentionally keeps some logical CPUs free for system responsiveness.
- Wordlists are read using `latin-1` with `utf-8` fallback to avoid losing bytes in problematic files.
- GPU mode relies on external tools for hash extraction and cracking instead of direct Python-only validation.
- If GPU mode is unavailable or unsuitable for a target, the app can safely fall back to CPU mode.

### Legal notice

This tool is intended only for recovering access to files you own or are explicitly authorized to access. Unauthorized use against third-party data may be illegal.

### 🟥 Safety note

🟥 This program is distributed *ONLY* here, if you see it on random sites, in a YouTube video, and where you are offered to download it from a repository other than this one, it is most likely a viral copy. Avoid scammers and download the program exclusively from here!

---

<div align="center">

[Back to top / Наверх](#bruteforcer)

</div>
