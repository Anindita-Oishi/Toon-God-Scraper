#!/usr/bin/env python3
r"""
toongod_crawler.py
==================

Downloads every chapter of a webcomic series from toongod.org into the project
directory and, optionally, turns the chapters into PDFs: one PDF per chapter
and/or one combined PDF containing the whole series, bookmarked per chapter.

Intended for personal, permitted use. Keep the downloaded files for your own
reading.

CONTENTS
    1. Requirements and installation
    2. Quick start
    3. Getting past Cloudflare (read this before the first run)
    4. Command-line options
    5. Output layout
    6. Resuming, retries and politeness
    7. Troubleshooting
    8. Adapting the script if the site layout changes


1. REQUIREMENTS AND INSTALLATION
--------------------------------
    - Python 3.9 or newer (developed and tested with 3.12).
    - Google Chrome (recommended; used for the Cloudflare step in section 3).

    Install the packages into the same interpreter/venv that runs the script.
    In PyCharm, use the Terminal tab (it activates the project's .venv):

        pip install playwright img2pdf pillow pikepdf
        playwright install chromium

    What each package does:
        playwright   required. Drives the browser and downloads the images.
        img2pdf      for --pdf / --merge. Builds chapter PDFs without re-encoding
                     the images (lossless, fast).
        pillow       fallback PDF builder for formats img2pdf cannot embed.
        pikepdf      recommended for --merge. Streams pages from disk, so memory
                     stays low on long series. If it is missing, the script falls
                     back to pypdf (pip install pypdf), which loads everything
                     into memory.

    "playwright install chromium" is needed for the default launch mode. It is
    harmless to run even if you only use --cdp-url (recommended, see section 3).


2. QUICK START
--------------
    Run it with the series URL as the first argument:

        python toongod_crawler.py https://www.toongod.org/webtoon/switch-on-uncensored/ ^
            --cdp-url http://127.0.0.1:9222 --pdf --merge

    (Put it on one line; "^" is the Windows cmd line-continuation character.)

    In PyCharm: Run > Edit Configurations > select this script > Parameters:

        https://www.toongod.org/webtoon/switch-on-uncensored/ --cdp-url http://127.0.0.1:9222 --pdf --merge

    If you start the script without a URL (for example with the plain Run
    button and an empty Parameters field), it asks for one in the console.

    Before the first run, do the one-time Cloudflare step in section 3.


3. GETTING PAST CLOUDFLARE (READ THIS BEFORE THE FIRST RUN)
-----------------------------------------------------------
    The site shows a "Verify you are human" check. Browsers that are launched
    by automation tools expose automation signals, so the check fails or loops
    forever, even if you click the box yourself.

    The reliable workaround is to pass the check yourself in a normal Chrome
    window and let the script attach to that window.

    Step 1 - Start a separate Chrome with a debugging port and its own profile
    folder. Do this once per session (leave the window open afterwards).

        Windows PowerShell (the "&" is required in PowerShell):
            & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-cdp-profile"

        Windows cmd, or the Win+R dialog:
            "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-cdp-profile"

        macOS (Terminal):
            /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"

        Linux:
            google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"

        Notes:
            - --user-data-dir is mandatory. Recent Chrome versions ignore the
              debugging port when the default profile is used.
            - If Chrome is installed elsewhere (for example under
              "Program Files (x86)" or %LOCALAPPDATA%), adjust the path.

    Step 2 - In that Chrome window, open the series URL and complete the
    verification by hand. Wait until the series page (with its chapter list)
    is visible, then leave the window open.

    Step 3 (optional) - Confirm the port is live: open
    http://127.0.0.1:9222/json/version in that window. It should show JSON.

    Step 4 - Run the script with --cdp-url http://127.0.0.1:9222
    The URL must start with http://, NOT https:// (the debugging port does not
    speak TLS; https:// fails with "ECONNRESET ... before secure TLS connection
    was established").

    While running, the script opens its own tab in that Chrome window and closes
    it when it is done. Your Chrome window stays open. Closing the debugging
    Chrome window while the script runs makes the script fail.

    Other launch modes (less reliable against Cloudflare):
        (no flag)         Launches Playwright's Chromium with a persistent profile
                          in ./.browser_profile next to this script. If a
                          challenge appears, solve it in the window.
        --channel chrome  Same, but launches your installed Chrome.
        --headless        Hides the window. Cloudflare usually blocks this.


4. COMMAND-LINE OPTIONS
-----------------------
    url                  Series URL, for example
                         https://www.toongod.org/webtoon/switch-on-uncensored/
                         (asked for interactively if omitted)
    --out DIR            Output root. Default: the folder containing this script.
    --start N            First chapter number to download (1-based). Default: 1.
    --end N              Last chapter number to download. Default: 0 = all.
                         Chapter numbers are positions in the site's chapter
                         list, oldest first (1 = first chapter). They can differ
                         from the numbers in chapter titles (specials, "12.5").
    --concurrency N      Images downloaded in parallel. Default: 6.
                         Lower it if you see errors or rate limiting.
    --pdf                Build one PDF per chapter.
    --merge              Also build one combined PDF with every completed chapter
                         in the --start/--end range, in order, with a bookmark per
                         chapter. Works without --pdf: missing chapter PDFs are
                         created and kept.
    --cdp-url URL        Attach to your own Chrome, for example
                         http://127.0.0.1:9222 (see section 3).
    --channel NAME       Launch an installed browser instead of bundled Chromium,
                         for example "chrome". Ignored with --cdp-url.
    --headless           Run without a visible window. Ignored with --cdp-url.

    Examples:
        Everything, with per-chapter and combined PDFs:
            <url> --cdp-url http://127.0.0.1:9222 --pdf --merge
        Only chapters 5 to 12, no PDFs:
            <url> --cdp-url http://127.0.0.1:9222 --start 5 --end 12
        Only a combined PDF for chapters 1-20, saved to another folder:
            <url> --cdp-url http://127.0.0.1:9222 --end 20 --merge --out D:\Comics


5. OUTPUT LAYOUT
----------------
    <out>/<series-slug>/
        chapter-001/
            001.jpg, 002.jpg, ...          images in reading order
            .done                          marker: chapter fully downloaded
        chapter-001.pdf                    with --pdf (or created by --merge)
        <series-slug>_ch001-NNN.pdf        with --merge: the whole range

    <series-slug> is the last part of the series URL (for example
    "switch-on-uncensored"). The images keep their original format (.jpg,
    .png, .webp, ...). In the PDFs, every image becomes one page.


6. RESUMING, RETRIES AND POLITENESS
-----------------------------------
    - Chapters that have a .done marker are skipped, so you can stop the script
      and rerun the same command to continue.
    - If any image of a chapter fails, the chapter gets no .done marker and the
      failures are printed. Rerun the same command to retry only those chapters.
    - Each image is tried up to 5 times, waiting 0.5 * 2^attempt + U(0, 1)
      seconds between attempts (exponential backoff with jitter).
    - At most --concurrency images are downloaded at once, with a pause of
      1.0 - 2.5 seconds between chapters.
    - --merge only includes completed chapters and reuses existing chapter
      PDFs. If you re-download a chapter's images, delete its chapter-NNN.pdf so
      it is rebuilt.
    - Check the site's robots.txt and keep the delays/concurrency modest.


7. TROUBLESHOOTING
------------------
    "error: the following arguments are required: url"
        Older versions of the script. Pass the URL in the Parameters field, or
        use the current version, which asks for it.

    "Client network socket disconnected before secure TLS connection was
    established (ECONNRESET)"
        --cdp-url was given as https://... Use http://127.0.0.1:9222.

    "connect ECONNREFUSED 127.0.0.1:9222" or a timeout
        The debugging Chrome is not running, was started without
        --user-data-dir, or uses a different port. Close that Chrome window and
        start it again with the exact command from section 3.

    The Cloudflare check loops or never finishes
        Do not use the launch modes; use the --cdp-url workflow (section 3).
        If it still loops in your own Chrome, turn off VPNs, proxies and
        ad-blocking extensions in that window.

    "No chapters found" or "no images found"
        Make sure the series/chapter page finished loading and is not showing a
        challenge. If it did load, the page structure differs from what the
        script expects: see section 8.

    HTTP 403 when downloading images
        Images are downloaded with Playwright's request client. It shares the
        browser's cookies but not the browser's own network fingerprint, so an
        image host may reject it. Open one image URL in the debugging Chrome to
        check; a browser-side download would be needed in that case.

    Some chapters are incomplete
        Rerun the same command (see section 6).

    A PDF fails on certain images
        img2pdf cannot embed some formats; the script then falls back to Pillow,
        which must be able to read the format (WebP works, AVIF may not).

    --merge uses a lot of memory or is slow
        Install pikepdf (pip install pikepdf). Without it, the pypdf fallback
        keeps everything in memory.


8. ADAPTING THE SCRIPT IF THE SITE LAYOUT CHANGES
-------------------------------------------------
    The selectors in the SELECTORS section below assume the WordPress "Madara"
    manga theme:

        CHAPTER_LINK_SELECTOR  links to chapters on the series page
        IMAGE_SELECTOR         page images on a chapter page

    The chapter list is read from the series page; if it is empty there, the
    script requests <series-url>/ajax/chapters/ (how Madara loads it). Image
    addresses are read from data-src, data-lazy-src or src.

    To find new selectors: open the page in Chrome, press F12, use the element
    picker on a chapter link or a comic image, and copy a CSS selector that
    matches all of them.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import BrowserContext, Page, async_playwright

# ----------------------------------------------------------------------------
# SELECTORS (adjust if the site layout differs)
# ----------------------------------------------------------------------------
CHAPTER_LINK_SELECTOR = "li.wp-manga-chapter > a"
IMAGE_SELECTOR = ".reading-content img"

JS_CHAPTERS_FROM_DOM = f"""
() => [...document.querySelectorAll('{CHAPTER_LINK_SELECTOR}')].map(a => a.href)
"""

# Madara loads the chapter list via AJAX: POST <series-url>/ajax/chapters/
JS_CHAPTERS_FROM_AJAX = f"""
async (url) => {{
  const r = await fetch(url, {{
    method: 'POST',
    credentials: 'include',
    headers: {{'X-Requested-With': 'XMLHttpRequest'}},
  }});
  const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
  return [...doc.querySelectorAll('{CHAPTER_LINK_SELECTOR}')].map(a => a.href);
}}
"""

JS_IMAGES = f"""
() => [...document.querySelectorAll('{IMAGE_SELECTOR}')]
  .map(i => (i.dataset.src || i.dataset.lazySrc || i.getAttribute('src') || '').trim())
  .filter(u => u && !u.startsWith('data:'))
"""

JS_AUTOSCROLL = """
async () => {
  await new Promise(resolve => {
    let y = 0;
    const timer = setInterval(() => {
      window.scrollBy(0, 900);
      y += 900;
      if (y >= document.body.scrollHeight) { clearInterval(timer); resolve(); }
    }, 120);
  });
}
"""

CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}
DONE_MARKER = ".done"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
async def wait_for_cloudflare(page: Page, timeout: float = 180.0) -> None:
    """Block until the Cloudflare interstitial is gone (solve it manually if shown)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    announced = False
    while loop.time() < deadline:
        try:
            title = (await page.title()).lower()
        except Exception:  # page is navigating
            await asyncio.sleep(1)
            continue
        if "just a moment" not in title and "attention required" not in title:
            return
        if not announced:
            print("Cloudflare challenge detected - complete it in the browser window...")
            announced = True
        await asyncio.sleep(1.5)
    raise TimeoutError("Cloudflare challenge was not completed in time.")


async def open_page(page: Page, url: str) -> None:
    await page.goto(url, wait_until="domcontentloaded")
    await wait_for_cloudflare(page)


def dedupe(items: list[str]) -> list[str]:
    """Order-preserving de-duplication (dict keys keep insertion order)."""
    return list(dict.fromkeys(items))


async def get_chapter_urls(page: Page, series_url: str) -> list[str]:
    await open_page(page, series_url)
    links = await page.evaluate(JS_CHAPTERS_FROM_DOM)
    if not links:
        ajax_url = urljoin(series_url.rstrip("/") + "/", "ajax/chapters/")
        links = await page.evaluate(JS_CHAPTERS_FROM_AJAX, ajax_url)
    links = dedupe(links)
    links.reverse()  # site lists newest first; we want chapter 1 first
    return links


async def get_image_urls(page: Page, chapter_url: str) -> list[str]:
    await open_page(page, chapter_url)
    try:
        await page.wait_for_selector(IMAGE_SELECTOR, timeout=30_000)
    except Exception:
        return []
    await page.evaluate(JS_AUTOSCROLL)  # triggers lazy-loaded images as a fallback
    urls = await page.evaluate(JS_IMAGES)
    return dedupe([urljoin(chapter_url, u) for u in urls])


def guess_extension(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return CONTENT_TYPE_EXT.get(content_type.split(";")[0].strip().lower(), ".jpg")


async def download_image(
    ctx: BrowserContext,
    url: str,
    dest_stem: Path,
    referer: str,
    sem: asyncio.Semaphore,
    retries: int = 5,
) -> Path:
    """Download one image with exponential backoff + jitter."""
    async with sem:
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                resp = await ctx.request.get(url, headers={"Referer": referer}, timeout=60_000)
                if not resp.ok:
                    raise RuntimeError(f"HTTP {resp.status}")
                body = await resp.body()
                ext = guess_extension(url, resp.headers.get("content-type", ""))
                dest = dest_stem.with_suffix(ext)
                dest.write_bytes(body)
                return dest
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                # delay = base * 2^attempt + uniform(0, 1)
                await asyncio.sleep(0.5 * 2**attempt + random.random())
        raise RuntimeError(f"Failed after {retries} attempts: {url} ({last_error})")


def natural_key(path: Path) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path.name)]


def build_pdf(chapter_dir: Path) -> Path | None:
    images = sorted(
        (p for p in chapter_dir.iterdir() if p.suffix.lower() in CONTENT_TYPE_EXT.values()),
        key=natural_key,
    )
    if not images:
        return None
    pdf_path = chapter_dir.with_suffix(".pdf")
    try:
        import img2pdf  # lossless: embeds JPEG/PNG streams without re-encoding

        pdf_path.write_bytes(img2pdf.convert([str(p) for p in images]))
    except Exception:
        from PIL import Image  # fallback: re-encodes, handles WebP/alpha

        pages = [Image.open(p).convert("RGB") for p in images]
        pages[0].save(pdf_path, save_all=True, append_images=pages[1:])
    return pdf_path


def merge_pdfs(chapter_pdfs: list[tuple[int, Path]], dest: Path) -> None:
    """Merge per-chapter PDFs (in the given order) into one PDF with a bookmark per chapter."""
    try:
        import pikepdf  # streams page data from disk, so memory stays low on big series
    except ImportError:
        pikepdf = None

    if pikepdf is not None:
        merged = pikepdf.Pdf.new()
        sources, starts = [], []
        for number, path in chapter_pdfs:
            src = pikepdf.Pdf.open(path)
            sources.append(src)  # must stay open until save()
            starts.append((number, len(merged.pages)))
            merged.pages.extend(src.pages)
        with merged.open_outline() as outline:
            for number, page_index in starts:
                outline.root.append(pikepdf.OutlineItem(f"Chapter {number}", page_index))
        merged.save(dest)
        for src in sources:
            src.close()
    else:
        from pypdf import PdfWriter  # pure-Python fallback (loads everything into memory)

        writer = PdfWriter()
        for number, path in chapter_pdfs:
            writer.append(str(path), outline_item=f"Chapter {number}")
        with open(dest, "wb") as fh:
            writer.write(fh)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
async def run(args: argparse.Namespace) -> None:
    series_url = args.url.rstrip("/") + "/"
    slug = [s for s in urlparse(series_url).path.split("/") if s][-1]
    out_root = Path(args.out) / slug
    out_root.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(__file__).resolve().parent / ".browser_profile"

    async with async_playwright() as pw:
        browser = None
        if args.cdp_url:
            # Attach to a normal Chrome you started yourself with --remote-debugging-port.
            browser = await pw.chromium.connect_over_cdp(args.cdp_url)
            ctx = browser.contexts[0]
            page = await ctx.new_page()
        else:
            launch_kwargs = {"channel": args.channel} if args.channel else {}
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=args.headless,
                viewport={"width": 1280, "height": 900},
                **launch_kwargs,
            )
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        chapters = await get_chapter_urls(page, series_url)
        if not chapters:
            sys.exit("No chapters found - check CHAPTER_LINK_SELECTOR for this site.")
        print(f"Found {len(chapters)} chapters.")

        end = args.end or len(chapters)
        selected = list(enumerate(chapters, start=1))[args.start - 1 : end]
        sem = asyncio.Semaphore(args.concurrency)

        for number, chapter_url in selected:
            chapter_dir = out_root / f"chapter-{number:03d}"
            if (chapter_dir / DONE_MARKER).exists():
                print(f"[{number:03d}] already downloaded, skipping")
                continue
            chapter_dir.mkdir(exist_ok=True)

            image_urls = await get_image_urls(page, chapter_url)
            if not image_urls:
                print(f"[{number:03d}] no images found at {chapter_url}")
                continue

            width = max(3, len(str(len(image_urls))))
            tasks = [
                download_image(ctx, url, chapter_dir / f"{i:0{width}d}", chapter_url, sem)
                for i, url in enumerate(image_urls, start=1)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failures = [r for r in results if isinstance(r, Exception)]
            for err in failures:
                print(f"  ! {err}")

            if failures:
                print(f"[{number:03d}] {len(failures)} image(s) failed; rerun to retry")
                continue

            (chapter_dir / DONE_MARKER).touch()
            print(f"[{number:03d}] saved {len(image_urls)} images -> {chapter_dir}")

            if args.pdf:
                pdf = build_pdf(chapter_dir)
                if pdf:
                    print(f"[{number:03d}] PDF -> {pdf}")

            await asyncio.sleep(random.uniform(1.0, 2.5))  # polite delay between chapters

        if browser is not None:
            await page.close()  # only close our own tab; leave your Chrome running
            await browser.close()  # disconnects from the CDP session
        else:
            await ctx.close()

    if args.merge:
        numbers = [n for n, _ in selected]
        chapter_pdfs: list[tuple[int, Path]] = []
        incomplete: list[int] = []
        for n in numbers:
            chapter_dir = out_root / f"chapter-{n:03d}"
            if not (chapter_dir / DONE_MARKER).exists():
                incomplete.append(n)
                continue
            pdf = chapter_dir.with_suffix(".pdf")
            if not pdf.exists():
                pdf = build_pdf(chapter_dir)
            if pdf:
                chapter_pdfs.append((n, pdf))
        if incomplete:
            print(f"Merge: skipping incomplete chapters {incomplete} (rerun to retry them)")
        if chapter_pdfs:
            dest = out_root / f"{slug}_ch{chapter_pdfs[0][0]:03d}-{chapter_pdfs[-1][0]:03d}.pdf"
            merge_pdfs(chapter_pdfs, dest)
            print(f"Merged {len(chapter_pdfs)} chapters -> {dest}")
        else:
            print("Merge: nothing to merge.")


def normalize_cdp_url(value: str) -> str:
    """Accept '9222', '127.0.0.1:9222' or a full URL; force http:// for local endpoints.

    Chrome's DevTools port speaks plain HTTP/WebSocket. An https:// URL makes the TLS
    handshake fail with ECONNRESET.
    """
    value = value.strip()
    if not value:
        return value
    if value.isdigit():
        value = f"127.0.0.1:{value}"
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        value = "http://" + value[len("https://"):]
    return value


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Download all chapters of a series.")
    ap.add_argument("url", nargs="?", help="Series URL, e.g. https://www.toongod.org/webtoon/switch-on-uncensored/")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent), help="Output root (default: project directory)")
    ap.add_argument("--start", type=int, default=1, help="First chapter number (1-based)")
    ap.add_argument("--end", type=int, default=0, help="Last chapter number (default: all)")
    ap.add_argument("--concurrency", type=int, default=6, help="Parallel image downloads")
    ap.add_argument("--pdf", action="store_true", help="Build one PDF per chapter")
    ap.add_argument("--merge", action="store_true", help="Also build one combined PDF with every chapter in order")
    ap.add_argument("--headless", action="store_true", help="Hide the browser (Cloudflare usually blocks this)")
    ap.add_argument("--cdp-url", default="", help="Attach to your own Chrome, e.g. http://127.0.0.1:9222")
    ap.add_argument("--channel", default="", help="Launch an installed browser instead of bundled Chromium, e.g. chrome")
    args = ap.parse_args()
    args.cdp_url = normalize_cdp_url(args.cdp_url)
    if not args.url:  # e.g. started with PyCharm's Run button and no parameters
        args.url = input("Series URL: ").strip()
    if not args.url:
        ap.error("a series URL is required")
    return args


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
