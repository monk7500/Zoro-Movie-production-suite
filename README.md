# AI Film Studio

A fully autonomous, local‑first AI film production swarm.
48 specialized agents transform a screenplay into a finished film,
with a Gradio dashboard for real‑time control.

## Features
- Zero‑cost – runs entirely offline, no API keys required
- Provider‑agnostic – plug in Ollama, ComfyUI, Blender, or use text‑only fallback
- Surgical recompute – change a single line and only the affected frame region is re‑rendered
- Interactive Bible – every creative decision is editable, versioned, and reversible

## Quick Start
1. Install Python 3.11+ and create a virtual environment.
2. `pip install -r requirements.txt`
3. Install free tools (Ollama, ComfyUI, Blender, FFmpeg) – see docs/setup.md
4. `python studio.py`
5. Open `http://localhost:7860`

## License
MIT
