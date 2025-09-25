import os
import json
from typing import Dict, Any, List, Tuple

import streamlit as st
from pyvis.network import Network
import networkx as nx


def load_doc_status() -> Dict[str, Any]:
    """Load document metadata (kv_store_doc_status.json)."""
    try:
        with open(os.path.join("rag_storage", "kv_store_doc_status.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def pick_document(docs: Dict[str, Any]) -> Tuple[str | None, Dict[str, Any] | None]:
    """Let user pick a document scope from sidebar."""
    if not docs:
        return None, None
    options = [
        (doc_id, meta.get("file_path", doc_id), meta.get("chunks_count", 0), meta.get("updated_at", ""))
        for doc_id, meta in docs.items()
    ]
    labels = ["All documents (merged)"] + [f"{fp}  •  {cc} chunks" for _, fp, cc, _ in options]
    idx = st.selectbox(
        "Scope",
        options=list(range(len(labels))),
        format_func=lambda i: labels[i],
    )
    if idx == 0:
        return "__ALL__", {}
    picked = options[idx - 1]
    doc_id = picked[0]
    return doc_id, docs[doc_id]


def load_graphml(path: str) -> nx.Graph:
    """Load the GraphML file into a NetworkX graph."""
    if not os.path.isfile(path):
        raise FileNotFoundError("graph_chunk_entity_relation.graphml not found under rag_storage")
    return nx.read_graphml(path)


def filter_subgraph_by_chunks(G, chunks: List[str]):
    """Filter graph to only edges/nodes relevant to the given chunks."""
    keep_edges = []
    for u, v, data in G.edges(data=True):
        src_ids = set(str(data.get("source_id", "")).split("||"))
        if not src_ids.isdisjoint(set(chunks)):
            keep_edges.append((u, v))
    nodes = set()
    for u, v in keep_edges:
        nodes.add(u)
        nodes.add(v)
    return G.subgraph(nodes).copy()


def build_pyvis_network(G, physics: bool = True) -> Network:
    """Build a PyVis network visualization from the NetworkX graph."""
    net = Network(height="750px", width="100%", bgcolor="#0e1117", font_color="#fafafa")

    if physics:
        net.barnes_hut()  # Barnes-Hut layout
    else:
        net.hrepulsion()  # Static repulsion layout

    # Add nodes
    for n, data in G.nodes(data=True):
        label = data.get("entity_id", n)
        title = data.get("description", "")
        group = data.get("entity_type", "entity")
        net.add_node(n, label=label, title=title, group=group)

    # Add edges
    for u, v, data in G.edges(data=True):
        desc = data.get("description", "")
        weight = float(data.get("weight", 1.0))
        net.add_edge(u, v, title=desc, value=weight)

    # Calm physics settings (no jitter, but still draggable)
    net.set_options(
        """
{
  "nodes": { "shape": "dot", "scaling": {"min": 5, "max": 25} },
  "edges": { "color": {"color": "#999", "highlight": "#f39c12"}, "smooth": false },
  "physics": { 
    "enabled": true,
    "solver": "barnesHut",
    "stabilization": { "enabled": true, "iterations": 300 },
    "minVelocity": 0.1,
    "barnesHut": { "springLength": 150, "springConstant": 0.01, "damping": 0.9 }
  },
  "interaction": { "hover": true, "tooltipDelay": 120, "dragNodes": true }
}
        """
    )

    return net


def main():
    st.set_page_config(page_title="Knowledge Graph Viewer", page_icon="🕸️", layout="wide")
    st.title("Knowledge Graph Viewer")
    st.caption("Visualize entities and relationships built by LightRAG.")

    # Sidebar controls
    with st.sidebar:
        st.subheader("Scope")
        docs = load_doc_status()
        doc_id, meta = pick_document(docs)
        limit_nodes = st.slider("Max nodes (approx)", min_value=50, max_value=2000, value=500, step=50)
        physics = st.checkbox("Enable physics", value=True)

    if not doc_id:
        st.info("No processed documents found. Ingest a document first.")
        return

    # Load graph
    try:
        G = load_graphml(os.path.join("rag_storage", "graph_chunk_entity_relation.graphml"))
    except Exception as exc:
        st.error(f"Failed to load graph: {exc}")
        return

    # Filter if specific doc selected
    if doc_id != "__ALL__":
        chunks = meta.get("chunks_list", [])
        if chunks:
            G = filter_subgraph_by_chunks(G, chunks)

    # Limit nodes for performance
    if G.number_of_nodes() > limit_nodes:
        nodes_by_deg = sorted(G.degree, key=lambda x: x[1], reverse=True)
        keep = set(n for n, _ in nodes_by_deg[:limit_nodes])
        G = G.subgraph(keep).copy()

    st.write(f"Nodes: {G.number_of_nodes()}  |  Edges: {G.number_of_edges()}")

    # Build and render network
    net = build_pyvis_network(G, physics=physics)
    html = net.generate_html(notebook=False)
    st.components.v1.html(html, height=780, scrolling=True)


if __name__ == "__main__":
    main()
