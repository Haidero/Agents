# How the AI Resume Screening System Works

This document provides a technical overview of the AI Resume Screening System, explaining its architecture, components, and workflows.

## 1. System High-Level Overview

The system is designed to automate the recruitment process by screening resumes using two distinct methods:
1.  **Rule-Based Screening**: Fast, deterministic, keyword-and-regex-based scoring.
2.  **LLM Agent Screening**: Advanced, semantic understanding using Large Language Models (LLMs) orchestrated through specialized agents.

It offers three main interfaces:
*   **Scanning CLI**: For batch processing local folders.
*   **Web Dashboard**: A user-friendly Streamlit interface for interactive analysis.
*   **Email Agent**: An autonomous bot that monitors an inbox, processes incoming resumes, and sends auto-replies.

## 2. Directory Structure & Key Files

```text
resume-screening-system/
├── main.py                 # CLI Entry point (handles scan, web, and email modes)
├── web_app.py              # Streamlit Web UI application
├── config.py               # Central configuration (Model paths, device settings)
├── core/
│   ├── screener.py         # Logic for Rule-Based Screening
│   └── llm_screener.py     # Logic for LLM Agent orchestration
├── agents/                 # Specialized AI Agents
│   ├── parser_agent.py     # Parses raw text from files
│   ├── classifier_agent.py # Segments resumes (experience vs education vs skills)
│   ├── grader_agent.py     # Generates scores and summaries
│   ├── decision_agent.py   # Make final hiring recommendations
│   └── email_agent/        # Email handling logic (IMAP/SMTP)
└── models/                 # Directory for local LLM weights (Llama-2, etc.)
```

## 3. Core Workflows

### A. The Resume Screening Pipeline (Rule-Based)
*Implemented in `core/screener.py`*

1.  **Parsing**: Reads `.pdf`, `.docx`, or `.txt` files to extract raw text.
2.  **Scoring Algorithm**:
    *   **Skills (30pts)**: Matches keywords against a weighted dictionary (e.g., Python=8, AWS=10) and normalizes the score.
    *   **Experience (25pts)**: Uses Regex to find "N years experience" or calculates duration from dates. Bonues for senior roles.
    *   **Education (15pts)**: Detects degrees (PhD, Masters) and checks for top universities.
    *   **Bonues**: Points for FAANG companies, certifications, and achievements.
3.  **Output**: Returns a score (0-100), detailed skill list, and a summary.

### B. The LLM Agent Pipeline
*Implemented in `core/llm_screener.py`*

This pipeline uses a chain of specialized agents:
1.  **Parser Agent**: Extracts structured data (sentences, metadata) from files.
2.  **Classifier Agent**: Classifies every sentence into categories (e.g., "Personal Info", "Skill", "Experience") to protect privacy (PII removal) and organize data.
3.  **Grader Agent**: Uses an LLM to "read" the relevant sections and generate a score and summary based on HR criteria.
4.  **Decision Agent**: Reviews the top candidates and provides a final hiring recommendation.

### C. The Email Automation Workflow
*Implemented in `agents/email_agent/email_agent.py`*

1.  **Monitoring**: Connects to Gmail via IMAP and searches for unread emails (last 7 days) with attachments.
2.  **Filtering**: Downloads valid attachments (PDF/DOCX) and ignores duplicates.
3.  **Processing**: Sends the downloaded resume to the **Screener** (defaulting to Rule-Based for speed) to get a score.
4.  **Response**:
    *   **Score > 80**: Sends "Accepted" email (Interview request).
    *   **Score 70-80**: Sends "Needs Review" email.
    *   **Score < 70**: Sends "Rejected" email.
5.  **Logging**: Saves results to `email_results/` and updates a processed log to prevent re-processing.

## 4. Key Configuration

*   **`config.py`**:
    *   **`ModelConfig`**: Controls whether to use CPU or GPU (`cuda`), and selects between Local LLMs (Llama-2) or OpenAI API.
    *   **`AgentConfig`**: Defines screening categories and privacy settings.
*   **`email_config.json`**: Stores email credentials (IMAP/SMTP) and message templates.

## 5. How to Run

1.  **Web Interface**:
    ```bash
    streamlit run web_app.py
    ```
2.  **Batch Scan**:
    ```bash
    python main.py scan --dir ./resumes --position software_engineer
    ```
3.  **Email Agent**:
    ```bash
    python main.py email --continuous
    ```
