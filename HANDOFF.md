# HANDOFF.md — Repository Status, Interconnections & Technical Continuity

## 1. Executive Summary & Repository State

This document provides the definitive handoff analysis for the entire **sigeduc-auto** monorepo. The repository is in an **operational, production-tested, and fully validated state**. All four independent test suites pass with zero failures.

The codebase represents a complete cyber-physical ecosystem spanning:
- Embedded C++ FreeRTOS dual-core firmware running on ESP32-S3 microcontrollers with PN532 RFID readers.
- Administrative web dashboards running on Supabase (PostgreSQL, Auth, Storage, Realtime) with an offline containerized Docker failover worktree.
- Government portal automation for Bahia State's **SIGEduc** portal, offered in dual modalities: a standalone Python/Playwright desktop app (`sigeduc_gui.exe`) and an in-browser Manifest V3 Chrome Extension (`extensao-notas`).
- Pedagogical interactive exhibition portals (`apresentacao-nfc` and `feira-exposicao`) designed for school science fairs with hardware simulation and LGPD compliance.

---

## 2. Key Files Inventory & Individual Purpose Mapping

### 2.1 Python Desktop Automation Suite (Root)
| File | Lines | Size | Purpose & Technical Scope |
|---|---|---|---|
| `sigeduc_core.py` | 1,331 | 50.7 KB | **Central Automation Engine**: Implements Playwright browser launch (`launch_persistent_context`), Unicode NFKD normalization, Brazilian Portuguese phonetic canonicalization (`canonicalizar_palavra`), anti-homonym logic, Excel parsing (`openpyxl`), RichFaces JSF tab navigation (Units 1 to 4), password confirmation modal auto-filling, and Falta Vinculada (FV) assignment. |
| `sigeduc_gui.py` | 1,200 | 53.2 KB | **Graphical Desktop Interface**: Built with `customtkinter` and `tkcalendar`. Features file selection dialogs, date pickers, real-time GUI logging redirector, and background thread execution (`threading.Thread`) to prevent UI freezing during Playwright execution. |
| `sigeduc_scraper.py` | 1,279 | 57.7 KB | **Academic Crawler & Report Generator**: Scrapes assigned classes, unit evaluation columns, weights, and daily attendance logs from SIGEduc BA into structured, styled multi-tab Excel workbooks (`relatorio_academico_sigeduc.xlsx`). |
| `lancar_frequencia.py` | 346 | 17.7 KB | **Interactive Terminal CLI**: Lightweight console automation supporting 5 attendance modes (100% Presentes fileless, Excel with markbox, TXT list, partial classes, manual input) and grade injection. Writes tracebacks to `erro_log.txt`. |
| `test_scraper_unit.py` | 211 | 9.3 KB | **Python Unit Test Suite**: Tests unit extraction, class alphanumeric regex (`extrair_turno`), Excel tab sanitization within 31 chars (`formatar_nome_aba`), and teacher panel qualification (`esta_no_painel_docente`). |
| `sigeduc_gui.spec` | 39 | 750 B | **PyInstaller Build Spec**: Packages `sigeduc_gui.py` into a single standalone Windows executable with UPX compression and windowed mode (`console=False`), bundling `icon.ico`. |
| `requirements.txt` | 5 | 88 B | **Python Dependencies**: Declares `playwright>=1.40.0`, `customtkinter>=5.2.0`, `openpyxl>=3.1.0`, `tkcalendar>=1.6.1`, and `pandas>=2.0.0`. |

### 2.2 Legacy Subproject Directory (`sigeduc-auto/`)
| File | Status | Notes |
|---|---|---|
| `sigeduc-auto/sigeduc_core.py` | Byte-for-byte identical to root | Verified via `filecmp.cmp` (`True`). |
| `sigeduc-auto/sigeduc_gui.py` | Byte-for-byte identical to root | Verified via `filecmp.cmp` (`True`). |
| `sigeduc-auto/lancar_frequencia.py` | Byte-for-byte identical to root | Verified via `filecmp.cmp` (`True`). |
| `sigeduc-auto/requirements.txt` | Byte-for-byte identical to root | Verified via `filecmp.cmp` (`True`). |
| `sigeduc-auto/sigeduc_scraper.py` | Older revision (1,123 lines vs 1,279 in root) | Lacks root's enhanced alphanumeric class code parsing (e.g., `ADMVES1SA`) and false-positive guards for `MATEMÁTICA`/`INFORMÁTICA`. |
| `sigeduc-auto/README.md` | Python-specific documentation | Focused strictly on the Python desktop tools. |

### 2.3 Chromium Manifest V3 Extension (`extensao-notas/`)
| File | Lines | Size | Purpose & Technical Scope |
|---|---|---|---|
| `manifest.json` | 66 | 2.1 KB | **Extension Manifest**: Configures MV3 permissions (`activeTab`, `tabs`, `storage`, `scripting`), host permissions for `*://*.educacao.ba.gov.br/*`, Main World script declaration, and popup action. |
| `content/page-bridge.js` | 28 | 903 B | **Main World Dialog Interceptor**: Injected into `world: "MAIN"` at `document_start`. Monkey-patches `window.confirm` and `window.alert` to auto-accept RichFaces batch confirmation dialogs. |
| `content/content.js` | 2,333 | 91.5 KB | **Isolated World DOM Controller**: Intercepts input events, enforces micro-delays (40-120ms) for RichFaces Ajax recalculation, checks Falta Vinculada, and manages batch calendar attendance traversal via `sessionStorage`. |
| `content/content.css` | 180 | 4.8 KB | **Visual Injected Stylesheet**: Highlights modified input fields (green), Falta Vinculada checkboxes (yellow), and displays floating toast status banners. |
| `lib/nomes.js` | 208 | 7.9 KB | **Phonetic & Anti-Homonym Engine**: Dual-export (ESM / CommonJS). Normalizes Brazilian Portuguese names (replaces `TH` $\rightarrow$ `T`, `Y` $\rightarrow$ `I`, `Z` $\rightarrow$ `S`, strips silent `H`) and blocks matches between homonyms with shared first names but differing middle surnames. |
| `lib/excel.js` | 718 | 27.2 KB | **Spreadsheet Extraction & Template Generator**: Scans up to row 25 for header rows, skips non-evaluative columns, extracts student grades, and generates downloadable blank `.xlsx` templates with native `=SUM()` formulas. |
| `vendor/xlsx.full.min.js` | ~15k | 838 KB | **SheetJS Library**: Standalone local build ensuring all spreadsheet processing occurs client-side inside the teacher's browser with zero external network requests (LGPD compliance). |
| `popup/popup.html` | 320 | 12.8 KB | **Extension UI**: Modern tabbed interface (Notas, Frequência, Diagnóstico). |
| `popup/popup.js` | 1,426 | 55.4 KB | **Popup Controller**: Handles file uploads, dynamically re-injects content scripts via `chrome.scripting` if disconnected, and controls logging. |
| `tests/mock_dom.js` | 350 | 13.1 KB | **Headless RichFaces DOM Simulator**: Emulates JSF tables, inputs, mutations, and asynchronous recalculation loops in Node.js. |
| `tests/test_extension.js` | 1,410 | 58.2 KB | **Automated Extension Test Suite**: 22 unit tests validating extraction, matching, and DOM injection across 6 real Bahia state school classes. |
| `scripts/empacotar.js` | 111 | 3.8 KB | **Extension Packager**: Compresses the extension directory into versioned zip files in `dist/`. |

### 2.4 Administrative Web Hub (`escola-nfc-web/`)
| File | Lines | Purpose & Technical Scope |
|---|---|---|
| `index.html` | 512 | **Central SPA**: Single-page application with views for Portaria (Gatehouse Kiosk), Secretaria (Registry), Histórico (Access Log), Usuários (RBAC), and Configurações (Settings). Zero external CDN dependencies. |
| `style.css` | 780 | **Responsive CSS**: Custom properties, dark/light themes, mobile/desktop responsiveness, and kiosk card layouts. |
| `package.json` | 38 | **Node.js Configuration**: Configures `"test": "node --test tests/"` and `"check": "node --check"`. |
| `supabase_setup.sql` | 670 | **Complete SQL Schema**: Idempotent provisioning of PostgreSQL schemas, tables (`perfis_usuarios`, `alunos`, `historico_acessos`), RLS policies with `public.tem_permissao()`, user creation trigger `public.lidar_novo_usuario()`, and Realtime publication. |
| `js/app.js` | 940 | **Main UI Controller**: Coordinates views, webcam video streams with native camera fallback, CSV import/export, and offline event queue synchronization. |
| `js/services/supabase.js` | 340 | **Supabase Service Layer**: Wraps Supabase client, paginates up to 20,000 students, executes RBAC RPCs, manages Realtime subscriptions, and handles storage uploads (`fotos-alunos`). |
| `js/services/esp32.js` | 220 | **ESP32 REST Service**: Manages gatehouse polling loop (`/api/ultimo`) with exponential backoff and `AbortController` timeouts, card synchronization (`/api/sincronizar_todos`), and health pings. |
| `js/lib/utils.js` | 410 | **Shared Utilities**: Hexadecimal UID normalizer, phone formatter, RFC 4180 CSV parser with BOM and delimiter detection (`,` or `;`), and UUID v4 generator. |
| `js/lib/config.js` | 85 | **Config Manager**: Accesses immutable `window.__APP_CONFIG__` and manages local ESP32 IP overrides in `localStorage`. |
| `scripts/mock-esp.mjs` | 180 | **ESP32 Mock Server**: Lightweight HTTP server on port 8787 simulating the ESP32 REST API for local testing without physical hardware. |
| `scripts/serve-local.mjs` | 95 | **Local Static Server**: Native Node.js HTTP server serving `escola-nfc-web` on port 5500. |
| `tests/` | 47 tests | **Unit Test Suite**: 47 automated tests verifying CSV processing, configuration builders, UUID generation, phone masking, and RBAC rules. |

### 2.5 Offline Supabase Worktree (`escola-nfc-web-offline/`)
| File / Directory | Purpose & Technical Scope |
|---|---|
| `lab/offline` (Git Worktree) | Dedicated worktree on branch `lab/offline` of `https://github.com/devmagary/escola-nfc-web.git` for on-premise, zero-internet school operation. |
| `supabase/config.toml` | Pinned Supabase CLI (v2.121.0) local stack provisioning Kong (`:54321`), PostgreSQL 15 (`:54322`), GoTrue, PostgREST, Storage (`fotos-alunos`), Inbucket (`:54324`), and Supabase Studio (`:54323`). |
| `supabase/seed.sql` | Realistic offline mock dataset for student registration, normalized UIDs, and access log simulation. |
| `lab.cmd` / `lab-menu.ps1` | Windows interactive terminal menu (TUI) with real-time status indicators for Docker, DB, Web, and ESP32. |
| `lab-ligar.cmd` / `lab-desligar.cmd` | Container lifecycle control and automated local server startup scripts. |
| `lab-checar.cmd` / `lab-estado.ps1` | Diagnostic scripts and background daemon for port and health inspection. |
| `lab-firewall-liberar.cmd` | Automatic Windows Firewall configuration opening ports 54321, 5500, and 54323 for the local school network. |
| `lab-criar-atalhos.cmd` / `lab-atalhos.ps1` | Automatic desktop shortcut creation for school operators. |
| `scripts/lab-setup.mjs` | Network discovery script detecting LAN IP (filtering out virtual adapters) and rewriting `.env.local` automatically. |
| `scripts/check-lab.mjs` | Multi-point offline laboratory health and IP inspector. |
| `tests/` | 54 automated unit and integration tests passing (`npm test`). |
| `AGENT.md` / `PROJECT.md` | Tailored AI agent operational manual and complete architectural specification committed and pushed to `lab/offline`. |

### 2.6 Embedded Firmware (`esp32-nfc-acesso/` & `esp32s3-nfc-acesso/`)
| File | Lines | Purpose & Technical Scope |
|---|---|---|
| `esp32-nfc-acesso/esp32-nfc-acesso.ino` | 648 | **Baseline Firmware**: Arduino C++ sketch for standard ESP32 / ESP32-C3 Super Mini. PN532 I2C (SDA=8, SCL=9), NVS storage (Preferences) with 50-card ceiling, and embedded WebServer on port 80. |
| `esp32-nfc-acesso/pagina_web.h` | 324 | **Baseline Web Header**: Dark-mode administrative SPA embedded in `PROGMEM`. |
| `esp32s3-nfc-acesso/esp32s3-nfc-acesso.ino` | 1,733 | **Production Firmware**: Arduino C++ for **YD-ESP32-S3 (N16R8)**. FreeRTOS Dual-Core pinning (Core 0: continuous NFC polling & 2.5s I2C heartbeat; Core 1: Web, DNS, NeoPixel, OTA), LittleFS/FFat auto-mounting (`/cartoes.json` without card limit, `/historico.json`), WS2812B NeoPixel on GPIO 48, captive portal Wi-Fi manager (`/wifi`), Web Serial Console (`/console`), Web OTA firmware flasher (`/ota`), and Supabase REST sync. |
| `esp32s3-nfc-acesso/pagina_web.h` | 528 | **Production Web Console**: Responsive CSS Grid/Subgrid SPA for card management, backup export/import, and live telemetry. |
| `esp32s3-nfc-acesso/pagina_wifi.h` | 451 | **Captive Portal UI**: Displays 2.4 GHz network scans, signal strength (RSSI), security types, and async connection management. |
| `esp32s3-nfc-acesso/web_ferramentas.h` | 458 | **Remote Tools Header**: Web Serial Console streaming circular logs from RAM, and Web OTA binary flasher via `Update.h`. |
| `esp32s3-nfc-acesso/MANUAL_DO_SISTEMA.md` | 223 | Operational manual detailing dual-core architecture, 2.4 GHz radio limits, wiring, and REST sync routes. |
| `esp32s3-nfc-acesso/GUIA_DE_PINOS_E_EXPANSAO.md`| 153 | Technical shield expansion guide, G-V-S bus standard, and forbidden PSRAM pin warning (GPIOs 35-37). |
| `esp32s3-nfc-acesso/GUIA_37_SENSORES_ESP32.md` | 742 | Encyclopedia of 37 sensor modules with physical principles, G-V-S wiring, and C++ code snippets. |
| `teste-compila-s3/teste-compila-s3.ino` | 16 | Smoke test sketch confirming ESP32-S3 library header compilation. |

### 2.7 Exhibition & Pedagogical Portals (`apresentacao-nfc/` & `feira-exposicao/`)
| File / Directory | Purpose & Technical Scope |
|---|---|
| `apresentacao-nfc/index.html` | Interactive presentation deck with turnstile simulation (SVG animation), Web Audio API tones, G-V-S wiring diagram, and 5 Senses interactive laboratory. |
| `feira-exposicao/index.html` | WAI-ARIA accessible offline science fair application with 5 stations, 37 sensors, 5 demos, and passport issuer. |
| `feira-exposicao/js/data.js` | Single Source of Truth: 37 sensor specifications, 111 practical use cases, 5 stations scripts, and 25-term glossary. |
| `feira-exposicao/js/logic.js` | Pure business logic: UID normalization, roulette angles, and categorization rules (exportable to Node.js). |
| `feira-exposicao/js/interactions.js` | Interactive simulation controllers for the 5 hands-on science fair demos. |
| `feira-exposicao/js/app.js` | UI coordinator, hash routing, reading level toggling, and visitor passport generator. |
| `feira-exposicao/tests/run-tests.js` | Automated unit test runner validating data integrity, logic functions, WCAG color contrast, and JS syntax. |
| `feira-exposicao/tests/run-e2e.js` | Headless Chrome CDP runner testing station transitions and generating PDF artifacts. |

### 2.8 Root Workspace Files & Packaging Artifacts
| File / Path | Size | Purpose & Technical Scope |
|---|---|---|
| `.env.local` | 384 B | Firebase configuration parameters for the web components. |
| `icon.ico` | 43.5 KB | Application icon embedded into PyInstaller executable and CustomTkinter windows. |
| `Notas Info 2.xlsx` | 40.1 KB | Real-world test workbook containing 7 class sheets (`Info`, `ADM`, `Nutrição`, etc.) with formulas and `FV` markers. |
| `relatorio_academico_sigeduc.xlsx` | 5.6 KB | Generated output artifact from `sigeduc_scraper.py` containing scraped class summaries. |
| `sigeduc_auto.log` | 79.5 KB | Real-world operational log (777 lines) recording session handling, table traversal, and FV assignments. |
| `erro_log.txt` | 637 B | Runtime exception traceback log from CLI execution. |
| `perfil_navegador/` | Variable | Persistent Chromium user data directory storing teacher authentication cookies and local storage. |
| `dist/sigeduc_gui.exe` | 68.3 MB | Standalone compiled Windows binary for the Python GUI application. |
| `dist/sigeduc-extensao-*.zip` | ~400 KB | Packaged zip archives of the Chrome Extension ready for deployment. |
| `extensao-notas.crx` / `.pem` | 485 KB | Packed Chrome extension binary and RSA private packaging key. |
| `build/` | ~36.5 MB | Compilation caches for PyInstaller and Arduino ESP32-S3. |

---

## 3. End-to-End Data Flow & Subsystem Interconnections

The following narrative and diagram trace the complete lifecycle of data across all hardware, database, web, and automation subsystems:

```
[Student NFC Card Tap]
         │ (13.56 MHz RFID / ISO14443A)
         ▼
[PN532 Reader Module] ──(I2C: SDA=8, SCL=9)──► [ESP32-S3 Microcontroller]
                                               │
                                               ├─► Core 0: Continuous NFC Polling (50ms)
                                               │   Local Flash Lookup: `/cartoes.json`
                                               │   Latency: < 1 ms (ZERO INTERNET NEEDED)
                                               │   Decision:
                                               │     ├─ Granted: WS2812B GREEN + Solenoid (GPIO 4)
                                               │     └─ Denied:  WS2812B RED
                                               │
                                               └─► Core 1: REST WebServer (Port 80)
                                                   Updates `/api/ultimo` & `/historico.json`
                                                           │
                                                           │ (LAN HTTP Polling: GET /api/ultimo)
                                                           ▼
                                               [escola-nfc-web Gatehouse Kiosk]
                                               │ (Browser on Portaria PC / Tablet)
                                               │ Displays photo, name, and audio alert
                                               │
                                               ├─► (If Online) Writes event to Supabase Cloud
                                               │   Table: `public.historico_acessos`
                                               │   Triggers: Supabase Realtime broadcast
                                               │
                                               └─► (If Offline) Queues event in LocalStorage
                                                   Flushes up to 200 events upon reconnection
                                                           │
                                                           │ (Administrative Export)
                                                           ▼
                                               [Student Rosters & Attendance Sheets]
                                               Exported as Excel `.xlsx` or CSV
                                                           │
                                                           ├─── Path A ───────────────┐
                                                           │                          │
                                                           ▼                          ▼
                                               [sigeduc-auto (Python)]    [extensao-notas (MV3)]
                                               Playwright Desktop Bot     Chrome Extension
                                               Reads `.xlsx` via openpyxl Reads `.xlsx` via SheetJS
                                               Uses `perfil_navegador`    Runs directly in browser
                                                           │                          │
                                                           └──────────┬───────────────┘
                                                                      │ (DOM Injection)
                                                                      ▼
                                               [SIGEduc BA Government Portal]
                                               (JavaServer Faces / RichFaces .jsf)
                                               │
                                               ├─ Step 1: Normalize & match student names phonetically
                                               ├─ Step 2: Switch Unit Tab (1ª a 4ª Unidade) via Ajax
                                               ├─ Step 3: Insert grades with 40-120ms micro-delays
                                               ├─ Step 4: Tick Falta Vinculada (FV) for empty grades
                                               ├─ Step 5: Intercept & accept RichFaces confirm dialogs
                                               └─ Step 6: Enter teacher password & submit grades
```

### Detailed Flow Narrative:
1. **Physical Card Tap**: A student approaches the school gate turnstile and taps their RFID card or keychain against the PN532 reader.
2. **Local Edge Verification**: The PN532 transmits the card UID over I2C to the ESP32-S3. Dedicated FreeRTOS Core 0 searches `/cartoes.json` in Flash memory. If authorized, the turnstile solenoid pulses for 3,000 ms and the WS2812B LED turns solid green. The entire decision takes $< 1\text{ ms}$, ensuring zero student bottleneck even if the school has completely lost power or internet.
3. **Gatehouse Kiosk Ingestion**: The portaria computer running `escola-nfc-web` polls the ESP32's `/api/ultimo` endpoint over local Wi-Fi/Ethernet. When a new sequence number appears, the kiosk sounds a welcoming chime, displays the student's photo and registration details, and sends an `INSERT` to Supabase `historico_acessos`.
4. **Attendance & Grade Consolidation**: At the end of each evaluation cycle or day, school coordinators export class attendance sheets and grade records from `escola-nfc-web` into formatted Excel workbooks (`.xlsx`).
5. **Government Portal Submission**:
   - **Method 1 (Desktop Automation)**: The teacher launches `sigeduc_gui.py` (or `sigeduc_gui.exe`). The Playwright engine opens Chromium with the teacher's active session profile (`perfil_navegador`), loads the Excel sheet, canonicalizes names phonetically to prevent misattribution, switches to the requested unit tab, fills grades with Ajax pacing, auto-checks Falta Vinculada (FV), auto-fills the confirmation password, and commits the records.
   - **Method 2 (In-Browser Extension)**: Alternatively, the teacher opens the SIGEduc portal in their own Chrome/Edge browser. The `extensao-notas` popup loads the Excel file client-side via SheetJS, executes phonetic matching against the table on screen, paces grade entry across the RichFaces inputs, auto-confirms alerts via `page-bridge.js`, and saves the unit without leaving the browser.

---

## 4. Technical Debt, Critical Caveats & Hardware Realities

### 4.1 Playwright vs. Selenium Clarification
- **The Myth**: Initial specifications and historical prompts occasionally refer to "Selenium automation".
- **The Codebase Reality**: The repository contains **zero lines of Selenium code**. All Python automation is implemented using **Playwright (`playwright.sync_api`)**.
- **Reasoning**: Playwright provides superior native handling of Chromium persistent contexts (`user_data_dir`), event-based dialog interception (`page.on("dialog")`), and direct CDP integration required to maintain stable sessions on the state's JSF portal.

### 4.2 Wi-Fi 2.4 GHz Only & Enterprise Network Incompatibility
- **Hardware Constraint**: The ESP32-S3 Wi-Fi transceiver operates **exclusively in the 2.4 GHz band (802.11 b/g/n)**. It cannot connect to 5 GHz-only SSIDs (802.11ac/ax).
- **Authentication**: WPA2-Enterprise (802.1X with RADIUS/domain logins common in university networks) is not supported by the firmware. Deployment routers must provide a dedicated 2.4 GHz SSID with WPA2-Personal (PSK) or run an isolated VLAN for the turnstiles.

### 4.3 YD-ESP32-S3 PSRAM Hardware Conflict (GPIOs 35, 36, 37)
- **Critical Danger**: The **YD-ESP32-S3 (N16R8)** features 8 MB of Octal (OPI) PSRAM. The Espressif ESP32-S3 chip internally dedicates **GPIOs 35, 36, and 37** to the high-speed PSRAM communication bus.
- **Consequence**: Connecting any sensor, jumper wire, or breadboard pin to GPIO 35, 36, or 37 causes immediate memory corruption, resulting in continuous processor panics (`LoadProhibited` or `TG1WDT_SYS_RESET`).
- **Rule**: Never allocate GPIOs 35, 36, or 37 in software or hardware.

### 4.4 Strapping Pins to Avoid During Boot
- **GPIO 0, 3, 45, and 46** determine chip boot modes, JTAG routing, and internal VDD_SPI voltage levels during the first 50 ms after reset.
- Connecting sensors with strong pull-up or pull-down resistors to these pins can force the ESP32 into ROM download mode or blow internal flash voltage regulators.
- **Rule**: PN532 reset was deliberately relocated to **GPIO 5** to avoid these strapping pins.

### 4.5 SIGEduc JSF/RichFaces DOM Quirks & Race Conditions
- **AJAX Re-render Traps**: When a grade input changes, RichFaces fires an AJAX request that recalculates unit totals on the server and re-renders part of the table DOM. If subsequent keystrokes arrive while this re-render is in flight, the DOM node is destroyed, dropping the student's grade.
- **Remedy**: Pacing micro-delays (40ms to 120ms) between rows and post-entry Live DOM verification are mandatory in both Python and Extension automation engines.
- **Session Timeouts**: SIGEduc BA destroys sessions after ~15 minutes of inactivity. Both engines implement active dialog listeners to dismiss timeout modals.

### 4.6 Subfolder `sigeduc-auto/` vs Root Divergence
- The files in `sigeduc-auto/` (`sigeduc_core.py`, `sigeduc_gui.py`, `lancar_frequencia.py`, `requirements.txt`) are identical to their counterparts in the root.
- However, `sigeduc_scraper.py` at the root contains critical production enhancements (alphanumeric class code parsing, Excel 31-character tab truncation) that are absent in `sigeduc-auto/sigeduc_scraper.py`.
- **Recommendation**: Always treat the root-level Python files as the canonical source.

---

## 5. Continuity Instructions & Future Roadmap

For any future engineer or AI agent continuing development on this repository:

1. **Verify Before Modifying**:
   Always run the complete test suite before making code changes:
   ```powershell
   python test_scraper_unit.py
   node extensao-notas/tests/test_extension.js
   npm --prefix escola-nfc-web test
   node feira-exposicao/tests/run-tests.js
   ```
2. **Adding New Sensors to the ESP32**:
   - Consult `esp32s3-nfc-acesso/GUIA_DE_PINOS_E_EXPANSAO.md` for safe GPIO allocations.
   - Use the G-V-S expansion shield rows (Black = GND, Red = 3.3V, Yellow = Signal).
   - Never use GPIO 35, 36, or 37.
3. **Updating Extension for New SIGEduc Changes**:
   - If SIGEduc BA alters table IDs or class selectors, update both `extensao-notas/content/content.js` and `sigeduc_core.py`.
   - Update `extensao-notas/tests/mock_dom.js` and re-run `node extensao-notas/tests/test_extension.js` to ensure the test mock reflects the portal's changes.
4. **Deploying Updates to School Turnstiles**:
   - Take advantage of the Web OTA firmware flasher (`http://<esp32-ip>/ota`) to update ESP32-S3 units over local Wi-Fi without unmounting the enclosure or connecting USB cables.
