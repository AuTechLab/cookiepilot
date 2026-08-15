# 🍪 CookiePilot

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Emulator-orange.svg)](#%EF%B8%8F-system-requirements)

**CookiePilot** is an automated bot for **Cookie Run Classic** powered by Python, ADB, and OpenCV. It features a modern, intuitive **GUI**, automated Anti-Bot solver, smart boost purchasing, automated reward collection, and human-like touch randomization.

---

## ✨ Features

- 🖥️ **Modern GUI Dashboard**: Dark theme interface featuring real-time statistics, run logs, and session controls.
- 🤖 **Full Auto-Loop**: Lobby → Buy Items/Boosts → Run Game → Claim Rewards → Repeat automatically.
- 🧩 **Auto Anti-Bot Solver**: Automatically detects and solves Anti-Bot challenges on the fly.
- ⚡ **Auto Power-Ups**: Automatically buys Fast Start, Cookie Relay, and rolls for selected Boosts (11 available types).
- 🏺 **Relic & Mystery Box**: Automatically opens mystery boxes and claims relic pieces.
- 🎁 **Gifts & Lives**: Sends/receives lives with friends and draws gift boxes automatically.
- 🪙 **Coin Tracker (OCR)**: Reads and logs coins farmed per run via optical character recognition.
- 🛡️ **Anti-Detection Protection**: Randomized click coordinates (jitter), variable delay timings, and periodic app restarts.

---

## 🛠️ System Requirements

- **OS**: Windows 10 / 11
- **Python**: 3.8 or higher ([Download Python](https://www.python.org/downloads/)) *(Make sure to check "Add Python to PATH" during installation)*
- **ADB**: Android Debug Bridge installed and added to System PATH ([Download Platform-Tools](https://developer.android.com/tools/releases/platform-tools))
- **Android Emulator / Device**: LDPlayer, Nox, BlueStacks, MEmu, etc.
- **Screen Resolution**: **1280 × 720 (DPI 240)** *(Required)*

---

## ⚙️ Emulator Configuration

1. Set the display resolution to **1280 × 720 (DPI 240)**.
2. Enable **ADB Debugging** (Root / ADB Connection) in emulator settings.
3. **Default ADB Port**:
   - **LDPlayer**: `5555`

---

## 📥 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AuTechLab/cookiepilot.git
   cd cookiepilot
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Getting Started

Launch via Terminal or double-click **`run.bat`**:

```bash
python gui.py
```

1. Enter or select your emulator's **ADB Port**.
2. Configure desired options (Fast Start, Cookie Relay, Preferred Boosts).
3. Click **Start Bot** to begin automation.

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| Buttons not detected / Misaligned clicks | Verify emulator resolution is set to **1280 × 720 (DPI 240)**. |
| Cannot connect to ADB | Verify emulator is running, ADB debugging is enabled, and port number is correct. |
| Missing dependencies (`No module named ...`) | Run `pip install -r requirements.txt` again. |

---

> ⚠️ **Disclaimer**: This project is developed for educational and automation research purposes only. The developers assume no responsibility for any consequences or account penalties that may result from using this software.
