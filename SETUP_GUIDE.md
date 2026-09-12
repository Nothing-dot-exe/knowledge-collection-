# 📖 Complete Setup & Usage Guide
### Knowledge Agent v3 — Google Colab, Telegram Topics & Multi-Account GitHub Vault

This guide provides step-by-step instructions on how to configure and run the autonomous Knowledge Agent, route content to Telegram topics, and archive clean knowledge into a **separate dedicated GitHub account**.

---

## 📑 Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Setting Up a Dedicated GitHub Storage Account](#2-setting-up-a-dedicated-github-storage-account)
3. [Setting Up Telegram Bot & Supergroup Topics](#3-setting-up-telegram-bot--supergroup-topics)
4. [Setting Up & Running in Google Colab](#4-setting-up--running-in-google-colab)
5. [Running Locally on Your Computer](#5-running-locally-on-your-computer)
6. [Troubleshooting & FAQ](#6-troubleshooting--faq)

---

## 1. Architecture Overview

Your bot can run anywhere (on your local computer or on a free Google Colab GPU) and automatically routes data across your accounts:

```
┌────────────────────────────────────────┐
│     RUNNER (Google Colab / Local PC)   │
│   • Scans arXiv & Hugging Face feeds   │
│   • Converts PDFs via Docling          │
│   • Sanitizes text (Zero Links)        │
│   • Chunks full text for fine-tuning   │
└──────────────────┬─────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐ ┌──────────────────────────────────┐
│  📱 TELEGRAM     │ │  🐙 DEDICATED GITHUB VAULT       │
│  Supergroup:     │ │  (Separate Storage Account)      │
│  • Topic 354: PDF│ │                                  │
│  • Topic 355: TXT│ │  ├── text_vault/    (Clean MD)   │
│  • Topic 356: DSET││  ├── dataset_vault/ (JSONL)      │
│  • Topic 1: ALERT│ │  └── README.md      (Master Cat) │
└──────────────────┘ └──────────────────────────────────┘
```

---

## 2. Setting Up a Dedicated GitHub Storage Account

If you want to keep your code in your main GitHub account, but store all the downloaded papers, clean text, and datasets in a **separate dedicated GitHub account**:

### Step 2.1: Create the Storage Repository
1. Log in to your **storage GitHub account**.
2. Click **New Repository** (e.g., name it `knowledge`).
3. Set visibility to **Public** or **Private** (both work).
4. Initialize with a `README.md` file.
5. Copy your repository URL (e.g. `https://github.com/Rawknowledge-database/knowledge`).

### Step 2.2: Generate a Personal Access Token (PAT)
1. On your storage account, click your profile picture (top right) $\rightarrow$ **Settings**.
2. In the left sidebar at the bottom, click **Developer settings**.
3. Click **Personal access tokens** $\rightarrow$ **Tokens (classic)**.
4. Click **Generate new token** $\rightarrow$ **Generate new token (classic)**.
5. In **Note**, enter `Knowledge Vault Bot`.
6. Set **Expiration** to `No expiration` (or 90 days).
7. Under **Select scopes**, check the box for:
   - ✅ **`repo`** *(Full control of private repositories, commits, and contents)*.
8. Click **Generate token** at the bottom.
9. **Copy the token immediately** (it looks like `ghp_xxxxxxxxxxxxxxxxxxxx`).

### Step 2.3: Configure the Bot
Update your `.env` (or Colab config):
```env
GITHUB_TOKEN=ghp_your_storage_account_token_here
GITHUB_REPO_URL=https://github.com/YourStorageAccount/knowledge
```

---

## 3. Setting Up Telegram Bot & Supergroup Topics

### Step 3.1: Create Your Telegram Bot
1. Open Telegram and search for `@BotFather`.
2. Send the command `/newbot`.
3. Give your bot a name (e.g., `Cyber Knowledge Bot`) and a username ending in `bot` (e.g., `cyber_knowledge_vault_bot`).
4. BotFather will give you an **HTTP API Token** (e.g., `8525850416:AAGtYIM...`).
5. Save this as `TELEGRAM_BOT_TOKEN`.

### Step 3.2: Create a Supergroup with Topics Enabled
1. In Telegram, create a **New Group** (e.g., `Knowledge Vault`).
2. Open **Group Settings / Edit Group**:
   - Turn **Topics / Forums** to **ON** (this enables topic threads).
3. Add your newly created Bot to the group.
4. Promote your Bot to **Administrator** with permissions to:
   - ✅ Send Messages
   - ✅ Manage Topics
   - ✅ Post Documents / Files

### Step 3.3: Create Topics & Find Their IDs
Create 3 topics inside the group:
1. `📄 Raw PDFs`
2. `📝 Clean Text`
3. `📊 Datasets`
*(The `General` topic already exists by default with ID `1`)*.

#### How to Find a Topic ID:
1. Open Telegram in your web browser: `https://web.telegram.org/a/`
2. Click on the topic (e.g., `📄 Raw PDFs`).
3. Look at your browser address bar:
   `https://web.telegram.org/a/#-1003958148223_354`
   - Group ID: `-1003958148223`
   - Topic ID: `354`
4. Repeat for the other topics to get `355` and `356`.

---

## 4. Setting Up & Running in Google Colab

Running in Google Colab gives you **free GPU acceleration** so Docling parses PDFs up to 10x faster.

### Option A: The 1-Cell Super Script (Easiest)
1. Open [Google Colab](https://colab.research.google.com/) and click **New Notebook**.
2. Enable GPU:
   - Click **Runtime** $\rightarrow$ **Change runtime type**.
   - Select **T4 GPU** $\rightarrow$ Click **Save**.
3. Open [colab_script.txt](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/colab_script.txt) in this project.
4. Copy all contents, paste into the Colab code cell.
5. Press **Shift + Enter**!

### Option B: Using the `.ipynb` Notebook
1. In Google Colab, click **File** $\rightarrow$ **Upload notebook**.
2. Choose [knowledge_agent_colab.ipynb](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/knowledge_agent_colab.ipynb) from your local project folder.
3. Run the cells sequentially:
   - **Step 1**: Installs `docling`, `PyGithub`, `requests`, `thefuzz`.
   - **Step 2**: Configures credentials safely.
   - **Step 3**: Writes the self-contained pipeline.
   - **Step 4**: Launches the 24/7 continuous autonomous loop!

### 💡 (Optional) Using Google Colab Secrets (🔑 Icon)
If you do not want your tokens visible in plain text in the notebook:
1. Click the **Key icon (Secrets)** on the left sidebar of Google Colab.
2. Add your secrets:
   - Name: `GITHUB_TOKEN` | Value: `ghp_...`
   - Name: `TELEGRAM_BOT_TOKEN` | Value: `8525850416:...`
   - Name: `HF_TOKEN` | Value: `hf_...`
3. Toggle on **Notebook access** for each secret.
4. The script automatically reads them using `_safe_get_colab_secret()`. If they are not present, it seamlessly falls back to your built-in credentials without throwing any error!

---

## 5. Running Locally on Your Computer

If you prefer running the bot on your own laptop or server:

### Step 5.1: Install Dependencies
Open PowerShell or Terminal in the project root:
```bash
pip install -r requirements.txt
```

### Step 5.2: Configure `.env`
Ensure your [.env](file:///c:/Users/kadam/OneDrive/Documents/knowledge%20bot/.env) contains your valid configuration:
```env
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_REPO_URL=https://github.com/Rawknowledge-database/knowledge
TELEGRAM_BOT_TOKEN=8525850416:AAGtYIM1sg8MF21_8lI2hOS1E-i9MosV4RE
TELEGRAM_GROUP_ID=-1003958148223

# Topic IDs
RAW_PDF_TOPIC_ID=354
TEXT_MD_TOPIC_ID=355
DATASET_TOPIC_ID=356
GENERAL_TOPIC_ID=1

ADMIN_CHAT_ID=6190001521
HF_TOKEN=hf_your_huggingface_token_here
PAPERS_PER_CATEGORY=15
```

### Step 5.3: Run the Bot
* **Run continuous 24/7 daemon loop**:
  ```bash
  python knowledge_agent.py
  ```
* **Run a single test cycle and exit**:
  ```bash
  python knowledge_agent.py --once
  ```

---

## 6. Troubleshooting & FAQ

#### Q: Why did Google Colab say `SecretNotFoundError` before?
> Colab throws this if you call `userdata.get("KEY")` and the secret is not created in Colab's 🔑 sidebar. In Knowledge Agent v3, this is now safely wrapped in a try/except function so it will never crash.

#### Q: How does the bot prevent duplicate downloads across multiple runs?
> The bot maintains a 4-layer deduplication guard:
> 1. Exact or version-stripped arXiv ID (`2609.0001v1` vs `2609.0001`)
> 2. Exact Title matching
> 3. Fuzzy Title ratio (threshold 88%)
> 4. SHA-256 PDF hash
> It syncs `registry.json` directly from your GitHub storage repo before and after every cycle.

#### Q: Where do the fine-tuning datasets go?
> Datasets are saved in `dataset_vault/KB-xxxx_dataset.jsonl` (per paper) and appended to `dataset_vault/dataset.jsonl` (master dataset). Each document is divided into ~2,000-token chunks with 120-word overlap to ensure 0% truncation during GPU training.
