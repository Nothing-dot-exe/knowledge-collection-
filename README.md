# ⚡ arXiv Paper Scraper & Knowledge Ingestion Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docling Powered](https://img.shields.io/badge/PDF%20Engine-Docling%20v2-orange.svg)](https://github.com/DS4SD/docling)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![arXiv API Compliant](https://img.shields.io/badge/arXiv-Rate%20Limit%20Compliant-purple.svg)](https://arxiv.org/help/api/tou)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Topic%20Routing-blue.svg)](https://core.telegram.org/bots)

An autonomous, high-performance research paper scraper and knowledge ingestion pipeline. It continuously monitors **Hugging Face Trending** and **10 arXiv Computer Science & Math tracks**, converts PDFs into structured Markdown using IBM's **Docling** engine, routes rich summaries to **Telegram Forum Topics**, and archives them to your **GitHub Knowledge Vault** with zero duplicate entries.

---

## 🌟 Key Features

* **Multi-Source Scraping**:
  * 🔥 **Hugging Face Daily Trending Papers** (extracts GitHub repos, stars, and upvotes).
  * 📚 **10 Curated CS & Math Tracks** (Algorithms, Software Eng, Systems, Networks, Security, LLMs, Deep Learning, Vision, Math).
* **Air-Tight 4-Layer Deduplication**:
  * **Layer 1:** Version-stripped arXiv ID matching (`2609.04199v1` == `2609.04199`).
  * **Layer 2:** Normalized alphanumeric title matching.
  * **Layer 3:** Fuzzy title matching (`thefuzz >= 88%`).
  * **Layer 4:** Streaming cryptographic SHA-256 PDF content hash.
* **Docling Layout & Table Engine**:
  * Converts multi-column papers, formulas, and complex tables into clean Markdown without OCR bottlenecks.
* **Rate-Limit Resilient Architecture**:
  * Built-in `3.5s` delay adhering strictly to [arXiv Terms of Use](https://arxiv.org/help/api/tou).
  * Auto-recovering exponential backoff (`12s` → `24s` → `48s` → `96s`) upon encountering `HTTP 429` or `503`.
* **Automated Telegram Topic Dispatch**:
  * Delivers raw PDFs to **Topic 10** and structured Markdown to **Topic 11**.
  * Interactive inline buttons for arXiv abstract, direct PDF, official GitHub code, and repository vault.
* **1-Click Google Colab Notebook**:
  * Free T4 GPU acceleration via `knowledge_agent_colab.ipynb` using secure Google Colab Secrets.

---

## 📂 Project Structure

```text
├── knowledge_agent.py          # Main autonomous scraper & ingestion pipeline
├── knowledge_agent_colab.ipynb  # 1-Click Google Colab runner with GPU support
├── registry.json               # Centralized deduplication ledger (IDs, hashes, titles)
├── markdown_files/             # Converted RAG-ready Markdown research papers
├── requirements.txt            # Python dependencies (no bloated web servers)
├── .env.example                # Template for environment variables
├── .gitignore                  # Keeps PDFs, logs, and secrets out of git
└── LICENSE                     # MIT License
```

---

## 🚀 Quickstart

### 1. Clone the Repository
```bash
git clone https://github.com/Nothing-dot-exe/arxiv-paper-scraper.git
cd arxiv-paper-scraper
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy the `.env.example` template:
```bash
cp .env.example .env
```
Fill in your credentials in `.env`:
```env
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_REPO_URL=https://github.com/Nothing-dot-exe/arxiv-paper-scraper
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_GROUP_ID=-1001234567890
RAW_PDF_TOPIC_ID=10
TEXT_MD_TOPIC_ID=11
ADMIN_CHAT_ID=123456789
PAPERS_PER_CATEGORY=15
```

### 4. Run the Pipeline
```bash
python knowledge_agent.py
```

---

## 📓 Running in Google Colab (Free GPU)

1. Open `knowledge_agent_colab.ipynb` in Google Colab.
2. In the left sidebar, click the **🔑 Secrets** icon and add:
   * `GITHUB_TOKEN`
   * `TELEGRAM_BOT_TOKEN`
   * `ADMIN_CHAT_ID`
3. Click **Run All** — papers will be processed on a free T4 GPU at 10x speed.

---

## 📜 Curriculum Tracks

| Track Name | ArXiv Query |
| :--- | :--- |
| **💻 Advanced Coding & Algorithms** | `cat:cs.DS OR cat:cs.PL` |
| **🛠 Software Eng & Architecture** | `cat:cs.SE` |
| **🐧 Linux & Operating Systems** | `cat:cs.OS` |
| **☁ Cloud & Distributed Systems** | `cat:cs.DC` |
| **🌐 Networks, Web & Protocols** | `cat:cs.NI OR cat:cs.IR` |
| **🛡 Cybersecurity & Exploits** | `cat:cs.CR` |
| **🤖 AI & Language Models (LLMs)** | `cat:cs.AI OR cat:cs.CL` |
| **🧠 Machine Learning & Deep Learning**| `cat:cs.LG OR cat:stat.ML` |
| **👁 Computer Vision & Multimodal** | `cat:cs.CV` |
| **📐 Mathematics & Computation** | `cat:math.CO OR cat:math.ST OR cat:math.PR` |

---

## ⚖️ Legal & Ethical Compliance

* **Open Access & CC Licenses**: arXiv papers are distributed under open licenses (primarily CC-BY 4.0 or arXiv non-exclusive license). Attribution is preserved in every generated Markdown document.
* **Fair Use**: Extracting metadata and converting papers for a personal RAG knowledge base qualifies as educational, transformative research under Fair Use.
* **Rate Limits**: This bot enforces a strict `delay_seconds=3.5` cooldown between queries to respect arXiv server resources and prevent 429 throttling.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
