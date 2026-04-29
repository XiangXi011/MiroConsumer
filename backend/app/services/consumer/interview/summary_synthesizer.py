"""Synthesize interview answers into a structured summary."""

from typing import Any, Dict, List


class InterviewSummarySynthesizer:
    """Produce summaries containing required sections per Phase 6I spec."""

    def synthesize_interview(
        self,
        answers: List[Dict[str, Any]],
        evidence_map: Dict[str, Any],
        followup_questions: List[Dict[str, Any]],
    ) -> str:
        supporting_quotes = []
        opposing_quotes = []
        misread_points = []
        evidence_demands = []
        price_resistances = []
        trust_repairs = []

        for answer in answers:
            role = answer.get("role", "")
            text = answer.get("answer", "")
            if not text:
                continue

            if role == "advocate":
                supporting_quotes.append(text)
            elif role == "skeptic":
                opposing_quotes.append(text)

            lowered = text.lower()
            if "unclear" in lowered or "misunderstand" in lowered or "confus" in lowered:
                misread_points.append(text)
            if "proof" in lowered or "evidence" in lowered:
                evidence_demands.append(text)
            if "price" in lowered or "expensive" in lowered or "cost" in lowered:
                price_resistances.append(text)
            if "trust" in lowered:
                trust_repairs.append(text)

        sections = []

        core = " ".join([a.get("answer", "") for a in answers[:2]])
        sections.append(f"Core conclusion: {core}")

        strongest_support = supporting_quotes[0] if supporting_quotes else (answers[0].get("answer", "") if answers else "")
        sections.append(f"Strongest supporting quote: {strongest_support}")

        strongest_opposing = opposing_quotes[0] if opposing_quotes else ""
        sections.append(f"Strongest opposing quote: {strongest_opposing}")

        misread = misread_points[0] if misread_points else "None identified"
        sections.append(f"Misread point: {misread}")

        evidence = evidence_demands[0] if evidence_demands else "None identified"
        sections.append(f"Evidence demand: {evidence}")

        price = price_resistances[0] if price_resistances else "None identified"
        sections.append(f"Price resistance: {price}")

        trust = trust_repairs[0] if trust_repairs else "None identified"
        sections.append(f"Trust repair condition: {trust}")

        what_if = "Test a variant with stronger clinical evidence and clearer packaging claims."
        if followup_questions:
            fq = followup_questions[0]
            if isinstance(fq, dict):
                what_if = f"Explore: {fq.get('question', what_if)}"
        sections.append(f"Next What-if experiment: {what_if}")

        return "\n\n".join(sections)
