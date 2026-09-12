# 🧠 Colab Telegram Agent — Interactive User Guide

A 24/7 autonomous document ingestion and dataset synthesis system powered by **Google Colab (T4 GPU)** and controlled directly from **Telegram**.

---

## 🚀 1-Click Setup in Google Colab

1. Open [Google Colab](https://colab.research.google.com) and create a **New Notebook**.
2. Set the GPU runtime:
   - Click **Runtime** -> **Change runtime type** -> select **T4 GPU** -> click **Save**.
3. Open [`colab_script.txt`](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/colab_script.txt) in this workspace.
4. Copy the entire contents of [`colab_script.txt`](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/colab_script.txt) and paste it into the first code cell in Google Colab.
5. Press **Shift + Enter** to run!

The script will automatically install all dependencies (`telethon`, `docling`, `PyGithub`, etc.), connect via MTProto, sync the GitHub registry, and announce itself in Telegram.

---

## 📡 Default Monitored Channel: [@mybooksaspdf](https://t.me/mybooksaspdf)

The bot continuously checks and listens to **@mybooksaspdf** for new incoming books and PDFs:
* **Strictly Read-Only**: The bot **NEVER deletes** any message or PDF from `@mybooksaspdf`. The source channel remains 100% untouched.
* **Strictly 1-by-1**: Each book is queued sequentially so Colab GPU memory and disk usage never overflow.
* **Dual Delivery**:
  - **Telegram**: Sends original PDF (`#354`), clean Markdown (`#355`), JSONL dataset (`#356`), and registry card (`#649`).
  - **GitHub Vault**: Commits `text_vault/`, `dataset_vault/`, `registry.json`, and `README.md` to [`Rawknowledge-database/knowledge`](https://github.com/Rawknowledge-database/knowledge).
* **Actual Book Names Everywhere**: All files are named after the actual book/document title (e.g. `Think Before You Link.md` and `Think Before You Link_dataset.jsonl`).

> [!TIP]
> **Admin Requirement for Channel Listening**: Make sure `@Automatedpush_bot` is added as an **Administrator** in `@mybooksaspdf` (with standard read/view permissions) so Telegram forwards new channel posts to the bot.

---

## 🎮 Telegram Mission Control (Topic #648)

You can send any PDF (up to **2 GB**) directly into **Topic #648** (`Upload data`).

### 1. Interactive Approval & ETA
When you drop a PDF, the bot calculates the file size and estimated time:
```
📄 [DOCUMENT RECEIVED — USER CONTROL]
File: Attention Is All You Need.pdf (2.4 MB)
⏱️ Estimated Time: ~25s (Deep SFT) / ~8s (Fast Chunks)

[ ▶️ Ingest (Deep SFT) ]   [ ⚡ Ingest (Fast Chunks) ]   [ ❌ Cancel ]
```

### 2. Live Dynamic Progress Bar
While processing, the message updates live:
```
🔄 [INGESTION IN PROGRESS]
📄 File: Attention Is All You Need.pdf -> KB-0022
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 [1/4] Download Complete ✅
⚙️ [2/4] Docling GPU OCR & Extraction... ⏳
🧠 [3/4] Dataset Synthesis ⏸️ Pending
🐙 [4/4] GitHub & Telegram Dispatch ⏸️ Pending
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ Elapsed: 7s | ETA: ~15s

[ ⏹️ Abort / Stop Processing ]
```

### 3. Telegram Commands in Topic #648
| Command | Action |
| :--- | :--- |
| `/status` | View registered documents count, queue status, and free disk space |
| `/mode` | Toggle between **Interactive** (confirm each PDF) and **Auto** (ingest on drop) |
| `/pause` | Pause the queue after current PDF finishes |
| `/resume` | Resume sequential processing |
| `/sync` | Force pull registry from GitHub and mirror to Topic #649 |
| `/help` | Show command reference |

---

## 🛡️ 4-Layer Deduplication (Zero Duplicates)

Before spending any GPU time, every incoming PDF is tested against:
1. **Binary SHA-256 Hash**: Matches against all registered papers (including the 21 existing papers).
2. **Exact Title Matching**: Normalized alphanumeric check.
3. **Fuzzy Similarity (>88%)**: Catches identical papers with slight formatting or punctuation changes.

If a match is found, the bot immediately warns you in Topic #648 and skips processing, preserving 100% vault integrity.

---

## 📌 Telegram Topic Distribution Map

| Topic ID | Topic Name | Content Delivered |
| :--- | :--- | :--- |
| **Topic 648** | `Upload data` | Interactive user control, live ETA, and progress card |
| **Topic 649** | `registry` | Live mirror of registry updates & SHA-256 hashes |
| **Topic 354** | `PDF` | Original PDF document |
| **Topic 355** | `TEXT` | Zero-link sanitized clean Markdown (`.md`) |
| **Topic 356** | `DATA SET` | Full-coverage 2K-token JSONL training dataset |
| **Topic 1** | `General` | System startup and milestone ingestion notices |

---

## 🐙 GitHub Vault Synchronization

Each completed document commits directly to [`Rawknowledge-database/knowledge`](https://github.com/Rawknowledge-database/knowledge):
- `text_vault/KB-XXXX.md`
- `dataset_vault/KB-XXXX_dataset.jsonl`
- `registry.json`
- `README.md`
