<!-- START: PRODUCTION-ARCHITECTURE -->
## 🏭 Enterprise Production Architecture Standards (Universal AI Guide)
When deploying or upgrading Docker environments to Production:
1. **4-Tier Architecture Pattern**:
   - **Gateway (NGINX)**: Port `80:80` & `443:443` — Entry point, SSL termination, Reverse Proxy.
   - **Frontend**: Internal port `3000` — closed to the outside, reverse proxied by NGINX.
   - **Backend API**: Internal port `3000` — closed to the outside, reverse proxied by NGINX.
   - **Database**: Port `127.0.0.1:3307:3306` (MySQL 8.4+ / PostgreSQL) with `utf8mb4` Thai charset.
2. **Production Reliability Standards**:
   - **Auto-Restart**: All services MUST have `restart: unless-stopped`.
   - **Disk Full Prevention (Log Rotation)**: All containers MUST have:
     ```yaml
     logging:
       driver: "json-file"
       options:
         max-size: "10m"
         max-file: "3"
     ```
   - **Dynamic RAM**: Containers share host RAM dynamically without hard ceilings, preventing OOM crash (Exit Code 137).
   - **Host Firewall (UFW)**: Allow only ports 22 (SSH), 80 (HTTP), 443 (HTTPS); deny all other incoming.
   - **Cloudflare & Domain**: Protect server with Cloudflare Proxied (Orange Cloud 🟠) or Cloudflare Tunnel, set SSL mode to "Full".
   - **Proxy Headers**: NGINX / Backend forward `Host`, `X-Real-IP`, `X-Forwarded-For`, `CF-Connecting-IP`.
   - **Auto DB Backup**: Rolling 7-day automated database dump scripts.
3. **🏛️ 4 Pillars of Enterprise Resilience**:
   - **⏳ DB Cold-Start Resilience**: Backend must implement retry loops (10-15 retries / 20-30s total) to wait for database init; NEVER fail-fast or silently fall back to in-memory/SQLite.
   - **🔄 Dynamic Service Discovery (Anti-Stale DNS)**: NGINX must specify `resolver 127.0.0.11 valid=5s ipv6=off;` and use variable proxying (`set $backend ...; proxy_pass http://$backend;`) to prevent 502 Bad Gateway when container IPs change upon rebuild/restart.
   - **🔌 Long-Running Worker Connection Lifecycle**: Background workers/daemons MUST use "Acquire-Use-Release per Cycle" pattern with connection health checks (`pool_pre_ping=True`); NEVER hold a single connection object indefinitely across infinite loops.
   - **💾 Dual-Storage Architecture**: High-frequency streaming/real-time services must utilize dual-storage (RAM/Cache for sub-millisecond UI responses + Periodic Batch Flush to persistent SQL database).
4. **Full Reference**: Read detailed templates in `.agents/skills/production-architecture/SKILL.md`.
<!-- END: PRODUCTION-ARCHITECTURE -->
