# 🆓 100% Free Deployment Guide

This guide explains how to deploy the DSMI Agent completely for free. By utilizing the free tiers of various cloud services, you can run the entire application (Frontend, Backend, and Databases) without entering a credit card or incurring monthly charges.

## The Free Stack
- **Frontend**: [Vercel](https://vercel.com) (Free Hobby Tier)
- **Backend API**: [Render](https://render.com) (Free Web Service)
- **Database**: [Neon.tech](https://neon.tech) (Free Serverless Postgres)
- **Cache**: [Upstash](https://upstash.com) (Free Serverless Redis)
- **Vector DB**: [Qdrant Cloud](https://cloud.qdrant.io/) (Free 1GB Cluster)

---

## Step 1: Provision the Free Databases

### 1. PostgreSQL (Neon.tech)
1. Go to [Neon.tech](https://neon.tech) and sign up.
2. Create a new project. Name it `dsmi-agent`.
3. Once created, go to the dashboard and copy the **Postgres Connection String**.
4. Save this as your `DATABASE_URL`. It will look like: `postgresql://user:pass@ep-rest-of-url.neon.tech/neondb`
   > **Note:** Just paste the URL exactly as Neon provides it.

### 2. Redis Cache (Upstash)
1. Go to [Upstash.com](https://upstash.com) and sign up.
2. Under Redis, click **Create Database**. Name it `dsmi-cache`.
3. Scroll down in your new database dashboard to the **Connect** section.
4. Copy the **Redis URL** (you can click the toggle to reveal the password in the URL).
5. Save this as your `REDIS_URL`. It will look like: `rediss://default:password@eu1-rest-of-url.upstash.io:30000`

### 3. Vector Database (Qdrant Cloud)
1. Go to [Qdrant Cloud](https://cloud.qdrant.io/) and sign up.
2. Create a new cluster and select the **Free Tier**.
3. Once the cluster is ready, generate an API key and copy the Cluster URL.
4. Save these as your `QDRANT_URL` and `QDRANT_API_KEY`.

---

## Step 2: Deploy the Backend API (Render)

Render allows you to host Python APIs for free.

1. **Push your code to GitHub:** Render needs to pull your code from a Git repository. Make sure your `dsmi_agent` folder is pushed to a public or private GitHub repository.
2. Go to [Render.com](https://render.com) and sign up.
3. Click **New** -> **Web Service**.
4. Connect your GitHub account and select your repository.
5. Configure the Web Service:
   - **Name:** `dsmi-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Select the **Free** tier.
6. Scroll down to **Environment Variables** and add all your secrets:
   - `DATABASE_URL`: (Your Neon URL)
   - `REDIS_URL`: (Your Upstash URL)
   - `QDRANT_URL`: (Your Qdrant URL)
   - `QDRANT_API_KEY`: (Your Qdrant API Key)
   - `JWT_SECRET_KEY`: (Generate a random long string)
   - `ENV`: `production`
7. Click **Create Web Service**. Wait a few minutes for it to build and deploy.
8. Copy the provided Render URL (e.g., `https://dsmi-api-abc.onrender.com`).

### Preventing Render Cold Starts
> [!TIP]
> Render's free tier spins down your server after 15 minutes of inactivity, causing the next request to take 30-50 seconds to respond. 
> To prevent this, sign up for [UptimeRobot](https://uptimerobot.com) (free) and set up an HTTP monitor to ping your Render API's health endpoint (`https://your-api.onrender.com/api/health`) every 10 minutes. This tricks Render into staying awake 24/7!

---

## Step 3: Deploy the Frontend (Vercel)

Vercel is the creator of Next.js and provides the best free hosting for it.

1. Go to [Vercel.com](https://vercel.com) and sign up.
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. When configuring the project, you need to tell Vercel that the frontend is inside the `frontend/` folder.
   - Set the **Root Directory** to `frontend`.
5. Under **Environment Variables**, add the URL to your Render API:
   - `NEXT_PUBLIC_API_URL`: (Your Render API URL, e.g., `https://dsmi-api-abc.onrender.com`)
6. Click **Deploy**. Vercel will build the Next.js app and provide you with a live URL.

---

## Step 4: Final Configuration
Ensure CORS is correctly configured. You may need to go back to your Render Dashboard and add a new Environment Variable:
- `CORS_ORIGINS`: (Your live Vercel frontend URL, e.g., `https://dsmi-frontend.vercel.app`)

Wait for Render to redeploy with the new environment variable.

### 🎉 Success!
You now have a fully functional, auto-scaling AI agent application deployed globally, and you will never receive a bill for it.
