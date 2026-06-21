"""
Verifies that all core, agent, and provider modules import without errors.
Run with: python tests/test_imports.py
"""

import sys, os

def test_core_imports():
    from core.bible import FilmBible
    from core.cache import ContentCache
    from core.orchestrator import Orchestrator, AgentRunner
    from core.graph_builder import build_dependency_graph
    from core.dependency import DataDependencyIndex
    from core.fault_propagation import FaultPropagationDecider
    from core.quality_inspector import QualityInspector
    from core.continuity_watchdog import ContinuityWatchdog
    print("✅ core imports OK")

def test_provider_imports():
    from providers.llm import OllamaProvider, OpenAICompatibleProvider
    from providers.tts import XTTSv2Provider, PiperProvider, ElevenLabsTTS, OpenAITTS
    from providers.image_gen import ComfyUIProvider
    from providers.render_engine import ComfyUIRenderProvider, BlenderRenderProvider
    from providers.physics import BlenderPhysicsProvider, SimplePhysicsProvider
    from providers.vfx import DiffusionVFXProvider
    from providers.music import MusicGenProvider
    from providers.audio_fx import AudioLDM2Provider
    from providers.assembly import FFmpegAssemblyProvider, TextFallbackAssemblyProvider
    print("✅ providers imports OK")

def test_agent_imports():
    # Import all 36 agent modules to verify they parse without errors
    import agents.script_parser
    import agents.subtext_analyzer
    import agents.wardrobe_parser
    import agents.environment_state
    import agents.character_visual_designer
    import agents.character_persona
    import agents.voice_profile
    import agents.anatomical_consultant
    import agents.location_scout
    import agents.world_rules
    import agents.prop_cataloger
    import agents.geography_definition
    import agents.prop_classifier
    import agents.style_guide_curator
    import agents.storyboard_artist
    import agents.cinematographer
    import agents.dialogue_breakdown
    import agents.voice_performance
    import agents.foley_designer
    import agents.ambience
    import agents.score_blueprint
    import agents.composer
    import agents.layout
    import agents.action_skills
    import agents.animation
    import agents.physics_simulator
    import agents.environment_fx
    import agents.lighting_consistency
    import agents.population_generator
    import agents.dynamic_prop_tracker
    import agents.render
    import agents.editor
    import agents.vfx
    import agents.color_grading
    import agents.lipsync
    import agents.final_assembly
    from agents.registry import build_registry
    print("✅ agents imports OK")

def test_registry_and_graph():
    registry = build_registry("cinematic")
    assert "Script Parser" in registry
    assert registry["Script Parser"]["model_version"] == "1.0"
    from core.graph_builder import build_dependency_graph
    graph = build_dependency_graph("cinematic")
    assert "Script Parser" in graph.nodes
    assert "Final Assembly Agent" in graph.nodes
    print("✅ registry & graph OK")

if __name__ == "__main__":
    test_core_imports()
    test_provider_imports()
    test_agent_imports()
    test_registry_and_graph()
    print("\n🎬 All imports successful. The AI Film Studio is ready.")
