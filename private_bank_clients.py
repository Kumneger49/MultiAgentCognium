import os
import sys
import json
from typing import Dict, Any

import networkx as nx
from pyvis.network import Network


def load_graph(path: str) -> nx.Graph:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"GraphML not found: {path}")
    return nx.read_graphml(path)


def build_pyvis(G: nx.Graph, physics: bool = False) -> Network:
    net = Network(height="800px", width="100%", bgcolor="#0e1117", font_color="#fafafa")
    # Disable dynamic motion; use repulsion without animation
    if physics:
        net.barnes_hut(gravity=-8000, central_gravity=0.2, spring_length=150, spring_strength=0.01, damping=0.9)
    else:
        net.hrepulsion(node_distance=180, central_gravity=0.0, spring_length=150, spring_strength=0.01, damping=0.95)

    for n, data in G.nodes(data=True):
        label = data.get("entity_id", n)
        title = data.get("description", "")
        group = data.get("entity_type", "entity")
        net.add_node(n, label=label, title=title, group=group)

    for u, v, data in G.edges(data=True):
        desc = data.get("description", "")
        weight = float(data.get("weight", 1.0))
        net.add_edge(u, v, title=desc, value=weight)

    # Turn off vis.js physics entirely and stabilize to avoid jittery motion
    net.set_options(
        """
{
  "nodes": { "shape": "dot", "scaling": {"min": 5, "max": 25} },
  "edges": { "color": {"color": "#999", "highlight": "#f39c12"}, "smooth": false },
  "physics": {
    "enabled": false,
    "stabilization": { "enabled": true, "iterations": 200 }
  },
  "interaction": { "hover": true, "tooltipDelay": 120, "dragNodes": false }
}
        """
    )
    return net


def limit_graph(G: nx.Graph, max_nodes: int) -> nx.Graph:
    if G.number_of_nodes() <= max_nodes:
        return G
    # Simple heuristic: take highest degree nodes first
    nodes_by_deg = sorted(G.degree, key=lambda x: x[1], reverse=True)
    keep = set(n for n, _ in nodes_by_deg[:max_nodes])
    return G.subgraph(keep).copy()


def main():
    graph_path = os.path.join("rag_storage", "graph_chunk_entity_relation.graphml")
    out_html = "private_bank_clients_graph.html"
    max_nodes = 500
    physics = False  # keep static by default to avoid fast moving nodes

    # CLI overrides: private_bank_clients.py [max_nodes] [physics:0/1]
    if len(sys.argv) >= 2:
        try:
            max_nodes = int(sys.argv[1])
        except Exception:
            pass
    if len(sys.argv) >= 3:
        physics = bool(int(sys.argv[2]))

    G = load_graph(graph_path)
    G = limit_graph(G, max_nodes=max_nodes)
    net = build_pyvis(G, physics=physics)
    # Avoid Jupyter/Streamlit notebook template issues by writing HTML explicitly
    net.write_html(out_html, open_browser=False, notebook=False)
    print(json.dumps({
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "output": os.path.abspath(out_html),
        "physics": physics,
    }, indent=2))


if __name__ == "__main__":
    main()


