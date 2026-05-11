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
    channel: str = "general"  # 传播渠道
    visibility_level: str = "public"  # public/friends/private
    interaction_frequency: float = 0.5  # 互动频率


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

    def get_activated_nodes(self, topic_seed_nodes: list, threshold: float = 0.5) -> Set[str]:
        """基于话题激活阈值获取被激活的节点

        从种子节点出发，沿出边扩散，仅当边权重 >= threshold 时才激活下游节点。
        返回所有被激活的节点集合（包含种子节点）。
        """
        activated: Set[str] = set(topic_seed_nodes)
        frontier: Set[str] = set(topic_seed_nodes)

        while frontier:
            next_frontier: Set[str] = set()
            for node in frontier:
                for edge in self.edges.get(node, []):
                    if edge.target_id not in activated and edge.weight >= threshold:
                        activated.add(edge.target_id)
                        next_frontier.add(edge.target_id)
            frontier = next_frontier

        return activated

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self.edges.values())

    @staticmethod
    def from_adjacency_list(adj_list: dict, edge_type: str = "custom") -> "SocialGraph":
        """从邻接表导入"""
        graph = SocialGraph()
        for source, targets in adj_list.items():
            graph.add_node(source)
            for target_info in (targets if isinstance(targets, list) else []):
                target = target_info if isinstance(target_info, str) else target_info.get("id")
                weight = target_info.get("weight", 0.5) if isinstance(target_info, dict) else 0.5
                graph.add_edge(SocialEdge(source, target, weight, edge_type, weight * 0.8))
        return graph

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> List[List[str]]:
        """BFS 找到从 source 到 target 的所有路径（限深度）"""
        paths = []
        queue = [(source_id, [source_id])]
        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            if current == target_id:
                paths.append(path)
                continue
            for edge in self.edges.get(current, []):
                if edge.target_id not in path:  # 避免环
                    queue.append((edge.target_id, path + [edge.target_id]))
        return paths

    def get_influence_path(self, source_id: str, max_depth: int = 3) -> List[dict]:
        """获取影响力传播路径"""
        visited = set()
        result = []
        queue = [(source_id, 0, [])]
        while queue:
            node, depth, path = queue.pop(0)
            if depth > max_depth or node in visited:
                continue
            visited.add(node)
            result.append({"node": node, "depth": depth, "path": path + [node]})
            for edge in self.edges.get(node, []):
                queue.append((edge.target_id, depth + 1, path + [node]))
        return result

    @staticmethod
    def compare_topologies(graph_a, graph_b) -> dict:
        """对比两个图拓扑的差异"""
        nodes_a = graph_a.nodes
        nodes_b = graph_b.nodes
        edges_a = graph_a.edge_count
        edges_b = graph_b.edge_count

        avg_degree_a = edges_a / len(nodes_a) if nodes_a else 0
        avg_degree_b = edges_b / len(nodes_b) if nodes_b else 0

        return {
            "graph_a": {"nodes": len(nodes_a), "edges": edges_a, "avg_degree": avg_degree_a},
            "graph_b": {"nodes": len(nodes_b), "edges": edges_b, "avg_degree": avg_degree_b},
            "density_diff": abs(avg_degree_a - avg_degree_b),
        }


class SocialGraphGenerator:
    """社交图谱生成器"""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def generate_random(self, node_ids: List[str], edge_probability: float = 0.1, seed: int = None) -> SocialGraph:
        """Erdős-Rényi 随机图"""
        rng = random.Random(seed) if seed is not None else self.rng
        graph = SocialGraph()
        for nid in node_ids:
            graph.add_node(nid)
        for i, n1 in enumerate(node_ids):
            for n2 in node_ids[i + 1:]:
                if rng.random() < edge_probability:
                    w = rng.uniform(0.1, 1.0)
                    graph.add_edge(SocialEdge(n1, n2, w, "random", w * 0.5))
                    graph.add_edge(SocialEdge(n2, n1, w, "random", w * 0.5))
        return graph

    def generate_scale_free(self, node_ids: List[str], m_edges: int = 3, seed: int = None) -> SocialGraph:
        """Barabási-Albert 无标度网络"""
        rng = random.Random(seed) if seed is not None else self.rng
        graph = SocialGraph()
        n = len(node_ids)
        if n == 0:
            return graph

        # 初始完全图
        initial = min(m_edges + 1, n)
        for i in range(initial):
            graph.add_node(node_ids[i])
        for i in range(initial):
            for j in range(i + 1, initial):
                w = rng.uniform(0.3, 1.0)
                graph.add_edge(SocialEdge(node_ids[i], node_ids[j], w, "friend", w * 0.8))
                graph.add_edge(SocialEdge(node_ids[j], node_ids[i], w, "friend", w * 0.8))

        # 优先连接
        degrees: Dict[str, int] = {}
        for nid in node_ids[:initial]:
            degrees[nid] = len(graph.edges.get(nid, [])) + len(graph.in_edges.get(nid, []))
        for i in range(initial, n):
            graph.add_node(node_ids[i])
            total_degree = sum(degrees.values()) or 1
            probs = [degrees.get(nid, 0) / total_degree for nid in node_ids[:i]]
            targets: Set[str] = set()
            attempts = 0
            while len(targets) < min(m_edges, i) and attempts < m_edges * 3:
                idx = rng.choices(range(i), weights=probs[:i], k=1)[0]
                targets.add(node_ids[idx])
                attempts += 1

            for t in targets:
                w = rng.uniform(0.3, 1.0)
                graph.add_edge(SocialEdge(node_ids[i], t, w, "influenced", w * 0.7))
                graph.add_edge(SocialEdge(t, node_ids[i], w, "influencer", w * 0.7))
                degrees[t] = degrees.get(t, 0) + 1
            degrees[node_ids[i]] = len(targets)

        return graph

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

    def generate_influencer_follower(self, node_ids: List[str], n_influencers: int = None, seed: int = None) -> SocialGraph:
        """influencer-follower 图：少数关键影响者节点，大量跟随者"""
        rng = random.Random(seed)
        n = len(node_ids)
        if n_influencers is None:
            n_influencers = max(2, n // 10)  # 10% 是影响者

        graph = SocialGraph()
        for nid in node_ids:
            graph.add_node(nid)

        influencers = node_ids[:n_influencers]
        followers = node_ids[n_influencers:]

        # 每个影响者连接到所有跟随者
        for inf in influencers:
            for fol in followers:
                w = rng.uniform(0.5, 1.0)
                graph.add_edge(SocialEdge(inf, fol, w, "influencer", w * 0.9))
                graph.add_edge(SocialEdge(fol, inf, w * 0.5, "follower", w * 0.4))

        # 影响者之间互相连接
        for i, inf1 in enumerate(influencers):
            for inf2 in influencers[i+1:]:
                w = rng.uniform(0.3, 0.7)
                graph.add_edge(SocialEdge(inf1, inf2, w, "peer", w * 0.6))
                graph.add_edge(SocialEdge(inf2, inf1, w, "peer", w * 0.6))

        return graph

    def generate_channel_separated(self, node_ids: List[str], channels: List[str] = None, seed: int = None) -> SocialGraph:
        """渠道分层图：每个渠道内紧密连接，渠道间稀疏"""
        rng = random.Random(seed)
        if channels is None:
            channels = ["weixin", "douyin", "xiaohongshu", "weibo"]

        graph = SocialGraph()
        n = len(node_ids)
        chunk_size = n // len(channels)

        for nid in node_ids:
            graph.add_node(nid)

        for i, channel in enumerate(channels):
            start = i * chunk_size
            end = start + chunk_size if i < len(channels) - 1 else n
            channel_nodes = node_ids[start:end]

            # 渠道内连接
            for j, n1 in enumerate(channel_nodes):
                for n2 in channel_nodes[j+1:]:
                    if rng.random() < 0.6:
                        w = rng.uniform(0.5, 1.0)
                        graph.add_edge(SocialEdge(n1, n2, w, channel, w * 0.8, channel=channel))
                        graph.add_edge(SocialEdge(n2, n1, w, channel, w * 0.8, channel=channel))

        # 渠道间桥接（稀疏）
        all_channel_nodes = [node_ids[i*chunk_size:(i+1)*chunk_size] if i < len(channels) - 1 else node_ids[i*chunk_size:] for i in range(len(channels))]
        for i, ch1_nodes in enumerate(all_channel_nodes):
            for j, ch2_nodes in enumerate(all_channel_nodes):
                if i >= j:
                    continue
                for n1 in ch1_nodes[:3]:  # 只取前3个做桥接
                    for n2 in ch2_nodes[:3]:
                        if rng.random() < 0.2:
                            w = rng.uniform(0.1, 0.3)
                            graph.add_edge(SocialEdge(n1, n2, w, "bridge", w * 0.3))

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
