# Slang Life Tracker (UK Edition & Deep Lore)
https://dishas-slanglifetracker.streamlit.app/ -deployed link
## 1. Project Abstract
The **Slang Life Tracker** is an advanced linguistic analysis tool designed to track the lifecycle of slang terms from their obscure origins to mainstream saturation and eventual "cringe" status.

Unlike static dictionaries, this application uses a dynamic, multi-layered approach:
-   **Layer 1 (The Archive)**: Consults a curated database of historical and modern slang (1600s - 2026).
-   **Layer 2 (Deep Search)**: If a term is unknown, it scrapes live Reddit data (`r/all`) to discover its usage context, sentiment, and current relevance.
-   **Lifecycle Analysis**: Calculates a "Cringe Score" and "Cultural Capital" to determine if a word is *Niche*, *Peak*, *Mainstream*, or *Dead*.

The project now features **Deep Lore Integration**, visualizing slang evolution on a **400-Year Chronos Timeline**, placing modern terms like "Rizz" alongside 17th-century insults like "Zounds" to show the cyclical nature of language.

## 2. System Requirements

### Hardware
-   **Processor**: Modern dual-core CPU or better (for data processing).
-   **RAM**: 4GB minimum (8GB recommended for smooth scraping/visualization).
-   **Storage**: ~100MB for application code and SQLite database.
-   **Internet Connection**: Required for the Live Reddit Scraper features.

### Software
-   **OS**: macOS, Windows 10/11, or Linux.
-   **Python**: Version 3.8 or higher.
-   **Browser**: Modern web browser (Chrome, Firefox, Safari) for the Streamlit interface.

### Dependencies
The project relies on the following key Python libraries:
-   `streamlit`: For the interactive web interface.
-   `plotly`: For the Chronos Timeline and Lifecycle charts.
-   `pandas`: For data manipulation.
-   `requests`: For API and scraping calls.
-   `nltk`: For natural language processing (if enabled in future).

## 3. Installation & Run

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/slang-life-tracker.git
    cd slang-life-tracker
    ```

2.  **Install Dependencies**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    streamlit run app/app.py
    ```

4.  **Explore**
    Open your browser to `http://localhost:8501` (or the port shown in terminal).

## 4. Key Features
-   ** Multi-Layered Search**: Instant DB lookups + On-demand Reddit scraping.
-   ** Chronos Timeline**: Visualizes words from 1600 to 2026.
-   ** Cringe Meter**: Real-time "Cringe" vs. "Based" scoring.
-   ** Auto-Learning**: Automatically saves improved data back to `word_vault.db`.
-   ** Cyber-Aesthetic**: Custom "Neubrutalist Pop" UI with bouncy animations.

## 5. Keeping the Database Fresh (Auto-Updater)
The slang archive (`data/slang_master_2026.csv`) doesn't have to be updated by hand.

-   **`data/auto_updater.py`** scans configured Reddit communities for trending terms,
    runs them through the existing slang-detection heuristic (`models/slang_detector.py`),
    estimates a lifecycle status, and appends genuinely new words to the CSV. It never
    overwrites or deletes existing entries — only adds new ones — so it's safe to re-run.
-   **`.github/workflows/update-slang-db.yml`** runs that script automatically once a day
    (06:00 UTC) via GitHub Actions, and commits any newly discovered words straight back
    to the repo. Streamlit Cloud auto-redeploys on every push, so the live app picks up
    new slang without anyone touching it manually.
-   To run it by hand instead: `python data/auto_updater.py`
-   To change the schedule: edit the `cron` line in the workflow file.
-   To trigger a run on demand: go to the repo's **Actions** tab → "Auto-Update Slang
    Database" → **Run workflow**.

-   ** Multi-Layered Search**: Instant DB lookups + On-demand Reddit scraping.
-   ** Chronos Timeline**: Visualizes words from 1600 to 2026.
-   ** Cringe Meter**: Real-time "Cringe" vs. "Based" scoring.
-   ** Auto-Learning**: Automatically saves improved data back to `word_vault.db`.
-   ** Cyber-Aesthetic**: Custom "Neubrutalist Pop" UI with bouncy animations.