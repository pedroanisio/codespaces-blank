#!/usr/bin/env python3
"""
Playwright pipeline to process research source files.

Extracts URLs from TypeScript research-map files, visits each one,
captures metadata (title, status, description), and produces a JSON report
plus optional screenshots and failure traces.

Usage:
    python playwright_pipeline.py [OPTIONS] <file1.ts> [file2.ts ...]

Options:
    --screenshots        Save a screenshot for each URL (default: off)
    --content            Save extracted page text for each URL (default: off)
    --traces             Save a Playwright trace on failure (default: off)
    --output FILE        JSON report path (default: pipeline_report.json)
    --timeout MS         Navigation timeout in ms (default: 15000)
    --concurrency N      Parallel browser pages (default: 3)
    --retry N            Retry failed URLs N times (default: 1)
    --no-headless        Show browser window

Dependencies:
    pip install playwright
    playwright install chromium
"""

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

# Resources to block — images, fonts, media, stylesheets (speeds up ~2-3x)
_BLOCKED_TYPES = {"image", "media", "font", "stylesheet"}
_BLOCKED_PATTERNS = ["**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,mp4,mp3}"]


# ─── Data models ────────────────────────────────────────────────────────────

@dataclass
class SourceEntry:
    id: str
    title: str
    url: str
    kind: str = ""
    publisher: str = ""
    language: str = ""
    topics: list = field(default_factory=list)


@dataclass
class VerificationResult:
    id: str
    title: str
    url: str
    kind: str
    publisher: str
    status: str = "pending"       # ok | error | timeout | blocked
    http_status: int | None = None
    final_url: str = ""
    page_title: str = ""
    meta_description: str = ""
    og_title: str = ""
    canonical_url: str = ""
    redirected: bool = False
    attempts: int = 0
    screenshot_path: str = ""
    content_path: str = ""
    content_length: int = 0
    trace_path: str = ""
    error: str = ""
    checked_at: str = ""


# ─── Parser ─────────────────────────────────────────────────────────────────

def parse_source_file(path: Path) -> list[SourceEntry]:
    """Extract source entries from a TypeScript research-map file via regex."""
    text = path.read_text(encoding="utf-8")
    entries: list[SourceEntry] = []
    blocks = re.split(r'(?=\{\s*\n?\s*id\s*:\s*")', text)

    for block in blocks:
        id_m = re.search(r'id\s*:\s*"([^"]+)"', block)
        url_m = re.search(r'url\s*:\s*"([^"]+)"', block)
        if not id_m or not url_m:
            continue

        def field_val(name: str) -> str:
            m = re.search(rf'{name}\s*:\s*"([^"]+)"', block)
            return m.group(1) if m else ""

        topics_m = re.search(r'topics\s*:\s*\[([^\]]*)\]', block)
        topics = re.findall(r'"([^"]+)"', topics_m.group(1)) if topics_m else []

        entries.append(SourceEntry(
            id=id_m.group(1),
            title=field_val("title"),
            url=url_m.group(1),
            kind=field_val("kind"),
            publisher=field_val("publisher"),
            language=field_val("language"),
            topics=topics,
        ))

    return entries


def deduplicate(entries: list[SourceEntry]) -> list[SourceEntry]:
    seen: set[str] = set()
    out: list[SourceEntry] = []
    for e in entries:
        if e.url not in seen:
            seen.add(e.url)
            out.append(e)
    return out


# ─── Playwright verification ─────────────────────────────────────────────────

async def _block_resources(route):
    """Abort requests for heavy resource types to speed up page loads."""
    if route.request.resource_type in _BLOCKED_TYPES:
        await route.abort()
    else:
        await route.continue_()


_CONTENT_EXTRACTOR = """() => {
    // Priority order: semantic article tags → main → largest <div> by text length
    const candidates = [
        'article',
        '[role="main"]',
        'main',
        '.article-body', '.post-content', '.entry-content',
        '.content', '#content', '#main-content',
    ];
    for (const sel of candidates) {
        const el = document.querySelector(sel);
        if (el) {
            const t = el.innerText.trim();
            if (t.length > 200) return t;
        }
    }
    // Final fallback: full body text, stripping nav/header/footer
    ['nav','header','footer','aside','script','style'].forEach(tag => {
        document.querySelectorAll(tag).forEach(el => el.remove());
    });
    return document.body ? document.body.innerText.trim() : '';
}"""


async def _extract_meta(page) -> dict:
    """Extract description, og:title, and canonical URL from the current page."""
    return await page.evaluate("""() => {
        const q = (sel) => {
            const el = document.querySelector(sel);
            return el ? (el.getAttribute('content') || el.getAttribute('href') || '') : '';
        };
        return {
            description: q('meta[name="description"]') || q('meta[property="og:description"]'),
            og_title:    q('meta[property="og:title"]'),
            canonical:   q('link[rel="canonical"]'),
        };
    }""")


async def _save_screenshot(page, entry: SourceEntry, screenshots_dir: Path) -> str:
    """Take a screenshot and return the saved path."""
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^\w-]", "_", entry.id)
    shot_path = screenshots_dir / f"{safe_id}.png"
    await page.screenshot(path=str(shot_path), full_page=False)
    return str(shot_path)


async def _save_content(
    page, entry: SourceEntry, checked_at: str, content_dir: Path
) -> tuple[str, int]:
    """Extract page text, write it to disk, and return (path, char_count)."""
    content_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^\w-]", "_", entry.id)
    raw_text = await page.evaluate(_CONTENT_EXTRACTOR)
    header = (
        f"SOURCE ID : {entry.id}\n"
        f"TITLE     : {entry.title}\n"
        f"URL       : {entry.url}\n"
        f"PUBLISHER : {entry.publisher}\n"
        f"RETRIEVED : {checked_at}\n"
        f"{'─' * 60}\n\n"
    )
    content_path = content_dir / f"{safe_id}.txt"
    content_path.write_text(header + (raw_text or ""), encoding="utf-8")
    return str(content_path), len(raw_text or "")


async def verify_source(
    context,
    entry: SourceEntry,
    *,
    timeout: int,
    screenshots: bool,
    screenshots_dir: Path,
    content: bool,
    content_dir: Path,
    traces: bool,
    traces_dir: Path,
    retry: int,
) -> VerificationResult:
    result = VerificationResult(
        id=entry.id,
        title=entry.title,
        url=entry.url,
        kind=entry.kind,
        publisher=entry.publisher,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )

    last_exc: Exception | None = None

    for attempt in range(1, retry + 2):  # retry+1 total attempts
        result.attempts = attempt
        page = await context.new_page()
        await page.route("**/*", _block_resources)

        if traces:
            await context.tracing.start(screenshots=True, snapshots=True, sources=False)

        try:
            response = await page.goto(
                entry.url, timeout=timeout, wait_until="domcontentloaded"
            )

            result.http_status = response.status if response else None
            result.final_url = page.url
            result.redirected = page.url.rstrip("/") != entry.url.rstrip("/")
            result.page_title = await page.title()

            meta = await _extract_meta(page)
            result.meta_description = (meta.get("description") or "")[:300]
            result.og_title         = (meta.get("og_title") or "")[:200]
            result.canonical_url    = (meta.get("canonical") or "")[:300]

            result.status = "ok" if (result.http_status or 0) < 400 else "error"

            if screenshots and result.status == "ok":
                result.screenshot_path = await _save_screenshot(page, entry, screenshots_dir)

            if content and result.status == "ok":
                result.content_path, result.content_length = await _save_content(
                    page, entry, result.checked_at, content_dir
                )

            if traces:
                await context.tracing.stop()

            last_exc = None
            break  # success — exit retry loop

        except Exception as exc:
            last_exc = exc
            msg = str(exc)

            if traces:
                traces_dir.mkdir(parents=True, exist_ok=True)
                safe_id = re.sub(r"[^\w-]", "_", entry.id)
                trace_path = traces_dir / f"{safe_id}_attempt{attempt}.zip"
                await context.tracing.stop(path=str(trace_path))
                result.trace_path = str(trace_path)

            result.status = "timeout" if "timeout" in msg.lower() else "error"
            result.error = msg[:200]

        finally:
            await page.close()

        if attempt <= retry:
            await asyncio.sleep(1.5 * attempt)  # back-off before retry

    if last_exc is not None:
        result.error = str(last_exc)[:200]

    return result


# ─── Pipeline ────────────────────────────────────────────────────────────────

async def run_pipeline(
    entries: list[SourceEntry],
    *,
    timeout: int,
    concurrency: int,
    retry: int,
    screenshots: bool,
    screenshots_dir: Path,
    content: bool,
    content_dir: Path,
    traces: bool,
    traces_dir: Path,
    headless: bool,
) -> list[VerificationResult]:
    from playwright.async_api import async_playwright

    semaphore = asyncio.Semaphore(concurrency)
    total = len(entries)
    lock = asyncio.Lock()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )

        async def process(idx: int, entry: SourceEntry) -> VerificationResult:
            async with semaphore:
                async with lock:
                    print(f"  [{idx:>3}/{total}] {entry.id:<10} {entry.url[:65]}")

                r = await verify_source(
                    context, entry,
                    timeout=timeout,
                    screenshots=screenshots,
                    screenshots_dir=screenshots_dir,
                    content=content,
                    content_dir=content_dir,
                    traces=traces,
                    traces_dir=traces_dir,
                    retry=retry,
                )

                icon = {"ok": "✓", "error": "✗", "timeout": "⏱", "blocked": "⊘"}.get(r.status, "?")
                extra = f"  [retry x{r.attempts-1}]" if r.attempts > 1 else ""
                trace_note = f"  trace→{r.trace_path}" if r.trace_path else ""
                async with lock:
                    print(f"         {icon} {r.status:<8} HTTP {r.http_status}{extra}{trace_note}")

                return r

        results = list(await asyncio.gather(*[process(i + 1, e) for i, e in enumerate(entries)]))
        await context.close()
        await browser.close()

    order = {e.url: i for i, e in enumerate(entries)}
    results.sort(key=lambda r: order.get(r.url, 9999))
    return results


# ─── Report ─────────────────────────────────────────────────────────────────

def build_report(results: list[VerificationResult], source_files: list[str]) -> dict:
    by_status: dict[str, list] = {}
    for r in results:
        by_status.setdefault(r.status, []).append(r)

    ok_count = len(by_status.get("ok", []))

    # Group failures by HTTP status code
    http_errors: dict[str, int] = {}
    for r in results:
        if r.status != "ok" and r.http_status:
            key = str(r.http_status)
            http_errors[key] = http_errors.get(key, 0) + 1

    saved_content = [r for r in results if r.content_path]
    total_chars = sum(r.content_length for r in results)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": source_files,
        "summary": {
            "total": len(results),
            "ok": ok_count,
            "errors": len(by_status.get("error", [])),
            "timeouts": len(by_status.get("timeout", [])),
            "success_rate": f"{ok_count / len(results) * 100:.1f}%" if results else "N/A",
            "http_error_breakdown": http_errors,
            "content_saved": len(saved_content),
            "total_content_chars": total_chars,
        },
        "results": [asdict(r) for r in results],
        "failed": [asdict(r) for r in results if r.status != "ok"],
    }


def print_summary(report: dict) -> None:
    s = report["summary"]
    width = 60
    print("\n" + "═" * width)
    print("PIPELINE SUMMARY")
    print("═" * width)
    print(f"  Total sources : {s['total']}")
    print(f"  OK            : {s['ok']}")
    print(f"  Errors        : {s['errors']}")
    print(f"  Timeouts      : {s['timeouts']}")
    print(f"  Success rate  : {s['success_rate']}")
    if s.get("content_saved"):
        print(f"  Content saved : {s['content_saved']} files  ({s['total_content_chars']:,} chars)")

    if s["http_error_breakdown"]:
        print("\n  HTTP error breakdown:")
        for code, count in sorted(s["http_error_breakdown"].items()):
            print(f"    {code}  →  {count} source(s)")

    if report["failed"]:
        print("\nFailed sources:")
        for r in report["failed"]:
            print(f"  [{r['status'].upper():>7}] {r['id']:<10}  {r['url']}")
            if r["error"]:
                print(f"           error: {r['error'][:80]}")
            if r["trace_path"]:
                print(f"           trace: {r['trace_path']}")
    print("═" * width)
    print(f"\nView a trace:  playwright show-trace <trace.zip>")


# ─── CLI ────────────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Playwright pipeline — verify URLs in research source files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("files", nargs="+", metavar="FILE", help="TypeScript source files to process")
    p.add_argument("--screenshots", action="store_true", help="Save screenshot for each successful URL")
    p.add_argument("--screenshots-dir", default="screenshots", metavar="DIR")
    p.add_argument("--content", action="store_true", help="Save extracted page text for each successful URL")
    p.add_argument("--content-dir", default="content", metavar="DIR")
    p.add_argument("--traces", action="store_true", help="Save Playwright trace on failure")
    p.add_argument("--traces-dir", default="traces", metavar="DIR")
    p.add_argument("--output", default="pipeline_report.json", metavar="FILE")
    p.add_argument("--timeout", type=int, default=15000, metavar="MS")
    p.add_argument("--concurrency", type=int, default=3, metavar="N")
    p.add_argument("--retry", type=int, default=1, metavar="N", help="Retry failed URLs N times (default: 1)")
    p.add_argument("--no-headless", dest="headless", action="store_false")
    p.set_defaults(headless=True)
    return p


async def main_async(args) -> int:
    all_entries: list[SourceEntry] = []
    for raw in args.files:
        path = Path(raw)
        if not path.exists():
            print(f"Warning: file not found — {path}", file=sys.stderr)
            continue
        entries = parse_source_file(path)
        print(f"Parsed {len(entries)} sources from {path.name}")
        all_entries.extend(entries)

    if not all_entries:
        print("No sources found. Exiting.", file=sys.stderr)
        return 1

    all_entries = deduplicate(all_entries)
    print(f"\nTotal unique sources to verify: {len(all_entries)}")
    print(f"Concurrency: {args.concurrency}  |  Timeout: {args.timeout}ms  |  Retry: {args.retry}\n")

    results = await run_pipeline(
        all_entries,
        timeout=args.timeout,
        concurrency=args.concurrency,
        retry=args.retry,
        screenshots=args.screenshots,
        screenshots_dir=Path(args.screenshots_dir),
        content=args.content,
        content_dir=Path(args.content_dir),
        traces=args.traces,
        traces_dir=Path(args.traces_dir),
        headless=args.headless,
    )

    report = build_report(results, args.files)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved → {output_path}")

    print_summary(report)
    return 0 if report["summary"]["errors"] == 0 and report["summary"]["timeouts"] == 0 else 1


def main() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("playwright not found. Install with:\n  pip install playwright\n  playwright install chromium")
        sys.exit(1)

    parser = build_arg_parser()
    args = parser.parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
