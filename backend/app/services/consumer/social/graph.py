"""社交图谱模型 — 基于小世界网络"""

import random
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field


@dataclass
class SocialEdge:
    """社交关系"""
    source_id: str
    target_id: str
    weight: float  # 关系强度 0-1
    edge_type: str  # family/colleague/friend/acquaintance
    influence_coefficient: float  # 影响系数


class SocialGraph:
    """社交图谱"""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[SocialEdge]] = {}  # node_id -> outgoing edges
        self.in_edges: Dict[str, List[SocialEdge]] = {}  # node_id -> incoming edges

    def add_node(self, node_id: str):
        self.nodes.add(node_id)
        if node_id not in self.edges:
            self.edges[node_id] = []
        if node_id not in self.in_edges:
            self.in_edges[node_id] = []

    def add_edge(self, edge: SocialEdge):
        self.nodes.add(edge.source_id)
        self.nodes.add(edge.target_id)
        self.edges.setdefault(edge.source_id, []).append(edge)
        self.in_edges.setdefault(edge.target_id, []).append(edge)

    def get_neighbors(self, node_id: str) -> List[SocialEdge]:
        return self.edges.get(node_id, [])

    def get_influencers(self, node_id: str) -> List[SocialEdge]:
        """获取能影响该节点的人"""
        return self.in_edges.get(node_id, [])

    def get_community(self, node_id: str, depth: int = 2) -> Set[str]:
        """BFS 获取社区（到 depth 层的邻居）"""
        visited: Set[str] = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            next_frontier: Set[str] = set()
            for n in frontier:
                for edge in self.edges.get(n, []):
                    if edge.target_id not in visited:
                        next_frontier.add(edge.target_id)
                for edge in self.in_edges.get(n, []):
                    if edge.source_id not in visited:
                        next_frontier.add(edge.source_id)
            visited.update(next_frontier)
            frontier = next_frontier
        return visited

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self.edges.values())


class SocialGraphGenerator:
    """社交图谱生成器"""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def generate_small_world(
        self,
        node_ids: List[str],
        k_neighbors: int = 4,
        rewire_probability: float = 0.3,
    ) -> SocialGraph:
        """Watts-Strogatz 小世界网络"""
        graph = SocialGraph()
        n = len(node_ids)

        for nid in node_ids:
            graph.add_node(nid)

        # 创建环形规则网络
        for i, nid in enumerate(node_ids):
            for j in range(1, k_neighbors // 2 + 1):
                target = node_ids[(i + j) % n]
                weight = self.rng.uniform(0.3, 1.0)
                graph.add_edge(SocialEdge(
                    source_id=nid,
                    target_id=target,
                    weight=weight,
                    edge_type="friend",
                    influence_coefficient=weight * 0.8,
                ))
                # 双向
                graph.add_edge(SocialEdge(
                    source_id=target,
                    target_id=nid,
                    weight=weight,
                    edge_type="friend",
                    influence_coefficient=weight * 0.8,
                ))

        # 随机重连
        edges_to_rewire = []
        for nid in node_ids:
            for edge in graph.edges.get(nid, []):
                if self.rng.random() < rewire_probability:
                    edges_to_rewire.append((nid, edge))

        for source_id, old_edge in edges_to_rewire:
            new_target = self.rng.choice(node_ids)
            while new_target == source_id:
                new_target = self.rng.choice(node_ids)

            # 移除旧边
            graph.edges[source_id] = [
                e for e in graph.edges[source_id]
                if e.target_id != old_edge.target_id
            ]
            graph.in_edges[old_edge.target_id] = [
                e for e in graph.in_edges[old_edge.target_id]
                if e.source_id != source_id
            ]

            # 添加新边
            new_edge = SocialEdge(
                source_id=source_id,
                target_id=new_target,
                weight=old_edge.weight,
                edge_type="acquaintance",
                influence_coefficient=old_edge.weight * 0.5,
            )
            graph.add_edge(new_edge)

        return graph

    def generate_community_structure(
        self,
        node_ids: List[str],
        n_communities: int = 4,
        intra_density: float = 0.6,
        inter_density: float = 0.05,
    ) -> SocialGraph:
        """社群结构图谱（社区内连接密集，社区间稀疏）"""
        graph = SocialGraph()
        for nid in node_ids:
            graph.add_node(nid)

        # 分配社区
        communities: List[List[str]] = []
        chunk_size = len(node_ids) // n_communities
        for i in range(n_communities):
            start = i * chunk_size
            end = start + chunk_size if i < n_communities - 1 else len(node_ids)
            communities.append(node_ids[start:end])

        # 社区内连接
        edge_types = ["family", "colleague", "friend"]
        for community in communities:
            for i, n1 in enumerate(community):
                for n2 in community[i + 1:]:
                    if self.rng.random() < intra_density:
                        w = self.rng.uniform(0.5, 1.0)
                        etype = self.rng.choice(edge_types)
                        graph.add_edge(SocialEdge(n1, n2, w, etype, w * 0.9))
                        graph.add_edge(SocialEdge(n2, n1, w, etype, w * 0.9))

        # 社区间连接
        for i, c1 in enumerate(communities):
            for c2 in communities[i + 1:]:
                for n1 in c1:
                    for n2 in c2:
                        if self.rng.random() < inter_density:
                            w = self.rng.uniform(0.1, 0.4)
                            graph.add_edge(SocialEdge(n1, n2, w, "acquaintance", w * 0.3))
                            graph.add_edge(SocialEdge(n2, n1, w, "acquaintance", w * 0.3))

        return graph
