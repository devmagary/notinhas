# PROJECT.md — Monorepo Architecture, Contracts & Code Layout

## 1. Monorepo Overview & Project Index

This repository contains an end-to-end, multi-tier school management, physical access control, and academic portal automation ecosystem. Designed primarily for Brazilian public schools (specifically Bahia State education network — SEC/BA), the system bridges physical hardware turnstiles at school gates with the official state education portal (**SIGEduc BA**), providing automated grade entry, daily attendance tracking, local and cloud database synchronization, offline resilience, and interactive pedagogical exhibitions.

### Subsystem Directory Index

| Subsystem / Path | Primary Technology | Architecture Role | Target Deployment |
|---|---|---|---|
| **`sigeduc-auto`** (Root Python Scripts) | Python 3.10+, Playwright, CustomTkinter, openpyxl, pandas | Desktop automation & scraping for Bahia State SIGEduc portal (JSF/RichFaces). | Local Windows PC (Standalone `.exe` via PyInstaller or Python CLI). |
| **`sigeduc-auto/`** (Subfolder) | Python 3.10+, Playwright | Historical/legacy standalone subproject directory with shared core engine. | Preserved subfolder containing original Python package. |
| **`extensao-notas/`** | JavaScript (ES2022), Chromium Manifest V3, SheetJS (xlsx) | Zero-dependency browser extension injecting directly into SIGEduc BA web forms. | Google Chrome, MS Edge, Brave, Opera (Unpacked or `.crx`). |
| **`escola-nfc-web/`** | Vanilla ES Modules, CSS3 (Tailwind/Custom Properties), Supabase Client | Central school management dashboard, gatehouse kiosk, card provisioning, and ESP32 polling. | Cloud hosting (Vercel) + Supabase Cloud, or local LAN server (Node.js). |
| **`escola-nfc-web-offline/`** | Docker, Docker Compose, Supabase CLI, PowerShell/CMD TUI | Standalone offline containerized lab stack (Kong, GoTrue, PostgREST, PostgreSQL, Studio). | School gatehouse on-premise laptop/server with no internet. |
| **`esp32-nfc-acesso/`** | C++ (Arduino IDE), Adafruit_PN532, NVS (Preferences), WebServer | Baseline single-core NFC turnstile firmware with embedded web console (50-card limit). | Standard ESP32 / ESP32-C3 Super Mini + PN532 I2C. |
| **`esp32s3-nfc-acesso/`** | C++ (Arduino IDE / ESP-IDF), FreeRTOS Dual-Core, LittleFS/FFat, NeoPixel | Production-grade NFC turnstile firmware with JSON flash persistence, captive portal, and REST sync. | YD-ESP32-S3 (N16R8: 16 MB Flash, 8 MB PSRAM) + PN532 I2C + WS2812B. |
| **`teste-compila-s3/`** | C++ (Arduino Sketch) | Minimal compilation smoke test sketch for ESP32-S3 library verification. | Development environment validation. |
| **`apresentacao-nfc/`** | HTML5, Tailwind CSS, Web Audio API, SVG Animations | Interactive single-page presentation deck & simulated school turnstile for stakeholders. | Modern browser (`file://`, GitHub Pages, or local web server). |
| **`feira-exposicao/`** | Vanilla HTML5/CSS/JS (Zero build tools), Node.js (test runner) | Offline-first interactive science fair portal (5 stations, 37 sensors, 5 demos, LGPD closure). | Offline browser (`file://`), Vercel, or local kiosk tablet. |

---

## 2. High-Level Architecture & Tiered Structure

The ecosystem is architecturally decoupled into four distinct tiers:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             TIER 1: PHYSICAL ACCESS                              │
│                                                                                  │
│   [Student NFC Card / Keychain]                                                  │
│                 │                                                                │
│                 ▼                                                                │
│   [PN532 RFID Module] (I2C: SDA=GPIO 8, SCL=GPIO 9)                              │
│                 │                                                                │
│                 ▼                                                                │
│   [ESP32-S3 N16R8 Dual-Core Firmware]                                            │
│   ├── Core 0: Continuous NFC Polling (50ms) & I2C Heartbeat (2.5s)               │
│   │           Verification in Local Flash: `/cartoes.json` (<1ms latency)        │
│   │           Turnstile Solenoid Trigger (GPIO 4/6) + NeoPixel RGB (GPIO 48)     │
│   └── Core 1: REST WebServer (Port 80) + DNS Captive Portal + Web OTA / Console  │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │ Local LAN HTTP REST (Polling & Sync)
                          │ Endpoints: GET /api/ultimo, POST /api/sincronizar_todos
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         TIER 2: ADMINISTRATIVE WEB HUB                           │
│                                                                                  │
│   [escola-nfc-web] (Vanilla ES SPA)                                              │
│   ├── Gatehouse Kiosk: Real-time student identification & photo display          │
│   ├── Secretary Portal: Student registration, webcam capture, NFC UID pairing     │
│   ├── Sync Service: Bi-directional replication between Supabase and ESP32 Flash │
│   └── Offline Queue: LocalStorage buffer (200 events) if network disconnects     │
│                 ▲                                                                │
│                 │ Realtime Subscriptions & PostgREST RPCs                        │
│                 ▼                                                                │
│   [Database Layer: Supabase (PostgreSQL 15)]                                     │
│   ├── Cloud: Supabase Managed Cloud (Auth, Storage `fotos-alunos`, Realtime)     │
│   └── Offline: [escola-nfc-web-offline] Local Docker Stack (Kong :54321, PG :54322)│
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │ Data Export: Student Rosters & Attendance
                          │ Formats: Excel (.xlsx), CSV (UTF-8 with BOM)
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      TIER 3: GOVERNMENT PORTAL AUTOMATION                        │
│                                                                                  │
│   Target: Bahia State Education Portal (SIGEduc BA) — JSF / RichFaces            │
│                                                                                  │
│   Path A: Desktop Automation [sigeduc-auto / sigeduc_gui.py]                      │
│   ├── Python 3 + Playwright Chromium (Persistent Context `perfil_navegador`)     │
│   ├── Phonetic & Unicode name matching engine (`sigeduc_core.py`)                │
│   ├── Unit tab navigation, password modal re-authentication, FV assignment       │
│   └── Web scraper for full academic report generation (`sigeduc_scraper.py`)     │
│                                                                                  │
│   Path B: Browser Extension [extensao-notas]                                     │
│   ├── Manifest V3: Chromium isolated content script + MAIN world `page-bridge.js`│
│   ├── Zero-dependency SheetJS Excel parsing directly in teacher's browser        │
│   ├── DOM mutation listener, RichFaces Ajax recalculation pacing (40-120ms)      │
│   └── Batch monthly attendance calendar automation via sessionStorage            │
└──────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     TIER 4: PEDAGOGICAL & EXHIBITION SYSTEMS                     │
│                                                                                  │
│   [apresentacao-nfc]                                                             │
│   └── High-level presentation deck with simulated turnstile & G-V-S animations.  │
│   [feira-exposicao]                                                              │
│   └── Science Fair Web Portal: 5 physical stations circuit, 37 sensors catalog   │
│       with photos & SVG schematics, 5 interactive demos, LGPD data deletion.     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Feature Inventory

### 3.1 Python Desktop Automation Suite (`sigeduc-auto` / Root)
- **Engine Technology**: Pure **Playwright (`playwright.sync_api`)**, operating over a persistent Chromium user data profile (`perfil_navegador`). No Selenium or WebDriver dependencies exist in the repository.
- **`sigeduc_core.py`**:
  - Unicode NFKD normalization and Brazilian Portuguese phonetic canonicalization (handles spelling variations, silent 'H', duplicated consonants, and phonetic equivalences like `Z` $\rightarrow$ `S`, `Y` $\rightarrow$ `I`, `K` $\rightarrow$ `C`).
  - Anti-homonym protection: Enforces matching of first name and last surname; blocks false matches when middle surnames conflict.
  - Excel `.xlsx` workbook parsing (`openpyxl`) and CSV/TXT auto-encoding detection.
  - Multi-unit JSF tab switching (`1ª a 4ª Unidade`) with explicit RichFaces AJAX completion wait states.
  - Password modal re-authentication (`preencher_senha_e_gravar`) required by recent SIGEduc BA security updates.
  - Falta Vinculada (FV) detection and batch checkbox marking for non-evaluated students.
- **`sigeduc_gui.py`**:
  - Built with `customtkinter` (dark/light themes) and `tkcalendar`.
  - Non-blocking background thread execution (`threading.Thread`) for all browser automation loops.
  - Real-time GUI log output redirector, file picker, and interactive date picker.
- **`sigeduc_scraper.py`**:
  - Full academic extraction from SIGEduc BA Digital Class Diary.
  - Maps assigned classes, extracts partial grades, evaluation titles, and weights across all 4 bimesters.
  - Generates multi-tab formatted Excel workbooks (`relatorio_academico_sigeduc.xlsx`) with 31-character tab name truncation and illegal character sanitization.
- **`lancar_frequencia.py`**:
  - Headless/CLI interactive terminal loop for attendance and grade injection.
  - Features 5 operation modes: 100% Presentes (fileless), Excel with Markbox, TXT List, Partial/Geminada, and Manual Input.
- **`sigeduc_gui.spec` & `dist/sigeduc_gui.exe`**:
  - PyInstaller single-file windowed binary distribution bundling `icon.ico`.

### 3.2 Chromium Browser Extension (`extensao-notas/`)
- **Manifest V3 Architecture**:
  - Content script isolation: `content/content.js` and `lib/nomes.js` run in isolated world.
  - Main World injection: `content/page-bridge.js` runs in `world: "MAIN"` at `run_at: "document_start"` to intercept and auto-confirm `window.confirm` and `window.alert` native modals rendered by RichFaces.
  - Dynamic re-injection: `popup.js` detects disconnected tabs and re-injects content scripts on the fly via `chrome.scripting.executeScript`.
- **Excel & Grade Processing (`lib/excel.js`)**:
  - Bundles standalone `vendor/xlsx.full.min.js` (SheetJS) for 100% local, client-side execution (LGPD compliant).
  - Dynamic header row scanning across the first 25 rows to bypass complex school report header banners.
  - Skips non-evaluative intermediate columns (e.g., `Faltas`, `Recuperação`).
  - Template generation: Generates downloadable blank `.xlsx` templates with native `=SUM(...)` formulas.
- **DOM Automation (`content/content.js`)**:
  - Injects into RichFaces tables (`formulario:result`, `formulario:resultj_id_1`, etc.).
  - Configurable pacing (40ms to 120ms micro-delays) to prevent overwhelming RichFaces AJAX queues.
  - Post-submission live DOM reconciliation auditing.
  - Monthly calendar automated batch traversal via `sessionStorage` state persistence (`"sgn_lote_frequencia"`).

### 3.3 School NFC Web Dashboard (`escola-nfc-web/`)
- **Technology Stack**: Modern Vanilla JavaScript (ES Modules), HTML5, CSS3 with responsive Grid/Flexbox, native `@supabase/supabase-js`. Zero runtime compile-time bundlers required.
- **SPA Views**:
  - *Portaria (Gatehouse)*: Live monitoring kiosk with audio feedback, student avatar, status badge, and WhatsApp notification shortcuts.
  - *Secretaria (Registry)*: Student CRUD, camera capture (WebRTC webcam with fallback to native OS camera via `capture="environment"`), NFC UID pairing.
  - *Histórico (Access Logs)*: Filterable access audit log connected to Supabase Realtime channel.
  - *Usuários (User Management)*: Role-based user admin with approval workflows.
  - *Configurações (Settings)*: Local ESP32 IP configuration, connection health ping, batch sync triggers.
- **Hardware Integration (`js/services/esp32.js`)**:
  - Periodic polling of `/api/ultimo` with exponential backoff and timeout handling via `AbortController`.
  - Batch synchronization pushing cloud student rosters to ESP32 Flash memory (`/api/sincronizar_todos`).
- **Resilience Engine**:
  - Offline local storage event queue buffering up to 200 access logs when network is lost, flushing automatically upon reconnection.

### 3.4 Offline Laboratory Stack (`escola-nfc-web-offline/`)
- **Deployment Model**: Git worktree (`lab/offline`) configured for containerized execution via Docker Desktop / Docker Compose.
- **Services Bundled**:
  - Kong API Gateway (`:54321`)
  - GoTrue Auth Service
  - PostgREST REST API
  - PostgreSQL 15 (`:54322`)
  - Supabase Studio Web UI (`:54323`)
  - Local static web server (`:5500`)
- **Automation Scripts**:
  - `lab-setup.mjs`: Automatic LAN IP discovery and configuration file updater (`.env.local`, `config.toml`).
  - `lab.cmd` / `lab-menu.ps1` / `lab-estado.ps1`: Interactive terminal UI for starting, inspecting, and stopping the container suite.

### 3.5 Embedded Firmware (`esp32-nfc-acesso/` & `esp32s3-nfc-acesso/`)
- **Baseline Firmware (`esp32-nfc-acesso/`)**:
  - Target: Standard ESP32 / ESP32-C3 Super Mini.
  - Storage: NVS (`Preferences.h`) with static array limit of 50 cards (`MAX_CARTOES`).
  - Web UI: Embedded dark-mode SPA served directly from flash memory (`PROGMEM` in `pagina_web.h`).
- **Production Firmware (`esp32s3-nfc-acesso/`)**:
  - Target: **YD-ESP32-S3 (N16R8)** (16 MB Flash, 8 MB Octal PSRAM).
  - Multi-Core FreeRTOS:
    - *Core 0 (`tarefaNFC`)*: Dedicated continuous tag polling (50ms timeout) and 2.5s I2C bus heartbeat. Local decision latency < 1ms.
    - *Core 1 (`setup`/`loop`)*: WebServer (port 80), captive portal DNS server, WS2812B RGB NeoPixel diagnostics, and Web OTA.
    - Synchronization: `xSemaphoreCreateMutex()` (`travaDados`).
  - Storage: Auto-detection and mounting of `LittleFS` or `FFat` (`/cartoes.json` with unlimited capacity, `/historico.json` with 50 persistent logs).
  - Diagnostic LED: WS2812B on GPIO 48 with 6-state color machine (Cyan breathing, Green granted, Red denied, Amber strobe for I2C disconnect, Yellow pulse for Wi-Fi reconnect, Purple fixed for AP mode, Blue flashing for config).
  - Wi-Fi Manager & Captive Portal: Serves `pagina_wifi.h` on `/wifi`, performs asynchronous 2.4 GHz network scans, persists credentials in NVS namespace `"acesso_nfc_wifi"`, and captures OS captive portal probes.
  - Remote Maintenance: Web Serial Console (`/console`) and Web OTA firmware updater (`/ota`) via Espressif's `Update.h`.

### 3.6 Exhibition & Pedagogical Portals (`apresentacao-nfc/` & `feira-exposicao/`)
- **`apresentacao-nfc/`**:
  - Single-page interactive slide deck (`index.html`) using Tailwind CSS and Web Audio API tone synthesis.
  - Interactive SVG turnstile simulator with animated rotor arms and card tap simulation.
  - Animated 3-wire G-V-S bus explanation with live pulse trigger.
  - 5 Senses interactive laboratory covering light (LDR), sound (microphone), touch (knock/tilt), magnetism (Reed/Hall), and climate (flame/PTC/DHT11).
- **`feira-exposicao/`**:
  - Complete, zero-dependency offline science fair application (Project ProSUB · Thauan).
  - Structured into 5 physical stations arranged in a "U"-shaped visitor circuit:
    - *Estação 1 ("O Toque Mágico")*: Physical ESP32-S3 + PN532 hardware kit.
    - *Estação 2 ("O Cérebro")*: ESP32-S3 microcontroller and G-V-S expansion shield.
    - *Estação 3 ("O Semáforo Falante")*: WS2812B NeoPixel state behaviors.
    - *Estação 4 ("A Caixa dos Sentidos")*: Physical exhibition of 37 sensor modules.
    - *Estação 5 ("A Memória que Não Esquece")*: Tablet mirroring the live web panel of Estação 1's ESP32-S3 over LAN, highlighting offline flash resilience and closing with LGPD student data privacy guarantees (permanent record erasure upon graduation).
  - Comprehensive 37-sensor catalog with 111 real-world use cases, dual reading levels (Simple vs Technical Mode), and 5 interactive demos.

---

## 4. Module Boundaries & Technology Matrix

```
┌─────────────────────────┬──────────────────┬───────────────────────┬─────────────────────────┐
│ Module / Subsystem      │ Language / Stack │ Primary Dependencies  │ Persistence Layer       │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ Root Python Automation  │ Python 3.10+     │ playwright, openpyxl, │ Chromium User Profile   │
│                         │                  │ customtkinter, pandas │ (`perfil_navegador/`)   │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `extensao-notas/`       │ JavaScript (ESM) │ SheetJS (vendored),   │ `chrome.storage.local`, │
│                         │ Manifest V3      │ Chromium Extension APIs│ `sessionStorage`        │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `escola-nfc-web/`       │ Vanilla JS (ESM) │ @supabase/supabase-js │ Supabase PostgreSQL +   │
│                         │ HTML5, CSS3      │ (local vendored ESM)  │ Browser `localStorage`  │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `escola-nfc-web-offline`│ Docker Compose   │ Supabase CLI, Kong,   │ PostgreSQL 15 Data      │
│                         │ PowerShell / CMD │ PostgREST, GoTrue     │ Volume (Docker host)    │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `esp32-nfc-acesso/`     │ C++ (Arduino)    │ Adafruit_PN532,       │ NVS Flash (`Preferences`)│
│                         │                  │ WebServer, WiFi       │ (Max 50 cards)          │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `esp32s3-nfc-acesso/`   │ C++ (Arduino)    │ Adafruit_PN532,       │ LittleFS / FFat Flash   │
│                         │ FreeRTOS Dual    │ Adafruit_NeoPixel     │ (`/cartoes.json`)       │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `apresentacao-nfc/`     │ HTML5 / CSS3 / JS│ Tailwind (CDN),       │ None (Stateless)        │
│                         │ Web Audio API    │ Space Grotesk Font    │                         │
├─────────────────────────┼──────────────────┼───────────────────────┼─────────────────────────┤
│ `feira-exposicao/`      │ Vanilla JS / SVG │ None (Zero external   │ Browser `localStorage`  │
│                         │ Node.js (tests)  │ dependencies/build)   │ (`feira:v1:*`)          │
└─────────────────────────┴──────────────────┴───────────────────────┴─────────────────────────┘
```

---

## 5. Interface Contracts & Protocol Specifications

### 5.1 ESP32-S3 Hardware Pinout & Bus Constraints

| Function / Component | GPIO Allocation | Bus / Mode | Critical Hardware Restrictions |
|---|---|---|---|
| **PN532 I2C SDA** | **GPIO 8** | I2C Data | Connects to Yellow pin row on expansion shield. |
| **PN532 I2C SCL** | **GPIO 9** | I2C Clock | Connects to Yellow pin row on expansion shield. |
| **PN532 IRQ** | **GPIO 2** | Virtual / Lib | Reserved in Adafruit library constructor. |
| **PN532 RESET** | **GPIO 5** | Digital Output | Allocated on GPIO 5 to prevent boot strapping conflicts. |
| **PN532 DIP Switches** | — | Hardware Pins | **Switch 1 = ON**, **Switch 2 = OFF** (Enables I2C mode). |
| **WS2812B NeoPixel** | **GPIO 48** | Single-wire Data | Internal on YD-ESP32-S3 PCB (45/255 brightness). |
| **Turnstile Solenoid**| **GPIO 4 or 6** | Digital Output | Active HIGH pulse (3000ms duration). Relay isolation required. |
| **Forbidden Pins** | **GPIO 35, 36, 37** | **Octal PSRAM** | **STRICTLY FORBIDDEN.** Internally connected to 8 MB Octal PSRAM. External connections crash MCU. |
| **Boot Strapping Pins**| **GPIO 0, 3, 45, 46** | Strapping | Avoid external pull-ups/pull-downs during 50ms boot window. |
| **Serial / Programming**| **GPIO 43 (TX), 44 (RX)**| UART | Reserved for USB CDC / Serial programming and console. |

### 5.2 ESP32 REST API Specification

All REST endpoints implement standard HTTP verbs, return `application/json`, and include CORS headers (`Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`).

#### Endpoints:
- `GET /api/status`
  - Response: `{"modo":"STA","ssid":"Escola-WiFi","ip":"192.168.1.105","rssi":-62,"nfc":true,"cartoes":412,"max":-1,"uptime":34210}`
- `GET /api/ultimo`
  - Response: `{"seq":14,"uid":"2C:9D:7E:8E","nome":"Lucas Silva","cadastrado":true,"autorizado":true,"ha":2}`
- `GET /api/cartoes`
  - Response: `[{"uid":"2C:9D:7E:8E","nome":"Lucas Silva","ativo":true}, ...]`
- `POST /api/sincronizar_aluno`
  - Payload: `{"uid":"2C9D7E8E","nome":"Lucas Silva","ativo":true}`
  - Response (200): `{"sucesso":true,"mensagem":"Cartão atualizado com sucesso"}`
- `POST /api/sincronizar_todos`
  - Payload: `[{"uid":"2C9D7E8E","nome":"Lucas Silva","ativo":true}, ...]`
  - Response (200): `{"sucesso":true,"total":412}`
- `POST /api/remover_aluno`
  - Payload: `{"uid":"2C9D7E8E"}`
  - Response (200): `{"sucesso":true}`
- `GET /api/wifi/scan`
  - Response: `[{"ssid":"Escola_2.4G","rssi":-55,"canal":6,"seguranca":"WPA2"}, ...]`
- `POST /api/wifi/conectar`
  - Payload: `{"ssid":"Escola_2.4G","senha":"secretpassword"}`
  - Response (202 Accepted): `{"sucesso":true,"status":"conectando"}`
- `POST /api/wifi/esquecer`
  - Clears NVS credentials and restarts in Access Point mode.
- `GET /api/logs?desde={id}`
  - Returns ring buffer log lines with severity and relative timestamps.
- `POST /api/comando?cmd={ping_nfc|status|limpar|reboot}`
  - Executes maintenance diagnostic routines.
- `POST /api/ota`
  - Multipart firmware upload streaming binary directly into flash via `Update.h`.

### 5.3 Supabase Database Schema, RBAC & Security Contracts

#### Schema (`supabase_setup.sql`):
1. **`public.perfis_usuarios`**:
   - `id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE`
   - `email TEXT NOT NULL`, `nome_completo TEXT NOT NULL`
   - `cargo VARCHAR(30) CHECK (cargo IN ('portaria', 'secretaria', 'coordenacao', 'direcao', 'admin'))`
   - `ativo BOOLEAN NOT NULL DEFAULT true`
2. **`public.alunos`**:
   - `id UUID PRIMARY KEY DEFAULT uuid_generate_v4()`
   - `uid_nfc VARCHAR(32) NOT NULL UNIQUE` (Normalized uppercase hexadecimal)
   - `nome_completo VARCHAR(120) NOT NULL`
   - `matricula VARCHAR(30) UNIQUE`, `turma VARCHAR(50)`, `curso VARCHAR(80)`
   - `nome_responsavel VARCHAR(120)`, `telefone_responsavel VARCHAR(25)`
   - `foto_url TEXT`, `foto_path TEXT` (Bucket: `fotos-alunos`)
   - `ativo BOOLEAN NOT NULL DEFAULT true`, `observacoes TEXT`
3. **`public.historico_acessos`**:
   - `id UUID PRIMARY KEY DEFAULT uuid_generate_v4()`
   - `uid_nfc VARCHAR(32) NOT NULL`, `aluno_id UUID REFERENCES public.alunos(id) ON DELETE SET NULL`
   - `nome_identificado VARCHAR(120)`, `turma VARCHAR(50)`
   - `tipo_evento VARCHAR(20) DEFAULT 'ENTRADA'`, `status VARCHAR(20)` (`LIBERADO`, `BLOQUEADO`, `NÃO CADASTRADO`)
   - `data_hora TIMESTAMPTZ DEFAULT now()`

#### Security & RBAC Policies:
- Function `public.tem_permissao(VARIADIC cargos TEXT[])` determines authorized role access using cached session claims.
- Privilege escalation guard: Trigger `public.lidar_novo_usuario()` forces any self-registered user into role `portaria` with `ativo = false`, unless the table is completely empty (in which case the first user becomes the system bootstrap `admin`).
- Last-Admin protection: Stored procedures `admin_alterar_usuario` and `admin_excluir_usuario` disallow demoting or deleting the final active admin account.
- Realtime publication: `historico_acessos` published to `supabase_realtime` replication slot.

### 5.4 Excel Workbook Interchange Format (`.xlsx`)

The grade export/import boundary conforms to the following schema:
- **Header Discovery**: The engine dynamically inspects the first 25 rows to identify the column header row (detecting markers like `NOME`, `ESTUDANTE`, `ALUNO`).
- **Student Name Column**: Column `A` or `B` containing normalized student names.
- **Activity Columns**: Sub-sequential columns representing evaluation components (e.g., `Ativ 1`, `Ativ 2`, `Simulado`, `Prova`). Intermediate non-grade columns (`Faltas`, `Recuperação`, blank columns) are skipped.
- **Falta Vinculada (FV)**: Empty grade cells or explicitly marked cells (`"FV"`, `"Não Fez"`, `"-"`) trigger the automated Falta Vinculada checkbox state in the SIGEduc interface.
- **Total Calculation**: Native formulas (`=SUM(B2:D2)`) or calculated unit totals are preserved and reconciled against live RichFaces DOM sums.

### 5.5 SIGEduc JSF/RichFaces DOM Selectors & Timings

```javascript
// Unit Grade Table Selectors:
const TABELA_UNIDADES = {
  1: "table[id='formulario:result']",
  2: "table[id='formulario:resultj_id_1']",
  3: "table[id='formulario:resultj_id_2']",
  4: "table[id='formulario:resultadoFinal']"
};

// Activity Input Selectors:
const INPUT_NOTA = "input[id*=':av__']";

// Falta Vinculada Checkbox Selectors:
const CHECKBOX_FV = "input[type='checkbox'][id*=':falta']";

// Password Confirmation Modal:
const INPUT_SENHA_MODAL = "input[type='password'][id*='senha']";
const BOTAO_CONFIRMAR_MODAL = "input[type='submit'][id*='confirmar']";

// Pacing & Timing Rules:
const INTER_KEYSTROKE_DELAY = 40; // ms
const AJAX_RECACL_WAIT = 120;     // ms
const TAB_SWITCH_TIMEOUT = 10000; // ms
```

---

## 6. Monorepo Code Layout

```
c:\Users\devma\.gemini\antigravity\scratch\sigeduc-auto\
├── .agents/                               # Multi-agent framework metadata
│   └── teamwork/                          # Collaboration artifacts (read-only for source)
│       ├── orchestrator/                  # Central survey synthesis & planning
│       ├── explorer_survey_1/             # Explorer 1 findings (Python & Scraper)
│       ├── explorer_survey_2/             # Explorer 2 findings (Web & Extension)
│       ├── explorer_survey_3/             # Explorer 3 findings (Firmware & Science Fair)
│       └── worker_docs_1/                 # Documentation specialist workspace
│
├── .env.local                             # Environment configuration (Firebase / Supabase)
├── .gitignore                             # Monorepo git exclusion rules
├── AGENT.md                               # Operational runbooks & rules of engagement
├── HANDOFF.md                             # State of repository, key files & data flows
├── PROJECT.md                             # Architecture, contracts, and code layout (this file)
├── README.md                              # User-facing guide (Extension, Desktop GUI, CLI)
├── package.json                           # Root NPM metadata descriptor
├── package-lock.json                      # Root NPM dependency lock
├── icon.ico                               # Application icon asset for PyInstaller & GUI
│
├── [Python Desktop Automation]
│   ├── sigeduc_core.py                    # Core business logic, name matching & Playwright engine
│   ├── sigeduc_gui.py                     # CustomTkinter graphical desktop interface
│   ├── sigeduc_scraper.py                 # Academic web scraper producing multi-tab Excel workbooks
│   ├── lancar_frequencia.py               # Interactive CLI loop for attendance and grade injection
│   ├── test_scraper_unit.py               # Unit test suite for scraper, tab naming & turn extraction
│   ├── requirements.txt                   # Python dependencies (playwright, openpyxl, pandas, etc.)
│   ├── sigeduc_gui.spec                   # PyInstaller specification for single-binary packaging
│   ├── Notas Info 2.xlsx                  # Real-world test workbook with multiple class sheets
│   ├── exemplo_alunos.txt                 # Plaintext sample student list for CLI attendance testing
│   ├── relatorio_academico_sigeduc.xlsx   # Output artifact from academic scraper execution
│   ├── sigeduc_auto.log                   # Historical operational execution log
│   ├── erro_log.txt                       # Runtime traceback exception log
│   ├── debug.log                          # Windows Chromium Mojo process log
│   ├── perfil_navegador/                  # Persistent Chromium user profile (cookies, local storage)
│   ├── build/sigeduc_gui/                 # PyInstaller intermediate compilation cache
│   └── dist/                              # Distributable artifacts:
│       ├── sigeduc_gui.exe                # Standalone Windows executable (~68 MB)
│       ├── sigeduc-extensao-v1.0.5.zip    # Packaged extension zip archive
│       ├── sigeduc-extensao-v1.1.0.zip    # Packaged extension zip archive
│       └── sigeduc-extensao.zip           # Packaged extension zip archive
│
├── sigeduc-auto/                          # Legacy subproject directory
│   ├── sigeduc_core.py                    # Identical copy of core logic
│   ├── sigeduc_gui.py                     # Identical copy of GUI
│   ├── lancar_frequencia.py               # Identical copy of CLI
│   ├── sigeduc_scraper.py                 # Baseline scraper version (prior to class tag enhancements)
│   ├── requirements.txt                   # Dependency definitions
│   └── README.md                          # Dedicated Python subproject documentation
│
├── extensao-notas/                        # Chromium Manifest V3 Extension
│   ├── manifest.json                      # Extension manifest (MV3, main-world bridge declaration)
│   ├── README.md                          # Extension documentation & installation guide
│   ├── instalar_extensao.bat              # One-click Windows installer script
│   ├── extensao-notas.crx                 # Packaged Chrome extension binary (root)
│   ├── extensao-notas.pem                 # Private RSA packaging key (root)
│   ├── content/                           # Injected scripts:
│   │   ├── page-bridge.js                 # MAIN world script auto-accepting window.confirm/alert
│   │   ├── content.js                     # ISOLATED world DOM automation & RichFaces pacing
│   │   └── content.css                    # Visual highlight stylesheet for modified inputs
│   ├── lib/                               # Core libraries:
│   │   ├── nomes.js                       # Phonetic canonicalization & strict homonym barrier
│   │   └── excel.js                       # SheetJS abstraction, header finder, template generator
│   ├── popup/                             # Extension toolbar popup UI:
│   │   ├── popup.html                     # Tabbed user interface (Grades, Attendance, Terminal)
│   │   ├── popup.js                       # Popup controller & dynamic re-injection manager
│   │   └── popup.css                      # Modern dark theme stylesheet
│   ├── vendor/                            # External vendored libraries:
│   │   └── xlsx.full.min.js               # SheetJS standalone distribution
│   ├── scripts/                           # Packaging & utility scripts:
│   │   ├── empacotar.js                   # Extension zip bundler
│   │   └── gerar_icones.js                # Canvas PNG icon generator
│   └── tests/                             # Extension automated test suite:
│       ├── mock_dom.js                    # RichFaces / JSF DOM mock environment
│       └── test_extension.js              # 22 unit tests validating 6 real state school classes
│
├── escola-nfc-web/                        # Administrative Web Hub & Portaria Kiosk
│   ├── index.html                         # SPA root (Portaria, Secretaria, Histórico, Config)
│   ├── style.css                          # Responsive CSS3 stylesheet (Grid/Flexbox/Dark mode)
│   ├── package.json                       # NPM configuration & test scripts (node --test)
│   ├── supabase_setup.sql                 # Complete idempotent database schema, RLS & triggers
│   ├── js/                                # Application ES modules:
│   │   ├── app.js                         # Central UI controller, camera handler & offline queue
│   │   ├── lib/
│   │   │   ├── config.js                  # Immutable runtime configuration reader
│   │   │   └── utils.js                   # UID normalizer, phone formatter, CSV parser/generator
│   │   └── services/
│   │       ├── supabase.js                # Supabase client wrapper, RPCs & Realtime channel
│   │       └── esp32.js                   # ESP32 REST client & portaria polling loop
│   ├── scripts/                           # Local server, build & maintenance utilities:
│   │   ├── build-config.mjs               # Environment config injector
│   │   ├── bootstrap-admin.mjs            # Service-role admin account initializer
│   │   ├── serve-local.mjs                # Local HTTP server on port 5500
│   │   ├── mock-esp.mjs                   # Simulated ESP32 hardware server on port 8787
│   │   ├── painel-build.mjs               # Asset compressor generating .gz for LittleFS
│   │   └── painel-upload.mjs              # Direct HTTP uploader to ESP32 flash
│   ├── painel-dist/                       # Gzipped web assets prepared for ESP32 flash
│   ├── supabase/migrations/               # Incremental database migration scripts
│   └── tests/                             # 47 unit tests for CSV, RBAC, config & utils
│
├── escola-nfc-web-offline/                # Standalone Offline Docker Stack (Git Worktree)
│   ├── lab.cmd / lab-menu.ps1             # Windows TUI control menu
│   ├── lab-ligar.cmd / lab-estado.ps1     # Container lifecycle scripts
│   ├── docker-compose.yml                 # Multi-container orchestration (Kong, PostgREST, etc.)
│   ├── scripts/lab-setup.mjs              # Dynamic LAN IP configurator
│   └── docs/                              # Offline mode guides & non-technical Docker tutorials
│
├── esp32-nfc-acesso/                      # Baseline ESP32 NFC Firmware
│   ├── esp32-nfc-acesso.ino               # Arduino C++ sketch (PN532 I2C, NVS, WebServer)
│   └── pagina_web.h                       # PROGMEM embedded HTML/CSS/JS administrative SPA
│
├── esp32s3-nfc-acesso/                    # Production ESP32-S3 Dual-Core Firmware
│   ├── esp32s3-nfc-acesso.ino             # FreeRTOS dual-core firmware (Core 0 NFC, Core 1 Web)
│   ├── pagina_web.h                       # Advanced web console & card manager SPA
│   ├── pagina_wifi.h                      # Captive portal Wi-Fi configuration UI
│   ├── web_ferramentas.h                  # Web Serial Console & Web OTA firmware updater
│   ├── MANUAL_DO_SISTEMA.md               # Detailed technical operations manual
│   ├── GUIA_DE_PINOS_E_EXPANSAO.md        # Shield expansion pin guide & G-V-S standard
│   ├── GUIA_37_SENSORES_ESP32.md          # 37 sensor encyclopedia with wiring & C++ snippets
│   └── build/esp32.esp32.esp32s3/         # Arduino CLI build artifacts (.bin, .elf, .merged.bin)
│
├── teste-compila-s3/                      # ESP32-S3 Compilation Smoke Test
│   └── teste-compila-s3.ino               # Minimal sketch verifying library dependencies
│
├── apresentacao-nfc/                      # Interactive Presentation Deck
│   ├── index.html                         # Responsive presentation with turnstile & G-V-S demos
│   └── README.md                          # Presentation usage guidelines
│
└── feira-exposicao/                       # 5-Station Science Fair Portal
    ├── index.html                         # WAI-ARIA accessible exhibition portal
    ├── css/                               # Dedicated stylesheets (styles, arte, demos, print)
    ├── js/                                # Modular architecture:
    │   ├── data.js                        # Catalog of 37 sensors, 5 stations, glossaries
    │   ├── logic.js                       # Pure business rules & UID normalizers (Node compatible)
    │   ├── art.js                         # SVG illustration generator for sensors & schematics
    │   ├── interactions.js                # 5 interactive simulation demos
    │   └── app.js                         # Hash routing, reading levels & passport issuer
    ├── assets/sensores/                   # 37 photographic assets of sensor modules
    ├── GUIA-MATERIAIS-E-MONTAGEM.md       # Bill of materials & assembly guide
    └── tests/                             # Unit tests (`run-tests.js`) and E2E CDP (`run-e2e.js`)
```
