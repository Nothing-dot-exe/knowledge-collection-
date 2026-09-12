# 🧠 Knowledge Agent v3 — 24/7 Omni-Source RAG & Full-Coverage Fine-Tuning Engine

A high-performance, **rate-limit-immune**, 24/7 autonomous research ingestion pipeline that generates pristine **zero-link markdown** for RAG and **100% full-coverage chunked datasets** for LLM fine-tuning without GPU memory truncation.

> 📖 **Step-by-Step Instructions:** Read the complete **[SETUP_GUIDE.md](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/SETUP_GUIDE.md)** for detailed walkthroughs on setting up Google Colab, Telegram topics, and connecting a separate GitHub storage account.

---

## ⚡ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ZERO-429 DUAL-STREAM DISCOVERY ENGINE                       │
├─────────────────┬───────────────────────────────────────────────────────────────┤
│  arXiv RSS CDN  │  Hugging Face Trending API (Authenticated)                    │
│  (0% rate limit)│  (GitHub companion repos + upvotes + metadata)                │
└────────┬────────┴───────────────────────────────┬───────────────────────────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          4-LAYER DEDUPLICATION GUARD                            │
│     L1: arXiv ID   |   L2: Exact Title   |   L3: Fuzzy Match   |   L4: SHA-256  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       PDF DOWNLOAD & DOCLING GPU ENGINE                         │
│     • Fast zero-OCR digital parsing with table & formula preservation           │
│     • Bibliography section isolation                                            │
│     • GitHub companion code README fetch                                        │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ZERO-LINK SANITIZATION ENGINE (PRISTINE)                    │
│     • Strips [text](url) -> plain text                                          │
│     • Strips raw URLs, web protocols, and GitHub badges                         │
│     • 0% link pollution in markdown text files                                  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
┌────────────────────────────────────────┐ ┌──────────────────────────────────────┐
│       100% FULL-COVERAGE CHUNKER       │ │       CLEAN MARKDOWN VAULT           │
│  • Slices paper into ~2K-token chunks  │ │  • Pure text + YAML metadata         │
│  • Zero truncation on GPU fine-tuning  │ │  • Saved to text_vault/KB-xxxx.md    │
│  • Output to dataset_vault/            │ │                                      │
└────────────────────┬───────────────────┘ └──────────────────┬───────────────────┘
                     │                                        │
                     └───────────────────┬────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          MULTI-DESTINATION DISPATCH                             │
│   • 📱 Telegram Topics:                                                         │
│       - 🚀 Upload & Control -> Topic 648 (https://t.me/c/3958148223/648)        │
│       - 📚 Registry Mirror  -> Topic 649 (https://t.me/c/3958148223/649)        │
│       - 📄 Raw PDFs         -> Topic 354 (https://t.me/c/3958148223/354)        │
│       - 📝 Clean Text       -> Topic 355 (https://t.me/c/3958148223/355)        │
│       - 📊 Datasets         -> Topic 356 (https://t.me/c/3958148223/356)        │
│       - 📢 General & Alerts -> Topic 1   (https://t.me/c/3958148223/1)          │
│   • 🐙 GitHub Dual-Vault: text_vault/ + dataset_vault/ + Master README.md       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔥 Key Features

| Feature | Description |
| :--- | :--- |
| **Zero Rate Limits** | Uses arXiv RSS CDN feeds instead of `export.arxiv.org/api/query` — immune to HTTP 429 errors. |
| **Zero-Link Sanitization** | Thorough regex engine strips all markdown links, raw URLs, image embeds, and badges. |
| **100% Full-Coverage Chunking** | Slices multi-page papers into ~2,000-token semantic chunks so GPUs never truncate long papers during fine-tuning. |
| **Multi-Topic Telegram Delivery** | Routes content to dedicated Supergroup topics: PDFs to **354**, Text to **355**, Datasets to **356**, and Alerts to **1**. |
| **GitHub Dual-Vault** | Separate folders for clean text (`text_vault/`) and training data (`dataset_vault/`) with an auto-updating catalog in `README.md`. |
| **24/7 Crash-Proof Daemon** | Non-stop autonomous loop that catches per-paper errors, alerts Topic 1, and continues without getting stuck. |
| **4-Layer Deduplication** | Layer 1 (arXiv ID), Layer 2 (Title), Layer 3 (Fuzzy 88%), Layer 4 (SHA-256 PDF hash). |

---

## 📁 Curriculum Tracks

| Track | arXiv Categories |
| :--- | :--- |
| 🛡 **Cybersecurity & Exploits** | `cs.CR` |
| 🤖 **AI & Language Models (LLMs)** | `cs.AI`, `cs.CL` |
| 🧠 **Machine Learning & Deep Learning** | `cs.LG`, `stat.ML` |
| 👁 **Computer Vision & Multimodal** | `cs.CV` |
| 💻 **Advanced Coding & Algorithms** | `cs.DS`, `cs.PL` |
| 🛠 **Software Eng & Git Architecture** | `cs.SE` |
| 🐧 **Linux & Operating Systems** | `cs.OS` |
| ☁ **Cloud, Servers & Distributed Sys** | `cs.DC` |
| 🌐 **Networks, Web & Protocols** | `cs.NI`, `cs.IR` |
| 📐 **Computational Mathematics** | `math.NA`, `math.OC`, `cs.CC` |

---

## 🚀 Quick Start

> 💡 For step-by-step instructions on creating Telegram bots, topic IDs, and separate GitHub storage tokens, see **[SETUP_GUIDE.md](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/SETUP_GUIDE.md)**.

### 1. Local Setup
```bash
pip install -r requirements.txt
python knowledge_agent.py
```

### 2. Google Colab (Recommended)
1. Open Google Colab and set GPU: **Runtime -> Change runtime type -> T4 GPU**.
2. Open `colab_script.txt` (or upload `knowledge_agent_colab.ipynb`).
3. Paste into a cell and run!

---

## 📋 Environment Configuration (`.env`)

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO_URL=https://github.com/Rawknowledge-database/knowledge
TELEGRAM_BOT_TOKEN=8525850416:AAGtYIM1sg8MF21_8lI2hOS1E-i9MosV4RE
TELEGRAM_GROUP_ID=-1003958148223

# Topic IDs
RAW_PDF_TOPIC_ID=354
TEXT_MD_TOPIC_ID=355
DATASET_TOPIC_ID=356
GENERAL_TOPIC_ID=1

ADMIN_CHAT_ID=6190001521
HF_TOKEN=hf_your_hf_token_here
PAPERS_PER_CATEGORY=15
```

---

## 📄 Output Formats

### 1. Clean Markdown (`text_vault/KB-0001.md`)
```yaml
---
kb_id: "KB-0001"
arxiv_id: "2609.04199"
title: "Paper Title"
track: "🛡 Cybersecurity & Exploits"
categories: "cs.CR"
authors: "Author Names"
published: "2026-09-12"
ingested: "2026-09-12T10:30:00Z"
word_count: 8250
page_count: 14
total_chunks: 6
has_code: true
---

# Section 1: Introduction
Pure sanitized text with zero URLs, badges, or link brackets...
```

### 2. Chunked Dataset (`dataset_vault/KB-0001_dataset.jsonl`)
```json
{"id": "KB-0001_c01", "kb_id": "KB-0001", "chunk_index": 1, "total_chunks": 6, "title": "...", "track": "🛡 Cybersecurity & Exploits", "text": "..."}
{"id": "KB-0001_c02", "kb_id": "KB-0001", "chunk_index": 2, "total_chunks": 6, "title": "...", "track": "🛡 Cybersecurity & Exploits", "text": "..."}
```
