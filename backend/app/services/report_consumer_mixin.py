"""Consumer report generation orchestration for ReportAgent."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..utils.locale import t
from ..utils.logger import get_logger
from .report_consumer_context_mixin import ConsumerReportContextMixin
from .report_consumer_render_mixin import ConsumerReportRenderMixin
from .report_manager import ReportManager
from .report_models import Report, ReportOutline, ReportSection, ReportStatus

logger = get_logger('miroconsumer.report_agent')


class ConsumerReportMixin(ConsumerReportContextMixin, ConsumerReportRenderMixin):
    def _generate_consumer_report(
        self,
        report: Report,
        report_id: str,
        start_time: datetime,
        completed_section_titles: List[str],
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ) -> Report:
        if self.report_logger:
            self.report_logger.log_planning_start()

        ReportManager.update_progress(
            report_id, "planning", 10, "正在整理消费者传播证据",
            completed_sections=completed_section_titles,
        )
        if progress_callback:
            progress_callback("planning", 10, "正在整理消费者传播证据")

        context = self._build_consumer_report_context()
        report.report_context = context
        outline = self._build_consumer_outline(context)
        report.outline = outline
        report.status = ReportStatus.GENERATING
        ReportManager.save_outline(report_id, outline)
        ReportManager.save_report(report)

        if self.report_logger:
            self.report_logger.log_planning_complete(outline.to_dict())

        total_sections = len(outline.sections)
        generated_section_contents: List[str] = []
        for index, section in enumerate(outline.sections, start=1):
            progress = 20 + int(((index - 1) / max(total_sections, 1)) * 70)
            ReportManager.update_progress(
                report_id,
                "generating",
                progress,
                f"正在生成章节：{section.title}",
                current_section=section.title,
                completed_sections=completed_section_titles,
            )
            if progress_callback:
                progress_callback("generating", progress, f"正在生成章节：{section.title}")

            section.content = self._render_consumer_section_with_optional_llm(
                section=section,
                outline=outline,
                context=context,
                previous_sections=generated_section_contents,
            )
            ReportManager.save_section(report_id, index, section)
            completed_section_titles.append(section.title)
            generated_section_contents.append(f"## {section.title}\n\n{section.content}".strip())

            if self.report_logger:
                self.report_logger.log_section_full_complete(
                    section_title=section.title,
                    section_index=index,
                    full_content=f"## {section.title}\n\n{section.content}".strip(),
                )

        report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.now().isoformat()

        total_time_seconds = (datetime.now() - start_time).total_seconds()
        if self.report_logger:
            self.report_logger.log_report_complete(
                total_sections=total_sections,
                total_time_seconds=total_time_seconds,
            )

        ReportManager.save_report(report)
        ReportManager.update_progress(
            report_id, "completed", 100, t('progress.reportComplete'),
            completed_sections=completed_section_titles,
        )
        if progress_callback:
            progress_callback("completed", 100, t('progress.reportComplete'))

        if self.console_logger:
            self.console_logger.close()
            self.console_logger = None

        return report

    def _consumer_report_llm_enabled(self) -> bool:
        return os.environ.get("CONSUMER_REPORT_LLM_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _render_consumer_section_with_optional_llm(
        self,
        *,
        section: ReportSection,
        outline: ReportOutline,
        context: Dict[str, Any],
        previous_sections: List[str],
    ) -> str:
        if not self._consumer_report_llm_enabled():
            return self._render_consumer_section(section.title, context)

        stats = getattr(
            self,
            "consumer_report_llm_stats",
            {"attempted": 0, "succeeded": 0, "failed": 0, "latencies": []},
        )
        stats["attempted"] += 1
        started_at = time.time()
        try:
            context_preview = json.dumps(context, ensure_ascii=False, default=str)[:4000]
            llm_previous_sections = [
                f"consumer_report_context:\n{context_preview}",
                *previous_sections,
            ]
            content = self._generate_section_react(section, outline, llm_previous_sections)
            stats["succeeded"] += 1
            stats["latencies"].append(round(time.time() - started_at, 4))
            self.consumer_report_llm_stats = stats
            return content
        except Exception as exc:
            stats["failed"] += 1
            stats["latencies"].append(round(time.time() - started_at, 4))
            self.consumer_report_llm_stats = stats
            logger.warning("Consumer report LLM section failed; falling back to template: %s", exc)
            return self._render_consumer_section(section.title, context)
