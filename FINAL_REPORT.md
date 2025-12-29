# AI Resume Screening System - Final Report

## Overview
This project is an advanced AI-powered resume screening system designed to automate the recruitment workflow. It uses a multi-agent architecture to parse, classify, and grade resumes from email attachments, providing a streamlined dashboard for HR professionals.

## Key Features Implemented

### 1. 📧 Intelligent Email Agent
-   **Auto-Fetch**: Connects to IMAP email servers to download resumes automatically.
-   **Date Filtering**: Supports scanning emails from the last 24 hours, 3 days, 1 week, or 1 month.
-   **Smart Search**: Uses `SINCE` search criteria to ensure ALL emails (read or unread) are processed.
-   **Force Rescan**: Option to ignore history and re-process previously screened emails.

### 2. 🧠 Advanced AI Grading
-   **Targeted Evaluation**: Grades resumes specifically against a selected **Position** (e.g., "Data Scientist", "DevOps Engineer").
-   **Structured Scoring**: Provides detailed breakdown:
    -   **Relevance Score**: How well the profile fits the job title.
    -   **Skills Score**: Assessment of technical competencies.
    -   **Experience Score**: Quality and depth of work history.
    -   **Formatting Score**: Clarity and professional presentation.
-   **JSON Output**: Uses structured JSON for reliable data parsing.

### 3. 💻 Modern Web Dashboard
-   **Global Position Sync**: Selected position applies to both manual uploads and email screening.
-   **Historical Data**: View consolidated results from all previous email runs.
-   **Rich Visualizations**: Interactive charts for score distribution, skill weights, and candidate ranking.
-   **Deprecation Fixes**: Updated UI code to comply with latest Streamlit standards (removed `use_container_width` warnings).

## Project Structure

```
Multi Agents/
├── agents/                 # AI Agent Implementations
│   ├── email_agent/        # Email Fetching & Processing
│   ├── grader_agent.py     # Resume Grading Logic
│   ├── parser_agent.py     # Resume Parsing
│   └── ...
├── core/                   # Core Logic Pipeline
│   ├── llm_screener.py     # Orchestrator
│   └── ...
├── email_results/          # Stored Analysis Results (JSON)
├── resumes/                # Downloaded Resume Files
├── web_app.py              # Streamlit Web User Interface
├── main.py                 # CLI Entry Point
├── email_config.json       # Email Credentials
└── requirements.txt        # Dependencies
```

## How to Run

1.  **Start the Web UI**:
    ```bash
    streamlit run web_app.py
    ```

2.  **Using the App**:
    -   Select a **Position Type** in the sidebar.
    -   Go to **Email Agent** section.
    -   Select **Scan Period** (e.g., Last 1 Week).
    -   (Optional) Check **Force Rescan** to re-process old emails.
    -   Click **Run Email Agent Now**.

3.  **Manual Mode**:
    -   Upload PDF/DOCX resumes directly in the main area to screen them instantly.

## Cleanup Performed
-   Removed temporary test scripts (`tests/`).
-   Cleared log files (`email_agent.log`).
-   Cleared previous run data (`email_results/`, `resumes/`) for a fresh start.
-   Removed python cache files (`__pycache__`).
