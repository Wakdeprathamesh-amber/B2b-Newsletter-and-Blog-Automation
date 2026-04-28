# Deployment Guide - Free Options

## 🏆 Recommended: Render.com (Best Free Option)

### Features:
- ✅ 750 hours/month free (24/7 for 1 service)
- ✅ Auto-deploy from GitHub
- ✅ No credit card required
- ⚠️ Spins down after 15 min inactivity (30s cold start)

### Step-by-Step Deployment:

#### 1. Sign Up
- Go to [render.com](https://render.com)
- Sign up with your GitHub account
- Authorize Render to access your repositories

#### 2. Create Web Service
- Click **"New +"** → **"Web Service"**
- Connect repository: `Wakdeprathamesh-amber/B2b-Newsletter-and-Blog-Automation`
- Click **"Connect"**

#### 3. Configure Service
```
Name: amber-newsletter-automation
Region: Choose closest to you
Branch: main
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn src.main:app --host 0.0.0.0 --port $PORT
Instance Type: Free
```

#### 4. Add Environment Variables
Click **"Environment"** tab and add:

```bash
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_MASTER_SHEET_ID=your-sheet-id
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CHANNEL_ID=C0XXXXXXXXX
DEV_MODE=false
```

#### 5. Upload Google Service Account Credentials

**Option A: Secret Files (Recommended)**
1. Go to **"Environment"** → **"Secret Files"**
2. Click **"Add Secret File"**
3. Filename: `/etc/secrets/google-creds.json`
4. Contents: Paste your `credentials/b2b-research-agent-492909-a74f688b6c7a.json` file content
5. Add environment variable: `GOOGLE_SERVICE_ACCOUNT_JSON=/etc/secrets/google-creds.json`

**Option B: Base64 Encoded (Alternative)**
```bash
# On your local machine
cat credentials/b2b-research-agent-492909-a74f688b6c7a.json | base64
```
Then add as environment variable:
```
GOOGLE_SERVICE_ACCOUNT_JSON_BASE64=<paste-base64-here>
```

And update `src/settings.py` to decode it.

#### 6. Deploy
- Click **"Create Web Service"**
- Render will automatically build and deploy
- Wait 3-5 minutes for first deployment
- Your app will be live at: `https://amber-newsletter-automation.onrender.com`

#### 7. Keep It Awake (Optional)
Free tier spins down after 15 min inactivity. To keep it alive:

**Option A: Cron Job (Free)**
Use [cron-job.org](https://cron-job.org):
- Create account
- Add job: `https://your-app.onrender.com/api/status`
- Schedule: Every 10 minutes

**Option B: UptimeRobot (Free)**
- Sign up at [uptimerobot.com](https://uptimerobot.com)
- Add monitor: `https://your-app.onrender.com/api/status`
- Check interval: 5 minutes

---

## 🥈 Alternative: Railway.app

### Features:
- ✅ $5 free credit/month (~500 hours)
- ✅ Better performance (no cold starts initially)
- ✅ Simpler setup
- ⚠️ Requires credit card

### Deployment:

#### 1. Sign Up
- Go to [railway.app](https://railway.app)
- Sign up with GitHub

#### 2. Deploy from GitHub
- Click **"New Project"**
- Select **"Deploy from GitHub repo"**
- Choose: `Wakdeprathamesh-amber/B2b-Newsletter-and-Blog-Automation`

#### 3. Add Environment Variables
Railway auto-detects Python. Add variables:
```bash
OPENAI_API_KEY=sk-proj-your-key
GOOGLE_MASTER_SHEET_ID=your-sheet-id
GOOGLE_SERVICE_ACCOUNT_JSON=/app/credentials/google-creds.json
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
SLACK_CHANNEL_ID=C0XXXXXXXXX
PORT=8000
```

#### 4. Upload Credentials
Use Railway CLI:
```bash
npm install -g @railway/cli
railway login
railway link
railway run --service amber-newsletter-automation
# Then manually upload via dashboard
```

#### 5. Configure Start Command
Railway auto-detects, but verify:
```bash
uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

#### 6. Deploy
- Railway auto-deploys
- Get URL from dashboard

---

## 🥉 Alternative: Fly.io

### Features:
- ✅ 3 shared-cpu VMs free
- ✅ 160GB bandwidth/month
- ✅ Good for background jobs
- ⚠️ Requires credit card

### Deployment:

#### 1. Install Fly CLI
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

#### 2. Sign Up & Login
```bash
fly auth signup
fly auth login
```

#### 3. Create fly.toml
Create `fly.toml` in project root:
```toml
app = "amber-newsletter-automation"
primary_region = "lhr"  # London, change as needed

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

#### 4. Set Secrets
```bash
fly secrets set OPENAI_API_KEY=sk-proj-your-key
fly secrets set GOOGLE_MASTER_SHEET_ID=your-sheet-id
fly secrets set SLACK_BOT_TOKEN=xoxb-your-token
fly secrets set SLACK_SIGNING_SECRET=your-secret
fly secrets set SLACK_CHANNEL_ID=C0XXXXXXXXX
```

#### 5. Upload Google Credentials
```bash
# Create a volume for credentials
fly volumes create credentials --size 1

# Then manually upload via fly ssh console
fly ssh console
# Upload file via scp or paste content
```

#### 6. Deploy
```bash
fly launch
fly deploy
```

---

## 📊 Comparison Table

| Feature | Render | Railway | Fly.io |
|---------|--------|---------|--------|
| **Free Hours** | 750/month | ~500/month | Unlimited |
| **Cold Start** | Yes (30s) | No (initially) | No |
| **Credit Card** | No | Yes | Yes |
| **Auto-Deploy** | Yes | Yes | Yes |
| **Ease of Setup** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Performance** | Good | Better | Best |
| **Best For** | Simple apps | Medium apps | Production-like |

---

## ⚠️ Important Notes

### 1. Database
Your app uses SQLite (`amber_content.db`). On free hosting:
- ❌ File storage is **ephemeral** (resets on restart)
- ✅ Google Sheets is your **persistent storage** (good!)
- ✅ No database migration needed

### 2. Long-Running Tasks
Phase 1 takes 15+ minutes:
- ✅ Render/Railway/Fly all support this
- ❌ Vercel/Netlify have 10s timeout (won't work)

### 3. Scheduled Cycles
To run weekly cycles automatically:
- Use **Render Cron Jobs** (paid feature)
- Or use **GitHub Actions** (free):

Create `.github/workflows/weekly-cycle.yml`:
```yaml
name: Weekly Content Cycle
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  run-cycle:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Phase 1
        run: |
          curl -X POST https://your-app.onrender.com/api/ui/phase1/start
```

### 4. Environment Variables
Never commit:
- ❌ `.env` file
- ❌ `credentials/*.json`
- ❌ API keys

Always use platform's environment variable system.

---

## 🚀 Quick Start (Render)

```bash
# 1. Push code to GitHub (already done ✅)

# 2. Go to render.com and sign up

# 3. Click "New +" → "Web Service"

# 4. Connect your repo

# 5. Configure:
#    - Build: pip install -r requirements.txt
#    - Start: uvicorn src.main:app --host 0.0.0.0 --port $PORT

# 6. Add environment variables (see above)

# 7. Deploy!

# 8. Access at: https://your-app.onrender.com
```

---

## 🆘 Troubleshooting

### App won't start
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `requirements.txt` is in repo root

### Google Sheets not working
- Verify `GOOGLE_SERVICE_ACCOUNT_JSON` path is correct
- Check service account has access to the sheet
- Test locally first: `python3 check_setup.py`

### Slack not working
- Verify bot token starts with `xoxb-`
- Check bot is added to channel
- Test locally: `python3 test_slack.py`

### Cold starts too slow
- Upgrade to paid tier ($7/month on Render)
- Or use UptimeRobot to keep it awake
- Or switch to Railway (no cold starts initially)

---

## 💰 Cost Estimate

### Free Forever:
- **Render Free**: 750 hours/month (enough for 24/7)
- **Railway**: $5 credit/month (~500 hours)
- **Fly.io**: 3 VMs free (enough for 24/7)

### If You Outgrow Free:
- **Render Starter**: $7/month (no cold starts)
- **Railway Pro**: $5/month + usage
- **Fly.io**: Pay as you go (~$5-10/month)

---

## ✅ Recommended Setup

**For Production Use:**
1. Deploy on **Render** (free)
2. Use **UptimeRobot** to prevent cold starts (free)
3. Use **GitHub Actions** for scheduled cycles (free)
4. Monitor with **Slack notifications** (already built-in)

**Total Cost: $0/month** 🎉

---

## 📚 Additional Resources

- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
- [Fly.io Docs](https://fly.io/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
