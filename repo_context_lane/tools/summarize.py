import json
import datetime
from pathlib import Path
from typing import Dict, Any, List

def summarize_graph(graph_path: Path, output_root: Path, dry_run: bool = True) -> Dict[str, Any]:
    graph_path = graph_path.resolve()
    
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")
    
    # Deriving project_id from path
    # Expected path: D:\graphify-results\<project_id>\graphify-out\graph.json
    project_id = "unknown"
    parts = graph_path.parts
    for i, part in enumerate(parts):
        if part == "graphify-results" and i + 1 < len(parts):
            project_id = parts[i+1]
            break
    if project_id == "unknown":
        project_id = graph_path.parent.parent.name # Fallback
        
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse graph.json: {e}")

    # Defensive parsing
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    communities = graph_data.get("communities", [])
    
    # Identify high-degree nodes
    node_degrees = {}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source:
            node_degrees[source] = node_degrees.get(source, 0) + 1
        if target:
            node_degrees[target] = node_degrees.get(target, 0) + 1
            
    sorted_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)
    high_degree_nodes = [{"id": n[0], "degree": n[1]} for n in sorted_nodes[:10]]
    
    # Identify entrypoints (heuristics based on names)
    entrypoints = []
    for node in nodes:
        node_id = str(node.get("id", ""))
        lower_id = node_id.lower()
        if any(x in lower_id for x in ["main", "index", "app", "router", "entry", "start"]):
            entrypoints.append(node_id)
            
    summary = {
        "project_id": project_id,
        "graph_path": str(graph_path),
        "timestamp": datetime.datetime.now().isoformat(),
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "communities": len(communities)
        },
        "high_degree_nodes": high_degree_nodes,
        "suggested_entrypoints": entrypoints[:10],
        "recommendations": [
            "Use communities for high-level context",
            "Focus on high-degree nodes for architectural overview"
        ]
    }
    
    if not dry_run:
        summary_dir = output_root / "graph_summaries"
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_path = summary_dir / f"{project_id}_summary.json"
        report_path = summary_dir / f"{project_id}_summary.md"
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
            
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Graph Summary: {project_id}\n\n")
            f.write(f"- **Graph Source**: `{graph_path}`\n")
            f.write(f"- **Timestamp**: {summary['timestamp']}\n\n")
            f.write("## Counts\n")
            f.write(f"- **Nodes**: {summary['counts']['nodes']}\n")
            f.write(f"- **Edges**: {summary['counts']['edges']}\n")
            f.write(f"- **Communities**: {summary['counts']['communities']}\n\n")
            
            if high_degree_nodes:
                f.write("## High-Degree Nodes (Potential Hubs)\n")
                for n in high_degree_nodes:
                    f.write(f"- `{n['id']}` (degree: {n['degree']})\n")
                f.write("\n")
                
            if entrypoints:
                f.write("## Likely Entrypoints\n")
                for e in entrypoints[:10]:
                    f.write(f"- `{e}`\n")
                f.write("\n")
                
            f.write("## Recommendations\n")
            for rec in summary["recommendations"]:
                f.write(f"- {rec}\n")
                
    return summary

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        o = Path("repo_context_lane")
        res = summarize_graph(p, o, dry_run=False)
        print(json.dumps(res, indent=2))
