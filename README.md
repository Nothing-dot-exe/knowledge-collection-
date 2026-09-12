# 🧠 Autonomous Knowledge Bot — 24/7 PDF-to-Dataset & Clean Text Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CUDA Accelerated](https://img.shields.io/badge/CUDA-100%25%20GPU%20Docling-green.svg)](https://developer.nvidia.com/cuda-zone)
[![Telegram MTProto](https://img.shields.io/badge/Telegram-MTProto%20(Up%20to%202GB)-0088cc.svg)](https://core.telegram.org/mtproto)
[![Google Colab](https://img.shields.io/badge/Google%20Colab-T4%20Ready-orange.svg)](https://colab.research.google.com)
[![GitHub Vault](https://img.shields.io/badge/GitHub%20Vault-Dual--Storage-black.svg)](https://github.com/Rawknowledge-database/knowledge)

An enterprise-grade, **24/7 autonomous document ingestion agent** running on Google Colab (T4 GPU) and local environments. It continuously ingests PDFs from a default monitored channel or manual Telegram uploads, extracts pristine **zero-link Markdown** for RAG, generates **100% full-coverage chunked fine-tuning datasets (JSONL)**, names all files using their **actual document titles**, and dispatches outputs to **6 dedicated Telegram topics** and a **GitHub Vault**.

---

## ⚡ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DUAL-SOURCE PDF INGESTION                             │
├────────────────────────────────────────┬────────────────────────────────────────┤
│  📡 Default Channel: @mybooksaspdf     │  🚀 Topic #648: User Control Center    │
│  • Continuous ID-batch backlog scanner │  • Interactive [Start] / [Abort] btns  │
│  • Instant real-time post listener     │  • Live progress % & dynamic ETA       │
│  • Strictly read-only (never deletes)  │  • Supports manual drops up to 2 GB    │
└───────────────────┬────────────────────┴───────────────────┬────────────────────┘
                    │                                        │
                    ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    STRICT 4-LAYER DEDUPLICATION SHIELD                          │
│   L1: Message ID Check | L2: Title Match | L3: Fuzzy (>85%) | L4: SHA-256 Hash  │
│   • Prevents duplicate processing even if filename differs or reposted          │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  DOCLING 100% CUDA GPU EXTRACTION ENGINE                        │
│   • Enforces 100% NVIDIA CUDA GPU execution on Google Colab (T4)                │
│   • TF32 tensor core acceleration & 8 worker threads                            │
│   • Preserves tables, mathematical LaTeX formulas & structured headings         │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ZERO-LINK SANITIZATION ENGINE (PRISTINE)                    │
│   • Completely strips [text](url) -> pure text                                  │
│   • Removes raw URLs, HTTP/HTTPS links, image embeds & web badges               │
│   • Produces 100% sanitized Markdown without link pollution                     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
┌────────────────────────────────────────┐ ┌──────────────────────────────────────┐
│       100% FULL-COVERAGE CHUNKER       │ │         CLEAN TEXT GENERATOR         │
│  • Slices document into ~2K-token SFT  │ │  • Pure text + YAML metadata header  │
│  • Unsloth & LLaMA-Factory JSONL       │ │  • Zero-link pristine Markdown       │
│  • Actual Title: <Title>_dataset.jsonl │ │  • Actual Title: <Title>.md          │
└───────────────────┬────────────────────┘ └──────────────────┬───────────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   DUAL-DESTINATION DISPATCH (1-BY-1 SEQUENTIAL)                 │
├────────────────────────────────────────┬────────────────────────────────────────┤
│  📱 Telegram Supergroup Topics:        │  🐙 GitHub Vault (Automated Sync):     │
│    • 📄 Topic #354 : Raw Named PDF     │    • text_vault/<Actual Title>.md      │
│    • 📝 Topic #355 : Clean Markdown    │    • dataset_vault/<Title>_dataset.json│
│    • 📊 Topic #356 : JSONL Dataset     │    • registry.json (Hashes & Catalog)  │
│    • 📚 Topic #649 : Registry Mirror   │    • README.md (Master Catalog Table)  │
│    • 📢 Topic #1   : General Alerts    │                                        │
│    • 🚀 Topic #648 : Delivery Summary  │                                        │
├────────────────────────────────────────┴────────────────────────────────────────┤
│  🗑️ ZERO DISK ACCUMULATION: Local raw PDF deleted immediately after dispatch   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔥 Key Highlights

| Feature | Specification |
| :--- | :--- |
| **Default Channel Ingestion** | Automatically monitors and scans `https://t.me/mybooksaspdf` from message 1 onwards in batches of 50. Ingests all backlog PDFs one-by-one. Strictly read-only: **never** deletes from the channel. |
| **Real-Time Listener** | Instantly catches newly posted PDFs in `@mybooksaspdf` and manual uploads in Topic `#648`. |
| **Actual Document Titles** | Files are saved in GitHub Vault and Telegram using their **real sanitized document titles** (e.g., `Mathematics for Machine Learning by Stanford University.md`), NOT generic IDs like `KB-0001`. |
| **MTProto 2GB Engine** | Powered by Telethon MTProto Client, bypassing Telegram's standard Bot API 20 MB limit up to **2 GB per file**. |
| **100% CUDA GPU Utilization** | Docling pipeline configured with `torch.backends.cuda.matmul.allow_tf32 = True` and `AcceleratorDevice.CUDA` for max throughput on Google Colab T4 GPUs. |
| **Strict 4-Layer Deduplication** | Pre-checks filename, fuzzy title match (>85%), binary SHA-256 hash, and processed message IDs. Duplicate PDFs are automatically skipped with alerts. |
| **Zero Disk Overflow** | Raw PDFs and temporary artifacts are unlinked immediately after dispatch. Disk usage remains essentially **0 MB**. |
| **Full GitHub Vault Sync** | Pushes clean text, datasets, `registry.json`, and updates `README.md` catalog on [Rawknowledge-database/knowledge](https://github.com/Rawknowledge-database/knowledge). |

---

## 📱 Telegram Forum Topic Topology

All processed documents and system updates are routed to dedicated topics in the RAG SYSTEM group (`-1003958148223`):

| Topic ID | Topic Name | Content & Output Delivered |
| :---: | :--- | :--- |
| **`648`** | **User Control Center** | Interactive start/abort controls, live % download progress, dynamic ETA, and completion cards. |
| **`649`** | **Registry Mirror** | Real-time registry mirror with SHA-256 checksums, total catalog count, and GitHub sync verification. |
| **`354`** | **PDF Vault** | Original named document archives (`<Actual Title>.pdf`). |
| **`355`** | **TEXT (Clean Markdown)** | 100% zero-link sanitized clean Markdown files (`<Actual Title>.md`). |
| **`356`** | **DATA SET** | 2,000-token semantic JSONL chunks formatted for Unsloth and LLaMA-Factory (`<Actual Title>_dataset.jsonl`). |
| **`1`** | **General Alerts** | System startup notices, milestone summaries, and pipeline health alerts. |

---

## 🚀 Quickstart: Running on Google Colab (Recommended)

Running the agent on Google Colab gives you a **free T4 GPU** with zero local dependencies:

1. **Open Google Colab**:
   - Go to [colab.research.google.com](https://colab.research.google.com) and create a New Notebook.
2. **Enable T4 GPU**:
   - Navigate to **Runtime -> Change runtime type**.
   - Select **T4 GPU** and click **Save**.
3. **Run the Script**:
   - Open [`colab_script.txt`](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/colab_script.txt) in this repo.
   - Copy the entire code and paste it into the Colab cell.
   - Press **Shift + Enter**.
4. **Autonomous Ingestion**:
   - The bot connects as `@collectionoffiles_bot`.
   - It will automatically index and process the PDF backlog from `https://t.me/mybooksaspdf` one-by-one.
   - You can also drop any PDF directly into Telegram **Topic #648**!

---

## 💻 Local Setup & Development

### 1. Prerequisites
- Python 3.10+
- NVIDIA GPU with CUDA (optional, CPU supported with fallback)
- Git

### 2. Installation
```bash
git clone https://github.com/Nothing-dot-exe/knowledge-collection-.git
cd knowledge-collection-
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment (`.env`)
Create or edit your `.env` file in the root directory:

```env
# ── GitHub Vault Repository ─────────────────────────────────────────
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_REPO_URL=https://github.com/Rawknowledge-database/knowledge

# ── Telegram MTProto Credentials ────────────────────────────────────
TELEGRAM_BOT_TOKEN=8405366649:AAGU5HqMhuj7Uh2WlSF_jxNDwETv_mY2ClY
TELEGRAM_API_ID=32962732
TELEGRAM_API_HASH=2b6abfa8621f5a53b2d0a3a79d3bf739
TELEGRAM_GROUP_ID=-1003958148223

# ── Forum Topic IDs ─────────────────────────────────────────────────
UPLOAD_TOPIC_ID=648
REGISTRY_TOPIC_ID=649
RAW_PDF_TOPIC_ID=354
TEXT_MD_TOPIC_ID=355
DATASET_TOPIC_ID=356
GENERAL_TOPIC_ID=1

# ── Channel & Pipeline Settings ─────────────────────────────────────
SOURCE_CHANNEL=mybooksaspdf
INGEST_MODE=interactive
DATASET_PAIRS_PER_PAPER=5
```

### 4. Run Controller
```bash
python colab_telegram_controller.py
```

---

## 📄 Output Samples

### 1. Sanitized Markdown (`text_vault/<Title>.md`)
```markdown
---
kb_id: "KB-0031"
title: "Mathematics for Machine Learning by Stanford University"
pages: 184
words: 62450
---

# Section 1: Linear Algebra and Matrix Decompositions
Let A be an m x n real-valued matrix...
[Zero links, pure pristine mathematical and textual representation]
```

### 2. Fine-Tuning Dataset (`dataset_vault/<Title>_dataset.jsonl`)
```json
{"messages": [{"role": "system", "content": "You are an expert AI researcher analyzing document KB-0031: 'Mathematics for Machine Learning by Stanford University'."}, {"role": "user", "content": "Provide comprehensive analysis of the following section..."}, {"role": "assistant", "content": "Here is the detailed synthesis of section 1..."}], "metadata": {"kb_id": "KB-0031", "title": "Mathematics for Machine Learning by Stanford University", "chunk_index": 1, "word_count": 1942}}
```

---

## 🛡️ Deduplication Guard Details

To prevent duplicate storage and save computational resources, every document passes through 4 checks:

1. **Message ID Deduplication**: Tracks all channel and topic message IDs in memory and ignores reposted messages.
2. **Title Pre-Check**: Sanitizes the incoming filename and tests for exact matches against registered titles in `registry.json`.
3. **Fuzzy Title Match**: Compares alphanumeric tokens using `thefuzz.fuzz.token_set_ratio`. If similarity > 85%, it triggers a duplicate warning and skips ingestion.
4. **SHA-256 Binary Hash**: After download, computes the document's cryptographic hash. If the hash exists in `registry.json`, processing terminates immediately before GPU extraction.

---

## 📁 Repository Structure

```
knowledge-collection-/
├── colab_script.txt               # Single-cell script ready to paste into Google Colab
├── colab_telegram_controller.py   # Full standalone MTProto controller script
├── requirements.txt               # Python package dependencies
├── registry.json                  # Source-of-truth local registry & SHA-256 hashes
├── COLAB_TELEGRAM_GUIDE.md        # Comprehensive visual guide & command reference
├── README.md                      # Master documentation (this file)
└── .env                           # Environment variables & credentials (local)
```

---

## 🤝 Contributing & License

Built for autonomous open-source research and continuous dataset synthesis. Pull requests, issues, and discussions are welcome!
Distributed under the **MIT License**.
