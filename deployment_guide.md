# Production Deployment Guide: Render & Vercel

This guide outlines the step-by-step instructions to deploy your Document OCR application. 

*   **Backend (FastAPI)**: Hosted on **Render** (ideal for persistent Python web servers).
*   **Frontend (React/Vite)**: Hosted on **Vercel** (ideal for static sites and frontend CDNs).

---

## Part 1: Deploying the Backend on Render

Render is the best platform for deploying the FastAPI backend because it fully supports persistent web service containers running Python and Uvicorn.

### Step 1: Create a Render Account
1. Go to [Render](https://render.com/) and sign up.
2. Connect your GitHub or GitLab account.

### Step 2: Create a New Web Service
1. Click **New +** in the top right and select **Web Service**.
2. Select your repository containing the project.
3. Configure the following settings:
   * **Name**: `document-ocr-backend` (or similar)
   * **Language**: `Python 3`
   * **Branch**: `main` (or whichever branch you push to)
   * **Root Directory**: `backend`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Environment Variables
Scroll down to the **Environment Variables** section (under the **Advanced** tab or the **Env** tab) and add the following keys:

| Key | Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | `your_actual_gemini_api_key` | Your Google AI Studio API Key. |
| `JWT_SECRET_KEY` | `generate_a_random_secure_hex_string` | Run `openssl rand -hex 32` or type a secure string. |
| `MOCK_VLM` | `True` | Bypasses local 6GB model download, routing all OCR & Q&A through Gemini. |
| `DATABASE_URL` | *Optional* | SQLite is used by default. If using a production DB, see below. |

### Step 4: Click Deploy
Render will build the dependencies and start your FastAPI server. Once completed, Render will provide a public URL like:
`https://document-ocr-backend.onrender.com`

---

## Part 2: Deploying the Frontend on Vercel

Vercel is the industry standard for hosting React/Vite single-page applications.

### Step 1: Create a Vercel Account
1. Go to [Vercel](https://vercel.com/) and sign up.
2. Link your GitHub account.

### Step 2: Import the Project
1. Click **Add New** -> **Project**.
2. Import your repository.
3. Configure the build parameters:
   * **Framework Preset**: `Vite`
   * **Root Directory**: `frontend`
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`

### Step 3: Configure Environment Variables
Open the **Environment Variables** dropdown and add the key to connect to your Render backend:

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://document-ocr-backend.onrender.com` | Replace with your actual Render Web Service URL. |

### Step 4: Deploy
Click **Deploy**. Vercel will build and launch your frontend static site in less than a minute. You will get a URL like:
`https://document-ocr-frontend.vercel.app`

---

## Database Persistence Note (SQLite vs PostgreSQL)

On Render's free tier, the file system is **ephemeral**. This means any uploaded PDFs or SQLite database files (`document_ocr.db`) will be deleted whenever the backend service restarts or redeploys.

To persist your database, you have two options:
1. **Render Persistent Volume**: Add a disk to your Render web service (costs $1/month) mounted at `/uploads` and update your `DATABASE_URL` path.
2. **Production Database (Recommended)**: Create a free **PostgreSQL** database on Render or Supabase, copy the connection URI, and add it to Render's environment variables as:
   `DATABASE_URL=postgresql://user:password@host:port/dbname`
   The backend code automatically detects PostgreSQL and initializes the tables on startup.
