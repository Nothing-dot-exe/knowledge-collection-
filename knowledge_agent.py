"""
Knowledge Agent — High-Performance Zero-Cost RAG Ingestion Pipeline
Fetches arXiv PDFs → Deduplicates (Air-Tight Multi-Layer) → Fast Docling Conversion
→ Routes to Telegram Topics with Inline Buttons → Syncs to GitHub → Logs Everything.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Auto-install missing packages in Google Colab / Fresh environments ─────────
for _mod, _pkg in [("arxiv", "arxiv"), ("docling", "docling"), ("github", "PyGithub"), ("thefuzz", "thefuzz"), ("requests", "requests")]:
    try:
        __import__(_mod)
    except ImportError:
        print(f"📦 Auto-installing missing package '{_pkg}' in environment...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", _pkg])

import arxiv
import requests
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from github import Github, GithubException, Auth
from thefuzz import fuzz

# ── Paths & Colab / Jupyter Safe Root ──────────────────────────────────────────
try:
    ROOT = Path(__file__).parent
except NameError:
    ROOT = Path.cwd()

MD_DIR = ROOT / "markdown_files"
PDF_DIR = ROOT / "raw_pdfs"
REGISTRY = ROOT / "registry.json"
LOG_DIR = ROOT / "logs"

MD_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── Logging Setup (with Colab/IPython force=True) ──────────────────────────────
log_file = LOG_DIR / f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    force=True,
)
log = logging.getLogger(__name__)

# Mute noisy internal loggers to keep output clean
for noisy in ["MatchingPostProcessor", "docling", "docling.pipeline", "urllib3", "arxiv", "github"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)


def status(msg: str, *args) -> None:
    """Print directly to terminal/Colab with flush=True so logs are never hidden."""
    formatted = msg % args if args else msg
    print(formatted, flush=True)
    log.info(formatted)
TECH_CURRICULUM = [
    # Coding, Advanced Algorithms & LeetCode
    ("💻 Advanced Coding & Algorithms", "cat:cs.DS OR cat:cs.PL"),
    ("🛠 Software Eng & Git Architecture", "cat:cs.SE"),
    # Linux, Servers, Cloud & Infrastructure
    ("🐧 Linux & Operating Systems", "cat:cs.OS"),
    ("☁ Cloud, Servers & Distributed Systems", "cat:cs.DC"),
    ("🌐 Networks, Web & Protocols", "cat:cs.NI OR cat:cs.IR"),
    # Cybersecurity & Cryptography
    ("🛡 Cybersecurity & Exploits", "cat:cs.CR"),
    # AI, LLMs, Vision & Machine Learning
    ("🤖 AI & Language Models (LLMs)", "cat:cs.AI OR cat:cs.CL"),
    ("🧠 Machine Learning & Deep Learning", "cat:cs.LG OR cat:stat.ML"),
    ("👁 Computer Vision & Multimodal", "cat:cs.CV"),
    # Mathematics & Theoretical Foundations
    ("📐 Mathematics & Computation", "cat:math.CO OR cat:math.ST OR cat:math.PR"),
]
ARXIV_CATEGORIES = [query for _, query in TECH_CURRICULUM]
PAPERS_PER_CATEGORY = int(os.environ.get("PAPERS_PER_CATEGORY", "15"))
FUZZY_THRESHOLD = 88
MIN_MD_CHARS = 400

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


# ── Registry helpers ──────────────────────────────────────────────────────────
def load_registry() -> dict:
    if REGISTRY.exists():
        try:
            return json.loads(REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            return {"papers": [], "hashes": [], "titles": []}
    return {"papers": [], "hashes": [], "titles": []}


def save_registry(reg: dict) -> None:
    REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def sync_remote_registry(gh_token: str, repo_url: str, local_reg: dict) -> dict:
    """Pull the latest remote registry from GitHub so documents are NEVER re-downloaded even across machines."""
    try:
        repo_name = re.sub(r"https?://github\.com/", "", repo_url).rstrip("/").removesuffix(".git")
        g = Github(auth=Auth.Token(gh_token))
        repo = g.get_repo(repo_name)
        remote_file = repo.get_contents("registry.json")
        remote_reg = json.loads(remote_file.decoded_content.decode("utf-8"))
        merged = {
            "papers": list(dict.fromkeys(local_reg.get("papers", []) + remote_reg.get("papers", []))),
            "hashes": list(dict.fromkeys(local_reg.get("hashes", []) + remote_reg.get("hashes", []))),
            "titles": list(dict.fromkeys(local_reg.get("titles", []) + remote_reg.get("titles", []))),
        }
        save_registry(merged)
        status("🔄 Registry synced with GitHub vault: %d existing papers known", len(merged["papers"]))
        return merged
    except Exception as e:
        status("⚠️ Could not sync remote registry from GitHub: %s. Using local.", e)
        return local_reg


# ── Strict 4-Layer Deduplication Guard ────────────────────────────────────────
def clean_str(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9 ]", "", s.lower()).strip()


def strip_arxiv_version(aid: str) -> str:
    """Normalize '2609.04199v1' -> '2609.04199' to prevent version duplicates."""
    return re.sub(r"v\d+$", "", aid.strip())


base_arxiv_id = strip_arxiv_version


def is_duplicate(arxiv_id: str, title: str, pdf_hash: str | None, reg: dict) -> str | None:
    """Bulletproof duplicate check:
    Layer 1: Exact or version-stripped arXiv ID
    Layer 2: Exact normalized title match
    Layer 3: High-similarity fuzzy title match
    Layer 4: SHA-256 PDF hash match
    """
    known_papers = reg.get("papers", [])
    known_titles = reg.get("titles", [])
    known_hashes = reg.get("hashes", [])

    # Layer 1 — arXiv ID & Base ID
    curr_base = base_arxiv_id(arxiv_id)
    for p in known_papers:
        if p == arxiv_id or base_arxiv_id(p) == curr_base:
            return f"Layer-1: arXiv ID '{arxiv_id}' matches existing '{p}'"

    # Layer 2 — Exact normalized title match
    clean_title = clean_str(title)
    clean_known = [clean_str(t) for t in known_titles]
    if clean_title in clean_known:
        idx = clean_known.index(clean_title)
        return f"Layer-2: Title matches exactly with '{known_titles[idx]}'"

    # Layer 3 — Fuzzy title match
    for existing_title in known_titles:
        score = fuzz.ratio(clean_title, clean_str(existing_title))
        if score >= FUZZY_THRESHOLD:
            return f"Layer-3: Title fuzzy match {score}% vs '{existing_title}'"

    # Layer 4 — PDF content SHA-256 hash
    if pdf_hash and pdf_hash in known_hashes:
        return f"Layer-4: Exact PDF SHA-256 ({pdf_hash[:12]}…) already in registry"

    return None


# ── PDF Download (Streaming + Direct with Retry) ──────────────────────────────
def download_pdf(paper: arxiv.Result, dest_dir: Path, max_retries: int = 3) -> tuple[Path, str]:
    """Stream download PDF and compute SHA-256 hash on the fly with retry logic."""
    safe_id = paper.get_short_id().replace("/", "_")
    pdf_path = dest_dir / f"{safe_id}.pdf"

    pdf_url = getattr(paper, "pdf_url", None) or f"https://arxiv.org/pdf/{paper.get_short_id()}.pdf"

    for attempt in range(max_retries):
        hasher = hashlib.sha256()
        try:
            with requests.get(pdf_url, headers={"User-Agent": "KnowledgeBot/2.0"}, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(pdf_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
            sha256 = hasher.hexdigest()
            return pdf_path, sha256
        except Exception as exc:
            if pdf_path.exists():
                pdf_path.unlink(missing_ok=True)
            if attempt < max_retries - 1:
                wait_sec = 3.0 * (attempt + 1)
                log.warning("PDF download retry %d/%d for %s (waiting %.1fs): %s", attempt + 1, max_retries, safe_id, wait_sec, exc)
                time.sleep(wait_sec)
            else:
                raise exc


# ── Fast Docling Conversion Engine ────────────────────────────────────────────
_converter: DocumentConverter | None = None


def get_converter() -> DocumentConverter:
    """Initialize fast zero-OCR Docling converter once and reuse in memory."""
    global _converter
    if _converter is None:
        log.info("Initializing fast Docling pipeline (zero-OCR digital mode)...")
        pipeline_options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
        _converter = DocumentConverter(
            format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
        )
    return _converter


def convert_to_markdown(pdf_path: Path) -> tuple[str, int, int]:
    """Convert PDF to structured Markdown using fast cached Docling engine."""
    converter = get_converter()
    result = converter.convert(str(pdf_path))
    md_text = result.document.export_to_markdown()

    word_count = len(md_text.split())
    try:
        page_count = len(result.document.pages)
    except Exception:
        page_count = max(1, word_count // 300)

    return md_text, word_count, page_count


def knowledge_score(word_count: int, page_count: int) -> float:
    return (word_count / 100) + (page_count * 10)


# ── Code Repository & Multi-Source Helpers ─────────────────────────────────────
def extract_code_repo(paper: arxiv.Result, md_text: str = "") -> str | None:
    """Scan paper comment, summary, and markdown text for official GitHub code repository."""
    search_space = f"{getattr(paper, 'comment', '') or ''} {paper.summary or ''} {md_text[:3000]}"
    matches = re.findall(r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", search_space)

    # Filter out generic/framework libraries
    ignored = {"docling", "pytorch", "huggingface", "tensorflow", "keras", "numpy", "scipy", "docling-project"}
    for m in matches:
        clean_m = m.rstrip("/").removesuffix(".git")
        parts = clean_m.split("/")
        if len(parts) == 2 and parts[0].lower() not in ignored and parts[1].lower() not in ignored:
            return f"https://github.com/{clean_m}"
    return None


def fetch_huggingface_trending(limit: int = 15) -> tuple[list[str], dict[str, dict]]:
    """Fetch top trending AI research papers from Hugging Face Daily Papers.
    Returns (list of arxiv_ids, metadata_dict keyed by stripped arxiv_id).
    """
    arxiv_ids = []
    meta = {}
    try:
        r = requests.get("https://huggingface.co/api/daily_papers", timeout=10)
        if r.status_code == 200:
            for item in r.json()[:limit]:
                paper_info = item.get("paper", {})
                raw_id = paper_info.get("id")
                if not raw_id:
                    continue
                base_id = strip_arxiv_version(raw_id)
                arxiv_ids.append(base_id)
                meta[base_id] = {
                    "code_repo": paper_info.get("githubRepo"),
                    "stars": paper_info.get("githubStars"),
                    "upvotes": paper_info.get("upvotes"),
                }
    except Exception as e:
        log.warning("Could not fetch Hugging Face trending papers: %s", e)
    return arxiv_ids, meta


# ── Rich Telegram Helpers ─────────────────────────────────────────────────────
def build_metadata_card(
    paper: arxiv.Result,
    kb_id: str,
    score: float,
    topic_badge: str = "Technology & Science",
    code_url: str | None = None,
    stars: int | None = None,
    upvotes: int | None = None,
) -> str:
    """Generate safe, sanitized HTML metadata card with abstract preview, code repo, and stars."""
    safe_title = html.escape(paper.title.strip().replace("\n", " "))
    cats = html.escape(", ".join(str(c) for c in paper.categories))
    authors = html.escape(", ".join(a.name for a in paper.authors[:3]))
    if len(paper.authors) > 3:
        authors += " et al."

    abstract = paper.summary.strip().replace("\n", " ")
    if len(abstract) > 320:
        abstract = abstract[:315] + "…"
    safe_abstract = html.escape(abstract)

    pub_date = paper.published.strftime("%Y-%m-%d") if paper.published else "Recent"

    meta_line = f"🆔 <code>{kb_id}</code> | 🧠 Score: <b>{score:.1f}</b>"
    if upvotes is not None and upvotes > 0:
        meta_line += f" | 🔥 <b>{upvotes}</b> upvotes"

    card = (
        f"📄 <b>{safe_title}</b>\n"
        f"{meta_line}\n\n"
        f"🏷 <b>Track:</b> {topic_badge}\n"
        f"👥 <i>{authors}</i> ({pub_date})\n"
        f"🗂 <code>{cats}</code>\n\n"
        f"📝 <b>Abstract:</b>\n{safe_abstract}"
    )
    if code_url:
        star_badge = f" ({stars} ⭐)" if stars else ""
        card += f"\n\n⭐ <b>Source Code{star_badge}:</b> <a href='{code_url}'>{code_url}</a>"
    return card


def build_inline_keyboard(
    paper: arxiv.Result,
    github_url: str | None = None,
    code_url: str | None = None,
) -> dict:
    """Build interactive action buttons including direct code link."""
    row1 = [
        {"text": "📖 Read on arXiv", "url": paper.entry_id},
        {"text": "📥 Direct PDF", "url": getattr(paper, "pdf_url", paper.entry_id)},
    ]
    row2 = []
    if code_url:
        row2.append({"text": "⭐ Source Code", "url": code_url})
    if github_url:
        row2.append({"text": "🐙 Vault Repo", "url": github_url})

    keyboard = [row1]
    if row2:
        keyboard.append(row2)
    return {"inline_keyboard": keyboard}


def tg_send_doc(
    token: str,
    chat_id: str,
    file_path: Path,
    caption: str,
    reply_markup: dict | None = None,
    **kwargs,
) -> requests.Response:
    url = TELEGRAM_API.format(token=token, method="sendDocument")
    if "message_thread_id" in kwargs and kwargs["message_thread_id"]:
        kwargs["message_thread_id"] = int(kwargs["message_thread_id"])

    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML", **kwargs}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    with open(file_path, "rb") as f:
        # Explicit filename tuple prevents Windows path formatting issues
        files = {"document": (file_path.name, f, "application/octet-stream")}
        r = requests.post(url, data=data, files=files, timeout=90)

    r.raise_for_status()
    return r


def tg_send(token: str, chat_id: str, text: str, **kwargs) -> requests.Response:
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    if "message_thread_id" in kwargs and kwargs["message_thread_id"]:
        kwargs["message_thread_id"] = int(kwargs["message_thread_id"])
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", **kwargs}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r


# ── GitHub Save ───────────────────────────────────────────────────────────────
def push_or_update(repo, file_path: str, commit_msg: str, content: str) -> None:
    """Safely create or update file with 404 check and sha-conflict retry."""
    for attempt in range(3):
        try:
            try:
                existing = repo.get_contents(file_path)
                repo.update_file(file_path, commit_msg, content, existing.sha)
                return
            except GithubException as ge:
                if ge.status == 404:
                    repo.create_file(file_path, commit_msg, content)
                    return
                # If not 404, file exists; wait and retry re-fetching sha
                time.sleep(1.5)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5)


def github_save(gh_token: str, repo_url: str, kb_id: str, md_text: str, reg: dict) -> None:
    """Push markdown and registry update to GitHub safely."""
    from github import Auth
    repo_name = re.sub(r"https?://github\.com/", "", repo_url).rstrip("/").removesuffix(".git")
    auth = Auth.Token(gh_token)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    md_path = f"markdown_files/{kb_id}.md"
    reg_path = "registry.json"
    commit_msg = f"[{kb_id}] Ingest paper into Knowledge Base"

    # Push markdown file
    push_or_update(repo, md_path, commit_msg, md_text)

    # Push registry update
    reg_content = json.dumps(reg, indent=2)
    push_or_update(repo, reg_path, commit_msg, reg_content)

    log.info("GitHub: Pushed %s and updated registry.json", md_path)


# ── ID Generator ──────────────────────────────────────────────────────────────
def next_kb_id(reg: dict) -> str:
    n = len(reg.get("papers", [])) + 1
    return f"KB-{n:04d}"


# ── Safe arXiv Fetcher with Exponential Backoff ──────────────────────────────
def safe_arxiv_results(
    client: arxiv.Client,
    search: arxiv.Search,
    max_retries: int = 5,
    backoff_seconds: float = 12.0,
) -> list[arxiv.Result]:
    """Execute search query with robust exponential backoff on HTTP 429/503 rate limits."""
    for attempt in range(max_retries):
        try:
            return list(client.results(search))
        except (arxiv.HTTPError, arxiv.UnexpectedEmptyPageError, requests.exceptions.RequestException) as exc:
            is_rate_limit = False
            status_code = getattr(exc, "status", None)
            if status_code in (429, 503):
                is_rate_limit = True
            elif "429" in str(exc) or "503" in str(exc):
                is_rate_limit = True

            if attempt < max_retries - 1:
                wait_time = backoff_seconds * (2 ** attempt)  # 12s, 24s, 48s, 96s
                err_label = f"HTTP {status_code} Rate Limit" if is_rate_limit else "Transient Network/API Error"
                status("  ⚠️ ArXiv %s encountered (%s). Pausing for %.0fs cooldown before retry %d/%d...",
                       err_label, str(exc).split("\n")[0][:120], wait_time, attempt + 1, max_retries)
                time.sleep(wait_time)
            else:
                status("  ❌ ArXiv track search aborted after %d retries: %s", max_retries, exc)
                return []
        except Exception as general_exc:
            status("  ❌ Unexpected error during arXiv query: %s", general_exc)
            return []
    return []


# ── Main Pipeline Runner ──────────────────────────────────────────────────────
def run(env: dict) -> dict:
    token = env["TELEGRAM_BOT_TOKEN"]
    group_id = env["TELEGRAM_GROUP_ID"]
    raw_topic = int(env["RAW_PDF_TOPIC_ID"])
    md_topic = int(env["TEXT_MD_TOPIC_ID"])
    admin_id = env["ADMIN_CHAT_ID"]
    gh_token = env["GITHUB_TOKEN"]
    gh_repo = env["GITHUB_REPO_URL"]

    # 1. Sync registry from GitHub first to ensure global deduplication
    reg = load_registry()
    reg = sync_remote_registry(gh_token, gh_repo, reg)

    stats = {"scanned": 0, "skipped": 0, "added": 0, "errors": 0}
    start_time = time.time()

    papers_per_cat = int(env.get("PAPERS_PER_CATEGORY", PAPERS_PER_CATEGORY))
    status("==================================================")
    status("🚀 Starting Knowledge Ingestion Pipeline (batch size: %d/track)...", papers_per_cat)
    status("==================================================")

    # 2. Build multi-source batches: HF Trending + arXiv Categories
    search_batches = []
    hf_meta: dict[str, dict] = {}

    status("🔥 Querying Hugging Face Daily Trending Papers...")
    hf_ids, hf_meta = fetch_huggingface_trending(limit=15)
    if hf_ids:
        candidate_hf_ids = [hid for hid in hf_ids if hid not in reg.get("papers", [])]
        if candidate_hf_ids:
            status("  Found %d new candidate papers on Hugging Face Trending", len(candidate_hf_ids))
            search_batches.append(("🔥 Hugging Face Trending", arxiv.Search(id_list=candidate_hf_ids)))
        else:
            status("  All %d HF trending papers already in registry!", len(hf_ids))

    for track_name, query in TECH_CURRICULUM:
        search_batches.append((
            track_name,
            arxiv.Search(
                query=query,
                max_results=papers_per_cat,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            ),
        ))

    # delay_seconds=3.5 strictly satisfies arXiv's requirement of >=3.0s per request
    client = arxiv.Client(page_size=papers_per_cat, delay_seconds=3.5, num_retries=3)

    for batch_name, search in search_batches:
        status("\n📚 Scanning track: %s", batch_name)
        papers = safe_arxiv_results(client, search)
        if not papers:
            status("  ℹ️ No new papers retrieved for this track (empty or rate-limited).")
            continue

        for paper in papers:
            stats["scanned"] += 1
            arxiv_id = paper.get_short_id()
            base_id = strip_arxiv_version(arxiv_id)
            status("  🔍 [%s] %s", arxiv_id, paper.title[:65])

            # Pre-download Check (Layers 1, 2, 3)
            dup_reason = is_duplicate(arxiv_id, paper.title, None, reg)
            if dup_reason:
                status("    ⏭ SKIP (Pre-download): %s", dup_reason)
                stats["skipped"] += 1
                continue

            pdf_path: Path | None = None
            pdf_hash: str | None = None
            try:
                # Fast Download
                t_dl = time.time()
                pdf_path, pdf_hash = download_pdf(paper, PDF_DIR)
                status("    ⬇ Downloaded in %.1fs (%d bytes)", time.time() - t_dl, pdf_path.stat().st_size)

                # Post-download Check (Layer 4 - Exact content hash)
                dup_reason = is_duplicate(arxiv_id, paper.title, pdf_hash, reg)
                if dup_reason:
                    status("    ⏭ SKIP (Hash duplicate): %s", dup_reason)
                    stats["skipped"] += 1
                    pdf_path.unlink(missing_ok=True)
                    continue

                # Fast Docling Conversion
                t_conv = time.time()
                status("    ⚡ Converting PDF with Docling engine...")
                md_text, word_count, page_count = convert_to_markdown(pdf_path)
                conv_duration = time.time() - t_conv

                if len(md_text) < MIN_MD_CHARS:
                    status("    ⏭ SKIP: Markdown too short (%d chars)", len(md_text))
                    stats["skipped"] += 1
                    pdf_path.unlink(missing_ok=True)
                    continue

                status("    ⚡ Converted in %.1fs (%d words, %d pages)", conv_duration, word_count, page_count)

                # Extract Code Repository & Trending Stats
                hf_info = hf_meta.get(base_id, {})
                code_url = hf_info.get("code_repo") or extract_code_repo(paper, md_text)
                stars = hf_info.get("stars")
                upvotes = hf_info.get("upvotes")

                score = knowledge_score(word_count, page_count)
                kb_id = next_kb_id(reg)
                md_path = MD_DIR / f"{kb_id}.md"
                md_path.write_text(md_text, encoding="utf-8")

                card = build_metadata_card(
                    paper, kb_id, score,
                    topic_badge=batch_name,
                    code_url=code_url,
                    stars=stars,
                    upvotes=upvotes,
                )
                keyboard = build_inline_keyboard(paper, gh_repo, code_url=code_url)

                # Send to Telegram (Topic 10: PDF, Topic 11: MD)
                status("    📤 Delivering to Telegram (Topics %d & %d)...", raw_topic, md_topic)
                tg_send_doc(token, group_id, pdf_path, card, reply_markup=keyboard, message_thread_id=raw_topic)
                tg_send_doc(token, group_id, md_path, card, reply_markup=keyboard, message_thread_id=md_topic)

                # Push to GitHub & Save Registry Atomically
                status("    🐙 Archiving %s to GitHub Vault...", kb_id)
                reg["papers"].append(base_id)
                reg["hashes"].append(pdf_hash)
                reg["titles"].append(paper.title)
                github_save(gh_token, gh_repo, kb_id, md_text, reg)
                save_registry(reg)

                stats["added"] += 1
                status("    ✅ SUCCESS: %s added to knowledge base! (Code: %s)", kb_id, code_url or "None")

            except Exception as exc:
                stats["errors"] += 1
                status("    ❌ ERROR on %s: %s", arxiv_id, exc)
                # Rollback tentative registry additions
                if base_id in reg.get("papers", []):
                    reg["papers"].remove(base_id)
                elif arxiv_id in reg.get("papers", []):
                    reg["papers"].remove(arxiv_id)
                if pdf_hash and pdf_hash in reg.get("hashes", []):
                    reg["hashes"].remove(pdf_hash)
                if paper.title in reg.get("titles", []):
                    reg["titles"].remove(paper.title)
            finally:
                if pdf_path and pdf_path.exists():
                    pdf_path.unlink()

        # Inter-track spacing to respect arXiv rate limits
        time.sleep(1.5)

    total_time = round(time.time() - start_time)
    status("==================================================")
    status("🎉 Batch Complete in %ds: %s", total_time, stats)
    status("==================================================")

    # Admin Alert (Silent DM)
    summary = (
        f"🤖 <b>Knowledge Agent Run Complete</b>\n"
        f"⏱ Duration: <b>{total_time}s</b>\n\n"
        f"📊 <b>Stats:</b>\n"
        f"  • Scanned: {stats['scanned']}\n"
        f"  • Added: {stats['added']}\n"
        f"  • Skipped (Duplicates): {stats['skipped']}\n"
        f"  • Errors: {stats['errors']}"
    )
    try:
        tg_send(token, admin_id, summary, disable_notification=True)
    except Exception as e:
        log.warning("Admin alert failed: %s", e)

    log.info("=== Run Complete in %ds: %s ===", total_time, stats)
    return stats


# ── Default Configuration (Credentials loaded from Environment / .env) ──────
DEFAULT_CONFIG = {
    "GITHUB_TOKEN": "",
    "GITHUB_REPO_URL": "https://github.com/Nothing-dot-exe/arxiv-paper-scraper",
    "TELEGRAM_BOT_TOKEN": "",
    "TELEGRAM_GROUP_ID": "-1003958148223",
    "RAW_PDF_TOPIC_ID": "10",
    "TEXT_MD_TOPIC_ID": "11",
    "ADMIN_CHAT_ID": "",
    "PAPERS_PER_CATEGORY": "15",
}


def prompt_env() -> dict:
    env_file = ROOT / ".env"
    file_cfg = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                file_cfg[k.strip()] = v.strip().strip("'\"")

    env = {}
    for k, default_v in DEFAULT_CONFIG.items():
        val = os.environ.get(k, "").strip() or str(file_cfg.get(k, "")).strip() or default_v
        env[k] = val
    return env


if __name__ == "__main__":
    collected_env = prompt_env()
    try:
        run(collected_env)
    except KeyboardInterrupt:
        print("\n🛑 Pipeline paused by user. Clean exit.")
