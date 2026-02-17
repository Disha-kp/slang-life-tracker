# 🚀 How to Deploy Slang Life Tracker for Free

This guide will help you deploy your app to **Streamlit Community Cloud**, which is free and easy to use.

## 1. Prepare Your GitHub Repository
Streamlit Cloud pulls code directly from GitHub.

1.  **Create a New Repository** on GitHub (e.g., `slang-life-tracker`).
2.  **Upload Your Files**:
    *   Ensure `requirements.txt` is in the root.
    *   Ensure `app/app.py` is present.
    *   Ensure `data/slang_master_2026.csv` is included (this seeds your data).
    *   **Do NOT** upload `venv` or `__pycache__` (the `.gitignore` file I created handles this).

    *If you are using the command line:*
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/slang-life-tracker.git
    git push -u origin main
    ```

## 2. Deploy on Streamlit Cloud
1.  Go to [share.streamlit.io](https://share.streamlit.io/) and sign up/login.
2.  Click **"New app"**.
3.  **Connect to GitHub** (if not already done) and authorize access.
4.  **Select Your Repository** (`slang-life-tracker`).
5.  **Branch**: `main`.
6.  **Main file path**: `app/app.py`.
7.  Click **"Deploy!"**.

## 3. Configure Secrets (Optional but Recommended)
If your app uses Reddit credentials (API), you need to add them safely.

1.  On your deployed app dashboard, click **Manage app** (bottom right) -> **⋮ Settings** -> **Secrets**.
2.  Paste your secrets in TOML format (matching your `.env` structure):
    ```toml
    # .streamlit/secrets.toml
    REDDIT_CLIENT_ID = "your_client_id"
    REDDIT_CLIENT_SECRET = "your_client_secret"
    REDDIT_USER_AGENT = "your_user_agent"
    ```
    *Note: Since we have a fallback scraper (`no_api_scraper.py`), the app will still work without these keys, but adding them makes it more robust.*

## 4. Wait for Build
Streamlit will install the libraries from `requirements.txt`. This usually takes 1-2 minutes.
Once done, your app will be live at a URL like `https://slang-life-tracker.streamlit.app`! 🎈
