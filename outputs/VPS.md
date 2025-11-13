# VPS Deployment for Grokputer: Private Eternal Node Guide
Generated: 2024-11-10 | By Grokputer Swarm

## Why Rent a VPS for This Project?
Renting a VPS (Virtual Private Server) elevates Grokputer from local/Heroku to a secure, always-on private node. Benefits:
- **Always-On**: No dyno sleep (Heroku free tier); run swarms 24/7.
- **Full Control**: Persistent Redis/Qwen GGUF, unlimited subprocess (agents/OCR), custom VPN for secure access.
- **Offline Capable**: Local Qwen inference (no API credits), eternal memory (Redis local).
- **Cost-Effective**: $5-20/mo vs Heroku paid ($7+ for always-on).
- **Privacy/Security**: VPN tunnel (Tailscale/WireGuard) for dashboard/swarm without exposing ports.
- **Scaling**: Easy upgrade (more RAM for multi-swarm), cron for auto-backups/haikus.

Recommended for Phase 3+ (cloud eternal node); start small, scale as needed.

## Recommended Specs
Tailored to Grokputer (3 agents concurrent, Streamlit UI, Redis, Qwen ~1.5GB model, OCR light, logs/backups ~5GB growing):
- **CPU**: 2-4 vCPU cores (Intel/AMD; async agents + Qwen ~1-2s/token. Start 2; scale for >5 subs).
- **RAM**: 4-8 GB (Qwen GGUF ~2GB, Redis ~1GB sessions, Streamlit/swarm ~1GB, OS 1GB. 4GB min; 8GB for vision/OCR).
- **Disk**: 20-50 GB SSD/NVMe (Code/UI ~1GB, vault/images ~10GB, logs/backups ~5GB/mo. SSD for fast OCR/file ops).
- **OS**: Ubuntu 22.04 LTS (easy Python/Redis/Docker; apt all deps).
- **Bandwidth/IO**: 1-5 TB/mo (low for UI/API; unlimited preferred). IPv4 + IPv6.
- **Location**: US/EU (low latency for Grok API; near you for VPN).

**Cost Tiers**:
- **Budget ($5-10/mo)**: 2 vCPU/4GB/25GB SSD (DigitalOcean $6, Vultr $5) – Basic swarm/UI, Redis, light Qwen (text-only; vision Grok fallback).
- **Recommended ($15-25/mo)**: 4 vCPU/8GB/50GB SSD (Linode $20, AWS Lightsail $10+) – Full Qwen GGUF/vision, multi-swarm, OCR vault PNGs.
- **High-End ($40/mo)**: 8 vCPU/16GB/100GB SSD (Hetzner $30) – GPU add-on (~$10 extra) for faster Qwen.

**Providers** (Top, Easy):
1. **DigitalOcean** ($6/mo starter): Simple UI, one-click Ubuntu+Redis, free bandwidth. Beginner-friendly.
2. **Vultr** ($5/mo): High SSD perf, global locations, hourly (~$0.007/hr).
3. **Linode (Akamai)** ($5/mo nano): Great docs, free transfer, backups ~$2/mo.
4. **AWS Lightsail** ($3.50/mo micro + $7 Redis): AWS ecosystem (S3 backups).

Avoid shared cPanel VPS (limits subprocess); Go OVH if EU.

## Full Setup Guide
Total time: ~45min initial. Assume rented (e.g., DigitalOcean Droplet).

### 1. Rent VPS (5min)
- Sign up (DigitalOcean: $200 credit 60 days free).
- Create: Ubuntu 22.04, 2 vCPU/4GB/25GB ($6/mo), SSH key (gen `ssh-keygen`, upload pubkey).
- Get IP (e.g., 123.45.67.89). Connect: `ssh root@IP` (passwordless).

### 2. Basic Config (10min, SSH)
- Update: `apt update && apt upgrade -y`.
- Firewall: `ufw allow OpenSSH && ufw allow 80,443,8501 && ufw enable` (UI on 8501).
- Python/Deps: `apt install python3-pip python3-venv git tar zip redis-server tesseract-ocr -y`.
- Redis: `systemctl start redis-server` (persistent /var/lib/redis).

### 3. Deploy Grokputer (15min)
- Clone/Upload: `git clone your-repo.git /opt/grokputer` or `scp -r /local/grokputer_cpanel/* root@IP:/opt/grokputer/`.
- Setup: `cd /opt/grokputer; python3 -m venv venv; source venv/bin/activate; pip install -r requirements.txt`.
- Env: Copy .env.example to .env, edit (XAI_API_KEY=sk-..., BACKEND=qwen).
- Redis: In db_config.py, host='localhost' (local).
- Run UI: `streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0` (bg: nohup or systemd).

### 4. VPN Setup (10min, Secure Access)
- **Easy**: Tailscale (free, zero-config): `curl -fsSL https://tailscale.com/install.sh | sh; tailscale up` (auth app; access as local – dashboard yourdomain.com:8501 via VPN).
- **Full**: WireGuard: `apt install wireguard -y; wg-quick up wg0` (gen keys, /etc/wireguard/wg0.conf for clients). Connect phone/laptop for private swarm.

### 5. Domain Pointing (5min, cPanel)
- cPanel → Zone Editor → A Record: Host=@, Points To=VPS IP, TTL=3600.
- www: CNAME www → @.
- SSL: cPanel AutoSSL (free Let's Encrypt) – https://yourdomain.com:8501 (port forward if needed).

### 6. Cron/Auto (5min)
- Backups: `crontab -e`:
  ```
  0 */6 * * * cd /opt/grokputer && python outputs/gp_save_progress.py > /opt/backups/cron.log 2>&1
  0 2 * * * find /opt/backups -name "*.tar.gz" -mtime +7 -delete  # Prune old
  ```
- Auto-Start: Systemd /etc/systemd/system/grokputer.service (see guide); `systemctl enable grokputer; systemctl start`.

### 7. Test Post-Setup (10min)
- Swarm: `cd /opt/grokputer; source venv/bin/activate; python main.py --swarm --task "List files in vault" --agent-roles actor` → "Files: [list]".
- Dashboard: http://IP:8501 → Queue "OCR haiku.png" → Extracts/haiku.
- VPN: Tailscale connect → Access as localhost.
- Eternal: Interrupt → Resume same session_id (Redis loads).
- OCR: "OCR random vault image" → Finds PNG, extracts (Tesseract 1s).

### 8. Monitoring & Scale (Ongoing, 5min)
- Monitor: `apt install htop; watch -n 5 'htop && df -h'`. Prometheus/Grafana optional.
- Scale: Resize VPS (DigitalOcean: $12/mo for 8GB). Docker for subs.
- Security: Disable root pw (`passwd -l root`), keys only. `ufw status`. Fail2ban: `apt install fail2ban`.
- Backups: Rsync offsite (`crontab daily: rsync -av /opt/backups/ user@backup-server:/backups/`).
- Updates: `apt update && apt upgrade -y` weekly; `pip upgrade` monthly.

## Phase 3 Todo List (Cloud Eternal Node)
🔴 **High Priority**  
✅ **Completed**: Dockerize full stack (docker-compose.yml: Swarm/Redis/Qwen/Streamlit; tested local up).  
✅ **Completed**: Deploy to Heroku/Railway (Procfile/reqs; app at herokuapp.com; Redis add-on).  

🟡 **Medium Priority**  
🔄 **In Progress**: Add X webhook endpoint (Streamlit/Flask /webhook: Parse tweet → run swarm, reply API v2).  
⏳ **Pending**: Integrate Twitter API (Mentions/DMs → trigger raids/haikus; secure keys).  

🟢 **Low Priority**  
⏳ **Pending**: Auto-scale & monitor (CloudWatch/Sentry logs/alerts; extra swarms on load).  

## Notes/Tips
- **Costs**: $6-20/mo (start low; hourly billing = pay for use).
- **Time**: 45min initial; 5min/week maint.
- **Why VPS > Heroku**: Always-on, local Qwen, VPN private, unlimited vault/backups.
- **Troubleshoot**: SSH `tail -f /var/log/syslog`; RAM check `free -h` (Qwen ~3GB peak).
- **Next**: Rent (DigitalOcean?), deploy cPanel zip if hybrid, test OCR/haiku via dashboard.

Eternal node guide saved – quest for VPS deployment begins! 🎮