"""
Builds the directed acyclic graph (DAG) for the agent pipeline.
Used by the orchestrator and the DataDependencyIndex.
"""

import networkx as nx


def build_dependency_graph(mode: str = "cinematic") -> nx.DiGraph:
    """Create the full dependency graph for the given mode.

    Edges go from upstream to downstream (A → B means A must run before B).
    """
    G = nx.DiGraph()

    # ---- Script Ingestion ----
    G.add_edges_from([
        ("Script Parser", "Subtext & Tone Analyzer"),
        ("Script Parser", "Wardrobe & Physical Change Parser"),
        ("Script Parser", "Environment State Agent"),
        ("Script Parser", "Character Persona Agent"),
        ("Script Parser", "World Rules Agent"),
        ("Script Parser", "Location Scout Agent"),
        ("Script Parser", "Action Skills Agent"),
        ("Script Parser", "Prop & Set Dressing Cataloger"),
    ])

    # ---- Character Pre‑Production ----
    G.add_edges_from([
        ("Wardrobe & Physical Change Parser", "Character Visual Designer"),
        ("Subtext & Tone Analyzer", "Character Visual Designer"),
        ("Style Guide Curator", "Character Visual Designer"),
        ("Subtext & Tone Analyzer", "Character Persona Agent"),
        ("Character Persona Agent", "Voice Profile Agent"),
        ("Character Visual Designer", "Anatomical Consultant"),
        ("World Rules Agent", "Anatomical Consultant"),
    ])

    # ---- World Building ----
    G.add_edges_from([
        ("Environment State Agent", "Location Scout Agent"),
        ("Location Scout Agent", "Geography Definition Agent"),
        ("Prop & Set Dressing Cataloger", "Geography Definition Agent"),
        ("Location Scout Agent", "Prop & Set Dressing Cataloger"),
        ("World Rules Agent", "Prop & Set Dressing Cataloger"),
        ("Geography Definition Agent", "Prop Classifier Agent"),
        ("Prop & Set Dressing Cataloger", "Prop Classifier Agent"),
    ])

    # ---- Visual Pre‑Production ----
    G.add_edges_from([
        ("Subtext & Tone Analyzer", "Style Guide Curator"),
        ("Character Visual Designer", "Storyboard Artist"),
        ("Location Scout Agent", "Storyboard Artist"),
        ("Geography Definition Agent", "Storyboard Artist"),
        ("Style Guide Curator", "Storyboard Artist"),
        ("Storyboard Artist", "Cinematographer Agent"),
        ("Geography Definition Agent", "Cinematographer Agent"),
        ("Style Guide Curator", "Cinematographer Agent"),
    ])

    # ---- Audio Pre‑Production (cinematic only) ----
    if mode == "cinematic":
        G.add_edges_from([
            ("Character Persona Agent", "Dialogue Breakdown Agent"),
            ("Subtext & Tone Analyzer", "Dialogue Breakdown Agent"),
            ("Dialogue Breakdown Agent", "Voice Performance Agent"),
            ("Voice Profile Agent", "Voice Performance Agent"),
            ("Prop Classifier Agent", "Foley Designer Agent"),
            ("Environment State Agent", "Foley Designer Agent"),
            ("Location Scout Agent", "Foley Designer Agent"),
            ("Environment State Agent", "Ambience & Soundscape Agent"),
            ("Location Scout Agent", "Ambience & Soundscape Agent"),
            ("Subtext & Tone Analyzer", "Score Blueprint Agent"),
            ("Score Blueprint Agent", "Composer Agent"),
        ])

    # ---- Production ----
    G.add_edges_from([
        ("Storyboard Artist", "Layout Agent"),
        ("Geography Definition Agent", "Layout Agent"),
        ("Cinematographer Agent", "Layout Agent"),
        ("Character Visual Designer", "Layout Agent"),
        ("Prop Classifier Agent", "Layout Agent"),
        ("Wardrobe & Physical Change Parser", "Layout Agent"),
        ("Character Persona Agent", "Action Skills Agent"),
        ("Wardrobe & Physical Change Parser", "Action Skills Agent"),
        ("World Rules Agent", "Action Skills Agent"),
        ("Geography Definition Agent", "Action Skills Agent"),
        ("Prop Classifier Agent", "Action Skills Agent"),
        ("Layout Agent", "Animation Agent"),
        ("Action Skills Agent", "Animation Agent"),
        ("Dialogue Breakdown Agent", "Animation Agent") if mode == "cinematic" else None,
        ("Voice Performance Agent", "Animation Agent") if mode == "cinematic" else None,
        ("Layout Agent", "Physics Simulator Agent"),
        ("Animation Agent", "Physics Simulator Agent"),
        ("Prop Classifier Agent", "Physics Simulator Agent"),
        ("Geography Definition Agent", "Physics Simulator Agent"),
        ("Environment State Agent", "Environmental Effects Simulator"),
        ("Geography Definition Agent", "Environmental Effects Simulator"),
        ("Cinematographer Agent", "Environmental Effects Simulator"),
        ("Cinematographer Agent", "Lighting Consistency Agent"),
        ("Geography Definition Agent", "Lighting Consistency Agent"),
        ("Layout Agent", "Lighting Consistency Agent"),
        ("Style Guide Curator", "Lighting Consistency Agent"),
        ("Environment State Agent", "Lighting Consistency Agent"),
        ("Geography Definition Agent", "Population Generator Agent"),
        ("Layout Agent", "Population Generator Agent"),
        ("Prop Classifier Agent", "Dynamic Prop Tracker Agent"),
        ("Layout Agent", "Dynamic Prop Tracker Agent"),
        ("Wardrobe & Physical Change Parser", "Dynamic Prop Tracker Agent"),
        ("Layout Agent", "Render Agent"),
        ("Animation Agent", "Render Agent"),
        ("Physics Simulator Agent", "Render Agent"),
        ("Lighting Consistency Agent", "Render Agent"),
        ("Environmental Effects Simulator", "Render Agent"),
        ("Population Generator Agent", "Render Agent"),
        ("Character Visual Designer", "Render Agent"),
        ("Dynamic Prop Tracker Agent", "Render Agent"),
        ("Action Skills Agent", "Render Agent"),
        ("Cinematographer Agent", "Render Agent"),
        ("Style Guide Curator", "Render Agent"),
        ("Geography Definition Agent", "Render Agent"),
    ])

    # Remove None edges from conditional adds
    G.remove_edges_from([e for e in G.edges if e is None])

    # ---- Post‑Production ----
    G.add_edges_from([
        ("Render Agent", "Editor Agent"),
        ("Storyboard Artist", "Editor Agent"),
        ("Cinematographer Agent", "Editor Agent"),
        ("Render Agent", "VFX Agent"),
        ("Action Skills Agent", "VFX Agent"),
        ("World Rules Agent", "VFX Agent"),
        ("Style Guide Curator", "VFX Agent"),
        ("Render Agent", "Color Grading Agent"),
        ("VFX Agent", "Color Grading Agent"),
        ("Style Guide Curator", "Color Grading Agent"),
        ("Cinematographer Agent", "Color Grading Agent"),
    ])

    if mode == "cinematic":
        G.add_edges_from([
            ("Color Grading Agent", "Lip‑Sync & Audio Alignment Agent"),
            ("Voice Performance Agent", "Lip‑Sync & Audio Alignment Agent"),
            ("Animation Agent", "Lip‑Sync & Audio Alignment Agent"),
            ("Dialogue Breakdown Agent", "Lip‑Sync & Audio Alignment Agent"),
            ("Layout Agent", "Lip‑Sync & Audio Alignment Agent"),
        ])

    G.add_edges_from([
        ("Editor Agent", "Final Assembly Agent"),
        ("Lip‑Sync & Audio Alignment Agent", "Final Assembly Agent") if mode == "cinematic" else None,
        ("Color Grading Agent", "Final Assembly Agent"),
        ("VFX Agent", "Final Assembly Agent"),
        ("Voice Performance Agent", "Final Assembly Agent") if mode == "cinematic" else None,
        ("Foley Designer Agent", "Final Assembly Agent") if mode == "cinematic" else None,
        ("Ambience & Soundscape Agent", "Final Assembly Agent"),
        ("Composer Agent", "Final Assembly Agent") if mode == "cinematic" else None,
    ])

    G.remove_edges_from([e for e in G.edges if e is None])

    return G
