<div align="center">

<img src="./static/image/MiroConsumer_logo_compressed.jpeg" alt="MiroConsumer Logo" width="68%"/>

# MiroConsumer

**面向概念测试与文案测试的 AI 消费者传播测试平台**

[![Consumer Simulation](https://img.shields.io/badge/Product-Consumer%20Simulation-111827?style=flat-square)](#什么是-miroconsumer)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue%203-42b883?style=flat-square&logo=vuedotjs&logoColor=white)](#快速开始)
[![Flask](https://img.shields.io/badge/Backend-Flask-0f172a?style=flat-square&logo=flask&logoColor=white)](#快速开始)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)](#快速开始)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?style=flat-square&logo=nodedotjs&logoColor=white)](#快速开始)

**MiroConsumer 帮助团队在产品上线前，用一个可传播、可分化、可追问的消费者社会仿真环境测试概念与文案。**

它不止输出静态 persona 打分，而是把 **初见反应、群体传播、误读放大、VOC 证据和报告追问** 串成一条完整工作流。

[English](./README.md) | [中文](./README-ZH.md)

</div>

## 什么是 MiroConsumer

MiroConsumer 是一个 AI 驱动的消费者传播测试平台。

它面向的问题不是“这句文案单独看起来好不好”，而是：

- 这个概念第一次被看到时，会让人感兴趣还是犹豫？
- 哪些文案点会被自然转述、扩散、放大？
- 哪些 claims 会被质疑、争议或误读？
- 哪类消费者会成为扩散者、阻断者、观望者？
- 上市前最应该改的是概念、表达，还是 claim 本身？

## 为什么它和传统消费者测试不一样

很多 AI 消费者测试工具停留在静态 persona 评审阶段。

MiroConsumer 的核心闭环是：

1. 先让消费者对概念和文案形成第一反应。
2. 再让消费者在仿真的社会环境里彼此影响。
3. 观察哪些观点被放大、哪些内容被误读、哪些态度发生反转。
4. 最终输出一份带 VOC 原声证据的传播测试报告。

所以它不是“静态打分器”，而是一个更适合上市前推演的 **传播测试沙盘**。

## 你可以用它测试什么

- **概念测试**
  看产品概念本身是否吸引人、可信，还是容易让人困惑。

- **文案测试**
  看哪些表达能种草，哪些表达会引发质疑或传播偏差。

- **上市前传播预演**
  在真正投放前，先观察消费者之间的口碑扩散和分化趋势。

- **共鸣点 / 风险点 / 误读点识别**
  把容易被转发的点、容易被争议的点、容易被误解的点提前暴露出来。

## 核心能力

- **Structured BusinessBrief**
  把概念素材、文案素材、目标人群、场景和研究目标整理成统一测试契约。

- **Consumer Persona Pack**
  建模传播相关的消费者特征，例如搜索倾向、认知层级、从众倾向、影响力。

- **Visibility-Aware Consumer Graph**
  区分“消费者一眼能看到的信息”和“传播中后期才会被挖出来的深层风险点”。

- **Round 0：初见反应**
  消费者只基于概念和文案做第一反应。

- **Round 1-N：传播演化**
  消费者开始互相转述、质疑、跟风、放大、误读。

- **VOC 驱动的传播测试报告**
  输出接受度变化、共鸣点、风险点、误读点和代表性消费者原声。

- **报告后深度追问**
  可以继续追问报告代理或代表性消费者，理解态度变化背后的原因。

- **源质量评分**
  每个研究来源都会按信任层级、新鲜度和覆盖范围打分，让你清楚发现是基于用户上传材料还是公开网络补充。

- **证据验证**
  发现进入报告前会先与其引用的片段核对。弱支持或缺乏支持的证据会被标记为 `weak_support` 或 `insufficient_support`。

- **置信度评分**
  报告结论携带结构化置信度标签和原因码，综合源质量、证据充分性和信号一致性计算得出。

- **基准回放**
  从研究包或项目快照保存基准案例，后续重新运行，并将当前输出与稳定的衍生信号基线进行对比。

## 产品工作流

1. **创建消费者测试**
   提交概念、文案、目标人群、场景和研究目标。

2. **构建消费者图谱**
   把 claims、驱动点、顾虑点和人群结构组织成传播测试图谱。

3. **准备仿真环境**
   生成消费者画像包与运行配置。

4. **运行传播仿真**
   分开观察 Round 0 初见反应和 Round 1-N 传播演化。

5. **生成传播测试报告**
   查看接受度变化、共鸣点、争议点、误读点和 VOC。

6. **继续追问**
   继续与报告代理或代表性消费者对话，获取更深层解释。

## 报告会回答什么

每次运行，系统都会尽量回答这些问题：

- 初始接受度和传播后接受度分别如何
- 态度转向率是多少
- 哪些点最容易形成共鸣
- 哪些点最容易引发争议
- 哪些表达最容易被误读
- 哪类消费者在放大信息，哪类在阻断信息
- 下一步应该改概念、改文案还是改 claim

## 示例 Brief

```json
{
  "task_type": "concept_test",
  "product_concept_assets": [
    "为忙碌早晨设计的高蛋白酸奶袋装早餐"
  ],
  "copy_material": [
    "14g 蛋白",
    "低糖",
    "通勤路上也能吃"
  ],
  "claims": [
    "14g 蛋白",
    "低糖"
  ],
  "target_audience": [
    "职场妈妈"
  ],
  "usage_scene": [
    "工作日早餐"
  ],
  "research_goal": "在上市前识别共鸣点、质疑点和误读风险"
}
```

## 系统截图

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/运行截图1.png" alt="界面截图 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图2.png" alt="界面截图 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图3.png" alt="界面截图 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图4.png" alt="界面截图 4" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图5.png" alt="界面截图 5" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图6.png" alt="界面截图 6" width="100%"/></td>
</tr>
</table>
</div>

## 快速开始

### 前置依赖

| 工具 | 版本要求 | 检查命令 |
| --- | --- | --- |
| Node.js | 18+ | `node -v` |
| Python | 建议 3.11+ | `python --version` |
| uv | 最新版 | `uv --version` |

### 1. 配置环境变量

```bash
cp .env.example .env
```

至少需要配置：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=your_zep_api_key
```

### 2. 安装依赖

```bash
npm run setup:all
```

或者分步安装：

```bash
npm run setup
npm run setup:backend
```

### 3. 启动项目

```bash
npm run dev
```

启动后地址：

- 前端：`http://localhost:3000`
- 后端 API：`http://localhost:5001`

如需分别启动：

```bash
npm run backend
npm run frontend
```

### 4. 构建前端

```bash
cd frontend
npm run build
```

## Docker

```bash
cp .env.example .env
docker compose up -d
```

默认端口：

- `3000` 前端
- `5001` 后端

## 技术基础

MiroConsumer 复用了原有的多 Agent 仿真主干能力：

- 图谱构建
- 仿真准备
- 多 Agent 运行时调度
- 报告生成
- 报告后交互

当前产品方向是在这条主干上，专门为 **概念测试与文案传播测试** 做领域化增强。

## 致谢

仿真层建立在 **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)** 之上。

同时也感谢原始的仿真架构，它提供了图谱、仿真、报告和交互主骨架，使 MiroConsumer 可以在同一底座上快速演进成一个消费者传播测试产品。
