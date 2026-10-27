#!/usr/bin/env python3
"""Cross-platform PDF reading for the draw-steel-import skill.

Uses PyMuPDF (pure Python, wheels for Windows/macOS/Linux, no system
dependencies). Auto-installs via pip if missing.

Usage:
    python pdf.py pages  <pdf>
    python pdf.py find   <pdf> <name> [<name> ...]
    python pdf.py text   <pdf> [<page>]
    python pdf.py render <pdf> <page> [<page> ...] [--out DIR]

Subcommands:
  pages   Print the number of pages in the PDF.
  find    Print every page (1-based) that contains any of the names
          (case-insensitive), with up to 6 matching lines as context.
  text    Print the extracted text of one page, or all pages (separated
          by "===== page N =====" headers).
  render  Render page(s) to 200-dpi PNGs. Default output directory is
          <OS temp dir>/draw-steel. Prints the path of each file written.

Use `python` on Windows and `python3` on Linux/macOS.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _import_fitz():
    """Import PyMuPDF, preferring the modern `pymupdf` name over the
    deprecated `fitz` alias (which prints a FutureWarning)."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            import pymupdf as fitz
            return fitz
        except ImportError:
            import fitz
            return fitz


def ensure_fitz():
    try:
        return _import_fitz()
    except ImportError:
        pass

    # Externally-managed Pythons (PEP 668) need a fallback flag; try plain
    # install first so normal environments (incl. Windows) stay untouched.
    attempts = [
        ["-m", "pip", "install", "-q", "pymupdf"],
        ["-m", "pip", "install", "-q", "--user", "pymupdf"],
        ["-m", "pip", "install", "-q", "--break-system-packages", "pymupdf"],
    ]
    for args in attempts:
        print(f"PyMuPDF not found — trying: {sys.executable} {' '.join(args)}",
              file=sys.stderr)
        if subprocess.run([sys.executable] + args).returncode == 0:
            try:
                import fitz
                return fitz
            except ImportError:
                continue
    die("could not install pymupdf automatically. "
        "Install it manually (python -m pip install pymupdf) and re-run.")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def open_pdf(path):
    p = Path(path)
    if not p.exists():
        die(f"PDF not found: {p}")
    try:
        return ensure_fitz().open(p)
    except Exception as e:  # fitz raises various types
        die(f"could not open {p}: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1]
    pdf = sys.argv[2] if len(sys.argv) > 2 else None
    if not pdf:
        print(__doc__)
        return 1

    doc = open_pdf(pdf)
    try:
        if cmd == "pages":
            print(doc.page_count)

        elif cmd == "find":
            names = sys.argv[3:]
            if not names:
                die("find needs at least one name to search for")
            pats = [re.compile(re.escape(n), re.IGNORECASE) for n in names]
            found = False
            for i, page in enumerate(doc, start=1):
                lines = page.get_text("text").splitlines()
                hits = [ln for ln in lines if any(p.search(ln) for p in pats)]
                if hits:
                    found = True
                    print(f"page {i}:")
                    for h in hits[:6]:
                        print(f"  {h.strip()}")
            if not found:
                print("no matching pages")

        elif cmd == "text":
            if len(sys.argv) > 3:
                p = int(sys.argv[3])
                if not 1 <= p <= doc.page_count:
                    die(f"page {p} out of range (1-{doc.page_count})")
                print(doc[p - 1].get_text("text"))
            else:
                for i, page in enumerate(doc, start=1):
                    print(f"\n===== page {i} =====\n")
                    print(page.get_text("text"))

        elif cmd == "render":
            args = sys.argv[3:]
            pages, outdir = [], None
            i = 0
            while i < len(args):
                if args[i] == "--out":
                    if i + 1 >= len(args):
                        die("--out needs a directory argument")
                    outdir = Path(args[i + 1])
                    i += 2
                else:
                    try:
                        pages.append(int(args[i]))
                    except ValueError:
                        die(f"bad page number: {args[i]}")
                    i += 1
            if not pages:
                die("render needs at least one page number")
            for p in pages:
                if not 1 <= p <= doc.page_count:
                    die(f"page {p} out of range (1-{doc.page_count})")
            if outdir is None:
                outdir = Path(tempfile.gettempdir()) / "draw-steel"
            outdir.mkdir(parents=True, exist_ok=True)
            stem = Path(pdf).stem
            for p in pages:
                out = outdir / f"{stem}-page{p}.png"
                doc[p - 1].get_pixmap(dpi=200).save(out)
                print(out)

        else:
            print(__doc__)
            return 1
    finally:
        doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
