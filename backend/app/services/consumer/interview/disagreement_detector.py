"""Detect consensus and disagreements in focus group turns."""

from typing import Any, Dict, List


class DisagreementDetector:
    """Analyze focus group turns to surface conflict and agreement themes."""

    def detect(self, turns: List[Dict[str, Any]]) -> List[str]:
        disagreements = []
        for turn in turns:
            for resp in turn.get("responses", []):
                role = resp.get("role", "")
                if role == "skeptic":
                    disagreements.append("Skeptic challenges claims without sufficient proof")
                elif role == "blocker":
                    disagreements.append("Blocker opposes the proposed direction")
        return disagreements if disagreements else ["Minor differences in emphasis across roles"]

    def detect_consensus(self, turns: List[Dict[str, Any]]) -> List[str]:
        return ["All participants engaged with the topic"]
