"""
AI Film Studio – Complete Gradio Dashboard
Launch with: python studio.py
"""

import gradio as gr
import json, threading, time, queue, os, sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# ---------- Core imports ----------
from core.bible import FilmBible
from core.cache import ContentCache
from core.orchestrator import Orchestrator, AgentRunner
from core.graph_builder import build_dependency_graph
from agents.registry import build_registry

# ---------- Provider imports ----------
from providers.llm import OllamaProvider, OpenAICompatibleProvider
from providers.tts import XTTSv2Provider, PiperProvider, ElevenLabsTTS, OpenAITTS
from providers.image_gen import ComfyUIProvider
from providers.render_engine import ComfyUIRenderProvider, BlenderRenderProvider
from providers.physics import BlenderPhysicsProvider, SimplePhysicsProvider
from providers.vfx import DiffusionVFXProvider
from providers.music import MusicGenProvider
from providers.audio_fx import AudioLDM2Provider
from providers.assembly import FFmpegAssemblyProvider, TextFallbackAssemblyProvider

# ---------- Global state ----------
event_queue = queue.Queue()
approval_event = threading.Event()
approval_result: Optional[dict] = None
orchestrator: Optional[Orchestrator] = None
bible: Optional[FilmBible] = None
cache: Optional[ContentCache] = None
llm_provider = None
providers = {}

class DashboardState:
    def __init__(self):
        self.phase = "idle"
        self.current_version = "v0001"
        self.agent_status: Dict[str, dict] = {}
        self.pending_approvals: list = []
        self.pending_proposals: list = []
        self.errors: list = []
        self.running = False

state = DashboardState()

# ---------- DAG builder ----------
def build_dag_json(agent_status, graph):
    nodes, edges = [], []
    for agent in graph.nodes():
        info = agent_status.get(agent, {})
        status = info.get("status", "pending")
        color = {"pending":"gray","running":"blue","cached":"green","re-run":"yellow","failed":"red"}.get(status,"gray")
        nodes.append({"id": agent, "label": agent, "color": color})
    for u, v in graph.edges():
        edges.append({"from": u, "to": v})
    return json.dumps({"nodes": nodes, "edges": edges})

# ---------- UI ----------
def build_ui():
    head_html = """
    <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
    <script>
    let network = null;
    function initNetwork(dataJson) {
        const container = document.getElementById("dag-container");
        if (!container) return;
        const data = JSON.parse(dataJson);
        const nodes = new vis.DataSet(data.nodes);
        const edges = new vis.DataSet(data.edges);
        const graphData = { nodes, edges };
        const options = { layout: { hierarchical: { direction: "LR", sortMethod: "directed" } }, physics: false };
        if (network) network.destroy();
        network = new vis.Network(container, graphData, options);
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                const input = document.querySelector('#clicked-agent-input input');
                if (input) {
                    input.value = params.nodes[0];
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        });
    }
    </script>
    """

    with gr.Blocks(head=head_html) as demo:
        dag_data_text = gr.Textbox(visible=False, elem_id="dag_data_text")
        clicked_agent_text = gr.Textbox(visible=False, elem_id="clicked-agent-input")

        with gr.Tabs():
            with gr.TabItem("Monitor"):
                with gr.Row():
                    phase_text = gr.Textbox(label="Phase", interactive=False)
                    version_text = gr.Textbox(label="Bible Version", interactive=False)
                    start_btn = gr.Button("Start Production")
                gr.HTML('<div id="dag-container" style="height:500px; border:1px solid #ccc;"></div>')
                agent_detail = gr.HTML("Click a node for details.")

            with gr.TabItem("Approvals"):
                approval_gallery = gr.Gallery(label="Assets to Approve")
                revision_notes = gr.Textbox(label="Revision Notes")
                with gr.Row():
                    approve_btn = gr.Button("Approve")
                    revise_btn = gr.Button("Revise")
                    reject_btn = gr.Button("Reject")
                approval_feedback = gr.Textbox(visible=False)

            with gr.TabItem("Errors"):
                error_df = gr.DataFrame(headers=["Shot","Symptom","Severity","Asset"], interactive=True)
                with gr.Row():
                    faulty_frame = gr.Image(label="Faulty Frame")
                    mask_image = gr.Image(label="Mask")
                root_cause_text = gr.Textbox(label="Root Cause")
                with gr.Row():
                    accept_error_btn = gr.Button("Accept Error")
                    rerun_btn = gr.Button("Re-run Fix")

            with gr.TabItem("Film Bible"):
                version_dropdown = gr.Dropdown(choices=["v0001"], value="v0001", label="Version")
                bible_json_editor = gr.JSON(label="Bible Content", value={})
                proposal_table = gr.DataFrame(headers=["Path","Old","New","Affected Agents"], interactive=True)
                with gr.Row():
                    apply_btn = gr.Button("Apply Selected Changes")
                    discard_btn = gr.Button("Discard All")
                    rollback_btn = gr.Button("Rollback to Selected Version")
                with gr.Accordion("Prompt Interpreter", open=False):
                    prompt_input = gr.Textbox(label="Describe changes in natural language")
                    interpret_btn = gr.Button("Interpret")
                    interpreter_status = gr.Markdown("")

            with gr.TabItem("Settings"):
                provider_dd = gr.Dropdown(
                    choices=["Ollama (local)","LM Studio (local)","Groq (cloud)","Custom OpenAI-compatible"],
                    value="Ollama (local)", label="LLM Provider"
                )
                model_txt = gr.Textbox(label="Model Name", value="llama3.1:8b")
                base_url_txt = gr.Textbox(label="Base URL", value="http://localhost:11434")
                api_key_txt = gr.Textbox(label="API Key (if needed)", type="password")
                test_llm_btn = gr.Button("Test Connection")
                llm_status = gr.Textbox(label="LLM Status", interactive=False)

        # ---- Polling ----
        demo.load(
            fn=poll_updates,
            outputs=[phase_text, version_text, dag_data_text, agent_detail, approval_gallery, error_df, version_dropdown, bible_json_editor],
            every=1
        )

        # ---- Events ----
        start_btn.click(fn=start_production, inputs=[provider_dd, model_txt, base_url_txt, api_key_txt], outputs=[phase_text])
        dag_data_text.change(fn=None, js="(val) => initNetwork(val)", outputs=None)
        clicked_agent_text.change(fn=on_agent_click, inputs=clicked_agent_text, outputs=agent_detail)
        approve_btn.click(fn=handle_approval, inputs=[gr.State("approved"), revision_notes], outputs=approval_feedback)
        revise_btn.click(fn=handle_approval, inputs=[gr.State("revised"), revision_notes], outputs=approval_feedback)
        reject_btn.click(fn=handle_approval, inputs=[gr.State("rejected"), revision_notes], outputs=approval_feedback)
        test_llm_btn.click(fn=test_llm_connection, inputs=[provider_dd, model_txt, base_url_txt, api_key_txt], outputs=llm_status)

    return demo


# ---------- Callbacks ----------
def start_production(provider_name, model, base_url, api_key):
    global llm_provider, orchestrator, state, bible, cache, providers

    # Build LLM provider
    if provider_name == "Ollama (local)":
        llm_provider = OllamaProvider(model, base_url)
    else:
        llm_provider = OpenAICompatibleProvider(model, base_url, api_key)

    # Initialize Bible & Cache
    bible = FilmBible(Path("./film_bible"))
    cache = ContentCache(Path("./cache"))

    # Build registry & graph
    registry = build_registry("cinematic")
    graph = build_dependency_graph("cinematic")

    # Collect all available providers
    providers = {
        "llm": llm_provider,
        "tts": XTTSv2Provider(),
        "image": ComfyUIProvider(),
        "render_engine": ComfyUIRenderProvider(),
        "physics": SimplePhysicsProvider(),
        "vfx": DiffusionVFXProvider(),
        "music": MusicGenProvider(),
        "audio_fx": AudioLDM2Provider(),
        "assembly": TextFallbackAssemblyProvider(),  # safe default
    }

    orchestrator = Orchestrator(
        bible=bible, cache=cache, registry=registry, graph=graph,
        mode="cinematic", llm_provider=llm_provider, providers=providers,
        event_callback=lambda e, d: event_queue.put((e, d)),
        approval_callback=_request_approval,
    )

    state.running = True
    threading.Thread(target=orchestrator.produce_film, args=("script.fountain",), daemon=True).start()
    return "Production started"


def _request_approval(agent_name, assets):
    state.pending_approvals = [{"agent": agent_name, "assets": assets}]
    approval_event.clear()
    approval_event.wait()
    return approval_result


def handle_approval(action_state, notes):
    global approval_result
    approval_result = {"action": action_state, "notes": notes}
    approval_event.set()
    state.pending_approvals = []
    return "ok"


def poll_updates():
    while not event_queue.empty():
        ev_type, data = event_queue.get_nowait()
        if ev_type == "phase_changed":
            state.phase = data["phase"]
        elif ev_type == "agent_started":
            state.agent_status[data["agent_name"]] = {"status": "running"}
        elif ev_type == "agent_completed":
            state.agent_status[data["agent_name"]] = {"status": "cached" if data.get("cached") else "re-run"}
        elif ev_type == "bible_version":
            state.current_version = data["version"]

    graph = orchestrator.graph if orchestrator else build_dependency_graph("cinematic")
    dag_json = build_dag_json(state.agent_status, graph)
    gallery_imgs = state.pending_approvals[0].get("assets", []) if state.pending_approvals else []
    error_rows = [[e.get("shot_id",""), e.get("symptom",""), e.get("severity",""), e.get("asset_id","")] for e in state.errors]
    versions = bible.list_versions() if bible else ["v0001"]
    bible_data = bible.read(state.current_version) if bible else {}

    return (state.phase, state.current_version, dag_json, "<p>Click a node</p>", gallery_imgs, error_rows, versions, bible_data)


def on_agent_click(agent_name):
    info = state.agent_status.get(agent_name, {})
    return f"<h3>{agent_name}</h3><p>Status: {info.get('status', 'unknown')}</p>"


def test_llm_connection(provider_name, model, url, api_key):
    try:
        if provider_name == "Ollama (local)":
            prov = OllamaProvider(model, url)
        else:
            prov = OpenAICompatibleProvider(model, url, api_key)
        ok = prov.health_check()
        return "✅ Connected" if ok else "❌ Failed"
    except Exception as e:
        return f"❌ {e}"


# ---------- Launch ----------
if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
