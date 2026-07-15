from __future__ import annotations
import itertools
import json
from collections import defaultdict
from typing import Any
from core import Complex, Point

type ComplexEnv = dict[str, Complex]

def _extract_complexes(env: ComplexEnv, filter_targets: bool = False) -> ComplexEnv:
    """Filters and extracts valid geometric complexes from the environment."""
    render_targets = env.get("__render_targets__") if filter_targets else None
    return {
        name: val for name, val in env.items()
        if name != "__render_targets__"
        and (render_targets is None or name in render_targets)
        and hasattr(val, "simplices")
    }

def _build_downward_closure(complexes: ComplexEnv) -> tuple[list[frozenset], dict[frozenset, str], dict[frozenset, set[str]]]:
    """Generates all sub-simplices, assigning unique string IDs and tracking their source variable atoms."""
    simplex_atoms: dict[frozenset, set[str]] = defaultdict(set)
    
    for name, complex_obj in complexes.items():
        for max_simplex in complex_obj.simplices:
            pts = list(max_simplex)
            # Generate all dimensional subsets (vertices, edges, faces)
            for r in range(1, len(pts) + 1):
                for sub_combo in itertools.combinations(pts, r):
                    simplex_atoms[frozenset(sub_combo)].add(name)
                    
    sorted_simplices = sorted(simplex_atoms.keys(), key=len)
    simplex_to_id = {simp: str(idx) for idx, simp in enumerate(sorted_simplices)}
    return sorted_simplices, simplex_to_id, simplex_atoms

def serialize_environment(env: ComplexEnv) -> dict[str, Any]:
    """Converts the active environment to JSON, respecting explicit render primitives."""
    # 1. Generate IDs using the ENTIRE environment so they match PolyLogicA's Poset exactly
    global_complexes = _extract_complexes(env, filter_targets=False)
    _, simplex_to_id, _ = _build_downward_closure(global_complexes)
    
    # 2. Filter down to only the complexes explicitly marked for rendering
    render_complexes = _extract_complexes(env, filter_targets=True)
    
    complexes_json = {}
    for name, val in render_complexes.items():
        verts = list(val.vertices)
        pt_to_id = {pt: f"v{i}" for i, pt in enumerate(verts)}
        
        # Format coordinate map - UPDATED HERE
        coords_dict = {
            pt_to_id[pt]: {
                "coords": list(pt.coords), # Dynamically captures all dimensions
                "id": simplex_to_id[frozenset([pt])]
            }
            for pt in verts
        }
        
        # Format structural simplices list
        simplices_list = []
        for max_simplex in val.simplices:
            pts = list(max_simplex)
            simplex_data = {
                "vertices": [pt_to_id[p] for p in pts],
                "id": simplex_to_id[frozenset(pts)],
                "edges": []
            }
            
            # Explicitly capture sub-boundary constraints for 2-simplices (triangles)
            if len(pts) == 3:
                for combo in itertools.combinations(pts, 2):
                    simplex_data["edges"].append({
                        "vertices": [pt_to_id[p] for p in combo],
                        "id": simplex_to_id[frozenset(combo)]
                    })
                    
            simplices_list.append(simplex_data)
            
        complexes_json[name] = {
            "coords": coords_dict,
            "simplices": simplices_list
        }
        
    return {"success": True, "complexes": complexes_json}

def serialize_polylogica_poset(env: ComplexEnv) -> dict[str, Any]:
    """Converts the active environment to PolyLogicA's Poset JSON schema."""
    complexes = _extract_complexes(env, filter_targets=False)
    sorted_simplices, simplex_to_id, simplex_atoms = _build_downward_closure(complexes)
    
    # Bucket simplices by length to optimize the upper-cover 'up' lookup performance
    simplices_by_len = defaultdict(list)
    for simp in sorted_simplices:
        simplices_by_len[len(simp)].append(simp)
        
    poset_points = []
    for simp in sorted_simplices:
        # Instead of scanning everything, only check elements exactly 1 dimension higher
        up_list = [
            simplex_to_id[other_simp]
            for other_simp in simplices_by_len[len(simp) + 1]
            if simp.issubset(other_simp)
        ]
        
        poset_points.append({
            "id": simplex_to_id[simp],
            "atoms": list(simplex_atoms[simp]),
            "up": up_list
        })
        
    return {"points": poset_points}


def export_polylogica_json(env: ComplexEnv, filename: str = "dsl1.json") -> None:
    """Writes the geometric environment to PolyLogicA poset format."""
    json_data = serialize_polylogica_poset(env)
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=4)
    print(f"Successfully exported PolyLogicA Poset environment to {filename}")