# AGENT.md — Developer & AI Agent Operating Manual

## 1. Welcome & Mental Model

This repository is an interconnected, multi-tier school management and access control ecosystem. As an AI agent or human developer working here, your mental model must recognize that this is **not** a collection of isolated scripts, but a coordinated pipeline:

1. **Edge Hardware**: Physical ESP32 microcontrollers authenticate students via NFC at the school gate in $< 1\text{ ms}$ from onboard flash memory, operating independently of the internet.
2. **Administrative Hub**: Web dashboards (`escola-nfc-web`) running on local LAN or cloud ingest hardware access logs, manage student registrations, and sync records bidirectionally with the edge readers.
3. **Government Portal Automation**: Grade records and attendance matrices exported from the local system are injected in bulk into the official Bahia State education portal (**SIGEduc BA**), either via a desktop Playwright bot or a zero-dependency Chrome Extension.
4. **Pedagogical Frontends**: Interactive web applications demystify the electronics for students, parents, and educators during school science fairs.

---

## 2. Rules of Engagement for AI Agents

When interacting with or modifying this codebase, you **must** adhere strictly to the following rules:

### 2.1 The Minimal Change Principle
- Only edit the exact lines necessary to accomplish your task.
- Do **not** perform unsolicited refactoring, formatting overhaul, or library replacements ("while I'm here").
- Do **not** delete comments, docstrings, or architectural notes.
- Preserve existing casing, variable nomenclature, and Portuguese-language domain terminology (e.g., `turma`, `matricula`, `falta_vinculada`, `portaria`).

### 2.2 Preservation of Hardware & Electrical Safety
- **CRITICAL HARDWARE RULE**: On the YD-ESP32-S3 (N16R8), **never** allocate or connect GPIOs **35, 36, or 37**. These pins are internally bonded to the Octal PSRAM bus; pulling them externally causes CPU crashes and hardware memory corruption.
- Avoid attaching pull-ups, pull-downs, or heavy capacitive loads to strapping pins (**GPIO 0, 3, 45, 46**) during the first 50 ms after boot.
- The PN532 module requires **Switch 1 = ON, Switch 2 = OFF** for I2C operation (SDA on GPIO 8, SCL on GPIO 9).
- The onboard diagnostic WS2812B NeoPixel is permanently tied to **GPIO 48**.

### 2.3 Strict LGPD & Privacy Rules
- **No Real Student PII in Git**: Never commit spreadsheets, CSVs, or logs containing real student names, national IDs (CPF), student IDs (matrícula), phone numbers, or facial photos.
- All real data belongs exclusively in `.gitignore` patterns (`*.xlsx`, `*.csv`, `*.log`, `perfil_navegador/`).
- Use synthetic names (e.g., "Lucas Silva", "Mariana Souza") in tests and fixtures.

### 2.4 Integrity & Verification Mandate
- **Never cheat or mock test results**: Run genuine test commands via the terminal.
- Verify existing tests before and after any modification:
  - `python test_scraper_unit.py`
  - `node extensao-notas/tests/test_extension.js`
  - `npm --prefix escola-nfc-web test`
  - `node feira-exposicao/tests/run-tests.js`
- All 4 test suites must exit with code 0 (`OK`).

---

## 3. Subsystem Runbooks & Operating Guidelines

### 3.1 Python Desktop Automation Suite (`sigeduc-auto` / Root)

#### Core Engine Clarification (Playwright vs Selenium)
> **CRITICAL ARCHITECTURAL FACT**: The Python automation in this repository uses **Playwright (`playwright.sync_api`)**, NOT Selenium. There are zero Selenium or WebDriver dependencies.

#### Architecture & Key Files
- `sigeduc_core.py`: Shared business logic, Unicode NFKD normalization, Brazilian Portuguese phonetic canonicalization, Excel reader (`openpyxl`), Playwright persistent context launcher, JSF tab navigation, and password modal auto-filling.
- `sigeduc_gui.py`: Desktop graphical application built with `customtkinter` and `tkcalendar`. Runs automation routines inside non-blocking `threading.Thread` workers.
- `sigeduc_scraper.py`: Academic crawler extracting class rosters, evaluation columns, and attendance calendars from SIGEduc into multi-tab formatted Excel workbooks (`relatorio_academico_sigeduc.xlsx`).
- `lancar_frequencia.py`: Terminal CLI loop featuring 5 operation modes (100% Presentes, Excel with Markbox, TXT List, Partial/Geminada, Manual).
- `test_scraper_unit.py`: Unit test suite verifying shift extraction, tab naming constraints (31 characters), and panel qualifiers.
- `sigeduc_gui.spec`: PyInstaller configuration packaging the GUI into a single Windows `.exe`.

#### Environment Setup
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

#### How to Run
```powershell
# Run the Desktop GUI Application:
python sigeduc_gui.py

# Run the Interactive Terminal CLI:
python lancar_frequencia.py

# Run the Academic Scraper:
python sigeduc_scraper.py

# Run the Unit Test Suite:
python test_scraper_unit.py
```

#### Packaging into Standalone Windows Executable
```powershell
pyinstaller sigeduc_gui.spec
# Output will be generated at: dist/sigeduc_gui.exe
```

#### Operational Guidelines for Playwright on SIGEduc
1. **Persistent Browser Session (`perfil_navegador/`)**: Always launch via `chromium.launch_persistent_context(user_data_dir=str(PERFIL_NAVEGADOR), headless=False)`. This preserves teacher login cookies and eliminates repeating 2FA/login at every run.
2. **Login Pause & Window Focus**: When the session expires, the automation detects the login page, pauses, and uses `ctypes.windll.user32.SetForegroundWindow` to bring Chrome to the front so the teacher can authenticate.
3. **JSF Dialog Interception**: Listen to `page.on("dialog", lambda dialog: dialog.accept())` to automatically dismiss native confirmation and session expiration alerts.
4. **Falta Vinculada (FV)**: Students without evaluations must have their respective `:falta` checkboxes ticked to satisfy SIGEduc's closing validation.

---

### 3.2 Chromium Browser Extension (`extensao-notas/`)

#### Architecture & Key Files
- `manifest.json`: Manifest V3 descriptor registering permissions (`activeTab`, `tabs`, `storage`, `scripting`) and host permissions for `*://*.educacao.ba.gov.br/*`.
- `content/page-bridge.js`: Injected into `world: "MAIN"` at `run_at: "document_start"`. Replaces `window.confirm` and `window.alert` to automatically accept RichFaces batch confirmation dialogs.
- `content/content.js`: Main content script (2,333 lines) running in the `ISOLATED` world. Manages DOM events, AJAX recalculation delays, and Falta Vinculada checkboxes.
- `lib/nomes.js`: Phonetic canonicalization engine (`Z` $\rightarrow$ `S`, `Y` $\rightarrow$ `I`, `K` $\rightarrow$ `C`, silent `H` stripping) and strict anti-homonym logic (blocks matches if middle surnames conflict).
- `lib/excel.js`: Spreadsheet extractor utilizing vendored `vendor/xlsx.full.min.js` (SheetJS). Dynamically searches up to row 25 for header rows and skips non-evaluative columns (`Faltas`, `Recuperação`).
- `popup/`: Modern dark-theme extension UI (`popup.html`, `popup.js`, `popup.css`).

#### How to Test & Package
```powershell
# Run automated extension test suite (Node.js mock DOM environment):
node extensao-notas/tests/test_extension.js

# Build zip distribution archives in dist/:
node extensao-notas/scripts/empacotar.js
```

#### How to Install in Browser
1. Open Google Chrome, Brave, Edge, or Opera and navigate to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in upper right corner).
3. Click **Load unpacked** and select the folder:
   `c:\Users\devma\.gemini\antigravity\scratch\sigeduc-auto\extensao-notas`
4. Alternatively, on Windows, run the one-click helper script:
   `.\extensao-notas\instalar_extensao.bat`

#### DOM Timing Guidelines on RichFaces
- RichFaces triggers an AJAX recalculation cycle on input `change` and `blur`.
- Pacing is mandatory: insert a delay between 40ms and 120ms between student rows to allow RichFaces to update intermediate state.
- Always perform a post-entry audit by re-reading input values from the Live DOM to verify that RichFaces AJAX hasn't reverted fields.

---

### 3.3 School NFC Web Dashboard (`escola-nfc-web/`)

#### Architecture & Key Files
- `index.html`: Single Page Application (SPA) containing Portaria (Kiosk), Secretaria (Registry), Histórico (Logs), Usuários (RBAC), and Configurações (Settings).
- `js/services/supabase.js`: Supabase JS client integration, authentication, RBAC authorization RPCs, Realtime channels, and storage uploads.
- `js/services/esp32.js`: REST client for local ESP32 communication (`/api/status`, `/api/ultimo`, `/api/sincronizar_todos`, `/api/remover_aluno`) with exponential backoff and `AbortController` timeouts.
- `js/app.js`: Central coordinator, webcam handler (with fallback to native camera), and offline event queue.
- `supabase_setup.sql`: Complete, idempotent SQL script provisioning PostgreSQL schemas, tables (`perfis_usuarios`, `alunos`, `historico_acessos`), RLS policies, and triggers.

#### Environment Configuration & Build
```powershell
cd c:\Users\devma\.gemini\antigravity\scratch\sigeduc-auto\escola-nfc-web

# Install dependencies (only dev dependencies for tests)
npm install

# Run the 47 unit tests
npm test

# Check JavaScript module syntax
npm run check

# Generate config.js from environment variables:
npm run build
```

#### Running Locally
```powershell
# Start local static web server on port 5500:
npm run dev
# Open browser at: http://localhost:5500

# Start mock ESP32 hardware simulator on port 8787:
npm run mock
```

#### Database Setup & RBAC Rules
1. Execute `supabase_setup.sql` in the Supabase SQL Editor.
2. The trigger `public.lidar_novo_usuario()` enforces:
   - The first user ever created in the database becomes an active `admin`.
   - Every subsequent user registers with role `portaria` and `ativo = false` until approved by an administrator.
3. To initialize the admin account via backend script:
   ```powershell
   node scripts/bootstrap-admin.mjs admin@escola.ba.gov.br SenhaForte123!
   ```

---

### 3.4 Standalone Offline Laboratory (`escola-nfc-web-offline/`)

#### Purpose & Architecture
For schools in rural zones or with unreliable internet, this module packages the entire Supabase stack (PostgreSQL 15, Kong, GoTrue, PostgREST, Studio) inside local Docker containers on the gatehouse PC.

#### Operational Runbook
```powershell
cd c:\Users\devma\.gemini\antigravity\scratch\sigeduc-auto\escola-nfc-web-offline

# Open the interactive Windows TUI control menu:
.\lab.cmd
# or
powershell -ExecutionPolicy Bypass -File .\lab-menu.ps1

# Start the Docker container stack:
.\lab-ligar.cmd

# Inspect service health:
powershell -ExecutionPolicy Bypass -File .\lab-estado.ps1
```

#### Network Ports Reference
- Port `5500`: Local Web Kiosk (`index.html`)
- Port `54321`: Kong API Gateway (Supabase API entry point)
- Port `54322`: PostgreSQL Database
- Port `54323`: Supabase Studio Web Console

---

### 3.5 Embedded Firmware (`esp32-nfc-acesso/` & `esp32s3-nfc-acesso/`)

#### Hardware Requirements & Target Selection
- **Baseline Firmware (`esp32-nfc-acesso/`)**: Standard ESP32 or ESP32-C3 Super Mini. Uses NVS flash (50-card ceiling).
- **Production Firmware (`esp32s3-nfc-acesso/`)**: **YD-ESP32-S3 (N16R8)** featuring 16 MB Flash and 8 MB Octal PSRAM.

#### Arduino IDE / PlatformIO Configuration for YD-ESP32-S3
- **Board**: `ESP32S3 Dev Module`
- **Flash Size**: `16MB (128Mb)`
- **Partition Scheme**: `16M Flash (3MB App/9.9MB FATFS)` or `app3M_fat9M_16MB`
- **PSRAM**: `OPI PSRAM` (Octal)
- **Upload Speed**: `921600`
- **USB Mode**: `Hardware CDC and JTAG`
- **USB CDC On Boot**: `Enabled`

#### Wiring Pinout
| Component | ESP32-S3 GPIO | Expansion Shield Color Row | Notes |
|---|---|---|---|
| PN532 SDA | **GPIO 8** | Yellow (Signal) | DIP Switch 1=ON, 2=OFF |
| PN532 SCL | **GPIO 9** | Yellow (Signal) | DIP Switch 1=ON, 2=OFF |
| PN532 IRQ | **GPIO 2** | Yellow (Signal) | Virtual IRQ |
| PN532 RESET | **GPIO 5** | Yellow (Signal) | Software Reset |
| WS2812B RGB | **GPIO 48** | Onboard PCB | NeoPixel status indicator |
| Relay / Solenoid | **GPIO 4 or 6** | Yellow (Signal) | Active HIGH (3000ms pulse) |
| **DO NOT USE** | **GPIO 35, 36, 37**| — | **Octal PSRAM internal bus** |

#### WS2812B LED Color Code Reference
- **Cyan Breathing**: Standby / Idle (Ready for card).
- **Fixed Green (2s)**: Access Granted (Authorized student).
- **Fixed Red (2s)**: Access Denied (Blocked or unregistered).
- **Amber Strobe (Rapid Flashing)**: PN532 Hardware Error (I2C disconnected).
- **Yellow Pulsing**: Wi-Fi Disconnected / Reconnecting.
- **Fixed Purple**: Access Point Mode (`ControleAcesso-S3`).
- **Blue Flashing**: Wi-Fi Connection in Progress.

#### Remote Maintenance Endpoints
- Web Serial Console: `http://<esp32-ip>/console`
- Web OTA Firmware Update: `http://<esp32-ip>/ota`
- Wi-Fi Configuration Portal: `http://<esp32-ip>/wifi`

---

### 3.6 Exhibition & Pedagogical Portals (`apresentacao-nfc/` & `feira-exposicao/`)

#### Presentation Deck (`apresentacao-nfc/`)
- Single-page application designed for classroom presentations, parents, and school boards.
- Features real-time turnstile simulation with Web Audio API sound effects and animated 3-wire G-V-S diagrams.
- Launch: Open `apresentacao-nfc/index.html` in any modern web browser.

#### Science Fair Portal (`feira-exposicao/`)
- 100% offline-first web portal for school science exhibitions (Project ProSUB · Thauan).
- 5 Physical Stations in "U"-shaped visitor circuit:
  - Estação 1: "O Toque Mágico" (Physical ESP32-S3 + PN532 hardware).
  - Estação 2: "O Cérebro" (ESP32-S3 microcontroller & G-V-S expansion).
  - Estação 3: "O Semáforo Falante" (WS2812B NeoPixel state behaviors).
  - Estação 4: "A Caixa dos Sentidos" (Physical display of 37 sensor modules).
  - Estação 5: "A Memória que Não Esquece" (Tablet mirroring Estação 1 web panel over LAN + LGPD privacy protocol).
- Running Tests:
  ```powershell
  # Unit tests (data integrity, logic, contrast):
  node feira-exposicao/tests/run-tests.js

  # End-to-end tests (requires Chrome):
  node feira-exposicao/tests/run-e2e.js
  ```

---

## 4. Troubleshooting & Common Pitfalls

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| ESP32-S3 boots in crash loop (`TG1WDT_SYS_RESET` or Memory Corruption). | Jumpers connected to GPIO 35, 36, or 37. | Disconnect all external wiring from GPIOs 35, 36, and 37 (Octal PSRAM bus). |
| PN532 reports "Não foi possível encontrar o PN532". | DIP switch set incorrectly or loose I2C wires. | Verify DIP Switch 1=ON, 2=OFF. Confirm SDA is on GPIO 8 and SCL is on GPIO 9. |
| ESP32 cannot connect to school Wi-Fi network. | Network is 5 GHz or requires 802.1X enterprise login. | ESP32-S3 supports **only 2.4 GHz 802.11 b/g/n** with WPA2-Personal. Connect to a 2.4 GHz SSID. |
| Playwright fails on SIGEduc login. | Session cookies expired and Chrome window was not visible. | Ensure `headless=False` is set. The script will bring the browser to the front for manual login. |
| RichFaces drops or reverts entered grades. | Keystrokes sent too rapidly without AJAX wait states. | Ensure pacing micro-delays (40ms - 120ms) are active in `content.js` or `sigeduc_core.py`. |
| Extension popup reports "Aba desconectada". | SIGEduc tab was reloaded or closed. | Navigate back to the SIGEduc grade page; `popup.js` will auto-reinject scripts via `chrome.scripting`. |
| Student photo upload fails in `escola-nfc-web`. | Supabase Storage bucket `fotos-alunos` not created or RLS blocked. | Verify `fotos-alunos` bucket exists and RLS allows public/authenticated read and write. |

---

## 5. Verification Checklist for AI Agents

Before submitting changes to this repository, execute and document this checklist:

- [ ] Run `python test_scraper_unit.py` $\rightarrow$ 4 passed, 0 failed.
- [ ] Run `node extensao-notas/tests/test_extension.js` $\rightarrow$ 22 passed, 100% success.
- [ ] Run `npm --prefix escola-nfc-web test` $\rightarrow$ 47 passed, 0 failed.
- [ ] Run `node feira-exposicao/tests/run-tests.js` $\rightarrow$ static checks passed.
- [ ] Verify no student PII or credentials have been committed.
- [ ] Verify no source code files were inadvertently deleted or renamed.
