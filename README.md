<div align="center">


# MiroConsumer

**AI-powered consumer propagation testing for concept and copy validation**

[![Consumer Simulation](https://img.shields.io/badge/Product-Consumer%20Simulation-111827?style=flat-square)](#what-is-miroconsumer)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue%203-42b883?style=flat-square&logo=vuedotjs&logoColor=white)](#quick-start)
[![Flask](https://img.shields.io/badge/Backend-Flask-0f172a?style=flat-square&logo=flask&logoColor=white)](#quick-start)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)](#quick-start)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?style=flat-square&logo=nodedotjs&logoColor=white)](#quick-start)

**MiroConsumer helps teams test product concepts and marketing copy in a simulated consumer society before launch.**

Instead of collecting only static persona ratings, it models **first impression, propagation, amplification, misread risk, and VOC-backed reporting** in one workflow.

[English](./README.md) | [中文](./README-ZH.md)

</div>

## What Is MiroConsumer

MiroConsumer is an AI-powered consumer propagation testing platform.

It is designed for teams who need to answer questions like:

- Will this concept create immediate interest or hesitation?
- Which copy points will spread naturally in conversation?
- Which claims are likely to be amplified, questioned, or misread?
- Which consumer segments become advocates, blockers, or fence-sitters?
- What should be rewritten before launch?

## Why It Is Different

Most AI-based concept testing tools stop at static persona evaluation.

MiroConsumer is built around a different loop:

1. Consumers react to a concept and copy for the first time.
2. Consumers influence each other in a simulated social environment.
3. Resonance, objections, and misreads spread unevenly.
4. The system turns those interactions into a structured report with representative VOC evidence.

That makes it useful for **pre-launch rehearsal**, not just static scoring.

## What You Can Test

- **Concept testing**
  Evaluate whether the product idea itself feels compelling, credible, or confusing.

- **Copy testing**
  See which lines trigger interest, skepticism, sharing, or distortion.

- **Pre-launch propagation rehearsal**
  Simulate how reactions evolve after consumers start repeating and reframing the message.

- **Resonance / risk / misread detection**
  Identify which message elements become hooks, which become debates, and which get misunderstood.

## Core Capabilities

- **Structured BusinessBrief**
  Turn concept assets, copy assets, target audience, scene, and research goal into a single test contract.

- **Consumer Persona Pack**
  Model propagation-relevant consumer traits such as search propensity, cognition level, herd tendency, and influence weight.

- **Visibility-Aware Consumer Graph**
  Separate what consumers see at first glance from deeper risk points that only emerge later in propagation.

- **Round 0: First Impression**
  Consumers react only to the direct concept and copy inputs.

- **Round 1-N: Propagation**
  Consumers begin to amplify, challenge, reinterpret, and misread each other's views.

- **VOC-Backed Consumer Report**
  Output a propagation report with acceptance shifts, resonance points, risks, misreads, and representative quotes.

- **Deep Follow-Up Interaction**
  Continue asking the report agent or representative simulated consumers why reactions changed.

- **Source Quality Scoring**
  Every research source is scored by trust tier, freshness, and coverage so you know whether a finding rests on user-uploaded materials or public-web supplements.

- **Evidence Validation**
  Findings are checked against their cited snippets before they reach the report. Weak or unsupported evidence is flagged as `weak_support` or `insufficient_support`.

- **Confidence Scoring**
  Report conclusions carry structured confidence labels and reason codes derived from source quality, evidence sufficiency, and signal consistency.

- **Benchmark Replay**
  Save a benchmark case from a research pack or project snapshot, rerun it later, and compare current outputs against stable derived-signal baselines.

## Product Workflow

1. **Create a consumer test**
   Submit a structured brief with concept, copy, audience, scene, and goal.

2. **Build the consumer graph**
   Convert claims, drivers, anxieties, and audience segments into a propagation-ready graph.

3. **Prepare the simulation**
   Generate the consumer persona pack and runtime configuration.

4. **Run the propagation simulation**
   Observe Round 0 first impression and Round 1-N propagation separately.

5. **Generate the consumer report**
   Review acceptance shifts, resonance, controversy, misreads, and representative VOC.

6. **Ask follow-up questions**
   Interrogate the report agent or representative consumers for deeper insight.

## Report Outputs

Each run is designed to help answer:

- Initial acceptance vs. post-propagation acceptance
- Attitude shift rate
- Top resonance points
- Top risk points
- Top misreads
- Which consumers amplify or block the message
- Which concept and copy changes should be made next

## Example Brief Shape

```json
{
  "task_type": "concept_test",
  "product_concept_assets": [
    "High-protein yogurt pouch for busy mornings"
  ],
  "copy_material": [
    "14g protein",
    "Low sugar",
    "Made for the commute"
  ],
  "claims": [
    "14g protein",
    "Low sugar"
  ],
  "target_audience": [
    "working moms"
  ],
  "usage_scene": [
    "weekday breakfast"
  ],
  "research_goal": "Find resonance, objection, and misread risks before launch"
}
```

## Screenshots

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/运行截图1.png" alt="Workbench screenshot 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图2.png" alt="Workbench screenshot 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图3.png" alt="Workbench screenshot 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图4.png" alt="Workbench screenshot 4" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图5.png" alt="Workbench screenshot 5" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图6.png" alt="Workbench screenshot 6" width="100%"/></td>
</tr>
</table>
</div>

## Quick Start

### Prerequisites

| Tool | Version | Check |
| --- | --- | --- |
| Node.js | 18+ | `node -v` |
| Python | 3.11+ recommended | `python --version` |
| uv | latest | `uv --version` |

### 1. Configure Environment Variables

```bash
cp .env.example .env
```

Required keys:

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=your_zep_api_key
```

`.env.example` includes `SECRET_KEY=dev-only-change-me` so local development can start after copying the file. Production deployments must replace it with a unique secret before startup.

### 2. Install Dependencies

```bash
npm run setup:all
```

Or step by step:

```bash
npm run setup
npm run setup:backend
```

### 3. Start The App

```bash
npm run dev
```

Service URLs:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

Run separately if needed:

```bash
npm run backend
npm run frontend
```

### 4. Build The Frontend

```bash
cd frontend
npm run build
```

## Docker

```bash
cp .env.example .env
docker compose up -d
```

Default ports:

- `3000` for frontend
- `5001` for backend

## Technical Foundation

MiroConsumer is built on a robust multi-agent simulation execution backbone:

- graph construction
- simulation preparation
- multi-agent runtime orchestration
- report generation
- post-report interaction

The current product direction specializes that backbone for **consumer concept and copy propagation testing**.

## Acknowledgments

The simulation layer builds on **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**.

We also thank the original simulation architecture for providing the graph, simulation, report, and interaction backbone that powers this product direction.

## Production Deployment Key Generation

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the generated key in your `.env` file:

```
SECRET_KEY=<your-generated-key>
```

## License

本项目采用 AGPL-3.0 许可证。

**AGPL 合规说明：**
- 如果您通过网络提供本软件的服务（SaaS），必须向使用者提供完整源代码
- 修改后的代码必须同样以 AGPL-3.0 发布
- 完整许可证条款见 [LICENSE](LICENSE) 文件

## Research Boundary Statement

本平台为 AI 消费者仿真研究工具。所有仿真结果由大语言模型推演生成，**不代表真实消费者行为**。

- 小样本模式 (< 30 agents): 仅用于灵感探索，禁止统计推断
- 研究模式 (30-100 agents): 可输出趋势和稳定性
- 企业验证模式 (100+ agents): 需配合真实基准校准
