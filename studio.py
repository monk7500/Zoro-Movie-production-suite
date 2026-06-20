import gradio as gr
import json, threading, time, queue, os
from pathlib import Path
from datetime import datetime

# ========== GLOBAL STATE ==========
event_queue = queue.Queue()
approval_event = threading.Event()
approval_result = None
orchestrator = None
bible = None
cache = None

class DashboardState:
    def __init__(self):
        self.phase = "idle"
        self.current_version = "v0001"
        self.agent_status = {}
        self.pending_approvals = []
        self.pending_proposals = []
        self.errors = []
        self.running = False

state = DashboardState()

# ========== DUMMY PROVIDER (replace with real imports) ==========
class OllamaProvider:
    def __init__(self, model, url): self.model, self.url = model, url
    def generate(self, prompt, system="", temperature=0.7, max_tokens=4096):
        return f"Mock response for: {prompt[:50]}..."
    def health_check(self): return True

# ========== BUILD UI ==========
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
        # Hidden fields
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

        # Polling timer
        demo.load(
            fn=poll_updates,
            outputs=[phase_text, version_text, dag_data_text, agent_detail, approval_gallery, error_df, version_dropdown, bible_json_editor],
            every=1
        )

        # Wire buttons
        start_btn.click(
            fn=start_production,
            inputs=[provider_dd, model_txt, base_url_txt, api_key_txt],
            outputs=[phase_text]
        )
        dag_data_text.change(fn=None, js="(val) => initNetwork(val)", outputs=None)
        clicked_agent_text.change(fn=on_agent_click, inputs=clicked_agent_text, outputs=agent_detail)
        approve_btn.click(fn=handle_approval, inputs=[gr.State("approved"), revision_notes], outputs=approval_feedback)
        revise_btn.click(fn=handle_approval, inputs=[gr.State("revised"), revision_notes], outputs=approval_feedback)
        reject_btn.click(fn=handle_approval, inputs=[gr.State("rejected"), revision_notes], outputs=approval_feedback)
        test_llm_btn.click(fn=test_llm_connection, inputs=[provider_dd, model_txt, base_url_txt, api_key_txt], outputs=llm_status)
        # Bible editing callbacks (simplified)
        apply_btn.click(fn=apply_proposals, inputs=proposal_table, outputs=[bible_json_editor, proposal_table, version_dropdown])
        rollback_btn.click(fn=rollback_version, inputs=version_dropdown, outputs=[bible_json_editor, version_dropdown])
        interpret_btn.click(fn=on_interpret_prompt, inputs=[prompt_input], outputs=[interpreter_status, proposal_table])

    return demo

# ========== CALLBACK FUNCTIONS ==========
def start_production(provider_name, model, base_url, api_key):
    global llm_provider, state
    if provider_name == "Ollama (local)":
        llm_provider = OllamaProvider(model, base_url)
    state.running = True
    state.phase = "Starting..."
    return state.phase

def poll_updates():
    while not event_queue.empty():
        ev_type, data = event_queue.get_nowait()
        if ev_type == "phase_changed":
            state.phase = data["phase"]
        elif ev_type == "bible_version":
            state.current_version = data["version"]
    dag_json = json.dumps({"nodes":[{"id":"Script Parser","label":"Script Parser","color":"blue"}],"edges":[]})
    versions = ["v0001"]
    return (state.phase, state.current_version, dag_json, "<p>Click a node</p>", [], [], versions, {})

def on_agent_click(agent_name):
    return f"<h3>{agent_name}</h3><p>Status: idle</p>"

def handle_approval(action_state, notes):
    global approval_result
    approval_result = {"action": action_state, "notes": notes}
    approval_event.set()
    state.pending_approvals = []
    return "ok"

def test_llm_connection(provider_name, model, url, api_key):
    try:
        if provider_name == "Ollama (local)":
            prov = OllamaProvider(model, url)
        else:
            prov = OllamaProvider(model, url)  # simplified
        ok = prov.health_check()
        return "✅ Connected" if ok else "❌ Failed"
    except Exception as e:
        return f"❌ {e}"

def apply_proposals(selected_rows):
    return {}, [], gr.update(choices=["v0001"])

def rollback_version(version):
    return {}, gr.update(choices=["v0001"])

def on_interpret_prompt(prompt):
    return "Interpretation complete.", []

# ========== LAUNCH ==========
if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
