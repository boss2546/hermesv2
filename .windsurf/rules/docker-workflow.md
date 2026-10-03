<!-- START: DOCKER-WORKFLOW -->
## 🐳 Docker Workflow Standards (Universal AI Guide)
When designing, containerizing, or managing Docker environments in development:
1. **3-Tier Architecture Pattern**:
   - **Frontend**: Port `3000` (React / Vite / Vue / Next.js) — with live reload volume mount.
   - **Backend API**: Port `3001` (Node.js / Python / Go) — with live reload and CORS enabled.
   - **Database**: Port `3307:3306` (MySQL 8.4+ / PostgreSQL) with `utf8mb4` Thai charset and named volume.
   - **Adminer**: Web GUI for DB at Port `8085` (no local DBeaver installation needed).
2. **Key Reliability & Workflow Standards**:
   - **Healthcheck & Cold-Start**: Database MUST have healthcheck, backend MUST use `depends_on: db: condition: service_healthy` and a 10-15 retry loop (20-30s) waiting for DB to ready.
   - **Live Reload**: Bind mounts (`./backend:/app`) for instant edits without rebuilds.
   - **Daily Operations**: Proactively assist with `docker compose up -d`, `down`, `ps`, `logs -f`, `exec`, and safe `prune`.
   - **Worker Safety**: Background loops must use Acquire-Use-Release per cycle, avoiding stale connections.
   - **Vibe Coding Communication**: Explain step-by-step in friendly Thai, explain terminal flags, and remind users to save files.
3. **Full Reference**: Read detailed templates in `.agents/skills/docker-workflow/SKILL.md`.
<!-- END: DOCKER-WORKFLOW -->
