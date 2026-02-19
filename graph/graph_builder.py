"""
Graph Builder Module
Builds graph structures from extracted entities and relationships
"""

from typing import List, Dict, Set


class GraphBuilder:
    """Build graph data structures from entities"""
    
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_ids = set()
    
    def build_graph(self, entities: List[Dict]) -> Dict:
        """Build graph from entities"""
        self.nodes = []
        self.edges = []
        self.node_ids = set()
        
        # Create nodes from entities
        for entity in entities:
            self._add_node(entity)
        
        # Create edges based on co-occurrence and source
        self._create_edges(entities)
        
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "stats": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges)
            }
        }
    
    def _add_node(self, entity: Dict):
        """Add a node to the graph"""
        node_id = entity.get("id") or entity.get("value", "unknown")
        
        if node_id not in self.node_ids:
            self.node_ids.add(node_id)
            
            node = {
                "id": node_id,
                "label": entity.get("value", ""),
                "type": entity.get("type", "unknown"),
                "source": entity.get("source", "default"),
                "data": entity
            }
            
            self.nodes.append(node)
    
    def _create_edges(self, entities: List[Dict]):
        """Create edges between related nodes"""
        # Group entities by source
        source_groups = {}
        for entity in entities:
            source = entity.get("source", "default")
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(entity)
        
        # Create edges within each source group
        for source, group_entities in source_groups.items():
            for i, entity1 in enumerate(group_entities):
                for entity2 in group_entities[i+1:]:
                    # Create edge if entities are related
                    if self._are_related(entity1, entity2):
                        edge_id = f"{entity1.get('id')}_{entity2.get('id')}"
                        self.edges.append({
                            "id": edge_id,
                            "source": entity1.get("id"),
                            "target": entity2.get("id"),
                            "type": "related",
                            "weight": 1
                        })
    
    def _are_related(self, entity1: Dict, entity2: Dict) -> bool:
        """Determine if two entities are related"""
        # Simple heuristic: entities from same source are related
        # In a real system, this would use NLP to determine semantic relationships
        
        # Check if they have similar types
        if entity1.get("type") == entity2.get("type"):
            return True
        
        # Check position proximity (if available)
        start1 = entity1.get("start", -1)
        start2 = entity2.get("start", -1)
        
        if start1 >= 0 and start2 >= 0:
            return abs(start1 - start2) < 200
        
        return False
    
    def add_custom_edge(self, source_id: str, target_id: str, edge_type: str = "custom"):
        """Add a custom edge between nodes"""
        if source_id in self.node_ids and target_id in self.node_ids:
            edge_id = f"{source_id}_{target_id}"
            self.edges.append({
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "type": edge_type,
                "weight": 1
            })
