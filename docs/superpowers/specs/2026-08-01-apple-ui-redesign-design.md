# SILARAS SD Portal Apple-Style UI/UX Redesign Specification

> **Date:** 2026-08-01  
> **Status:** PROPOSED  
> **Target Path:** `portal/v2/index.html` (Isolated standalone implementation before migrating `portal/index.html`)

---

## 1. Overview & Objectives

SILARAS SD (Sistem Lakehouse Anggaran RAB dan IKU Sains Data) currently features a functional single-page management portal at `portal/index.html`. While feature-complete, its visual density, rigid sidebar layout, high exposure of developer technical logs/paths, and legacy styling create cognitive overload for general academic and financial users (e.g., Kaprodi and administrative staff).

This specification outlines the UI/UX redesign of SILARAS SD, adhering strictly to **Apple's Human Interface Guidelines (HIG)**:
- **Clean & Focused Workflows**: Prioritizing core tasks (Excel upload, pipeline execution, Gold summary, Superset BI access) while decluttering technical artifacts.
- **Auto-adaptive Theme System**: Seamless dynamic theme switching between Light Mode (macOS Sequoia style) and Dark Mode (Space Gray/Midnight obsidian style) with automatic OS preference detection.
- **Collapsible iPadOS-Style Sidebar**: Responsive floating navigation bar with a smooth toggle between expanded (icon + text) and collapsed (icon-only) states.
- **Dual Audience Modes**: A header-level toggle between **Mode Ringkas (User Mode)** for general users and **Mode Detail (Developer Mode)** for technical auditing (exposing live log terminals, MinIO S3 manifests, container ports, and parquet file paths).
- **100% Functional Parity**: Complete preservation of all real backend API interactions (`/api/upload/excel-dataset`, `/api/pipeline/excel-lakehouse`, `/api/iku-review/*`, `/api/uat/*`, `/api/status/services`, `/api/activity`, etc.).

---

## 2. Design System Tokens & Aesthetics

### 2.1 Color Palette & Theme Tokens
| Token | Light Mode (macOS Sequoia) | Dark Mode (Space Gray/Midnight) | Usage |
| :--- | :--- | :--- | :--- |
| `--canvas-bg` | `#f5f5f7` | `#000000` | Main application background |
| `--surface-glass` | `rgba(255, 255, 255, 0.75)` | `rgba(28, 28, 30, 0.75)` | Card & panel background |
| `--surface-glass-border` | `rgba(0, 0, 0, 0.08)` | `rgba(255, 255, 255, 0.12)` | Glass card subtle outline |
| `--text-primary` | `#1d1d1f` | `#f5f5f7` | Primary headings & body text |
| `--text-secondary` | `#86868b` | `#98989d` | Captions, subtitles, labels |
| `--accent-blue` | `#0071e3` | `#0a84ff` | Primary action buttons, active states |
| `--accent-green` | `#34c759` | `#30d158` | Status OK, validated, success badges |
| `--accent-amber` | `#ff9f0a` | `#ffd60a` | Warning states, pending reviews |
| `--accent-red` | `#ff453a` | `#ff453a` | Error, failed, shutdown actions |

### 2.2 Glassmorphism & Elevation
- **Frosted Blur Effect**: `backdrop-filter: blur(25px) saturate(180%); -webkit-backdrop-filter: blur(25px) saturate(180%);`
- **Border Radius Standards**:
  - Main Cards & Modals: `20px`
  - Inner Panels & Tables: `14px`
  - Buttons, Inputs, & Badges: `10px` or `999px` (Pill shape)
- **Shadow System**:
  - Elevated Cards: `0 8px 32px 0 rgba(0, 0, 0, 0.08), 0 2px 8px 0 rgba(0, 0, 0, 0.04)`
  - Active Floating Headers: `0 4px 20px 0 rgba(0, 0, 0, 0.06)`

### 2.3 Typography & Micro-Interactions
- **Font Stack**: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif`
- **Transitions**: `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)` for spring-like responsiveness.
- **Button Micro-Feedback**: Active press down effect (`transform: scale(0.98)`). Hover glow & elevation (`transform: translateY(-1px)`).

---

## 3. Architecture & Layout Specification

### 3.1 Layout Anatomy
```text
+-----------------------------------------------------------------------------------+
|  [ ☰ Toggle ] SILARAS SD  | [ Mode: User/Dev ] [ Theme: ☀️/🌙/💻 ] [ ID/EN ]       | <-- Floating Header
+---------------------------+-------------------------------------------------------+
|  COLLAPSIBLE SIDEBAR      | MAIN CONTENT AREA                                     |
|  - 🚀 Beranda & Upload    |                                                       |
|  - 📊 Lakehouse & Data    | [ Dynamic Active View Component ]                     |
|  - 📈 Analytics & Superset|                                                       |
|  - ⚙️ Status System & Log |                                                       |
|                           |                                                       |
|  (Width: 260px -> 72px)   |                                                       |
+---------------------------+-------------------------------------------------------+
|  FOOTER STATUS BAR: System OK (Online 10/10) | Lakehouse: Ready | Last Run: 12:45    |
+-----------------------------------------------------------------------------------+
```

### 3.2 Navigation & Header Components
- **Sidebar**:
  - Expanded width: `260px`. Collapsed width: `72px` (icon-only with Apple tooltips).
  - Smooth animation collapse toggle at top header.
- **Header Controls**:
  - **Audience Mode Toggle**: Segmented pill control (`[ 👤 Ringkas (User) | 🛠️ Detail (Developer) ]`). Switching modes conditionally shows/hides technical log consoles, raw paths, and container configurations.
  - **Theme Picker**: Segmented pill control (`[ ☀️ Light | 🌙 Dark | 💻 Auto ]`). Auto listens to `prefers-color-scheme`.
  - **Language Selector**: Pill dropdown (`[ ID | EN ]`).

---

## 4. Detailed 4-Page Breakdown & Backend Parity

### Page 1: 🚀 Beranda & Upload (`#page-beranda`)
1. **Header Metric Grid**:
   - Total Anggaran (`fact_anggaran.total_jumlah` formatted in IDR).
   - Total Item Anggaran (`fact_anggaran.fact_rows` count).
   - Data Quality Score (`quality_gate` score %).
   - Pipeline Status badge (Success/Running/Failed).
2. **Guided Excel Upload Card**:
   - Modern drag-and-drop file dropzone (`.xlsx, .xlsm, .xltx, .xltm`).
   - Metadata inputs: Tahun (default 2025), Periode (Tahunan/Jan-Jun/Jul-Des), Prodi, Fakultas.
   - Real Action Buttons:
     - `[ ☁️ 1. Upload Data ]`: Form submission to `POST /api/upload/excel-dataset`.
     - `[ ▶️ 2. Jalankan Sistem ]`: Pipeline trigger to `POST /api/pipeline/excel-lakehouse`.
   - Realtime progress bar and inline status notifications.
3. **Interactive Medallion Stepper**:
   - 5 visual steps: Upload Excel $\rightarrow$ Baca Cell $\rightarrow$ Rapikan Data $\rightarrow$ Buat Gold $\rightarrow$ Dashboard BI.
   - Dynamic status badges (Ready / Running / Waiting / Failed).
4. **Developer Mode Additions**:
   - Ingestion Activity & Pipeline Run Log Table.

### Page 2: 📊 Lakehouse & Data (`#page-lakehouse`)
1. **Medallion Lineage Diagram**:
   - Live status flow card across Raw $\rightarrow$ Bronze $\rightarrow$ Silver $\rightarrow$ Gold $\rightarrow$ Superset layers.
2. **Interactive IKU Review Queue Panel**:
   - Fetch queue from `GET /api/iku-review/queue?limit=100`.
   - Displays unmapped items with suggested Nomenklatur matches.
   - Interactive dropdown selection and `[ 💾 Simpan Review ]` action (`POST /api/iku-review/save`).
3. **Gold Data Mart Preview**:
   - Interactive table preview for `fact_anggaran` and Silver normalised tables.
4. **Developer Mode Additions**:
   - MinIO / S3 Storage Layer Mapping Table (`s3://lakehouse/...` vs local paths) with Copy Path buttons.
   - Parquet count validation statistics.

### Page 3: 📈 Analytics & Superset (`#page-analytics`)
1. **Superset BI Integration Card**:
   - Status badge for Superset service.
   - Direct launch buttons for per-year dashboards (`GET /api/dashboard/links/current`).
2. **User Acceptance Testing (UAT) Form**:
   - 5 Evaluated Criteria (Navigation Facility, Visualization Clarity, Data Relevance, Consistency, Decision Usefulness).
   - 5-Star score rating buttons for each criterion.
   - Inputs for Evaluator Name/ID, Evaluated Module, and Feedback Textarea.
   - Action `[ 💾 Simpan Data Evaluasi ]`: Sends payload to `POST /api/uat/submit` and backs up to `localStorage`.
3. **UAT Analytics & History**:
   - Visual distribution bar charts for rating stars.
   - Overall Average Rating badge (e.g. `4.8 / 5.0`).
   - Local evaluation history table with Delete entry functionality.
   - Official backend UAT Matrix Summary table (`uat_matrix_summary.json`).

### Page 4: ⚙️ Status Sistem & Log (`#page-system`)
1. **10 Service Health Monitor**:
   - Cards/Table for 10 core stack services: Airflow (8085), Superset (8089), MinIO API (9000), MinIO Console (9001), Spark Master (8080), Spark RPC (7077), Spark Worker (8081), Trino (8082), PostgreSQL (5432), Portal (8090).
   - Includes health badges, credentials, and Copy Connection String buttons.
2. **Realtime Airflow Terminal Console**:
   - macOS-style terminal window with glowing cursor.
   - Streams live Airflow DAG execution logs with syntax-highlighted level tags (INFO/SUCCESS/WARN/ERROR).
3. **System Admin Actions**:
   - `[ 🔌 Matikan Layanan ]` admin button with modal alert.

---

## 5. File Isolation & Verification Strategy

- **Isolated File Location**: All new UI/UX code will be placed in `portal/v2/index.html`.
- **Existing Portal Protection**: `portal/index.html` remains untouched until explicit verification and approval.
- **Server Support**: `portal/server.py` natively serves static files under `portal/`, making `http://localhost:8090/v2/` instantly accessible upon file creation.
- **Verification Plan**:
  1. Validate layout responsiveness across desktop and tablet viewpoints.
  2. Test theme switching (Light / Dark / System Auto).
  3. Verify collapsible sidebar functionality.
  4. Test all form submissions and button clicks against backend API endpoints.
  5. Verify that User Mode hides developer log clutter while Developer Mode displays complete technical information.

---
