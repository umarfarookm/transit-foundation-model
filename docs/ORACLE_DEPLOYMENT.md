# Oracle Cloud Deployment Guide — UmarTransit-1B

Deploy the UmarTransit-1B GGUF backend on Oracle Cloud Always Free ARM instance.

> **Last updated:** July 2026
> **Cost:** Free (Oracle Cloud Always Free tier)
> **Architecture:** GGUF Q4_K_M + llama-cpp-python + FastAPI on ARM Ampere

## Overview

```
Vercel Frontend (app/web)
    |
    |-- Demo mode --> pre-computed answers (no backend needed)
    |
    |-- Live mode (Oracle) --> Oracle VM:8000 (main_gguf.py — GGUF, fast)
    |
    |-- Live mode (Local)  --> localhost:8000 (main.py — Transformers, fallback)
```

**Existing local setup is untouched.** This deployment adds new files alongside existing ones.

### What Stays (Untouched)

| Component | File | Purpose |
|-----------|------|---------|
| Local inference | `inference/run_local.py` | Transformers/safetensors CPU inference |
| Local backend | `app/api/main.py` | FastAPI backend using Transformers |
| Frontend | `app/web/` | Next.js on Vercel (demo + live modes) |

### What Gets Added (New Files)

| New File | Purpose |
|----------|---------|
| `inference/run_local_gguf.py` | GGUF inference using llama-cpp-python |
| `app/api/main_gguf.py` | FastAPI backend using GGUF inference |

---

## Free Tier Specs (As of June 2026)

| Resource | Limit |
|----------|-------|
| ARM Ampere A1 | 2 OCPUs + 12 GB RAM |
| Boot volume storage | 200 GB |
| Network | 10 Gbps |
| Cost | Free forever (no expiry) |

> **Note:** Oracle halved ARM limits in June 2026 (was 4 OCPUs + 24 GB). 2 OCPUs + 12 GB is still more than enough for the Q4_K_M model (1 GB).

---

## Phase 1: Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Click **Start for Free**
3. Fill in details — **credit card required** (verification hold only, no charge)
4. **Choose region:** Pick **Frankfurt (eu-frankfurt-1)** or **Singapore (ap-singapore-1)**
   - US regions often have capacity issues for free ARM instances
5. Wait for account approval (minutes to hours)

> **Tip:** Oracle does NOT accept PIN-based debit cards, virtual single-use cards, or prepaid cards.

---

## Phase 2: Create ARM VM Instance

1. Log in to Oracle Cloud Console
2. Navigate: **Compute → Instances → Create Instance**
3. Configure:
   - **Name:** `umartransit-api`
   - **Placement:** Leave default availability domain
   - **Image:** Click **Change Image** → Select **Ubuntu 24.04 LTS** (Canonical, aarch64)
   - **Shape:** Click **Change Shape** → Select **Ampere** → **VM.Standard.A1.Flex**
     - OCPUs: **2**
     - Memory: **12 GB**
   - **Networking:**
     - Create new VCN or use existing
     - Create new public subnet
     - Check **"Assign a public IPv4 address"**
   - **SSH Key:**
     - Generate locally: `ssh-keygen -t rsa -b 4096 -f ~/.ssh/oracle_umartransit`
     - Upload the **public key** file (`oracle_umartransit.pub`)
4. Click **Create**

### If You See "Out of Host Capacity"

This is common on the free tier. Options:
- Try a **different availability domain** in the same region
- Try a **different region** (Frankfurt and Singapore tend to have more capacity)
- Keep retrying — capacity refreshes periodically
- Upgrade to **Pay-As-You-Go** (still free, but gives access to larger pool)

---

## Phase 3: Open Port 8000

1. Navigate: **Networking → Virtual Cloud Networks → [Your VCN]**
2. Click **Security Lists** in left sidebar
3. Click the security list (usually "Default Security List for [VCN name]")
4. Click **Add Ingress Rule**
5. Configure:
   - **Stateless:** Leave unchecked
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** TCP
   - **Destination Port Range:** `8000`
6. Click **Add Ingress Rules**

### Also Open Port in Ubuntu Firewall (iptables)

Oracle Linux/Ubuntu images have iptables rules that block ports by default. After SSH-ing in (Phase 4), run:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

---

## Phase 4: SSH and Server Setup

### Connect to the VM

```bash
ssh -i ~/.ssh/oracle_umartransit ubuntu@<YOUR_PUBLIC_IP>
```

### Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential git
```

### Clone the Project

```bash
cd ~
git clone https://github.com/umarfarookm/transit-foundation-model.git
cd transit-foundation-model
```

### Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python Dependencies

```bash
pip install fastapi uvicorn llama-cpp-python huggingface-hub
```

> **Note:** `llama-cpp-python` compiles from source on ARM. This may take a few minutes but works out of the box on Ubuntu ARM.

---

## Phase 5: Download the GGUF Model

```bash
# Install huggingface CLI
pip install "huggingface-hub[cli]"

# Download Q4_K_M quantized model (~986 MB)
mkdir -p ~/models
huggingface-cli download umarfarookm/UmarTransit-1B \
  UmarTransit-1B.Q4_K_M.gguf \
  --local-dir ~/models
```

Verify download:
```bash
ls -lh ~/models/UmarTransit-1B.Q4_K_M.gguf
# Should show ~986 MB
```

---

## Phase 6: Start the API Server

### Test Manually First

```bash
cd ~/transit-foundation-model
source .venv/bin/activate
uvicorn app.api.main_gguf:app --host 0.0.0.0 --port 8000
```

### Verify from Your Local Machine

```bash
# Health check
curl http://<YOUR_PUBLIC_IP>:8000/health

# Test a question
curl -X POST http://<YOUR_PUBLIC_IP>:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What does route_type 3 mean in GTFS?"}'
```

---

## Phase 7: Run as a System Service (Survives Reboots)

### Create systemd Service

```bash
sudo nano /etc/systemd/system/umartransit.service
```

Paste this content:

```ini
[Unit]
Description=UmarTransit-1B GGUF API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/transit-foundation-model
Environment="PATH=/home/ubuntu/transit-foundation-model/.venv/bin:/usr/bin"
ExecStart=/home/ubuntu/transit-foundation-model/.venv/bin/uvicorn app.api.main_gguf:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable umartransit
sudo systemctl start umartransit
```

### Useful Commands

```bash
# Check status
sudo systemctl status umartransit

# View logs
sudo journalctl -u umartransit -f

# Restart after code changes
sudo systemctl restart umartransit
```

---

## Phase 8: Connect Vercel Frontend

Update the API URL in your Vercel frontend environment:

```
NEXT_PUBLIC_API_URL=http://<YOUR_PUBLIC_IP>:8000
```

The frontend's live mode will now point to the Oracle Cloud backend.

**Fallback:** To switch back to local, change the URL to `http://localhost:8000` (uses the original `main.py` with Transformers).

---

## Phase 9: Prevent Idle Reclamation

Oracle reclaims Always Free instances with <20% CPU utilization (95th percentile) over 7 days.

### Add a Cron Job

```bash
crontab -e
```

Add this line:

```
0 */6 * * * curl -s http://localhost:8000/health > /dev/null 2>&1
```

This pings the API every 6 hours to keep the instance active.

---

## Troubleshooting

### "Out of Host Capacity" During Instance Creation
- Try a different availability domain or region
- Upgrade to Pay-As-You-Go (free tier still applies, larger capacity pool)
- Use automated retry scripts: https://github.com/hitrov/oci-arm-host-capacity

### Can't Connect to Port 8000
1. Check Oracle Security List has the ingress rule (Phase 3)
2. Check Ubuntu iptables: `sudo iptables -L INPUT -n --line-numbers`
3. Check the service is running: `sudo systemctl status umartransit`
4. Check the server is listening: `ss -tlnp | grep 8000`

### Model Loading Fails (Out of Memory)
- Use Q4_K_M (986 MB) not Q8_0 (1.65 GB)
- Check available RAM: `free -h`
- Kill other processes if needed: `top`

### Slow First Response
- First request after startup loads the model into RAM (~5-10 sec)
- Subsequent requests are fast
- This is normal for GGUF models

### Account Suspended
- Oracle suspends accounts idle for 30+ days
- Log in to the console regularly
- The cron job (Phase 9) keeps the VM active but not the console session

---

## Architecture Summary

```
                    Internet
                       |
            +----------+----------+
            |                     |
     Vercel (Frontend)    Oracle Cloud (Backend)
     app/web/             VM.Standard.A1.Flex
     - Demo mode          2 OCPU / 12 GB RAM
     - Live mode -------> Ubuntu 24.04 ARM
                          FastAPI + uvicorn
                          llama-cpp-python
                          UmarTransit-1B.Q4_K_M.gguf (986 MB)
                          Port 8000
                          systemd managed
```

**Fallback:** If Oracle is down, switch frontend to `localhost:8000` to use the original Transformers backend locally.

---

## Cost Summary

| Component | Cost |
|-----------|------|
| Oracle Cloud VM | Free (Always Free tier) |
| Vercel Frontend | Free (Hobby plan) |
| HuggingFace Model Hosting | Free |
| Domain (optional) | ~$10/year |
| **Total** | **$0/month** |
