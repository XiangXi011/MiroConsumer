"""Bind evidence to interview answers using Phase 6F support levels."""

from typing import Any, Dict


class InterviewEvidenceBinder:
    """Attach event IDs, finding IDs, source IDs, quote IDs and support level to each answer."""

    def bind_answer(
        self,
        card: Dict[str, Any],
        answer: Dict[str, Any],
        target_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        event_ids = list(card.get("event_ids", []))
        finding_ids = list(target_context.get("finding_ids", []))
        if "finding_id" in target_context:
            finding_ids.append(target_context["finding_id"])

        source_ids = list(card.get("evidence_ids", []))
        source_ids.extend(target_context.get("source_ids", []))

        quote_ids = list(target_context.get("quote_ids", []))

        answer_text = answer.get("answer", "")

        if finding_ids and source_ids and answer_text:
            support_level = "supported"
        elif (card.get("evidence_ids") or event_ids) and answer_text:
            support_level = "weak_support"
        else:
            support_level = "insufficient_support"

        return {
            "agent_id": card["agent_id"],
            "event_ids": event_ids,
            "finding_ids": finding_ids,
            "source_ids": source_ids,
            "quote_ids": quote_ids,
            "support_level": support_level,
        }
