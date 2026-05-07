# LLM Integration Guide

## Supported Models

| Model | Provider | Configuration |
|-------|----------|---------------|
| GPT-4o-mini | OpenAI | LLM_BASE_URL=https://api.openai.com/v1 |
| MiMo-v2.5 | Xiaomi | LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1 |
| DeepSeek | DeepSeek | LLM_BASE_URL=https://api.deepseek.com/v1 |

## Configuration

Set in `.env`:
```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
```

## Budget Policy

- **Per-tenant budget**: independent token cap per tenant
- **Per-user budget**: independent token cap per user
- **Per-project budget**: independent token cap per project
- **Circuit breaker**: trips after 5 consecutive failures, recovers after 60s
- **Retry policy**: exponential backoff, max 3 retries

Configuration:
```env
LLM_BUDGET_LIMIT=500
LLM_DEEP_REASONING_RATIO=0.1
```

## Governance

- Per-call logging: model name, prompt_hash, token usage, latency
- Output validation: empty output, too short, math inference, repetition
- Degradation: auto-switch to template engine on LLM failure
- Chain-of-thought control: disable in production via ENABLE_REASONING_TRACE=false
