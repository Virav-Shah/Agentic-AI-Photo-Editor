# **AI Photo Editor of 2030 – Inter IIT Tech Meet 14 (Adobe Product Dev)**

A mobile-first, AI-assisted photo editing system built as a solution for the **Inter IIT Tech Meet 14 – Adobe Product Development Problem Statement**.

This repository contains all deliverables — design, report, full codebase (backend + web + mobile), AI models, and documentation.

---

## 🚀 Overview

**AI Photo Editor 2030** reimagines Photoshop as a mobile-first, AI-driven editing app with:

- 🧊 **3D Parallax Effects**  
- 🌗 **Day → Night timeline transformations (weather-aware)**  
- 🤖 **Dual-Mode AI**  
  - **Fast Agent** (Gemma 3-1B) for quick edits  
  - **Thinking Mode** (Llama 3.2-3B) for multi-step reasoning  
- 🗣️ **Voice-based editing** (Deepgram STT)  
- 🖼️ **Full vision toolkit**: segmentation, depth, detection, inpainting, SR, filters  
- 🔒 **Local inference via Ollama** (no cloud required)

---

## 📁 Repository Structure

```
Deliverable-1 - Product Design/
Deliverable-2 - Report/
Deliverable-3 - Code + Doc + Readme/
.gitignore
```

- **Deliverable-1:** Product concepts, UI/UX flows, architecture sketches  
- **Deliverable-2:** Complete written report for submission  
- **Deliverable-3:** Backend (FastAPI), Orchestrator, Website (React), Mobile App (React Native), model pipelines, documentation  

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, ONNX Runtime, PyTorch  
- **Frontend:** React + Vite  
- **Mobile App:** React Native (Expo)  
- **LLMs (via Ollama):** Gemma 3-1B, Llama 3.2-3B  
- **Vision Models:** YOLO11n, MobileSAM, BiRefNet, Depth-Anything-V2, MI-GAN, SwinIR  

---

## ▶️ Quick Start

To run the full application (backend + web + mobile):

1. Install **Ollama** and pull required models  
2. Add models inside `/backend/models`  
3. Set environment variables in `/backend/.env`  
4. Run:

```bash
.\SETUP.bat
.\START.bat
```

For manual instructions, see the detailed README inside:

```
Deliverable-3 - Code + Doc + Readme/README.md
```

---

## 📜 License

MIT License — see `LICENSE` for details.

---

Built with ❤️ for creators of 2030.  
A submission for **Inter IIT Tech Meet 14 – Adobe Product Development**.
