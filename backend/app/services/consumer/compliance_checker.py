"""
合规话术边界检查模块
检查营销 claim 的广告法风险，输出合规话术边界表供报告使用。
支持按渠道（小红书/抖音/直播间/详情页）的差异化合规规则。

基于《中华人民共和国广告法》（2021修正）、《化妆品监督管理条例》等法规，
对口腔护理品类营销话术进行自动化风险筛查与合规改写建议。
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 枚举定义
# ---------------------------------------------------------------------------

class RiskLevel(str):
    """风险等级常量"""
    HIGH = "高风险"       # 可能违反广告法，必须修改
    MEDIUM = "中风险"     # 存在误读风险，建议加限定语
    LOW = "低风险"        # 基本安全，可直接使用


class RiskCategory(str):
    """风险类别常量"""
    ABSOLUTE_CLAIM = "绝对化用语"           # 最、第一、唯一等
    MEDICAL_CLAIM = "医疗化表达"             # 治疗、修复、治愈等
    CERTAINTY_EFFECT = "确定性效果承诺"       # X天必白、保证有效等
    UNVERIFIABLE = "不可验证声明"            # 无法证实的效果描述
    MISLEADING_COMPARISON = "误导性对比"      # 比XX好、超越所有等
    PLATFORM_RESTRICTED = "平台限制内容"      # 特定平台禁止的内容


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ComplianceIssue:
    """单个合规问题"""
    original_expression: str           # 原始表达
    risk_level: str                    # 风险等级
    risk_category: str                 # 风险类别
    risk_reason: str                   # 风险原因
    suggested_alternative: str         # 建议替代表达
    legal_reference: str               # 法规参考（如"《广告法》第X条"）
    platform_rules: Dict[str, str] = field(default_factory=dict)  # 各平台特殊规则


@dataclass
class ClaimComplianceResult:
    """单个 claim 的合规检查结果"""
    claim_text: str                    # 原始 claim
    overall_risk: str                  # 整体风险等级
    issues: List[ComplianceIssue]      # 具体问题列表
    safe_expression: str               # 安全表达建议
    channel_guidelines: Dict[str, str] = field(default_factory=dict)  # 各渠道话术指南


@dataclass
class _FindingView:
    """兼容 report_agent 渲染层的扁平化 finding 视图。

    report_agent._render_compliance_table 访问 ``comp_report.findings``，
    每个 finding 需要 ``expression``、``risk_reason``、``suggested_alternative``。
    此类将 ComplianceIssue 的字段映射为渲染层期望的属性名。
    """

    expression: str
    risk_reason: str
    suggested_alternative: str
    risk_level: str = ""
    risk_category: str = ""
    source_claim: str = ""


@dataclass
class ComplianceReport:
    """合规检查报告"""
    results: List[ClaimComplianceResult]
    high_risk_claims: List[str]        # 高风险 claim 列表
    medium_risk_claims: List[str]      # 中风险 claim 列表
    safe_claims: List[str]             # 安全 claim 列表
    channel_faq: Dict[str, List[str]]  # 各渠道 FAQ 话术
    livestream_script: List[str]       # 直播间话术要点
    detail_page_order: List[str]       # 详情页模块顺序建议

    @property
    def findings(self) -> List[_FindingView]:
        """将所有 claim 的 issues 扁平化为渲染层可消费的 finding 列表。

        report_agent._render_compliance_table 通过
        ``comp_report.findings`` + ``finding.expression`` / ``finding.risk_reason``
        / ``finding.suggested_alternative`` 访问合规数据，此属性提供兼容接口。
        """
        views: List[_FindingView] = []
        for result in self.results:
            for issue in result.issues:
                views.append(_FindingView(
                    expression=issue.original_expression,
                    risk_reason=issue.risk_reason,
                    suggested_alternative=issue.suggested_alternative or result.safe_expression,
                    risk_level=issue.risk_level,
                    risk_category=issue.risk_category,
                    source_claim=result.claim_text,
                ))
        return views


# ---------------------------------------------------------------------------
# 风险规则库
# ---------------------------------------------------------------------------

# 规则结构: (正则表达式, 风险类别, 风险等级, 风险原因, 法规参考)
RISK_RULES: List[Tuple[str, str, str, str, str]] = [
    # --- 绝对化用语检测 (广告法第九条第三项) ---
    (
        r"最[^一-鿿]|[最][一-鿿]{0,2}[的]",
        RiskCategory.ABSOLUTE_CLAIM, RiskLevel.HIGH,
        "含有\"最\"字绝对化用语，违反广告法关于禁止使用绝对化用语的规定",
        "《广告法》第九条第三项",
    ),
    (
        r"第一|首位|首个|首创|排行第一|No\.?\s*1|Top\s*1",
        RiskCategory.ABSOLUTE_CLAIM, RiskLevel.HIGH,
        "含有\"第一/首位\"等表示最高级别的绝对化用语",
        "《广告法》第九条第三项",
    ),
    (
        r"唯一|独一无二|仅此一家|绝无仅有|史无前例",
        RiskCategory.ABSOLUTE_CLAIM, RiskLevel.HIGH,
        "含有\"唯一\"等排他性绝对化用语",
        "《广告法》第九条第三项",
    ),
    (
        r"顶级|极致|无敌|全能|万能|超级[^一-鿿]",
        RiskCategory.ABSOLUTE_CLAIM, RiskLevel.HIGH,
        "含有\"顶级/极致\"等夸大性质的绝对化用语",
        "《广告法》第九条第三项",
    ),
    (
        r"100\s*%|百分之?百",
        RiskCategory.ABSOLUTE_CLAIM, RiskLevel.HIGH,
        "含有\"100%\"等绝对化数据承诺",
        "《广告法》第九条第三项",
    ),
    (
        r"国家级|世界级|全球级|宇宙级",
        RiskCategory.ABSOLUTE_CLAIM, RiskLevel.HIGH,
        "含有\"国家级\"等超越实际的级别描述",
        "《广告法》第九条第三项",
    ),

    # --- 医疗化表达检测 (广告法第十七条、化妆品监督管理条例) ---
    (
        r"修复(?!.*视觉)|修护(?!.*损伤)|治愈|疗效|药用|医用|根治|杜绝",
        RiskCategory.MEDICAL_CLAIM, RiskLevel.HIGH,
        "使用了医疗化表述，暗示产品具有治疗/修复功效，化妆品不得宣称医疗效果",
        "《广告法》第十七条、《化妆品监督管理条例》第四十三条",
    ),
    (
        r"治疗|医治|诊治|处方|临床治疗",
        RiskCategory.MEDICAL_CLAIM, RiskLevel.HIGH,
        "直接使用医疗术语，严重违反化妆品宣传规定",
        "《广告法》第十七条",
    ),
    (
        r"药效|药物|配方药|消炎|杀菌(?!.*清新)|抗菌(?!.*配方)",
        RiskCategory.MEDICAL_CLAIM, RiskLevel.HIGH,
        "将日化产品与药品概念混淆，误导消费者",
        "《广告法》第十七条、《化妆品监督管理条例》",
    ),
    (
        r"修护牙釉质|修复牙釉质|再矿化|再生",
        RiskCategory.MEDICAL_CLAIM, RiskLevel.HIGH,
        "对牙齿结构修复的描述属于医疗化宣称，普通牙膏不得如此表述",
        "《广告法》第十七条、《化妆品监督管理条例》第四十三条",
    ),

    # --- 确定性效果承诺 (广告法第四条) ---
    (
        r"\d+天[^一-鿿]*[白亮净淡去减消]",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.HIGH,
        "含确定性时间+效果承诺，暗示在固定时间内保证达成效果",
        "《广告法》第四条",
    ),
    (
        r"\d+天[^一-鿿]*\d+度",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.HIGH,
        "含\"X天X度\"的精确效果量化承诺，无法对所有消费者保证",
        "《广告法》第四条",
    ),
    (
        r"保证|必定|一定[^一-鿿]*有效|必然|肯定",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.HIGH,
        "使用确定性承诺用语，暗示效果的绝对确定性",
        "《广告法》第四条",
    ),
    (
        r"立竿见影|即刻见效|马上[^一-鿿]*白",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.HIGH,
        "夸大即时效果承诺，与实际产品体验可能不符",
        "《广告法》第四条",
    ),
    (
        r"临床验证|临床实[验测]|临床数据",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.MEDIUM,
        "引用临床数据需确保来源权威且标注具体测试条件",
        "《广告法》第四条、第十一条",
    ),
    (
        r"长效\d+[小时时]",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.MEDIUM,
        "长时间效果声明需有可验证的测试数据支撑",
        "《广告法》第四条",
    ),
    (
        r"瞬降\d+[度℃]",
        RiskCategory.CERTAINTY_EFFECT, RiskLevel.MEDIUM,
        "精确数字的效果声明容易被质疑，建议用模糊表达替代",
        "《广告法》第四条",
    ),

    # --- 不可验证声明 (广告法第四条) ---
    (
        r"全球领先|行业领先|世界领先",
        RiskCategory.UNVERIFIABLE, RiskLevel.MEDIUM,
        "\"领先\"地位声明需要权威第三方数据支撑",
        "《广告法》第四条",
    ),
    (
        r"行业首创|全球首创|国内首创",
        RiskCategory.UNVERIFIABLE, RiskLevel.MEDIUM,
        "\"首创\"声明需提供专利或权威机构的首创认定",
        "《广告法》第四条",
    ),
    (
        r"革命性|突破性|颠覆性|里程碑",
        RiskCategory.UNVERIFIABLE, RiskLevel.MEDIUM,
        "使用过度夸张的科技描述，容易被视为虚假宣传",
        "《广告法》第四条",
    ),
    (
        r"独创|独家|独有|专利(?!号|申请)",
        RiskCategory.UNVERIFIABLE, RiskLevel.MEDIUM,
        "\"独创/独家\"声明需有专利或知识产权佐证",
        "《广告法》第四条",
    ),

    # --- 误导性对比 (广告法第十三条) ---
    (
        r"比.{0,8}好|比.{0,8}强|优于.{0,6}",
        RiskCategory.MISLEADING_COMPARISON, RiskLevel.MEDIUM,
        "对比性描述需提供客观数据支撑，否则易构成误导",
        "《广告法》第十三条",
    ),
    (
        r"超越|碾压|秒杀|完胜|吊打|甩开",
        RiskCategory.MISLEADING_COMPARISON, RiskLevel.MEDIUM,
        "攻击性对比用语可能构成不正当竞争",
        "《广告法》第十三条、《反不正当竞争法》",
    ),
]


# ---------------------------------------------------------------------------
# Claim 专属分析规则
# ---------------------------------------------------------------------------

# 结构: {claim子串: {risk_level, risk_category, risk_reason, alternative, channel_notes, must_add, must_avoid}}
CLAIM_SPECIFIC_RULES: Dict[str, Dict[str, Any]] = {
    "冷光修白": {
        "risk_level": RiskLevel.MEDIUM,
        "risk_category": RiskCategory.UNVERIFIABLE,
        "risk_reason": "\"冷光\"容易被消费者误解为医美冷光美白技术，存在误导风险",
        "alternative": "模拟光学显白思路，帮助改善黄牙视觉观感",
        "channel_notes": {
            "抖音": "需配合视觉演示动画，说明非医美冷光",
            "直播间": "主播需口头说明为产品配方概念，非医美项目",
            "小红书": "图文笔记中添加免责声明小字",
            "详情页": "在成分说明区域解释\"冷光\"概念来源",
        },
    },
    "以紫修黄": {
        "risk_level": RiskLevel.LOW,
        "risk_category": RiskCategory.UNVERIFIABLE,
        "risk_reason": "\"以紫修黄\"为色彩理论应用描述，风险较低",
        "alternative": "利用色彩互补原理，紫色调配方帮助中和黄牙视觉",
        "channel_notes": {},
    },
    "7天白4度": {
        "risk_level": RiskLevel.HIGH,
        "risk_category": RiskCategory.CERTAINTY_EFFECT,
        "risk_reason": "\"7天白4度\"为精确时间+精确效果的双重确定性承诺，消费者个体差异大，无法对所有人保证",
        "alternative": "基于特定测试条件，连续使用后牙色改善最高可达…（需附测试条件）",
        "channel_notes": {
            "抖音": "必须标注\"效果因人而异\"字样",
            "直播间": "主播需说明\"基于实验室数据，实际效果因个人情况不同\"",
            "小红书": "正文中需注明测试来源和条件",
            "详情页": "以脚注形式附完整测试条件说明",
        },
        "must_add": ["测试来源机构", "限定条件（如：配合正确刷牙方式）", "\"效果因人而异\"免责声明"],
    },
    "SGS临床验证": {
        "risk_level": RiskLevel.LOW,
        "risk_category": RiskCategory.CERTAINTY_EFFECT,
        "risk_reason": "引用权威机构验证本身风险较低，但需确保数据真实且标注完整",
        "alternative": "经SGS机构检测验证（附检测报告编号更佳）",
        "channel_notes": {
            "小红书": "建议用一句话解释SGS权威性：\"SGS是国际公认的检验鉴定机构\"",
            "抖音": "可在视频字幕中简要展示SGS logo",
            "详情页": "附SGS检测报告缩略图",
        },
        "must_add": ["一句话说明SGS权威性", "检测报告编号（如有）"],
    },
    "持证美白": {
        "risk_level": RiskLevel.LOW,
        "risk_category": RiskCategory.CERTAINTY_EFFECT,
        "risk_reason": "\"持证\"表述风险较低，但需确保所持证书与宣传内容匹配",
        "alternative": "具备合规美白功效依据，具体以产品标识为准",
        "channel_notes": {
            "直播间": "可展示证书实物或扫描件",
            "详情页": "在资质区域展示相关证书",
        },
    },
    "16小时长效清新口气": {
        "risk_level": RiskLevel.MEDIUM,
        "risk_category": RiskCategory.CERTAINTY_EFFECT,
        "risk_reason": "\"16小时\"的精确时间声明需要有严谨的测试数据支撑",
        "alternative": "持久清新口气体验",
        "channel_notes": {
            "抖音": "绑定通勤/会议/约会等具体使用场景更安全",
            "直播间": "用\"一整天清新\"替代精确数字",
            "小红书": "以个人体验角度描述：\"早上用完到晚上还有清新感\"",
            "详情页": "以图表形式展示留香曲线，附测试条件",
        },
        "must_add": ["测试方法和条件说明"],
    },
    "口腔温度瞬降4℃": {
        "risk_level": RiskLevel.MEDIUM,
        "risk_category": RiskCategory.CERTAINTY_EFFECT,
        "risk_reason": "精确温度数字声明容易被消费者质疑和较真，且可能暗示医疗级效果",
        "alternative": "清凉感显著提升",
        "channel_notes": {
            "抖音": "用\"清凉感\"表达更安全，配合使用场景演示",
            "直播间": "主播可用\"冰冰凉凉的感觉\"替代精确数字",
            "小红书": "以感官体验描述为主，避免数字",
            "详情页": "如需保留数字，必须附测试方法说明",
        },
    },
    "修护牙釉质": {
        "risk_level": RiskLevel.HIGH,
        "risk_category": RiskCategory.MEDICAL_CLAIM,
        "risk_reason": "\"修护牙釉质\"属于对牙齿结构的修复宣称，普通牙膏不得使用医疗化表述",
        "alternative": "帮助保护牙釉质，减少日常酸蚀损伤",
        "channel_notes": {
            "抖音": "绝对不可使用\"修复\"二字，可用\"呵护/保护\"",
            "直播间": "主播口播时注意避免脱口说出\"修复\"",
            "小红书": "文案中用\"守护/呵护\"替代",
            "详情页": "在功效描述中使用\"保护\"并附说明",
        },
        "must_avoid": ["修复", "修护（单独使用）", "治疗", "再生", "再矿化"],
    },
}


# ---------------------------------------------------------------------------
# 渠道专属规则
# ---------------------------------------------------------------------------

CHANNEL_RESTRICTED_RULES: Dict[str, List[Tuple[str, str, str]]] = {
    "小红书": [
        (r"买它|赶紧下单|限时\d+小时", RiskLevel.MEDIUM, "小红书对强营销话术限流，建议用种草体验替代"),
        (r"医美同款|医美级", RiskLevel.HIGH, "小红书严格管控医美相关内容，日化品不得借势医美"),
    ],
    "抖音": [
        (r"史上最|全网最", RiskLevel.HIGH, "抖音对绝对化用语审核严格，可能直接下架"),
        (r"秒杀价|亏本卖", RiskLevel.MEDIUM, "抖音电商对价格欺诈类话术有专项审核"),
    ],
    "直播间": [
        (r"最后一次|错过不再|马上抢完", RiskLevel.MEDIUM, "直播间虚假紧迫感话术已被平台重点关注"),
        (r"明星同款|大牌平替", RiskLevel.MEDIUM, "直播间借势名人/品牌需有授权证明"),
    ],
    "详情页": [
        (r"(?<!\*)效果因人而异(?!\*)", RiskLevel.LOW, "免责声明应以显著方式标注，建议加粗或加星号"),
    ],
}


# ---------------------------------------------------------------------------
# 渠道 FAQ 模板
# ---------------------------------------------------------------------------

CHANNEL_FAQ_TEMPLATES: Dict[str, List[str]] = {
    "小红书": [
        "Q: 这个牙膏真的能美白吗？\nA: 我们采用光学显白配方，通过色彩互补原理帮助改善牙色视觉观感。坚持使用配合正确刷牙方式，可以看到变化哦~",
        "Q: 和医美冷光美白有什么区别？\nA: 完全不同的思路~我们是通过日常刷牙就能实现的温和亮白方案，不是医美项目，更适合日常长期使用。",
        "Q: 7天能白几个度？\nA: 实验室数据显示连续使用有明显改善，但每个人情况不同，建议坚持使用28天以上观察~",
        "Q: SGS认证是什么？\nA: SGS是国际知名的第三方检测机构，我们的产品经SGS检测验证，品质有保障。",
        "Q: 敏感牙能用吗？\nA: 建议先小范围试用，如有不适请停用并咨询牙医。",
    ],
    "抖音": [
        "【15秒脚本】黄牙星人看过来！这支牙膏用色彩互补原理帮你改善牙色观感（展示产品），配合正确刷牙方式坚持使用，牙齿视觉变化看得见（展示效果对比）。SGS检测验证，品质放心！",
        "【评论区置顶话术】效果因个人情况不同，建议持续使用观察变化。产品经SGS检测，详情见主页。",
    ],
    "直播间": [
        "这款牙膏的亮点是采用了光学显白的思路（拿起产品展示），紫色配方帮助中和黄牙的视觉效果。",
        "它通过了SGS的检测验证（展示报告），大家知道SGS是国际权威的第三方检测机构，品质方面大家可以放心。",
        "使用方法很简单，像普通牙膏一样每天早晚刷就行，建议坚持使用观察效果。效果因人而异哈~",
        "（应对追问\"几天能白\"）每个人牙齿情况不同，实验室数据是有改善趋势，但建议大家给自己多一点时间，一般28天是一个比较合理的观察周期。",
        "（应对追问\"能不能修复牙釉质\"）我们更准确的说法是帮助保护牙釉质，减少日常饮食带来的酸蚀影响，不是医疗修复哦。",
    ],
}


# ---------------------------------------------------------------------------
# 详情页模块顺序建议
# ---------------------------------------------------------------------------

DETAIL_PAGE_MODULE_ORDER: List[str] = [
    "1. 核心卖点区（安全版本，不含绝对化用语）",
    "2. 光学显白原理说明（配图文解释\"冷光\"概念来源，非医美）",
    "3. 权威认证区（SGS检测报告展示，证书编号）",
    "4. 成分安全区（主要成分及安全说明）",
    "5. 使用效果区（附测试条件、\"效果因人而异\"免责声明）",
    "6. 使用场景区（通勤/约会/会议等场景化描述）",
    "7. 使用方法与注意事项",
    "8. 用户评价区（真实评价，不含诱导性好评）",
    "9. 品牌资质区（生产许可、质检报告等）",
    "10. FAQ区（预埋常见问题及合规回答）",
]


# ---------------------------------------------------------------------------
# 直播间话术要点
# ---------------------------------------------------------------------------

LIVESTREAM_SCRIPT_POINTS: List[str] = [
    "开场：\"今天给大家带来一款很有意思的牙膏，它的思路和普通牙膏不太一样\"",
    "核心卖点：\"它用的是光学显白的原理，紫色配方帮助中和黄牙的视觉效果\"",
    "权威背书：\"这款产品通过了SGS的检测验证，SGS是国际知名的第三方检测机构\"",
    "使用引导：\"每天早晚像正常牙膏一样使用就好，建议坚持一段时间观察效果\"",
    "效果回答：\"每个人情况不同，实验室数据显示有改善趋势，建议给自己28天的观察期\"",
    "安全提示：\"效果因人而异，如有不适请停用并咨询专业人士\"",
    "禁忌词汇：绝对不说\"修复、治疗、保证、一定、7天必白\"",
    "互动引导：\"有没有黄牙困扰的姐妹扣个1，给大家看一下对比图\"",
]


# ---------------------------------------------------------------------------
# 核心检查逻辑
# ---------------------------------------------------------------------------

def _match_risk_rules(text: str) -> List[ComplianceIssue]:
    """
    将文本与风险规则库进行正则匹配，返回命中的合规问题列表。

    Args:
        text: 待检查文本

    Returns:
        命中的合规问题列表
    """
    issues: List[ComplianceIssue] = []
    seen_categories: set = set()

    for pattern, category, level, reason, legal_ref in RISK_RULES:
        match = re.search(pattern, text)
        if match:
            # 同一类别只报一次，避免重复
            dedup_key = (category, match.group())
            if dedup_key in seen_categories:
                continue
            seen_categories.add(dedup_key)

            matched_text = match.group()
            issues.append(ComplianceIssue(
                original_expression=matched_text,
                risk_level=level,
                risk_category=category,
                risk_reason=reason,
                suggested_alternative="",  # 将在后续由 claim 专属规则补充
                legal_reference=legal_ref,
            ))

    return issues


def _check_channel_rules(text: str) -> List[ComplianceIssue]:
    """
    检查各渠道的平台专属限制规则。

    Args:
        text: 待检查文本

    Returns:
        渠道限制相关的合规问题列表
    """
    issues: List[ComplianceIssue] = []

    for channel, rules in CHANNEL_RESTRICTED_RULES.items():
        for pattern, level, reason in rules:
            match = re.search(pattern, text)
            if match:
                issues.append(ComplianceIssue(
                    original_expression=match.group(),
                    risk_level=level,
                    risk_category=RiskCategory.PLATFORM_RESTRICTED,
                    risk_reason=f"[{channel}] {reason}",
                    suggested_alternative="",
                    legal_reference="平台社区规范",
                    platform_rules={channel: reason},
                ))

    return issues


def _analyze_claim_specific(claim_text: str) -> Optional[Dict[str, Any]]:
    """
    对单个 claim 进行专属规则分析。

    Args:
        claim_text: claim 原文

    Returns:
        匹配到的专属规则字典，未匹配返回 None
    """
    for keyword, rule in CLAIM_SPECIFIC_RULES.items():
        if keyword in claim_text:
            return rule
    return None


def _get_max_risk_level(levels: Sequence[str]) -> str:
    """
    从多个风险等级中取最高级别。

    Args:
        levels: 风险等级列表

    Returns:
        最高风险等级
    """
    priority = {RiskLevel.HIGH: 3, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 1}
    if not levels:
        return RiskLevel.LOW
    return max(levels, key=lambda x: priority.get(x, 0))


def _build_channel_guidelines(claim_text: str, specific_rule: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    构建各渠道的话术指南。

    Args:
        claim_text: claim 原文
        specific_rule: claim 专属规则（如有）

    Returns:
        {渠道名: 话术指南} 字典
    """
    guidelines: Dict[str, str] = {}

    # 默认指南
    default_guidelines = {
        "小红书": "以个人体验角度撰写，避免绝对化用语，附免责声明",
        "抖音": "配合场景化视频演示，字幕标注\"效果因人而异\"",
        "直播间": "主播口播时避免精确数字承诺，用感官描述替代",
        "详情页": "附完整测试条件说明，以脚注形式标注免责声明",
    }

    if specific_rule and "channel_notes" in specific_rule:
        channel_notes = specific_rule["channel_notes"]
        for channel in ["小红书", "抖音", "直播间", "详情页"]:
            if channel in channel_notes:
                guidelines[channel] = channel_notes[channel]
            else:
                guidelines[channel] = default_guidelines.get(channel, "")
    else:
        guidelines = default_guidelines

    return guidelines


def _build_safe_expression(claim_text: str, specific_rule: Optional[Dict[str, Any]]) -> str:
    """
    构建安全表达建议。

    Args:
        claim_text: claim 原文
        specific_rule: claim 专属规则（如有）

    Returns:
        安全替代表达
    """
    if specific_rule and "alternative" in specific_rule:
        return specific_rule["alternative"]

    # 通用安全化处理
    safe = claim_text
    # 替换绝对化用语
    safe = re.sub(r"最[^一-鿿]", "更", safe)
    safe = re.sub(r"第一|首位|首个", "领先", safe)
    safe = re.sub(r"唯一|独一无二", "独特", safe)
    safe = re.sub(r"顶级|极致", "优质", safe)
    safe = re.sub(r"100\s*%|百分之?百", "高比例", safe)
    # 替换医疗化用语
    safe = re.sub(r"修复|修护", "保护", safe)
    safe = re.sub(r"治疗|治愈", "改善", safe)
    # 替换确定性承诺
    safe = re.sub(r"保证|必定|一定", "帮助", safe)

    return safe


def _check_single_claim(claim_text: str) -> ClaimComplianceResult:
    """
    对单个 claim 进行完整的合规检查。

    Args:
        claim_text: 单个营销 claim 文本

    Returns:
        该 claim 的完整合规检查结果
    """
    # 1. 通用规则匹配
    rule_issues = _match_risk_rules(claim_text)

    # 2. 渠道专属规则匹配
    channel_issues = _check_channel_rules(claim_text)

    # 3. Claim 专属规则分析
    specific_rule = _analyze_claim_specific(claim_text)

    # 合并所有问题
    all_issues: List[ComplianceIssue] = list(rule_issues) + list(channel_issues)

    # 如果有专属规则，添加专属规则的问题
    if specific_rule:
        specific_issue = ComplianceIssue(
            original_expression=claim_text,
            risk_level=specific_rule["risk_level"],
            risk_category=specific_rule["risk_category"],
            risk_reason=specific_rule["risk_reason"],
            suggested_alternative=specific_rule.get("alternative", ""),
            legal_reference="综合评估",
            platform_rules=specific_rule.get("channel_notes", {}),
        )
        all_issues.append(specific_issue)

        # 补充 must_add 提示
        must_add = specific_rule.get("must_add", [])
        if must_add:
            for item in must_add:
                all_issues.append(ComplianceIssue(
                    original_expression="[补充要求]",
                    risk_level=RiskLevel.LOW,
                    risk_category=RiskCategory.PLATFORM_RESTRICTED,
                    risk_reason=f"建议补充：{item}",
                    suggested_alternative="",
                    legal_reference="合规最佳实践",
                ))

        # 补充 must_avoid 提示
        must_avoid = specific_rule.get("must_avoid", [])
        if must_avoid:
            for item in must_avoid:
                if item in claim_text:
                    all_issues.append(ComplianceIssue(
                        original_expression=item,
                        risk_level=RiskLevel.HIGH,
                        risk_category=RiskCategory.MEDICAL_CLAIM,
                        risk_reason=f"该词属于禁用词汇\"{item}\"，必须替换",
                        suggested_alternative="建议替换为\"保护/呵护\"",
                        legal_reference="《广告法》第十七条",
                    ))

    # 计算整体风险等级
    risk_levels = [issue.risk_level for issue in all_issues]
    overall_risk = _get_max_risk_level(risk_levels)

    # 构建安全表达
    safe_expression = _build_safe_expression(claim_text, specific_rule)

    # 构建渠道指南
    channel_guidelines = _build_channel_guidelines(claim_text, specific_rule)

    return ClaimComplianceResult(
        claim_text=claim_text,
        overall_risk=overall_risk,
        issues=all_issues,
        safe_expression=safe_expression,
        channel_guidelines=channel_guidelines,
    )


# ---------------------------------------------------------------------------
# MISREAD / RISK 信号集成
# ---------------------------------------------------------------------------

def _integrate_misread_signals(
    results: List[ClaimComplianceResult],
    misread_quotes: Optional[List[Dict[str, Any]]],
) -> List[ClaimComplianceResult]:
    """
    将仿真产生的 MISREAD_CLAIM 信号整合到合规检查结果中。
    消费者误读意味着该 claim 有额外的合规风险。

    Args:
        results: 现有合规检查结果
        misread_quotes: 仿真输出的误读信号列表，每个元素包含
                        {"claim": str, "misread_as": str, "persona": str, ...}

    Returns:
        更新后的合规检查结果
    """
    if not misread_quotes:
        return results

    # 建立 claim -> result 的索引
    claim_index = {r.claim_text: r for r in results}

    for signal in misread_quotes:
        claim = signal.get("claim", "")
        misread_as = signal.get("misread_as", "")
        persona = signal.get("persona", "未知人群")

        if not claim:
            continue

        # 尝试模糊匹配
        matched_result = None
        for result in results:
            if claim in result.claim_text or result.claim_text in claim:
                matched_result = result
                break

        if matched_result is None:
            continue

        # 添加误读信号作为新的合规问题
        misread_issue = ComplianceIssue(
            original_expression=f"消费者误读：\"{claim}\" 被理解为 \"{misread_as}\"",
            risk_level=RiskLevel.MEDIUM,
            risk_category=RiskCategory.MISLEADING_COMPARISON,
            risk_reason=(
                f"仿真中 {persona} 人群将该表述误读为\"{misread_as}\"，"
                "说明当前话术存在歧义，需要修改以避免误导"
            ),
            suggested_alternative="增加限定语或解释性文字，消除歧义",
            legal_reference="《广告法》第四条（不得含有虚假或引人误解的内容）",
        )
        matched_result.issues.append(misread_issue)

        # 升级风险等级（如果原来是 LOW）
        if matched_result.overall_risk == RiskLevel.LOW:
            matched_result.overall_risk = RiskLevel.MEDIUM

    return results


def _integrate_risk_signals(
    results: List[ClaimComplianceResult],
    risk_quotes: Optional[List[Dict[str, Any]]],
) -> List[ClaimComplianceResult]:
    """
    将仿真产生的风险信号整合到合规检查结果中。

    Args:
        results: 现有合规检查结果
        risk_quotes: 仿真输出的风险信号列表

    Returns:
        更新后的合规检查结果
    """
    if not risk_quotes:
        return results

    for signal in risk_quotes:
        claim = signal.get("claim", "")
        risk_type = signal.get("risk_type", "未知风险")
        severity = signal.get("severity", "中风险")
        detail = signal.get("detail", "")

        if not claim:
            continue

        # 模糊匹配
        matched_result = None
        for result in results:
            if claim in result.claim_text or result.claim_text in claim:
                matched_result = result
                break

        if matched_result is None:
            continue

        risk_issue = ComplianceIssue(
            original_expression=claim,
            risk_level=severity,
            risk_category=risk_type,
            risk_reason=f"[仿真风险信号] {detail}" if detail else f"仿真检测到风险类型：{risk_type}",
            suggested_alternative="请参考安全表达建议进行修改",
            legal_reference="仿真风险评估",
        )
        matched_result.issues.append(risk_issue)

        # 升级风险等级
        priority = {RiskLevel.HIGH: 3, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 1}
        if priority.get(severity, 0) > priority.get(matched_result.overall_risk, 0):
            matched_result.overall_risk = severity

    return results


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------

def _build_compliance_report(results: List[ClaimComplianceResult]) -> ComplianceReport:
    """
    基于各 claim 的合规检查结果，生成完整的合规报告。

    Args:
        results: 所有 claim 的合规检查结果

    Returns:
        完整合规报告
    """
    high_risk: List[str] = []
    medium_risk: List[str] = []
    safe: List[str] = []

    for result in results:
        if result.overall_risk == RiskLevel.HIGH:
            high_risk.append(result.claim_text)
        elif result.overall_risk == RiskLevel.MEDIUM:
            medium_risk.append(result.claim_text)
        else:
            safe.append(result.claim_text)

    return ComplianceReport(
        results=results,
        high_risk_claims=high_risk,
        medium_risk_claims=medium_risk,
        safe_claims=safe,
        channel_faq=CHANNEL_FAQ_TEMPLATES,
        livestream_script=LIVESTREAM_SCRIPT_POINTS,
        detail_page_order=DETAIL_PAGE_MODULE_ORDER,
    )


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def check_compliance(
    claims: List[str],
    misread_quotes: Optional[List[Dict[str, Any]]] = None,
    risk_quotes: Optional[List[Dict[str, Any]]] = None,
) -> ComplianceReport:
    """
    检查所有 claim 的合规风险，生成完整的合规报告。

    对每个营销 claim 进行多维度风险筛查：
    1. 通用广告法规则匹配（绝对化用语、医疗化表达等）
    2. 渠道专属平台规则检查（小红书/抖音/直播间/详情页）
    3. Claim 专属深度分析（针对口腔护理品类的特定话术）
    4. 整合仿真产生的 MISREAD_CLAIM 和风险信号

    Args:
        claims: 待检查的营销 claim 列表
        misread_quotes: 仿真输出的消费者误读信号，格式：
            [{"claim": str, "misread_as": str, "persona": str, ...}, ...]
        risk_quotes: 仿真输出的风险信号，格式：
            [{"claim": str, "risk_type": str, "severity": str, "detail": str, ...}, ...]

    Returns:
        ComplianceReport: 包含风险分级、安全表达建议、渠道指南等完整报告

    Raises:
        ValueError: 当 claims 为空时
    """
    if not claims:
        raise ValueError("claims 列表不能为空，请至少提供一个待检查的营销 claim")

    logger.info("开始合规检查，共 %d 个 claim 待检", len(claims))

    # 第一轮：逐条 claim 检查
    results: List[ClaimComplianceResult] = []
    for claim in claims:
        try:
            result = _check_single_claim(claim)
            results.append(result)
        except Exception as exc:
            logger.error("检查 claim [%s] 时发生异常: %s", claim, exc, exc_info=True)
            # 降级处理：标记为高风险，人工复核
            results.append(ClaimComplianceResult(
                claim_text=claim,
                overall_risk=RiskLevel.HIGH,
                issues=[ComplianceIssue(
                    original_expression=claim,
                    risk_level=RiskLevel.HIGH,
                    risk_category=RiskCategory.UNVERIFIABLE,
                    risk_reason=f"自动检查异常，需人工复核：{exc}",
                    suggested_alternative="请人工审核",
                    legal_reference="系统降级处理",
                )],
                safe_expression="（需人工审核）",
            ))

    # 第二轮：整合仿真信号
    if misread_quotes:
        logger.info("整合 %d 条 MISREAD_CLAIM 信号", len(misread_quotes))
        results = _integrate_misread_signals(results, misread_quotes)

    if risk_quotes:
        logger.info("整合 %d 条风险信号", len(risk_quotes))
        results = _integrate_risk_signals(results, risk_quotes)

    # 生成报告
    report = _build_compliance_report(results)

    logger.info(
        "合规检查完成：高风险 %d 条，中风险 %d 条，安全 %d 条",
        len(report.high_risk_claims),
        len(report.medium_risk_claims),
        len(report.safe_claims),
    )

    return report


def check_single_claim(claim_text: str) -> ClaimComplianceResult:
    """
    检查单个 claim 的合规风险（便捷方法）。

    Args:
        claim_text: 单个营销 claim 文本

    Returns:
        该 claim 的合规检查结果
    """
    if not claim_text or not claim_text.strip():
        raise ValueError("claim 文本不能为空")
    return _check_single_claim(claim_text.strip())


def get_risk_summary(report: ComplianceReport) -> Dict[str, Any]:
    """
    从合规报告中提取风险摘要，便于集成到其他报告模块。

    Args:
        report: 合规报告

    Returns:
        风险摘要字典，包含分级统计和关键建议
    """
    total = len(report.results)
    high_count = len(report.high_risk_claims)
    medium_count = len(report.medium_risk_claims)
    safe_count = len(report.safe_claims)

    # 收集所有高风险问题的关键建议
    critical_suggestions: List[str] = []
    for result in report.results:
        if result.overall_risk == RiskLevel.HIGH:
            critical_suggestions.append(
                f"「{result.claim_text}」建议改为：{result.safe_expression}"
            )

    return {
        "total_claims": total,
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "safe_count": safe_count,
        "compliance_rate": round(safe_count / total * 100, 1) if total > 0 else 0.0,
        "critical_suggestions": critical_suggestions,
        "requires_immediate_action": high_count > 0,
    }
