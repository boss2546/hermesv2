# API & Reference Cheatsheet

This file demonstrates how to store deep technical documentation, API specs, or cheatsheets for your skill.

## Key Concepts

- **Progressive Disclosure:** Keep `SKILL.md` focused on the main workflow (~100-200 lines). Move extensive command tables, raw API schemas, and reference material here into `references/`.
- **Referencing:** The agent or user can view this file whenever they need deep details about this specific skill: `skills/_template_skill/references/api-cheatsheet.md`.

## Example API Endpoints / Commands

| Endpoint / Command | Method / Parameters | Description |
|---|---|---|
| `GET /v1/health` | None | Check service liveness |
| `POST /v1/process` | `{"input": "..."}` | Submit asynchronous processing job |
| `GET /v1/status/:id` | `id: string` | Query job status and retrieve result |
