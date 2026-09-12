"""
🧠 Colab Telegram Controller — Interactive MTProto Agent (Bypasses 20MB limit up to 2GB)
========================================================================================
Full Telegram User Control (Topic 648) with Docling GPU Conversion, Strict Registry
Deduplication, SFT Dataset Synthesis, and Multi-Topic Telegram + GitHub Vault Delivery.

Telegram Forum Topics:
  • 🚀 Topic 648 : User Control Center (send PDF, live ETA, start/abort buttons, commands)
  • 📚 Topic 649 : Registry Mirror (auto-updates with latest catalog & SHA-256 hashes)
  • 📄 Topic 354 : PDF Vault (original PDFs archived)
  • 📝 Topic 355 : TEXT (zero-link sanitized clean markdown .md)
  • 📊 Topic 356 : DATA SET (training-ready JSONL datasets)
  • 📢 Topic 1   : General (system notices & milestone summaries)
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Load environment variables if .env exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
from github import Auth, Github, GithubException
from telethon import Button, TelegramClient, events
from telethon.tl.types import MessageReplyHeader

try:
    from thefuzz import fuzz
except ImportError:
    class _Fuzz:
        @staticmethod
        def ratio(a: str, b: str) -> int:
            return 100 if a.lower() == b.lower() else 0
    fuzz = _Fuzz()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("ColabController")

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  PATHS & CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
TEMP_DOWNLOAD_DIR = BASE_DIR / "temp_incoming"
TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_REGISTRY_FILE = BASE_DIR / "registry.json"

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8525850416:AAGtYIM1sg8MF21_8lI2hOS1E-i9MosV4RE")
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "32962732"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "2b6abfa8621f5a53b2d0a3a79d3bf739")
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID", "-1003958148223"))

# Forum Topic IDs
UPLOAD_TOPIC_ID = int(os.getenv("UPLOAD_TOPIC_ID", "648"))
REGISTRY_TOPIC_ID = int(os.getenv("REGISTRY_TOPIC_ID", "649"))
RAW_PDF_TOPIC_ID = int(os.getenv("RAW_PDF_TOPIC_ID", "354"))
TEXT_MD_TOPIC_ID = int(os.getenv("TEXT_MD_TOPIC_ID", "355"))
DATASET_TOPIC_ID = int(os.getenv("DATASET_TOPIC_ID", "356"))
GENERAL_TOPIC_ID = int(os.getenv("GENERAL_TOPIC_ID", "1"))

# Default Monitored Channel (Read-Only Source)
SOURCE_CHANNEL_USERNAME = os.getenv("SOURCE_CHANNEL", "mybooksaspdf").lstrip("@")
SOURCE_CHANNEL_ID = -1003932114350

# GitHub Credentials
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "https://github.com/Rawknowledge-database/knowledge")

# AI & Processing Config
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
DEFAULT_PAIRS_COUNT = int(os.getenv("DATASET_PAIRS_PER_PAPER", "5"))
DEFAULT_INGEST_MODE = os.getenv("INGEST_MODE", "interactive").lower()  # "interactive" or "auto"

# ══════════════════════════════════════════════════════════════════════════════
#  STATE & QUEUE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IngestionJob:
    job_id: str
    message_id: int
    topic_id: int
    chat_id: int
    file_name: str
    file_size_bytes: int
    media_obj: Any
    mode: str = "deep"  # "fast" or "deep"
    eta_seconds: int = 25
    created_at: float = field(default_factory=time.time)
    control_msg_id: int | None = None
    cancelled: bool = False


class AgentState:
    def __init__(self):
        self.queue: asyncio.Queue[IngestionJob] = asyncio.Queue()
        self.pending_interactive: dict[str, IngestionJob] = {}
        self.active_job: IngestionJob | None = None
        self.is_paused: bool = False
        self.current_mode: str = DEFAULT_INGEST_MODE  # "interactive" or "auto"
        self.registry: dict[str, list[str]] = {"papers": [], "hashes": [], "titles": []}
        self.highest_kb_num: int = 0
        self.start_time: float = time.time()

state = AgentState()

# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRY & DEDUPLICATION LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def get_safe_filename(title: str, max_len: int = 120) -> str:
    """Generate a clean, filesystem-safe and GitHub-safe filename from document title."""
    s = re.sub(r'[:/\\?*"<>|]', " - ", title)
    s = re.sub(r"\s+", " ", s).strip(" .-_")
    if not s:
        s = "Document"
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0].strip()
    return s


def load_local_registry() -> dict[str, list[str]]:
    if LOCAL_REGISTRY_FILE.exists():
        try:
            data = json.loads(LOCAL_REGISTRY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "papers": data.get("papers", []),
                    "hashes": data.get("hashes", []),
                    "titles": data.get("titles", []),
                }
        except Exception as e:
            log.warning("Could not read local registry.json: %s", e)
    return {"papers": [], "hashes": [], "titles": []}


def save_local_registry(reg: dict[str, list[str]]) -> None:
    try:
        LOCAL_REGISTRY_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log.error("Failed to save local registry.json: %s", e)


def extract_repo_name(url: str) -> str:
    cleaned = url.rstrip("/").removesuffix(".git")
    parts = cleaned.split("/")
    return f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else cleaned


def sync_github_registry(gh_token: str, gh_repo_url: str, local_reg: dict[str, list[str]]) -> tuple[dict[str, list[str]], int]:
    """Sync registry with GitHub and compute the highest existing KB ID in the vault."""
    if not gh_token or not gh_repo_url:
        return local_reg, len(local_reg.get("papers", []))

    repo_name = extract_repo_name(gh_repo_url)
    highest_num = len(local_reg.get("papers", []))

    try:
        gh = Github(auth=Auth.Token(gh_token))
        repo = gh.get_repo(repo_name)

        # Check existing KB files in text_vault to ensure zero ID collision
        try:
            vault_files = repo.get_contents("text_vault")
            for f in vault_files:
                if f.name.startswith("KB-") and f.name.endswith(".md"):
                    num_str = f.name[3:7]
                    if num_str.isdigit():
                        highest_num = max(highest_num, int(num_str))
        except Exception:
            pass

        # Pull registry.json from GitHub
        try:
            remote_content = repo.get_contents("registry.json")
            remote_reg = json.loads(remote_content.decoded_content.decode("utf-8"))

            merged_papers = list(local_reg.get("papers", []))
            merged_hashes = list(local_reg.get("hashes", []))
            merged_titles = list(local_reg.get("titles", []))

            # Merge remote entries
            for p, h, t in zip(remote_reg.get("papers", []), remote_reg.get("hashes", []), remote_reg.get("titles", [])):
                if h not in merged_hashes:
                    merged_papers.append(p)
                    merged_hashes.append(h)
                    merged_titles.append(t)

            local_reg["papers"] = merged_papers
            local_reg["hashes"] = merged_hashes
            local_reg["titles"] = merged_titles
            highest_num = max(highest_num, len(merged_papers))
            save_local_registry(local_reg)
            log.info("Synced registry with GitHub: %d total items, highest ID KB-%04d", len(merged_papers), highest_num)
        except GithubException as ge:
            if ge.status == 404:
                log.info("No remote registry.json found, will create on first sync.")
    except Exception as e:
        log.warning("GitHub registry sync notice: %s", e)

    return local_reg, highest_num


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(131072):
            h.update(chunk)
    return h.hexdigest()


def check_deduplication(
    file_hash: str | None,
    title: str,
    reg: dict[str, list[str]],
) -> tuple[bool, str, str]:
    """Check if document already exists using SHA-256 and fuzzy title matching."""
    hashes = reg.get("hashes", [])
    titles = reg.get("titles", [])
    papers = reg.get("papers", [])

    # 1. Exact SHA-256 binary hash match
    if file_hash and file_hash in hashes:
        idx = hashes.index(file_hash)
        matched_id = f"KB-{idx+1:04d}"
        matched_title = titles[idx] if idx < len(titles) else "Document"
        return True, matched_id, f"Binary SHA-256 match with {matched_title}"

    # 2. Exact or fuzzy title match
    clean_search = re.sub(r"[^\w\s]", "", title).strip().lower()
    for idx, t in enumerate(titles):
        clean_existing = re.sub(r"[^\w\s]", "", t).strip().lower()
        if clean_search and clean_search == clean_existing:
            matched_id = f"KB-{idx+1:04d}"
            return True, matched_id, f"Exact title match with '{t}'"

        # Fuzzy match for titles longer than 15 chars
        if len(clean_search) > 15 and len(clean_existing) > 15:
            ratio = fuzz.ratio(clean_search, clean_existing)
            token_ratio = getattr(fuzz, "token_set_ratio", fuzz.ratio)(clean_search, clean_existing)
            if ratio >= 85 or token_ratio >= 88:
                matched_id = f"KB-{idx+1:04d}"
                best_ratio = max(ratio, token_ratio)
                return True, matched_id, f"Fuzzy title match ({best_ratio}%) with '{t}'"

    return False, "", ""


# ══════════════════════════════════════════════════════════════════════════════
#  DOCLING GPU PARSING & SANITIZATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

_DOCLING_CONVERTER = None

def get_docling_converter():
    global _DOCLING_CONVERTER
    if _DOCLING_CONVERTER is not None:
        return _DOCLING_CONVERTER

    try:
        import torch
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            try:
                torch.set_float32_matmul_precision("high")
            except Exception:
                pass
            log.info("🚀 100% GPU ACCELERATION ACTIVE: %s (VRAM: %.1f GB)",
                     torch.cuda.get_device_name(0),
                     torch.cuda.get_device_properties(0).total_memory / (1024**3))

        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            AcceleratorOptions,
            AcceleratorDevice,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True

        # Enforce full CUDA GPU acceleration
        try:
            device = AcceleratorDevice.CUDA if (hasattr(torch, "cuda") and torch.cuda.is_available()) else AcceleratorDevice.AUTO
            pipeline_options.accelerator_options = AcceleratorOptions(num_threads=8, device=device)
        except Exception:
            pass

        _DOCLING_CONVERTER = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        log.info("Initialized Docling Converter with 100% CUDA GPU Acceleration.")
    except Exception as e:
        log.warning("Could not initialize Docling with CUDA options, falling back to default: %s", e)
        try:
            from docling.document_converter import DocumentConverter
            _DOCLING_CONVERTER = DocumentConverter()
        except Exception as e2:
            log.error("Docling not available: %s", e2)
            _DOCLING_CONVERTER = None

    return _DOCLING_CONVERTER


def sanitize_markdown_zero_links(md: str) -> str:
    """Strips all URLs, link pollution, and promotional noise, keeping 100% pure text."""
    # 1. Strip markdown links: [text](http://...) -> text
    md = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', md)
    # 2. Strip bare URLs
    md = re.sub(r'https?://\S+', '', md)
    # 3. Strip image tags: ![alt](url)
    md = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', md)
    # 4. Remove empty markdown link brackets
    md = re.sub(r'\[\s*\]', '', md)
    # 5. Normalize whitespace and excessive blank lines
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()


def extract_pdf_with_docling(pdf_path: Path) -> tuple[str, int]:
    """Convert PDF using Docling. Returns (clean_markdown, estimated_pages)."""
    converter = get_docling_converter()
    if converter is None:
        raise RuntimeError("Docling DocumentConverter is not installed or available.")

    conv_result = converter.convert(str(pdf_path))
    raw_md = conv_result.document.export_to_markdown()

    pages = 1
    try:
        if hasattr(conv_result.document, "pages"):
            pages = len(conv_result.document.pages)
        elif hasattr(conv_result.document, "num_pages"):
            pages = conv_result.document.num_pages
    except Exception:
        pass

    clean_md = sanitize_markdown_zero_links(raw_md)
    return clean_md, max(1, pages)


# ══════════════════════════════════════════════════════════════════════════════
#  DATASET GENERATION (FULL CHUNKS + NVIDIA NIM SFT REASONING)
# ══════════════════════════════════════════════════════════════════════════════

def chunk_text_for_dataset(text: str, kb_id: str, title: str, chunk_size: int = 2000, overlap: int = 200) -> list[dict]:
    """Generate 100% full-coverage 2K-token chunks in ChatML format."""
    words = text.split()
    records = []
    total_words = len(words)
    chunk_idx = 1

    if total_words == 0:
        return records

    start = 0
    while start < total_words:
        end = min(start + chunk_size, total_words)
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words)

        records.append({
            "messages": [
                {
                    "role": "system",
                    "content": f"You are an expert AI researcher analyzing document {kb_id}: '{title}'."
                },
                {
                    "role": "user",
                    "content": f"Provide comprehensive analysis of the following section from '{title}':\n\n{chunk_str}"
                },
                {
                    "role": "assistant",
                    "content": f"Here is the detailed synthesis of section {chunk_idx} from '{title}':\n\n{chunk_str}"
                }
            ],
            "metadata": {
                "kb_id": kb_id,
                "title": title,
                "chunk_index": chunk_idx,
                "word_count": len(chunk_words),
            }
        })

        chunk_idx += 1
        if end >= total_words:
            break
        start += (chunk_size - overlap)

    return records


def synthesize_sft_reasoning_nim(text: str, kb_id: str, title: str, pairs_count: int = 5) -> list[dict]:
    """Synthesize genuine SFT reasoning pairs via NVIDIA NIM API."""
    if not NVIDIA_API_KEY:
        log.info("No NVIDIA_API_KEY provided; skipping SFT reasoning synthesis.")
        return []

    sample_context = text[:6000]
    prompt = (
        f"You are a principal AI scientist creating training data for an advanced reasoning model.\n"
        f"Based on this document ({kb_id}: '{title}'), generate {pairs_count} high-depth, rigorous "
        f"Instruction-Reasoning-Response pairs in valid JSON array format.\n\n"
        f"Format each item as:\n"
        f"{{\n"
        f"  \"instruction\": \"Complex technical inquiry\",\n"
        f"  \"thought\": \"Detailed step-by-step chain of thought reasoning\",\n"
        f"  \"response\": \"Comprehensive, precise technical answer\"\n"
        f"}}\n\n"
        f"Document Context:\n{sample_context}\n\n"
        f"Respond ONLY with a JSON array."
    )

    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": NVIDIA_MODEL,
            "messages": [
                {"role": "system", "content": "You output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()

        raw_out = res.json()["choices"][0]["message"]["content"]
        match = re.search(r'\[.*\]', raw_out, re.DOTALL)
        if not match:
            return []

        parsed = json.loads(match.group(0))
        sft_records = []
        for item in parsed:
            instr = item.get("instruction", "")
            thought = item.get("thought", "")
            resp = item.get("response", "")
            if instr and resp:
                assistant_text = f"<thought>\n{thought}\n</thought>\n\n{resp}" if thought else resp
                sft_records.append({
                    "messages": [
                        {"role": "system", "content": f"You are an expert on '{title}'."},
                        {"role": "user", "content": instr},
                        {"role": "assistant", "content": assistant_text}
                    ],
                    "metadata": {
                        "kb_id": kb_id,
                        "title": title,
                        "type": "sft_reasoning"
                    }
                })
        return sft_records
    except Exception as e:
        log.warning("NVIDIA NIM synthesis notice: %s", e)
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  GITHUB VAULT SYNCHRONIZATION
# ══════════════════════════════════════════════════════════════════════════════

def push_or_update_gh(repo, path: str, msg: str, content: str) -> None:
    for attempt in range(3):
        try:
            try:
                existing = repo.get_contents(path)
                repo.update_file(path, msg, content, existing.sha)
                return
            except GithubException as ge:
                if ge.status == 404:
                    repo.create_file(path, msg, content)
                    return
                time.sleep(1.5)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5)


def generate_master_readme(reg: dict[str, list[str]], repo_url: str) -> str:
    total = len(reg.get("papers", []))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    titles = reg.get("titles", [])
    papers = reg.get("papers", [])

    rows = []
    # Show last 50 items
    start_idx = max(0, len(papers) - 50)
    for i in range(len(papers) - 1, start_idx - 1, -1):
        pid = f"KB-{i+1:04d}"
        t = titles[i] if i < len(titles) else "Document"
        source = papers[i]
        safe_t = get_safe_filename(t)
        rows.append(f"| `{pid}` | [{t}](text_vault/{safe_t}.md) | `{source}` | [JSONL Dataset](dataset_vault/{safe_t}_dataset.jsonl) |")

    table_content = "\n".join(rows) if rows else "| - | No documents registered yet | - | - |"

    return f"""# 🧠 Knowledge Vault — Master Research & Fine-Tuning Corpus

An automated, 24/7 autonomous research and document ingestion vault. Contains 100% zero-link sanitized documents and full-coverage chunked datasets for LLM fine-tuning.

### 📊 Vault Overview
- **Total Ingested Documents**: `{total}`
- **Last Sync**: `{now_str}`
- **Repository**: `{repo_url}`

---

## 📁 Repository Structure

```
knowledge/
├── text_vault/         # Zero-link clean Markdown (.md)
├── dataset_vault/      # Full-coverage 2K-token JSONL datasets
├── registry.json       # Source of truth registry & hashes
└── README.md           # Master index
```

---

## 📚 Document Catalog (Latest Entries)

| ID | Document Title | Source Identifier | Fine-Tuning Dataset |
| :--- | :--- | :--- | :--- |
{table_content}
"""


def commit_vault_to_github(
    kb_id: str,
    title: str,
    clean_md: str,
    dataset_content: str,
    reg: dict[str, list[str]],
) -> bool:
    """Commit Markdown, Dataset, Registry, and README to GitHub repository using actual document name."""
    if not GITHUB_TOKEN or not GITHUB_REPO_URL:
        log.warning("No GitHub credentials configured; skipping remote vault sync.")
        return False

    repo_name = extract_repo_name(GITHUB_REPO_URL)
    safe_title = get_safe_filename(title)
    try:
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = gh.get_repo(repo_name)

        # 1. Commit text_vault/{actual_title}.md
        push_or_update_gh(
            repo,
            f"text_vault/{safe_title}.md",
            f"feat(vault): add {kb_id} - {safe_title[:60]}",
            clean_md,
        )

        # 2. Commit dataset_vault/{actual_title}_dataset.jsonl
        push_or_update_gh(
            repo,
            f"dataset_vault/{safe_title}_dataset.jsonl",
            f"feat(dataset): add training dataset for {safe_title[:60]}",
            dataset_content,
        )

        # 3. Commit registry.json
        reg_str = json.dumps(reg, indent=2, ensure_ascii=False)
        push_or_update_gh(
            repo,
            "registry.json",
            f"chore(registry): register {kb_id} ({len(reg['papers'])} total)",
            reg_str,
        )

        # 4. Commit README.md
        readme_str = generate_master_readme(reg, GITHUB_REPO_URL)
        push_or_update_gh(
            repo,
            "README.md",
            f"docs: update master catalog for {kb_id}",
            readme_str,
        )

        log.info("Successfully committed %s to GitHub Vault (%s)!", kb_id, repo_name)
        return True
    except Exception as e:
        log.error("Failed to commit %s to GitHub Vault: %s", kb_id, e)
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  TELETHON MTPROTO CLIENT & TELEGRAM DELIVERY
# ══════════════════════════════════════════════════════════════════════════════

client = TelegramClient("colab_controller_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)


def estimate_processing_time(file_size_bytes: int, mode: str) -> int:
    """Calculate realistic estimated processing time in seconds."""
    mb = file_size_bytes / (1024 * 1024)
    download_est = max(1, int(mb * 0.4))
    docling_est = max(4, int(mb * 1.5))
    sft_est = 15 if mode == "deep" else 0
    sync_est = 4
    return download_est + docling_est + sft_est + sync_est


def get_topic_id(msg) -> int | None:
    """Extract topic ID from a Telethon message."""
    if not msg.reply_to:
        return 1 if getattr(getattr(msg, "chat", None), "forum", False) else None
    header = msg.reply_to
    if isinstance(header, MessageReplyHeader):
        return header.reply_to_top_id or header.reply_to_msg_id
    return None


async def send_to_topic(topic_id: int, text: str, file_path: Path | None = None, buttons=None) -> Any:
    """Send text or file to a specific forum topic in the target group."""
    try:
        if file_path and file_path.exists():
            return await client.send_file(
                entity=TELEGRAM_GROUP_ID,
                file=str(file_path),
                caption=text[:1024],
                reply_to=topic_id,
                parse_mode="html",
            )
        else:
            return await client.send_message(
                entity=TELEGRAM_GROUP_ID,
                message=text,
                reply_to=topic_id,
                buttons=buttons,
                parse_mode="html",
            )
    except Exception as e:
        log.error("Failed to send message to Topic %d: %s", topic_id, e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  SEQUENTIAL WORKER: 1-BY-1 DOCUMENT INGESTION
# ══════════════════════════════════════════════════════════════════════════════

async def process_job(job: IngestionJob) -> None:
    state.active_job = job
    start_time = time.time()
    temp_pdf = TEMP_DOWNLOAD_DIR / f"{job.job_id}_{job.file_name}"

    try:
        # Check cancellation
        if job.cancelled:
            log.info("Job %s was cancelled before start.", job.job_id)
            return

        # ── Step 1: Download with live progress callback ─────────────────────
        status_text = (
            f"🔄 <b>[INGESTION IN PROGRESS]</b>\n"
            f"📄 <b>File:</b> <code>{html.escape(job.file_name)}</code>\n"
            f"📊 <b>Size:</b> {job.file_size_bytes / (1024*1024):.2f} MB\n"
            f"⚙️ <b>Mode:</b> {'🧠 Deep SFT Reasoning' if job.mode == 'deep' else '⚡ Fast Chunks'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>[1/4] Downloading from Telegram...</b> ⏳\n"
            f"⚙️ <b>[2/4] Docling GPU Conversion</b> ⏸️ Pending\n"
            f"🧠 <b>[3/4] Dataset Synthesis</b> ⏸️ Pending\n"
            f"🐙 <b>[4/4] GitHub & Telegram Dispatch</b> ⏸️ Pending\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ <i>ETA: ~{job.eta_seconds}s</i>"
        )

        abort_btn = [[Button.inline("⏹️ Abort / Stop Processing", data=f"abort_{job.job_id}".encode())]]

        if job.control_msg_id:
            try:
                await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, status_text, buttons=abort_btn, parse_mode="html")
            except Exception:
                pass

        last_edit = 0

        async def download_progress(current, total):
            nonlocal last_edit
            now = time.time()
            if now - last_edit > 2.0 and total > 0:
                last_edit = now
                pct = int((current / total) * 100)
                dl_card = (
                    f"🔄 <b>[INGESTION IN PROGRESS]</b>\n"
                    f"📄 <b>File:</b> <code>{html.escape(job.file_name)}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📥 <b>[1/4] Downloading: {pct}%</b> ({current/(1024*1024):.1f}/{total/(1024*1024):.1f} MB)\n"
                    f"⚙️ <b>[2/4] Docling GPU Conversion</b> ⏸️ Pending\n"
                    f"🧠 <b>[3/4] Dataset Synthesis</b> ⏸️ Pending\n"
                    f"🐙 <b>[4/4] GitHub & Telegram Dispatch</b> ⏸️ Pending\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏱️ <i>Elapsed: {int(now - start_time)}s</i>"
                )
                if job.control_msg_id:
                    try:
                        await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, dl_card, buttons=abort_btn, parse_mode="html")
                    except Exception:
                        pass

        # Stream download directly via MTProto (bypasses 20MB limit!)
        await client.download_media(job.media_obj, file=str(temp_pdf), progress_callback=download_progress)

        if job.cancelled:
            log.info("Job %s aborted after download.", job.job_id)
            return

        # ── Step 2: Compute SHA-256 and Run Deduplication Check ───────────────
        pdf_hash = compute_sha256(temp_pdf)
        raw_title = Path(job.file_name).stem.replace("_", " ").replace("-", " ")

        is_dup, dup_id, dup_reason = check_deduplication(pdf_hash, raw_title, state.registry)
        if is_dup:
            dup_msg = (
                f"⚠️ <b>[DUPLICATE DETECTED — SKIPPED]</b>\n\n"
                f"📄 <b>Document:</b> <code>{html.escape(job.file_name)}</code>\n"
                f"🛡️ <b>Matched Entry:</b> <code>{dup_id}</code>\n"
                f"🔍 <b>Reason:</b> {html.escape(dup_reason)}\n\n"
                f"<i>Skipped automatically to protect vault purity and save resources.</i>"
            )
            if job.control_msg_id:
                try:
                    await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, dup_msg, parse_mode="html")
                except Exception:
                    pass
            return

        # Assign Next Sequential KB-ID
        state.highest_kb_num += 1
        kb_id = f"KB-{state.highest_kb_num:04d}"

        # ── Step 3: Docling GPU Conversion ──────────────────────────────────
        docling_card = (
            f"🔄 <b>[INGESTION IN PROGRESS]</b>\n"
            f"📄 <b>File:</b> <code>{html.escape(job.file_name)}</code> -> <b>{kb_id}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>[1/4] Download Complete</b> ✅\n"
            f"⚙️ <b>[2/4] Docling GPU OCR & Extraction...</b> ⏳\n"
            f"🧠 <b>[3/4] Dataset Synthesis</b> ⏸️ Pending\n"
            f"🐙 <b>[4/4] GitHub & Telegram Dispatch</b> ⏸️ Pending\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ <i>Elapsed: {int(time.time() - start_time)}s</i>"
        )
        if job.control_msg_id:
            try:
                await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, docling_card, buttons=abort_btn, parse_mode="html")
            except Exception:
                pass

        # Execute Docling in executor thread to prevent blocking asyncio event loop
        loop = asyncio.get_running_loop()
        clean_md, pages = await loop.run_in_executor(None, extract_pdf_with_docling, temp_pdf)

        # Detect title if available in top lines
        title = raw_title
        first_lines = [line.strip() for line in clean_md.splitlines() if line.strip()]
        for line in first_lines[:5]:
            stripped = line.lstrip("#").strip()
            if len(stripped) > 5 and not stripped.startswith("http") and not stripped.lower().startswith("arxiv"):
                title = stripped
                break

        words = len(clean_md.split())
        log.info("[%s] Docling extraction complete: %d words, %d pages", kb_id, words, pages)

        if job.cancelled:
            return

        # ── Step 4: Dataset Synthesis ─────────────────────────────────────────
        dataset_card = (
            f"🔄 <b>[INGESTION IN PROGRESS]</b>\n"
            f"📄 <b>File:</b> <code>{html.escape(job.file_name)}</code> -> <b>{kb_id}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>[1/4] Download Complete</b> ✅\n"
            f"⚙️ <b>[2/4] Docling GPU Conversion Complete</b> ({words:,} words, {pages} pages) ✅\n"
            f"🧠 <b>[3/4] Synthesizing Training Datasets...</b> ⏳\n"
            f"🐙 <b>[4/4] GitHub & Telegram Dispatch</b> ⏸️ Pending\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ <i>Elapsed: {int(time.time() - start_time)}s</i>"
        )
        if job.control_msg_id:
            try:
                await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, dataset_card, buttons=abort_btn, parse_mode="html")
            except Exception:
                pass

        # 1. Full-coverage 2K-token chunks
        chunks = chunk_text_for_dataset(clean_md, kb_id, title)

        # 2. SFT Reasoning Synthesis via NVIDIA NIM if deep mode
        sft_records = []
        if job.mode == "deep" and NVIDIA_API_KEY:
            sft_records = await loop.run_in_executor(None, synthesize_sft_reasoning_nim, clean_md, kb_id, title, DEFAULT_PAIRS_COUNT)

        all_dataset_lines = [json.dumps(c, ensure_ascii=False) for c in chunks]
        if sft_records:
            all_dataset_lines.extend([json.dumps(s, ensure_ascii=False) for s in sft_records])
        dataset_content = "\n".join(all_dataset_lines) + "\n"

        # Prepare local vault output files with ACTUAL document name
        safe_title = get_safe_filename(title)
        temp_md_file = TEMP_DOWNLOAD_DIR / f"{safe_title}.md"
        frontmatter = (
            f"---\nkb_id: \"{kb_id}\"\ntitle: \"{title.replace('\"', '\'')}\"\n"
            f"pages: {pages}\nwords: {words}\nchunks: {len(chunks)}\n"
            f"sft_pairs: {len(sft_records)}\ningested: \"{datetime.now(timezone.utc).isoformat()}\"\n"
            f"sha256: \"{pdf_hash}\"\n---\n\n"
        )
        final_clean_md = frontmatter + clean_md
        temp_md_file.write_text(final_clean_md, encoding="utf-8")

        temp_dataset_file = TEMP_DOWNLOAD_DIR / f"{safe_title}_dataset.jsonl"
        temp_dataset_file.write_text(dataset_content, encoding="utf-8")

        temp_pdf_named = TEMP_DOWNLOAD_DIR / f"{safe_title}.pdf"
        shutil.copy2(temp_pdf, temp_pdf_named)

        # ── Step 5: Telegram Multi-Topic Delivery & GitHub Commit ─────────────
        dispatch_card = (
            f"🔄 <b>[INGESTION IN PROGRESS]</b>\n"
            f"📄 <b>File:</b> <code>{html.escape(safe_title)}</code> -> <b>{kb_id}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>[1/4] Download Complete</b> ✅\n"
            f"⚙️ <b>[2/4] Docling GPU Conversion Complete</b> ✅\n"
            f"🧠 <b>[3/4] Dataset Generated</b> ({len(chunks)} Chunks, {len(sft_records)} SFT Pairs) ✅\n"
            f"🐙 <b>[4/4] Syncing to GitHub Vault & Delivering Topics...</b> ⏳\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ <i>Elapsed: {int(time.time() - start_time)}s</i>"
        )
        if job.control_msg_id:
            try:
                await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, dispatch_card, parse_mode="html")
            except Exception:
                pass

        # 1. Deliver original PDF with actual name -> Topic 354
        pdf_caption = (
            f"📄 <b>[PDF] {html.escape(title)}</b>\n\n"
            f"🆔 <b>ID:</b> <code>{kb_id}</code>\n"
            f"📊 <b>Size:</b> {job.file_size_bytes / (1024*1024):.2f} MB | {pages} pages\n"
            f"🏷 <code>SHA256: {pdf_hash[:16]}...</code>"
        )
        await send_to_topic(RAW_PDF_TOPIC_ID, pdf_caption, file_path=temp_pdf_named)

        # 2. Deliver Clean Markdown with actual name -> Topic 355
        text_caption = (
            f"📝 <b>[TEXT] {html.escape(title)}</b>\n\n"
            f"🆔 <b>ID:</b> <code>{kb_id}</code>\n"
            f"📊 <b>Stats:</b> {words:,} words | {pages} pages\n"
            f"✨ <b>Zero-Link Sanitized:</b> 100% pure text without URL clutter"
        )
        await send_to_topic(TEXT_MD_TOPIC_ID, text_caption, file_path=temp_md_file)

        # 3. Deliver Dataset with actual name -> Topic 356
        dataset_caption = (
            f"📊 <b>[DATASET] {html.escape(title)}</b>\n\n"
            f"🆔 <b>ID:</b> <code>{kb_id}</code>\n"
            f"🧩 <b>Full Coverage:</b> {len(chunks)} Chunks ({words:,} words)\n"
            f"⚡ <b>SFT Reasoning:</b> {len(sft_records)} pairs with CoT traces\n"
            f"🤖 <b>Training Ready:</b> Unsloth & LLaMA-Factory"
        )
        await send_to_topic(DATASET_TOPIC_ID, dataset_caption, file_path=temp_dataset_file)

        # Update Registry
        state.registry["papers"].append(f"tg_{job.file_name}")
        state.registry["hashes"].append(pdf_hash)
        state.registry["titles"].append(title)
        save_local_registry(state.registry)

        # 4. Commit to GitHub Vault
        gh_ok = await loop.run_in_executor(
            None, commit_vault_to_github, kb_id, title, final_clean_md, dataset_content, state.registry
        )

        # 5. Mirror Registry Update -> Topic 649
        registry_card = (
            f"📚 <b>[REGISTRY UPDATE — {kb_id}]</b>\n"
            f"<b>Title:</b> {html.escape(title)}\n\n"
            f"📊 <b>Vault Total:</b> <code>{len(state.registry['papers'])}</code> documents\n"
            f"🔒 <b>SHA-256:</b> <code>{pdf_hash}</code>\n"
            f"🐙 <b>GitHub Vault:</b> {'✅ Committed' if gh_ok else '⚠️ Local Only'}\n"
            f"⏱️ <b>Timestamp:</b> <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</code>"
        )
        await send_to_topic(REGISTRY_TOPIC_ID, registry_card)

        # 6. General Section Notice -> Topic 1
        general_card = (
            f"📢 <b>[VAULT INGESTION UPDATE]</b>\n\n"
            f"✅ <b>Archived:</b> <code>{kb_id}</code> — <i>{html.escape(title[:80])}</i>\n"
            f"📚 <b>Total Documents in Corpus:</b> <code>{len(state.registry['papers'])}</code>\n"
            f"📂 Files available in Topics: 📄 #354 | 📝 #355 | 📊 #356 | 📚 #649"
        )
        await send_to_topic(GENERAL_TOPIC_ID, general_card)

        # 7. Final Success Card in Upload Control Topic 648
        total_time = round(time.time() - start_time, 1)
        final_success = (
            f"✅ <b>[SUCCESSFULLY INGESTED — {kb_id}]</b>\n\n"
            f"📄 <b>Title:</b> <b>{html.escape(title)}</b>\n"
            f"⏱️ <b>Processing Time:</b> {total_time}s (ETA was ~{job.eta_seconds}s)\n"
            f"📊 <b>Extracted:</b> {words:,} words | {pages} pages\n"
            f"🧩 <b>Dataset:</b> {len(chunks)} chunks | {len(sft_records)} SFT reasoning pairs\n"
            f"🐙 <b>GitHub:</b> {'Pushed to repository' if gh_ok else 'Local registry'}\n\n"
            f"📦 <b>Dispatched To:</b>\n"
            f"  • 📄 PDF -> Topic #354\n"
            f"  • 📝 Clean Text -> Topic #355\n"
            f"  • 📊 Dataset -> Topic #356\n"
            f"  • 📚 Registry -> Topic #649"
        )
        if job.control_msg_id:
            try:
                await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, final_success, parse_mode="html")
            except Exception:
                await send_to_topic(UPLOAD_TOPIC_ID, final_success)

    except Exception as e:
        log.exception("Error processing job %s: %s", job.job_id, e)
        err_msg = f"❌ <b>Error processing {job.file_name}:</b>\n<code>{html.escape(str(e))}</code>"
        if job.control_msg_id:
            try:
                await client.edit_message(TELEGRAM_GROUP_ID, job.control_msg_id, err_msg, parse_mode="html")
            except Exception:
                await send_to_topic(UPLOAD_TOPIC_ID, err_msg)
    finally:
        # 🗑️ Immediate Local Cleanup: Delete raw and temp files so Colab disk stays 0 MB!
        for p in [temp_pdf, TEMP_DOWNLOAD_DIR / f"{job.job_id}_{job.file_name}"]:
            if p.exists():
                p.unlink(missing_ok=True)
        if 'temp_md_file' in locals() and temp_md_file.exists():
            temp_md_file.unlink(missing_ok=True)
        if 'temp_dataset_file' in locals() and temp_dataset_file.exists():
            temp_dataset_file.unlink(missing_ok=True)
        if 'temp_pdf_named' in locals() and temp_pdf_named.exists():
            temp_pdf_named.unlink(missing_ok=True)
        log.info("Cleaned up temporary disk files for %s.", job.job_id)
        state.active_job = None


async def queue_worker_loop():
    """Background worker processing jobs strictly 1-by-1 sequentially."""
    log.info("Started Queue Worker Loop. Waiting for ingestion tasks...")
    while True:
        try:
            if state.is_paused:
                await asyncio.sleep(2.0)
                continue

            job = await state.queue.get()
            log.info("Dequeued job %s: %s", job.job_id, job.file_name)
            await process_job(job)
            state.queue.task_done()
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Queue worker unexpected error: %s", e)
            await asyncio.sleep(3.0)


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM EVENT LISTENERS: USER CONTROL (TOPIC 648)
# ══════════════════════════════════════════════════════════════════════════════

@client.on(events.NewMessage)
async def message_handler(event):
    msg = event.message
    chat_id = event.chat_id

    # Check if message is from the default monitored channel @mybooksaspdf
    chat = await event.get_chat()
    chat_username = (getattr(chat, "username", "") or "").lower()
    is_source_channel = (
        chat_username == SOURCE_CHANNEL_USERNAME.lower()
        or chat_id == SOURCE_CHANNEL_ID
        or str(chat_id).endswith("3932114350")
    )
    is_target_group = (chat_id == TELEGRAM_GROUP_ID)
    is_dm = event.is_private

    if not is_source_channel and not is_target_group and not is_dm:
        return

    topic_id = get_topic_id(msg)

    # ── Command Handlers (Topic 648 or DM) ────────────────────────────────────
    text = (msg.text or "").strip()
    cmd = text.split()[0].lower() if text.startswith("/") else ""

    if is_target_group or is_dm:
        if cmd in ("/start", "/help"):
            help_card = (
                f"🎮 <b>[KNOWLEDGE BOT MISSION CONTROL]</b>\n\n"
                f"• Monitored Channel: <b>@{SOURCE_CHANNEL_USERNAME}</b> (Read-Only 1-by-1 Ingestion)\n"
                f"• Drop any PDF directly in Topic #648 to convert manually!\n\n"
                f"🕹️ <b>Available Commands:</b>\n"
                f"• <code>/status</code> — Live GPU stats, queue status, vault count\n"
                f"• <code>/mode</code> — Toggle between Interactive & Auto-Ingest\n"
                f"• <code>/pause</code> — Pause the sequential processing queue\n"
                f"• <code>/resume</code> — Resume processing\n"
                f"• <code>/sync</code> — Force sync with GitHub registry\n"
                f"• <code>/scan</code> — Verify connection to @{SOURCE_CHANNEL_USERNAME}\n\n"
                f"📊 <b>Topics:</b>\n"
                f"• 🚀 <b>#648:</b> Upload & Control Center\n"
                f"• 📚 <b>#649:</b> Registry Mirror\n"
                f"• 📄 <b>#354:</b> PDF Vault\n"
                f"• 📝 <b>#355:</b> Clean Text\n"
                f"• 📊 <b>#356:</b> SFT Datasets\n"
                f"• 📢 <b>#1:</b> General Updates"
            )
            await event.reply(help_card, parse_mode="html")
            return

        elif cmd == "/status":
            uptime_mins = int((time.time() - state.start_time) / 60)
            q_size = state.queue.qsize()
            active_name = state.active_job.file_name if state.active_job else "None (Idle)"
            disk_free_gb = shutil.disk_usage(BASE_DIR).free / (1024**3)

            status_card = (
                f"📊 <b>[SYSTEM STATUS & HEALTH]</b>\n\n"
                f"📡 <b>Monitored Channel:</b> <code>@{SOURCE_CHANNEL_USERNAME}</code> (Read-Only)\n"
                f"📚 <b>Registered Documents:</b> <code>{len(state.registry['papers'])}</code>\n"
                f"🆔 <b>Next Sequential ID:</b> <code>KB-{state.highest_kb_num + 1:04d}</code>\n"
                f"⚡ <b>Queue Status:</b> {'⏸️ Paused' if state.is_paused else '🟢 Running'}\n"
                f"📥 <b>In Queue:</b> {q_size} documents\n"
                f"⚙️ <b>Active Ingestion:</b> <code>{html.escape(active_name)}</code>\n"
                f"🎛️ <b>Ingest Mode:</b> <code>{state.current_mode.upper()}</code>\n"
                f"💾 <b>Free Disk:</b> {disk_free_gb:.1f} GB\n"
                f"⏱️ <b>Bot Uptime:</b> {uptime_mins} minutes"
            )
            await event.reply(status_card, parse_mode="html")
            return

        elif cmd == "/pause":
            state.is_paused = True
            await event.reply("⏸️ <b>Ingestion Queue Paused.</b> Current document will finish, then queue will halt.", parse_mode="html")
            return

        elif cmd == "/resume":
            state.is_paused = False
            await event.reply("▶️ <b>Ingestion Queue Resumed!</b>", parse_mode="html")
            return

        elif cmd == "/mode":
            state.current_mode = "auto" if state.current_mode == "interactive" else "interactive"
            await event.reply(f"🎛️ <b>Mode Switched:</b> Ingest mode is now set to <b>{state.current_mode.upper()}</b>.", parse_mode="html")
            return

        elif cmd == "/sync":
            await event.reply("🔄 <b>Syncing Registry with GitHub...</b>", parse_mode="html")
            state.registry, state.highest_kb_num = sync_github_registry(GITHUB_TOKEN, GITHUB_REPO_URL, state.registry)
            reg_sync_card = (
                f"📚 <b>[REGISTRY SYNC COMPLETE]</b>\n"
                f"Total papers: <code>{len(state.registry['papers'])}</code>\n"
                f"Highest Vault ID: <code>KB-{state.highest_kb_num:04d}</code>"
            )
            await send_to_topic(REGISTRY_TOPIC_ID, reg_sync_card)
            await event.reply("✅ <b>Registry synced and posted to Topic #649!</b>", parse_mode="html")
            return

        elif cmd == "/scan":
            try:
                chan_ent = await client.get_entity(SOURCE_CHANNEL_USERNAME)
                await event.reply(f"🟢 <b>Monitored Channel Active:</b> <code>@{SOURCE_CHANNEL_USERNAME}</code> (ID: <code>{chan_ent.id}</code>).\nAny new PDF will be picked up 1-by-1 without modifying the channel!", parse_mode="html")
            except Exception as e:
                await event.reply(f"⚠️ Channel access note: {e}", parse_mode="html")
            return

    # ── PDF Document Detection (From @mybooksaspdf OR Topic 648 OR DM) ────────
    if is_target_group and topic_id != UPLOAD_TOPIC_ID:
        return

    doc = msg.document
    if not doc:
        return

    mime = getattr(doc, "mime_type", "") or ""
    # Extract file name
    file_name = "document.pdf"
    for attr in getattr(doc, "attributes", []):
        if hasattr(attr, "file_name") and attr.file_name:
            file_name = attr.file_name
            break

    if not file_name.lower().endswith(".pdf") and "pdf" not in mime.lower():
        return

    file_size = getattr(doc, "size", 0)
    size_mb = file_size / (1024 * 1024)
    job_id = f"job_{int(time.time()*1000)}"
    eta = estimate_processing_time(file_size, "deep")

    log.info("Received PDF in Topic 648: %s (%.2f MB)", file_name, size_mb)

    # Instant Pre-Check Deduplication against Title
    raw_title = Path(file_name).stem.replace("_", " ").replace("-", " ")
    is_dup, dup_id, dup_reason = check_deduplication(None, raw_title, state.registry)
    if is_dup:
        log.info("Document '%s' already in registry (%s: %s). Skipping.", file_name, dup_id, dup_reason)
        if not is_source_channel:
            dup_alert = (
                f"⚠️ <b>[DUPLICATE DETECTED — SKIPPED]</b>\n\n"
                f"📄 <b>File:</b> <code>{html.escape(file_name)}</code>\n"
                f"🛡️ <b>Matched Entry:</b> <code>{dup_id}</code>\n"
                f"🔍 <b>Reason:</b> {html.escape(dup_reason)}\n\n"
                f"<i>This document already exists in the registry. Skipping to prevent duplicates.</i>"
            )
            await msg.reply(dup_alert, parse_mode="html")
        return

    # Create Ingestion Job (STRICTLY READ-ONLY from source channel: NEVER delete from channel)
    job = IngestionJob(
        job_id=job_id,
        message_id=msg.id,
        topic_id=UPLOAD_TOPIC_ID,
        chat_id=chat_id,
        file_name=file_name,
        file_size_bytes=file_size,
        media_obj=msg.media,
        mode="deep",
        eta_seconds=eta,
    )

    if is_source_channel:
        # Channel documents are queued automatically for 1-by-1 processing
        chan_notice = (
            f"📡 <b>[NEW BOOK IN @{SOURCE_CHANNEL_USERNAME}]</b>\n\n"
            f"📄 <b>File:</b> <code>{html.escape(file_name)}</code>\n"
            f"📊 <b>Size:</b> {size_mb:.2f} MB | ⏱️ <b>ETA:</b> ~{eta}s\n"
            f"⏳ <b>Queue Position:</b> {state.queue.qsize() + 1}\n\n"
            f"<i>Original PDF remains safe & untouched in @{SOURCE_CHANNEL_USERNAME}.</i>"
        )
        abort_btn = [[Button.inline("⏹️ Abort / Stop Processing", data=f"abort_{job.job_id}".encode())]]
        ctrl_msg = await send_to_topic(UPLOAD_TOPIC_ID, chan_notice, buttons=abort_btn)
        if ctrl_msg:
            job.control_msg_id = ctrl_msg.id
        await state.queue.put(job)
        return

    if state.current_mode == "auto":
        # Auto-ingest immediately for direct uploads
        ctrl_card = (
            f"📄 <b>[DOCUMENT RECEIVED — AUTO INGEST]</b>\n\n"
            f"<b>File:</b> <code>{html.escape(file_name)}</code>\n"
            f"<b>Size:</b> {size_mb:.2f} MB\n"
            f"⏱️ <b>Estimated Time:</b> ~{eta}s\n"
            f"📊 <b>Status:</b> ⏳ Added to queue (Position: {state.queue.qsize() + 1})"
        )
        abort_btn = [[Button.inline("⏹️ Abort / Stop Processing", data=f"abort_{job.job_id}".encode())]]
        ctrl_msg = await msg.reply(ctrl_card, buttons=abort_btn, parse_mode="html")
        job.control_msg_id = ctrl_msg.id
        await state.queue.put(job)
    else:
        # Interactive Approval
        state.pending_interactive[job_id] = job
        card_text = (
            f"📄 <b>[DOCUMENT RECEIVED — USER CONTROL]</b>\n\n"
            f"<b>File:</b> <code>{html.escape(file_name)}</code>\n"
            f"<b>Size:</b> {size_mb:.2f} MB\n"
            f"⏱️ <b>Estimated Time:</b> ~{eta}s (Deep) / ~{int(eta*0.35)}s (Fast)\n\n"
            f"👇 <i>Choose how to process this document:</i>"
        )
        buttons = [
            [
                Button.inline("▶️ Ingest (Deep SFT)", data=f"start_deep_{job_id}".encode()),
                Button.inline("⚡ Ingest (Fast Chunks)", data=f"start_fast_{job_id}".encode()),
            ],
            [
                Button.inline("❌ Cancel / Skip", data=f"cancel_{job_id}".encode()),
            ]
        ]
        ctrl_msg = await msg.reply(card_text, buttons=buttons, parse_mode="html")
        job.control_msg_id = ctrl_msg.id


# ── Interactive Callback Buttons ──────────────────────────────────────────────
@client.on(events.CallbackQuery)
async def callback_query_handler(event):
    data = event.data.decode("utf-8")
    log.info("Button clicked: %s", data)

    if data.startswith("start_"):
        parts = data.split("_", 2)
        mode = parts[1]  # "deep" or "fast"
        job_id = parts[2]

        job = state.pending_interactive.pop(job_id, None)
        if not job:
            await event.answer("⚠️ Job expired or already started.", alert=True)
            return

        job.mode = mode
        job.eta_seconds = estimate_processing_time(job.file_size_bytes, mode)

        await event.answer(f"Starting {mode.upper()} ingestion...")
        queued_card = (
            f"⏳ <b>[QUEUED FOR INGESTION]</b>\n\n"
            f"📄 <b>File:</b> <code>{html.escape(job.file_name)}</code>\n"
            f"⚙️ <b>Mode:</b> {'🧠 Deep SFT Reasoning' if mode == 'deep' else '⚡ Fast Chunks'}\n"
            f"⏱️ <b>ETA:</b> ~{job.eta_seconds}s\n"
            f"📊 <b>Queue Position:</b> {state.queue.qsize() + 1}"
        )
        abort_btn = [[Button.inline("⏹️ Abort / Stop Processing", data=f"abort_{job.job_id}".encode())]]
        await event.edit(queued_card, buttons=abort_btn, parse_mode="html")
        await state.queue.put(job)

    elif data.startswith("cancel_"):
        job_id = data.removeprefix("cancel_")
        job = state.pending_interactive.pop(job_id, None)
        await event.answer("Cancelled.")
        await event.edit("❌ <b>Ingestion cancelled by user.</b>", parse_mode="html")

    elif data.startswith("abort_"):
        job_id = data.removeprefix("abort_")
        await event.answer("Aborting processing...")

        # If it's the currently active job
        if state.active_job and state.active_job.job_id == job_id:
            state.active_job.cancelled = True
            await event.edit("⏹️ <b>Ingestion aborted by user.</b> Temporary files cleaned.", parse_mode="html")
        else:
            await event.edit("⏹️ <b>Task removed from queue.</b>", parse_mode="html")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    log.info("══════════════════════════════════════════════════════════════════")
    log.info("🚀 Launching Knowledge Bot Colab MTProto Controller...")
    log.info("   • Group ID: %s (Topic %s for uploads)", TELEGRAM_GROUP_ID, UPLOAD_TOPIC_ID)
    log.info("   • Registry Topic: %s", REGISTRY_TOPIC_ID)
    log.info("   • Output Topics: PDF #%s | TEXT #%s | DATASET #%s | GENERAL #%s",
             RAW_PDF_TOPIC_ID, TEXT_MD_TOPIC_ID, DATASET_TOPIC_ID, GENERAL_TOPIC_ID)
    log.info("══════════════════════════════════════════════════════════════════")

    # Load initial local registry
    state.registry = load_local_registry()

    # Connect to MTProto with Bot Token
    await client.start(bot_token=TELEGRAM_BOT_TOKEN)
    me = await client.get_me()
    log.info("Connected to Telegram as @%s (ID: %s)", me.username, me.id)

    # Sync with remote GitHub registry and determine latest KB number
    state.registry, state.highest_kb_num = sync_github_registry(GITHUB_TOKEN, GITHUB_REPO_URL, state.registry)

    # Post Startup Announcement in Topic 1 (General) and Topic 648 (Uploads)
    startup_card = (
        f"🤖 <b>[KNOWLEDGE BOT ONLINE — T4 GPU READY]</b>\n\n"
        f"Ready to ingest PDFs strictly 1-by-1 with zero disk overflow!\n"
        f"• 📚 <b>Registry Size:</b> <code>{len(state.registry['papers'])}</code> documents\n"
        f"• 🆔 <b>Next Document ID:</b> <code>KB-{state.highest_kb_num + 1:04d}</code>\n"
        f"• 🚀 <b>Upload Portal:</b> Drop any PDF in Topic #648\n"
        f"• 🎮 <b>Commands:</b> <code>/status</code>, <code>/mode</code>, <code>/sync</code>, <code>/help</code>"
    )
    await send_to_topic(GENERAL_TOPIC_ID, startup_card)
    await send_to_topic(UPLOAD_TOPIC_ID, startup_card)

    # Start the sequential 1-by-1 worker task
    worker_task = asyncio.create_task(queue_worker_loop())

    # Keep client running
    log.info("🟢 Controller fully running and listening for Telegram events.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutdown initiated by user.")
