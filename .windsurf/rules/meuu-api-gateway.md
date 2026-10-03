<!-- START: MEUU-API-GATEWAY -->
## 🌐 Meuu AI API Gateway Standards (api.meuu.club)
When connecting to or integrating with the central AI API Gateway (9Router):
1. **Central Gateway URL & Auth**:
   - Base URL: `https://api.meuu.club/v1`
   - Master API Key: `sk-07ccde1e709eb2ca-e05r6c-a11b5d7c`
   - Quota: 12,000 req/week across 6 auto-failover load balanced accounts.
2. **Recommended AI Models**:
   - `ag/claude-sonnet-4-6`: Coding, complex reasoning, autonomous agents, and tool calling.
   - `ag/gemini-2.5-flash`: High-speed chat, multimodal vision, OCR, fast STT (2.7s), and direct audio processing.
   - `edge-tts/th-TH-PremwadeeNeural` / `edge-tts/th-TH-NiwatNeural`: High quality natural Thai TTS.
3. **Dual Protocol Endpoints**:
   - OpenAI v1: `POST /v1/chat/completions` (Chat, Vision, Audio Input).
   - Anthropic Native: `POST /v1/messages` (Header: `x-api-key`, `anthropic-version: 2023-06-01`).
   - Text-to-Speech (TTS): `POST /v1/audio/speech` (`{"model": "edge-tts/th-TH-PremwadeeNeural", "input": text, "voice": "..."}`).
   - Models List: `GET /v1/models`.
4. **Full Reference**: Read detailed request/response schemas and code examples in `.agents/skills/meuu-api-gateway/SKILL.md`.
<!-- END: MEUU-API-GATEWAY -->
