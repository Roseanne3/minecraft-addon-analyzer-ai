# ⛏ Minecraft Addon Analyzer AI

A full-stack production tool for Minecraft Bedrock Edition addon developers to **analyze, debug, and auto-fix addons**.

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TailwindCSS, Chart.js, React Router v6 |
| Backend | Python FastAPI + Uvicorn |
| Database | SQLite + SQLAlchemy |

---

## 🚀 Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at: http://localhost:3000

---

## 📁 Project Structure

```
minecraft-addon-analyzer-ai/
├── backend/
│   ├── main.py               # FastAPI app + all routes
│   ├── database.py           # SQLite + SQLAlchemy setup
│   ├── models.py             # ORM models: User, Addon, Report, FileRecord
│   ├── extractor.py          # ZIP/MCADDON/MCPACK extraction + file tree scan
│   ├── scanner.py            # Orchestrates all analyzers, computes score
│   ├── manifest_checker.py   # manifest.json validation + auto-fix
│   ├── json_validator.py     # JSON syntax validation + repair
│   ├── behavior_checker.py   # Behavior pack (entities, items, loot tables)
│   ├── resource_checker.py   # Resource pack (textures, animations, models)
│   ├── dependency_checker.py # Pack dependency UUID validation
│   ├── performance_checker.py# File size, nesting depth, animation count
│   ├── ai_analyzer.py        # Rule-based AI suggestions
│   ├── fix_engine.py         # Auto-fix engine + fixed ZIP output
│   └── requirements.txt
│
├── frontend/
│   ├── public/index.html
│   └── src/
│       ├── App.js            # Router
│       ├── index.js
│       ├── index.css         # Design system
│       ├── pages/
│       │   ├── UploadPage.js # Drag & drop upload
│       │   ├── Dashboard.js  # Analytics + issue list
│       │   └── FileViewer.js # File tree + detail view
│       └── components/
│           ├── Navbar.js     # Nav + recent addons
│           ├── ScoreCard.js  # SVG score ring
│           ├── ChartPanel.js # Chart.js charts
│           ├── FixPanel.js   # Auto-fix trigger + download
│           └── FileTree.js   # Recursive file explorer
│
├── uploads/                  # Uploaded & extracted addons
├── reports/                  # (reserved for future export)
├── fixed_addons/             # Fixed addon ZIPs
└── database.db               # Auto-created by SQLAlchemy
```

---

## ✨ Features

| Feature | Description |
|---------|------------|
| **Upload** | ZIP, MCADDON, MCPACK drag-and-drop |
| **Structure Detection** | Checks for behavior_packs, resource_packs, manifest.json |
| **Manifest Analyzer** | UUID validation, version format, module types |
| **JSON Validator** | Syntax repair, bracket balancing, comment stripping |
| **Behavior Pack** | Entity identifiers, components, events, loot tables |
| **Resource Pack** | Textures, animations, models, animation controllers |
| **Dependency Checker** | Cross-pack UUID reference validation |
| **Performance Analyzer** | File size, nesting depth, texture size |
| **AI Analyzer** | Rule-based suggestions for complex entities & scripts |
| **Auto Fix Engine** | Repairs JSON, fixes manifests, generates UUIDs, creates missing structure |
| **Score System** | 0–100 quality score with visual ring |
| **File Explorer** | Full addon file tree with per-file issue drill-down |
| **Charts** | Error distribution, file types, severity breakdown |

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload-addon` | Upload & analyze addon |
| GET | `/addon/{id}` | Full analysis report |
| GET | `/addon/{id}/file-reports?file_path=` | Per-file issues |
| POST | `/addon/{id}/fix` | Run auto-fix engine |
| GET | `/addon/{id}/download-fixed` | Download fixed ZIP |
| GET | `/addons` | List recent addons |
| DELETE | `/addon/{id}` | Delete addon & files |

---

## 🎯 Addon Score Calculation

- Start at **100**
- Each **Error** = -10 points
- Each **Warning** = -3 points  
- Each **Info** = -0.5 points
- Capped between 0 and 100

Score labels: EXCELLENT (90+), GOOD (80+), FAIR (60+), POOR (40+), CRITICAL (<40)
