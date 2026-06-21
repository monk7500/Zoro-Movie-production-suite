"""
Complete agent registry – maps every agent name to its input contract,
model version, required providers, and run function.
"""

import agents.script_parser as script_parser
import agents.subtext_analyzer as subtext_analyzer
import agents.wardrobe_parser as wardrobe_parser
import agents.environment_state as environment_state
import agents.character_visual_designer as character_visual_designer
import agents.character_persona as character_persona
import agents.voice_profile as voice_profile
import agents.anatomical_consultant as anatomical_consultant
import agents.location_scout as location_scout
import agents.world_rules as world_rules
import agents.prop_cataloger as prop_cataloger
import agents.geography_definition as geography_definition
import agents.prop_classifier as prop_classifier
import agents.style_guide_curator as style_guide_curator
import agents.storyboard_artist as storyboard_artist
import agents.cinematographer as cinematographer
import agents.dialogue_breakdown as dialogue_breakdown
import agents.voice_performance as voice_performance
import agents.foley_designer as foley_designer
import agents.ambience as ambience
import agents.score_blueprint as score_blueprint
import agents.composer as composer
import agents.layout as layout
import agents.action_skills as action_skills
import agents.animation as animation
import agents.physics_simulator as physics_simulator
import agents.environment_fx as environment_fx
import agents.lighting_consistency as lighting_consistency
import agents.population_generator as population_generator
import agents.dynamic_prop_tracker as dynamic_prop_tracker
import agents.render as render
import agents.editor as editor
import agents.vfx as vfx
import agents.color_grading as color_grading
import agents.lipsync as lipsync
import agents.final_assembly as final_assembly


def build_registry(mode: str = "cinematic") -> dict:
    """
    Returns the full agent registry.
    Narration mode disables dialogue/foley/lip‑sync and enables
    Narrative Script Compiler + Narrator Voice agents.
    """
    registry = {
        "Script Parser": {
            "input_spec": {"script_raw": "meta.script_raw", "mode": "meta.mode"},
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": script_parser.run,
        },
        "Subtext & Tone Analyzer": {
            "input_spec": {"parsed_script": "parsed_script"},
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": subtext_analyzer.run,
        },
        "Wardrobe & Physical Change Parser": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": wardrobe_parser.run,
        },
        "Environment State Agent": {
            "input_spec": {"parsed_script": "parsed_script"},
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": environment_state.run,
        },
        "Character Visual Designer": {
            "input_spec": {
                "characters": "parsed_script.characters",
                "wardrobe_timeline": "wardrobe_timeline.characters",
                "style_guide": "style_guide",
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": ["image"],
            "max_retries": 2,
            "retry_delay": 5.0,
            "run_func": character_visual_designer.run,
        },
        "Character Persona Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": character_persona.run,
        },
        "Voice Profile Agent": {
            "input_spec": {
                "characters": "parsed_script.characters",
                "personas": "character_personas.characters",
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": voice_profile.run,
        },
        "Anatomical Consultant": {
            "input_spec": {
                "character_visuals": "character_visuals",
                "world_rules": "world_rules",
            },
            "model_version": "1.0",
            "required_providers": ["vision"],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": anatomical_consultant.run,
        },
        "Location Scout Agent": {
            "input_spec": {
                "scenes": "parsed_script.scenes",
                "environment_timeline": "environment_timeline.scenes",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": location_scout.run,
        },
        "World Rules Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "world_guide": "meta.world_guide",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": world_rules.run,
        },
        "Prop & Set Dressing Cataloger": {
            "input_spec": {
                "entities": "parsed_script.entities",
                "props": "parsed_script.props",
                "location_profiles": "location_profiles.locations",
                "world_rules": "world_rules",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": prop_cataloger.run,
        },
        "Geography Definition Agent": {
            "input_spec": {
                "location_profiles": "location_profiles.locations",
                "prop_catalog": "prop_catalog.props",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": geography_definition.run,
        },
        "Prop Classifier Agent": {
            "input_spec": {
                "prop_catalog": "prop_catalog.props",
                "geography": "geography.locations",
                "parsed_script": "parsed_script",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": prop_classifier.run,
        },
        "Style Guide Curator": {
            "input_spec": {
                "tone_analysis": "tone_analysis",
                "references": "inputs.references.style_guide",
                "director_notes": "meta.director_notes",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": style_guide_curator.run,
        },
        "Storyboard Artist": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "character_visuals": "character_visuals",
                "location_profiles": "location_profiles.locations",
                "geography": "geography.locations",
                "style_guide": "style_guide",
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": ["image"],
            "max_retries": 2,
            "retry_delay": 3.0,
            "run_func": storyboard_artist.run,
        },
        "Cinematographer Agent": {
            "input_spec": {
                "storyboard": "storyboard.shots",
                "style_guide": "style_guide",
                "geography": "geography.locations",
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": cinematographer.run,
        },
        "Dialogue Breakdown Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "tone_analysis": "tone_analysis",
                "personas": "character_personas.characters",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": dialogue_breakdown.run,
        },
        "Voice Performance Agent": {
            "input_spec": {
                "voice_profiles": "voice_profiles.characters",
                "dialogue_scenes": "dialogue_breakdown.scenes",
                "character_dialogue_index": "dialogue_breakdown.characters",
            },
            "model_version": "1.0",
            "required_providers": ["tts"],
            "max_retries": 2,
            "retry_delay": 2.0,
            "run_func": voice_performance.run,
        },
        "Foley Designer Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "prop_classification": "prop_classification.props",
                "environment_timeline": "environment_timeline.scenes",
                "location_profiles": "location_profiles.locations",
            },
            "model_version": "1.0",
            "required_providers": ["audio_fx"],
            "max_retries": 2,
            "retry_delay": 2.0,
            "run_func": foley_designer.run,
        },
        "Ambience & Soundscape Agent": {
            "input_spec": {
                "environment_timeline": "environment_timeline.scenes",
                "location_profiles": "location_profiles.locations",
                "parsed_script": "parsed_script",
            },
            "model_version": "1.0",
            "required_providers": ["audio_fx"],
            "max_retries": 2,
            "retry_delay": 2.0,
            "run_func": ambience.run,
        },
        "Score Blueprint Agent": {
            "input_spec": {
                "tone_analysis": "tone_analysis",
                "parsed_script": "parsed_script",
                "temp_track_refs": "inputs.references.temp_tracks",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": score_blueprint.run,
        },
        "Composer Agent": {
            "input_spec": {
                "score_blueprint": "score_blueprint",
                "tone_analysis": "tone_analysis",
                "parsed_script": "parsed_script",
            },
            "model_version": "1.0",
            "required_providers": ["music"],
            "max_retries": 2,
            "retry_delay": 3.0,
            "run_func": composer.run,
        },
        "Layout Agent": {
            "input_spec": {
                "storyboard": "storyboard.shots",
                "geography": "geography.locations",
                "cinematography": "cinematography.shots",
                "character_visuals": "character_visuals.characters",
                "prop_classification": "prop_classification.props",
                "wardrobe_timeline": "wardrobe_timeline.characters",
                "parsed_script": "parsed_script",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": layout.run,
        },
        "Action Skills Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "character_personas": "character_personas.characters",
                "wardrobe_timeline": "wardrobe_timeline.characters",
                "world_rules": "world_rules",
                "geography": "geography.locations",
                "prop_classification": "prop_classification.props",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": action_skills.run,
        },
        "Animation Agent": {
            "input_spec": {
                "layout": "layout.shots",
                "dialogue_breakdown": "dialogue_breakdown.scenes",
                "voice_audio": "voice_audio.characters",
                "character_personas": "character_personas.characters",
                "wardrobe_timeline": "wardrobe_timeline.characters",
                "cinematography": "cinematography.shots",
                "action_choreography": "action_choreography.scenes",
                "mode": "meta.mode",
            },
            "model_version": "1.0",
            "required_providers": ["motion", "facial_animation"],
            "max_retries": 2,
            "retry_delay": 3.0,
            "run_func": animation.run,
        },
        "Physics Simulator Agent": {
            "input_spec": {
                "layout": "layout.shots",
                "animation": "animation.shots",
                "prop_classification": "prop_classification.props",
                "geography": "geography.locations",
                "character_visuals": "character_visuals.characters",
            },
            "model_version": "1.0",
            "required_providers": ["physics"],
            "max_retries": 2,
            "retry_delay": 5.0,
            "run_func": physics_simulator.run,
        },
        "Environmental Effects Simulator": {
            "input_spec": {
                "environment_timeline": "environment_timeline.scenes",
                "geography": "geography.locations",
                "cinematography": "cinematography.shots",
                "parsed_script": "parsed_script",
            },
            "model_version": "1.0",
            "required_providers": ["environment_fx"],
            "max_retries": 2,
            "retry_delay": 5.0,
            "run_func": environment_fx.run,
        },
        "Lighting Consistency Agent": {
            "input_spec": {
                "cinematography": "cinematography.shots",
                "geography": "geography.locations",
                "layout": "layout.shots",
                "style_guide": "style_guide",
                "environment_timeline": "environment_timeline.scenes",
            },
            "model_version": "1.0",
            "required_providers": ["render_engine"],
            "max_retries": 2,
            "retry_delay": 2.0,
            "run_func": lighting_consistency.run,
        },
        "Population Generator Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "geography": "geography.locations",
                "layout": "layout.shots",
                "environment_timeline": "environment_timeline.scenes",
                "style_guide": "style_guide",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": population_generator.run,
        },
        "Dynamic Prop Tracker Agent": {
            "input_spec": {
                "prop_classification": "prop_classification.props",
                "parsed_script": "parsed_script",
                "layout": "layout.shots",
                "wardrobe_timeline": "wardrobe_timeline.characters",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": dynamic_prop_tracker.run,
        },
        "Render Agent": {
            "input_spec": {
                "layout": "layout.shots",
                "animation": "animation.shots",
                "physics": "physics.shots",
                "lighting": "lighting.shots",
                "environment_fx": "environment_fx.scenes",
                "population": "population.shots",
                "character_visuals": "character_visuals.characters",
                "prop_tracker": "prop_tracker.props",
                "action_choreography": "action_choreography.scenes",
                "cinematography": "cinematography.shots",
                "style_guide": "style_guide",
                "geography": "geography.locations",
                "rework_mask": "validator_fixes.SHOT_ID.region",
            },
            "model_version": "1.0",
            "required_providers": ["render_engine"],
            "max_retries": 2,
            "retry_delay": 10.0,
            "run_func": render.run,
        },
        "Editor Agent": {
            "input_spec": {
                "render_manifest": "renders.shots",
                "storyboard": "storyboard.shots",
                "cinematography": "cinematography.shots",
                "audio_manifests": {
                    "voice": "voice_audio.characters",
                    "foley": "foley.scenes",
                    "ambience": "ambience.scenes",
                    "score": "score_audio.scenes",
                },
                "tone_analysis": "tone_analysis",
            },
            "model_version": "1.0",
            "required_providers": [],
            "max_retries": 2,
            "retry_delay": 1.0,
            "run_func": editor.run,
        },
        "VFX Agent": {
            "input_spec": {
                "parsed_script": "parsed_script",
                "render_manifest": "renders.shots",
                "action_choreography": "action_choreography.scenes",
                "world_rules": "world_rules",
                "style_guide": "style_guide",
                "cinematography": "cinematography.shots",
            },
            "model_version": "1.0",
            "required_providers": ["vfx"],
            "max_retries": 2,
            "retry_delay": 5.0,
            "run_func": vfx.run,
        },
        "Color Grading Agent": {
            "input_spec": {
                "vfx_manifest": "vfx.shots",
                "render_manifest": "renders.shots",
                "style_guide": "style_guide",
                "cinematography": "cinematography.shots",
            },
            "model_version": "1.0",
            "required_providers": ["color_grading"],
            "max_retries": 2,
            "retry_delay": 2.0,
            "run_func": color_grading.run,
        },
        "Lip‑Sync & Audio Alignment Agent": {
            "input_spec": {
                "graded_manifest": "graded.shots",
                "voice_manifest": "voice_audio.characters",
                "animation": "animation.shots",
                "dialogue_breakdown": "dialogue_breakdown.scenes",
                "layout": "layout.shots",
            },
            "model_version": "1.0",
            "required_providers": ["lip_sync"],
            "max_retries": 2,
            "retry_delay": 5.0,
            "run_func": lipsync.run,
        },
        "Final Assembly Agent": {
            "input_spec": {
                "edit_manifest": "edit",
                "lipsync_manifest": "lipsync.shots",
                "grade_manifest": "graded.shots",
                "vfx_manifest": "vfx.shots",
                "audio_manifests": {
                    "voice": "voice_audio.characters",
                    "foley": "foley.scenes",
                    "ambience": "ambience.scenes",
                    "score": "score_audio.scenes",
                },
                "parsed_script
