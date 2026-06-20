# Setup Guide

## Required Free Tools

1. **Python 3.11+** – [python.org](https://python.org)
2. **Ollama** – [ollama.com](https://ollama.com)  
   Pull models: `ollama pull llama3.1:8b`
3. **ComfyUI** – `git clone https://github.com/comfyanonymous/ComfyUI.git`  
   Download SDXL / Flux models and run on port 8188.
4. **Blender** – [blender.org](https://blender.org) (≥3.6 LTS)
5. **FFmpeg** – `winget install ffmpeg` (Windows), `brew install ffmpeg` (macOS), `sudo apt install ffmpeg` (Linux)

## Python Environment

```bash
python3.11 -m venv ai-studio
source ai-studio/bin/activate
pip install -r requirements.txt
