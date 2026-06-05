"""Consumer report outline and template rendering helpers for ReportAgent."""

from __future__ import annotations

from typing import Any, Dict, List

from .report_models import ReportOutline, ReportSection


class ConsumerReportRenderMixin:
    def _build_consumer_outline(self, context: Dict[str, Any]) -> ReportOutline:
        summary = context["summary"]
        task_type = str(context.get("task_type", "")).strip().lower()
        research_findings_value = context.get("research_findings", [])
        research_findings_count = int(
            context.get("research_findings_count")
            or (len(research_findings_value) if isinstance(research_findings_value, list) else 0)
        )

        # Determine concept recommendation for summary
        post_pos = summary['post_propagation_acceptance']['positive']
        init_pos = summary['initial_acceptance']['positive']
        shift_rate = summary['attitude_shift_rate']
        neg_growth = summary['post_propagation_acceptance']['negative'] - summary['initial_acceptance']['negative']
        if post_pos > init_pos and shift_rate > 0.1:
            recommendation = "建议继续推进"
        elif neg_growth > 0.1:
            recommendation = "建议暂缓"
        else:
            recommendation = "建议优化后继续"

        outline_summary = (
            f"本报告基于 {research_findings_count} 条研究发现与消费者原声综合生成，"
            f"概念决策：{recommendation}。"
            f"初始正向接受度 {init_pos:.0%}，"
            f"传播后正向接受度 {post_pos:.0%}，"
            f"态度转向率 {shift_rate:.0%}。"
        )

        sections = [
            # Layer 1: Executive Summary
            ReportSection(title="总裁结论页", content=""),
            # Layer 2: Action Playbook
            ReportSection(title="卖点决策表", content=""),
            ReportSection(title="合规话术边界", content=""),
            ReportSection(title="渠道策略与执行建议", content=""),
            # Layer 3: Technical Appendix
            ReportSection(title="测试概览", content=""),
            ReportSection(title="研究发现综合", content=""),
            ReportSection(title="传播演化", content=""),
            ReportSection(title="风险与误读", content=""),
            ReportSection(title="代表性消费者原声", content=""),
        ]

        # Task-specific sections still appended to Layer 3
        if task_type == "price_test":
            sections.insert(7, ReportSection(title="价格敏感度与 WTP 分析", content=""))
            sections.insert(8, ReportSection(title="价格接受区间与弹性", content=""))
        elif task_type == "packaging_test":
            sections.insert(7, ReportSection(title="视觉认知与货架吸引力", content=""))
            sections.insert(8, ReportSection(title="包装识别与注意力路径", content=""))
        elif task_type == "ab_test":
            sections.insert(7, ReportSection(title="偏好对比与统计显著性", content=""))
            sections.insert(8, ReportSection(title="版本差异与选择理由", content=""))

        return ReportOutline(
            title="消费者传播测试与市场决策报告",
            summary=outline_summary,
            sections=sections,
        )

    # ── Layer 1 & 2 rendering methods ──────────────────────────────────

    def _render_executive_summary(self, context: Dict[str, Any]) -> str:
        """Render 总裁结论页 — Layer 1 executive summary."""
        summary = context["summary"]
        init_pos = summary['initial_acceptance']['positive']
        post_pos = summary['post_propagation_acceptance']['positive']
        shift_rate = summary['attitude_shift_rate']
        neg_growth = summary['post_propagation_acceptance']['negative'] - summary['initial_acceptance']['negative']

        # Concept recommendation
        if post_pos > init_pos and shift_rate > 0.1:
            recommendation = "建议继续推进"
        elif neg_growth > 0.1:
            recommendation = "建议暂缓"
        else:
            recommendation = "建议优化后继续"

        lines: List[str] = []
        lines.append(f"## 概念决策：{recommendation}")
        lines.append("")

        # Core findings — top 3 resonance points
        lines.append("## 核心发现")
        resonance = context.get('top_resonance_points', [])
        for point in resonance[:3]:
            lines.append(f"- {point}")
        if not resonance:
            lines.append("- 暂无显著共鸣点")
        lines.append("")

        # Biggest opportunity & biggest risk
        top_opportunity = resonance[0] if resonance else "暂无"
        risk_points = context.get('top_risk_points', [])
        top_risk = risk_points[0] if risk_points else "暂无"
        lines.append(f"## 最大机会\n{top_opportunity}")
        lines.append("")
        lines.append(f"## 最大风险\n{top_risk}")
        lines.append("")

        # Main selling point suggestion
        sp_report = context.get('selling_point_report')
        main_rec = None
        if isinstance(sp_report, dict):
            main_rec = sp_report.get('main_recommendation')
            if not main_rec:
                analyses = sp_report.get('analyses') or sp_report.get('recommendations') or []
                if analyses:
                    a = analyses[0]
                    main_rec = a.get('claim_text', a.get('claim', '')) if isinstance(a, dict) else getattr(a, 'claim_text', '')
        elif sp_report is not None:
            main_rec = getattr(sp_report, 'main_recommendation', None)
            if not main_rec:
                analyses = getattr(sp_report, 'analyses', None) or getattr(sp_report, 'recommendations', None) or []
                if analyses:
                    main_rec = getattr(analyses[0], 'claim_text', '')
        if main_rec:
            lines.append(f"## 主卖点建议\n{main_rec}")
        else:
            anchor = resonance[0] if resonance else "暂无"
            lines.append(f"## 主卖点建议\n围绕核心共鸣点「{anchor}」构建主传播叙事")
        lines.append("")

        # Next steps
        lines.append("## 下一步行动")
        lines.append(f"1. 根据概念决策（{recommendation}），明确下一阶段资源配置")
        if resonance:
            lines.append(f"2. 围绕「{resonance[0]}」打磨核心文案与传播素材")
        if risk_points:
            lines.append(f"3. 针对风险点「{risk_points[0]}」准备应对话术与证据")
        lines.append("4. 参阅执行页（Layer 2）获取卖点、合规、渠道的具体落地方案")
        return "\n".join(lines)

    def _render_selling_point_table(self, context: Dict[str, Any]) -> str:
        """Render 卖点决策表 — Layer 2 selling point decision table."""
        sp_report = context.get('selling_point_report')
        # Handle both dict (model_dump) and object forms
        analyses = None
        if isinstance(sp_report, dict):
            analyses = sp_report.get('analyses') or sp_report.get('recommendations')
        elif sp_report is not None:
            analyses = getattr(sp_report, 'analyses', None) or getattr(sp_report, 'recommendations', None)
        if analyses:
            lines: List[str] = []
            lines.append("## 卖点决策表")
            lines.append("")
            lines.append("| 排名 | 卖点 | 建议角色 | 共鸣度 | 风险度 | 最佳渠道 | 处理方式 |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for a in analyses:
                if isinstance(a, dict):
                    rank = a.get('priority_rank', a.get('rank', ''))
                    claim = a.get('claim_text', a.get('claim', ''))
                    role = a.get('role', '')
                    resonance = a.get('resonance_score', 0)
                    risk = a.get('risk_score', 0)
                    best_ch = a.get('best_channel', '')
                    handling = a.get('handling_suggestion', a.get('handling', ''))
                else:
                    rank = getattr(a, 'priority_rank', '')
                    claim = getattr(a, 'claim_text', '')
                    role = getattr(a, 'role', '')
                    resonance = getattr(a, 'resonance_score', 0)
                    risk = getattr(a, 'risk_score', 0)
                    best_ch = getattr(a, 'best_channel', '')
                    handling = getattr(a, 'handling_suggestion', '')
                try:
                    resonance_str = f"{float(resonance):.0%}"
                except (ValueError, TypeError):
                    resonance_str = str(resonance)
                try:
                    risk_str = f"{float(risk):.0%}"
                except (ValueError, TypeError):
                    risk_str = str(risk)
                lines.append(
                    f"| {rank} | {claim} | {role} | {resonance_str} | {risk_str} | {best_ch} | {handling} |"
                )
            return "\n".join(lines)

        # Fallback: simplified table from existing context data
        lines = []
        lines.append("## 卖点决策表")
        lines.append("")
        lines.append("| 卖点 | 建议角色 | 原因 | 风险 | 处理方式 |")
        lines.append("| --- | --- | --- | --- | --- |")
        resonance = context.get('top_resonance_points', [])
        risk_points = context.get('top_risk_points', [])
        for i, point in enumerate(resonance[:5]):
            role = "主打卖点" if i == 0 else "辅助卖点"
            reason = "消费者高共鸣" if i == 0 else "强化概念支撑"
            risk = risk_points[i] if i < len(risk_points) else "暂无已知风险"
            handling = "持续强化传播" if i == 0 else "配合主卖点使用"
            lines.append(f"| {point} | {role} | {reason} | {risk} | {handling} |")
        if not resonance:
            lines.append("| 暂无 | - | - | - | - |")
        return "\n".join(lines)

    def _render_compliance_table(self, context: Dict[str, Any]) -> str:
        """Render 合规话术边界 — Layer 2 compliance boundary table."""
        comp_report = context.get('compliance_report')
        # Handle both dict (model_dump) and object forms
        findings = None
        if isinstance(comp_report, dict):
            findings = comp_report.get('findings')
        elif comp_report is not None:
            findings = getattr(comp_report, 'findings', None)
        if findings:
            lines: List[str] = []
            lines.append("## 合规话术边界")
            lines.append("")
            lines.append("| 高风险表达 | 风险原因 | 建议替代表达 |")
            lines.append("| --- | --- | --- |")
            for finding in findings:
                if isinstance(finding, dict):
                    expr = finding.get('expression', '')
                    reason = finding.get('risk_reason', '')
                    alternative = finding.get('suggested_alternative', '')
                else:
                    expr = getattr(finding, 'expression', '')
                    reason = getattr(finding, 'risk_reason', '')
                    alternative = getattr(finding, 'suggested_alternative', '')
                lines.append(f"| {expr} | {reason} | {alternative} |")
            return "\n".join(lines)

        # Fallback: derive from misreads and risk points
        lines = []
        lines.append("## 合规话术边界")
        lines.append("")
        lines.append("| 高风险表达 | 风险原因 | 建议替代表达 |")
        lines.append("| --- | --- | --- |")
        misreads = context.get('top_misreads', [])
        for misread in misreads[:3]:
            lines.append(f"| {misread} | 消费者误读/歧义 | 建议使用更明确、具体化表述 |")
        risk_points = context.get('top_risk_points', [])
        for risk in risk_points[:3]:
            lines.append(f"| {risk} | 可能引发负面解读 | 建议补充证据支撑或弱化表述 |")
        if not misreads and not risk_points:
            lines.append("| 暂无 | - | - |")
        lines.append("")
        lines.append("> 注：以上为自动生成的初步筛查，正式发布前请法务/合规团队复核。")
        return "\n".join(lines)

    def _render_channel_strategy(self, context: Dict[str, Any]) -> str:
        """Render 渠道策略与执行建议 — Layer 2 channel strategy."""
        channel_metrics = context.get('channel_metrics', {})
        channel_fit = context.get('channel_fit_scores', {})
        resonance = context.get('top_resonance_points', [])
        risk_points = context.get('top_risk_points', [])
        main_hook = resonance[0] if resonance else "产品核心价值"
        main_risk = risk_points[0] if risk_points else "暂无已知风险"

        lines: List[str] = []
        lines.append("## 渠道策略与执行建议")
        lines.append("")

        # Per-channel recommendations
        channels = [
            ("小红书", "种草笔记 + 素人口碑", "图文笔记、合集测评、素人试用分享"),
            ("抖音", "短视频 + 信息流", "15-60秒短视频、达人合作、信息流投放"),
            ("直播间", "即时转化场景", "主播话术、互动引导、限时促销"),
            ("详情页", "深度说服场景", "长图文、对比数据、FAQ、用户证言"),
        ]
        for name, positioning, format_hint in channels:
            fit_score = channel_fit.get(name, channel_fit.get(name.lower(), ""))
            fit_label = f"（适配度: {fit_score}）" if fit_score else ""
            ch_metric = channel_metrics.get(name, channel_metrics.get(name.lower(), {}))
            lines.append(f"### {name} {fit_label}")
            lines.append(f"- 定位：{positioning}")
            lines.append(f"- 推荐形式：{format_hint}")
            lines.append(f"- 核心传播锚点：「{main_hook}」")
            if ch_metric and isinstance(ch_metric, dict):
                for k, v in ch_metric.items():
                    lines.append(f"- {k}: {v}")
            lines.append("")

        # 直播间FAQ预埋
        lines.append("## 直播间FAQ预埋")
        lines.append("")
        faq_items = [
            (f"这个产品的核心优势是什么？", f"核心优势在于「{main_hook}」，这是我们测试中消费者最认可的点。"),
            ("跟竞品相比有什么不同？", "我们的差异化在于经过消费者传播验证的独特卖点组合。"),
            ("适合什么样的人群？", f"目标人群画像详见报告，核心受众对「{main_hook}」有强需求。"),
            ("有没有什么需要注意的？", f"关于「{main_risk}」的疑问，我们准备了专业的解答话术。"),
            ("效果怎么样？有数据吗？", "消费者传播测试显示了明确的正向接受度，具体数据可在详情页查看。"),
        ]
        for i, (q, a) in enumerate(faq_items, 1):
            lines.append(f"**Q{i}: {q}**")
            lines.append(f"A: {a}")
            lines.append("")

        # 短视频脚本建议
        lines.append("## 短视频脚本建议")
        lines.append("")
        angles = [
            ("痛点切入", f"从消费者常见痛点出发，引出「{main_hook}」作为解决方案"),
            ("对比实验", f"通过与现有方案的对比，直观展示「{main_hook}」的优势"),
            ("用户证言", f"用真实消费者原声包装，围绕「{main_hook}」讲述使用体验"),
        ]
        for i, (title, desc) in enumerate(angles, 1):
            lines.append(f"**角度{i}: {title}**")
            lines.append(f"- {desc}")
            lines.append("")

        # 评论区回复模板
        lines.append("## 评论区回复模板")
        lines.append("")
        lines.append("**正面评论回复：**")
        lines.append(f"「感谢认可！「{main_hook}」确实是我们最引以为傲的特点，感谢您的支持！」")
        lines.append("")
        lines.append("**质疑/负面评论回复：**")
        lines.append(f"「感谢您的反馈。关于您提到的「{main_risk}」，我们非常重视，这里补充一些说明……」")
        lines.append("")
        lines.append("**咨询类评论回复：**")
        lines.append(f"「您好！关于产品详情，核心卖点是「{main_hook}」，详情页有完整的数据和说明，欢迎查看～」")
        return "\n".join(lines)

    # ── Layer 3 rendering (existing) ───────────────────────────────────

    def _render_consumer_section(self, section_title: str, context: Dict[str, Any]) -> str:
        # Layer 1 & 2 sections — delegate to dedicated renderers
        if section_title == "总裁结论页":
            return self._render_executive_summary(context)
        if section_title == "卖点决策表":
            return self._render_selling_point_table(context)
        if section_title == "合规话术边界":
            return self._render_compliance_table(context)
        if section_title == "渠道策略与执行建议":
            return self._render_channel_strategy(context)

        # Layer 3 sections — existing template-based rendering
        summary = context["summary"]
        task_type = str(context.get("task_type", "")).strip().lower()
        research_findings_value = context.get("research_findings", [])
        research_findings_count = int(
            context.get("research_findings_count")
            or (len(research_findings_value) if isinstance(research_findings_value, list) else 0)
        )

        if section_title == "测试概览":
            lines = [
                f"- 事件样本数：{context['events_count']}",
                f"- 研究发现总数：{research_findings_count}",
                f"- 证据原子数：{context.get('evidence_atom_count', 0)}",
                f"- 初始接受度：{self._format_acceptance(summary['initial_acceptance'])}",
                f"- 传播后接受度：{self._format_acceptance(summary['post_propagation_acceptance'])}",
                f"- 态度转向率：{summary['attitude_shift_rate']:.0%}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"- 包装吸引点：{self._format_points(context['top_packaging_hooks'])}")
            if task_type == "ab_test" and context.get("winning_variant"):
                lines.append(f"- 占优 variant：{context['winning_variant']}")
            if task_type == "price_test" and context.get("price_context"):
                lines.append(f"- 价格背景：{context['price_context']}")
            return "\n".join(lines)

        if section_title == "研究发现综合":
            type_counts = context.get("research_finding_type_counts") or {}
            pillars = context.get("research_insight_pillars") or []
            quote_groups = context.get("representative_voc_quotes") or {}
            lines = [
                f"- 研究发现总数：{research_findings_count}",
                f"- 主题分布：{self._format_finding_type_counts(type_counts)}",
                f"- 综合洞察：{context.get('research_insight_summary') or '暂无'}",
            ]
            if pillars:
                lines.append("- 关键研究主线：")
                for pillar in pillars[:4]:
                    lines.append(f"  - [{pillar.get('finding_type_label', pillar.get('finding_type', ''))}] {pillar.get('summary', '')}")
                    evidence_preview = str(pillar.get("evidence_preview", "") or "").strip()
                    if evidence_preview:
                        lines.append(f"    - 证据：{evidence_preview}")
            quote_bridge: List[str] = []
            if quote_groups.get("resonance"):
                quote_bridge.append(f'正向："{quote_groups["resonance"][0].get("quote", "")}"')
            if quote_groups.get("risk"):
                quote_bridge.append(f'风险："{quote_groups["risk"][0].get("quote", "")}"')
            if quote_groups.get("misread"):
                quote_bridge.append(f'误读："{quote_groups["misread"][0].get("quote", "")}"')
            if quote_bridge:
                lines.append("- 原声印证：")
                for item in quote_bridge:
                    lines.append(f"  - {item}")
            return "\n".join(lines)

        if section_title == "初始反应":
            lines = [
                f"- 高共鸣点：{self._format_points(context['top_resonance_points'])}",
                f"- 代表性正向原声：\n{self._format_quotes(context['representative_voc_quotes']['resonance'])}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"- 包装第一眼吸引：{self._format_points(context['top_packaging_hooks'])}")
            if task_type == "ab_test" and context.get("top_variant_deltas"):
                lines.append("- Variant 差异感知：")
                for delta in context["top_variant_deltas"][:3]:
                    d_type = delta.get("type", "")
                    d_quote = delta.get("quote", "")
                    lines.append(f"  - [{d_type}] {d_quote}")
            if task_type == "price_test" and context.get("acceptable_price_points"):
                lines.append(f"- 可接受价格：{self._format_points(context['acceptable_price_points'])}")
            return "\n".join(lines)

        if section_title == "传播演化":
            lines = [
                f"- 传播后接受度：{self._format_acceptance(summary['post_propagation_acceptance'])}",
                f"- 态度转向率：{summary['attitude_shift_rate']:.0%}",
                f"- 扩散中的高频讨论点：{self._format_points(context['top_resonance_points'])}",
            ]
            if task_type == "packaging_test" and context.get("top_trust_objections"):
                lines.append(f"- 信任疑虑：{self._format_points(context['top_trust_objections'])}")
            if task_type == "ab_test" and context.get("top_persona_divergences"):
                lines.append(f"- 人群差异：{self._format_points(context['top_persona_divergences'])}")
            if task_type == "price_test" and context.get("resisted_price_points"):
                lines.append(f"- 抗拒价格：{self._format_points(context['resisted_price_points'])}")
            return "\n".join(lines)

        if section_title == "价格敏感度与 WTP 分析":
            return "\n".join([
                f"- 可接受价格：{self._format_points(context.get('acceptable_price_points', []))}",
                f"- 抗拒价格：{self._format_points(context.get('resisted_price_points', []))}",
                f"- 价格异议：{self._format_points(context.get('top_price_objections', []))}",
            ])

        if section_title == "价格接受区间与弹性":
            return "\n".join([
                f"- 价格背景：{context.get('price_context', '') or '暂无'}",
                "- WTP 分布应结合真实价格带和传播后接受度共同解释。",
            ])

        if section_title == "视觉认知与货架吸引力":
            return "\n".join([
                f"- 包装吸引点：{self._format_points(context.get('top_packaging_hooks', []))}",
                f"- 混淆触发点：{self._format_points(context.get('top_confusion_triggers', []))}",
            ])

        if section_title == "包装识别与注意力路径":
            return "\n".join([
                f"- 信任疑虑：{self._format_points(context.get('top_trust_objections', []))}",
                "- 货架吸引力应结合第一眼理解、证据位置和包装差异化判断。",
            ])

        if section_title == "偏好对比与统计显著性":
            lines = [f"- 占优 variant：{context.get('winning_variant', '') or '暂无'}"]
            for delta in context.get("top_variant_deltas", [])[:3]:
                lines.append(f"  - {delta.get('quote', delta)}")
            lines.append("- 统计显著性需结合样本量、重复种子和置信度输出。")
            return "\n".join(lines)

        if section_title == "版本差异与选择理由":
            return "\n".join([
                f"- 人群差异：{self._format_points(context.get('top_persona_divergences', []))}",
                "- 版本选择理由应优先引用差异化 VOC 与事件链。",
            ])

        if section_title == "风险与误读":
            lines = [
                f"- 高风险点：{self._format_points(context['top_risk_points'])}",
                f"- 高误读点：{self._format_points(context['top_misreads'])}",
                f"- 风险原声：\n{self._format_quotes(context['representative_voc_quotes']['risk'])}",
                f"- 误读/疑问原声：\n{self._format_quotes(context['representative_voc_quotes']['misread'])}",
            ]
            if task_type == "packaging_test" and context.get("top_confusion_triggers"):
                lines.append(f"- 包装混淆点：{self._format_points(context['top_confusion_triggers'])}")
            if task_type == "price_test" and context.get("top_price_objections"):
                lines.append(f"- 价格异议：{self._format_points(context['top_price_objections'])}")
            if context.get("top_risk_findings"):
                lines.append("- 因果触发发现：")
                for finding in context["top_risk_findings"]:
                    lines.append(f"  - [{finding['finding_type']}] {finding['summary']}")
            if context.get("causal_chains"):
                lines.append("- 事件因果链：")
                for chain in context["causal_chains"][:3]:
                    lines.append(f"  - 发现 {chain['finding_summary']} 触发了事件 {', '.join(chain['event_ids'])}")
            return "\n".join(lines)

        if section_title == "代表性消费者原声":
            lines = [
                f"**正向原声**\n{self._format_quotes(context['representative_voc_quotes']['resonance'])}",
                f"**风险原声**\n{self._format_quotes(context['representative_voc_quotes']['risk'])}",
                f"**误读/疑问原声**\n{self._format_quotes(context['representative_voc_quotes']['misread'])}",
            ]
            if task_type == "packaging_test" and context.get("top_packaging_hooks"):
                lines.append(f"**包装相关原声**\n{self._format_task_quotes(context['top_packaging_hooks'])}")
            if task_type == "price_test" and context.get("top_price_objections"):
                lines.append(f"**价格相关原声**\n{self._format_task_quotes(context['top_price_objections'])}")
            return "\n\n".join(lines)

        if section_title == "行动建议":
            resonance_point = self._first_point(context["top_resonance_points"], "现有核心卖点")
            risk_point = self._first_point(context["top_risk_points"], "潜在争议点")
            misread_point = self._first_point(context["top_misreads"], "传播中的模糊表述")
            lines = [
                f"- 放大高共鸣表达：围绕“{resonance_point}”继续强化概念与文案。",
                f"- 提前澄清风险：针对“{risk_point}”准备更直接的解释与证据。",
                f"- 修正文案误读：对“{misread_point}”补充更具体、更少歧义的表述。",
            ]
            pillars = context.get("research_insight_pillars") or []
            if pillars:
                anchor = self._first_point([str(p.get("summary", "")).strip() for p in pillars if str(p.get("summary", "")).strip()], "研究发现")
                lines.append(f"- 综合传播锚点：优先围绕“{anchor}”统一原声、证据和文案。")
            if task_type == "packaging_test":
                trust = self._first_point(context.get("top_trust_objections", []), "信任疑虑")
                confusion = self._first_point(context.get("top_confusion_triggers", []), "混淆点")
                lines.append(f"- 优化包装信任感：针对“{trust}”增加背书或认证信息。")
                lines.append(f"- 消除包装混淆：对“{confusion}”简化设计或增加说明。")
            if task_type == "ab_test":
                variant = context.get("winning_variant", "") or "占优 variant"
                lines.append(f"- 推广优胜 variant：重点投放“{variant}”并分析其优势要素。")
            if task_type == "price_test":
                acceptable = self._first_point(context.get("acceptable_price_points", []), "可接受价格带")
                resisted = self._first_point(context.get("resisted_price_points", []), "抗拒价格点")
                lines.append(f"- 锚定合理价格：以“{acceptable}”为传播锚点强化价值感知。")
                lines.append(f"- 规避价格雷区：针对“{resisted}”提前准备价值解释或促销话术。")
            if context.get("top_risk_findings"):
                lines.append("- 针对风险发现的优先行动：")
                for finding in context["top_risk_findings"][:3]:
                    lines.append(f"  - 处理 [{finding['finding_type']}] {finding['summary']}")
            if context.get("event_counts"):
                lines.append(f"- 事件类型分布：{context['event_counts']}")
            return "\n".join(lines)

        return ""

    def _format_task_quotes(self, items: List[str]) -> str:
        if not items:
            return "- 暂无"
        lines = []
        for item in items:
            lines.append(f'- "{item}"')
        return "\n".join(lines)

    def _format_acceptance(self, acceptance: Dict[str, float]) -> str:
        return (
            f"正向 {acceptance.get('positive', 0.0):.0%} / "
            f"中立 {acceptance.get('neutral', 0.0):.0%} / "
            f"负向 {acceptance.get('negative', 0.0):.0%}"
        )

    def _format_points(self, points: List[str]) -> str:
        if not points:
            return "暂无显著点位"
        return "；".join(points)

    def _format_finding_type_counts(self, counts: Any) -> str:
        if not isinstance(counts, dict) or not counts:
            return "暂无"

        preferred_order = [
            "category_context",
            "competitor_signal",
            "risk_signal",
            "trend_signal",
            "propagation_signal",
        ]
        lines: List[str] = []
        seen: set[str] = set()
        for finding_type in preferred_order:
            if finding_type in counts:
                seen.add(finding_type)
                lines.append(
                    f"{self._finding_type_label(finding_type)} {int(counts.get(finding_type, 0) or 0)}"
                )
        for finding_type, value in counts.items():
            if finding_type in seen:
                continue
            lines.append(f"{self._finding_type_label(str(finding_type))} {int(value or 0)}")
        return "，".join(lines) if lines else "暂无"

    def _format_quotes(self, quotes: List[Dict[str, Any]]) -> str:
        if not quotes:
            return "- 暂无代表性原声"

        def is_template_generated(item: Dict[str, Any]) -> bool:
            metadata = item.get("quote_metadata") or {}
            if isinstance(metadata, dict) and "template_generated" in metadata:
                return bool(metadata.get("template_generated"))
            return True

        sorted_quotes = sorted(quotes, key=is_template_generated)
        llm_count = sum(1 for item in sorted_quotes if not is_template_generated(item))
        template_count = len(sorted_quotes) - llm_count
        lines = [f"- Source: LLM\u751f\u6210 {llm_count} / \u6a21\u62df\u751f\u6210 {template_count}"]
        for item in sorted_quotes:
            quote = str(item.get("quote", "")).strip()
            if not quote:
                continue
            engagement = item.get("engagement", 0)
            source_label = " [\u6a21\u62df\u751f\u6210\uff0c\u975eLLM\u63a8\u7406]" if is_template_generated(item) else ""
            lines.append(f'- "{quote}"{source_label} (engagement {engagement})')
        return "\n".join(lines) if len(lines) > 1 else "- 暂无代表性原声"
