"""Automated tests for gh-md-toc offline execution, README CI parity, Diataxis, STE, and Mermaid."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
QUADRANTS = ("01-tutorials", "02-how-to-guides", "03-reference", "04-explanation")

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")
MERMAID_HEAD_RE = re.compile(
    r"^\s*(?:flowchart(?:-elk)?(?:\s+(?:TD|TB|LR|RL|BT))?|graph\s+(?:TD|TB|LR|RL|BT)|"
    r"sequenceDiagram|stateDiagram(?:-v2)?|classDiagram|erDiagram|gantt|pie|gitGraph|"
    r"mindmap|timeline|xychart-beta)\b"
)
BARE_ARROW_RE = re.compile(r"(?:(?<![<!])-->|(?<!<!)<--|(?<![=])==>|─+>|▼|▲)")
BOX_CHAR_RE = re.compile(r"[┌┐┘╔╗╚╝]|\+[-=]{2,}\+")
FORBIDDEN_HOWTO_MODAL_RE = re.compile(
    r"\b(?:should|would|may|might|shall|ought|can't|don't|won't|isn't|aren't|doesn't|didn't)\b",
    re.IGNORECASE,
)
FRENCH_LEAK_RE = re.compile(
    r"\b(?:tutoriels|guides\s+pratiques|explications|étapes|erreur|succès|fichiers)\b",
    re.IGNORECASE,
)

# Exact README.md headings asserted by tests/tests.bats so CI stays green.
EXPECTED_README_HEADINGS = [
    "gh-md-toc",
    "Table of contents",
    "Installation",
    "Usage",
    "STDIN",
    "Local files",
    "Remote files",
    "Multiple files",
    "Combo",
    "Auto insert and update TOC",
    "GitHub token",
    "TOC generation with Github Actions",
    "Tests",
    "Dependency",
    "Docker",
    "Local",
    "Public",
]


def _iter_repo_markdowns() -> list[Path]:
    skip = {".git", "node_modules", ".venv", "__pycache__"}
    files: list[Path] = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in sorted(names):
            if name.lower().endswith(".md"):
                files.append(Path(base) / name)
    return files


def _split_prose_and_code(text: str) -> tuple[list[tuple[str, bool]], list[tuple[str, str, int, str]]]:
    blocks: list[tuple[str, str, int, str]] = []
    prose: list[tuple[str, bool]] = []
    para_lines: list[str] = []
    in_fence = False
    fchar = ""
    flen = 0
    findent = ""
    flang = ""
    fline = 0
    fbody: list[str] = []

    def flush_para() -> None:
        if para_lines:
            joined = " ".join(para_lines).strip()
            if joined:
                prose.append((joined, joined.upper().startswith("NOTE:")))
            para_lines.clear()

    for idx, line in enumerate(text.splitlines(), start=1):
        if not in_fence:
            m = FENCE_RE.match(line)
            if m and not (m.group(2)[0] == "`" and "`" in m.group(3)):
                flush_para()
                in_fence = True
                findent = m.group(1)
                fchar = m.group(2)[0]
                flen = len(m.group(2))
                flang = m.group(3).strip().split()[0].lower() if m.group(3).strip() else ""
                fline = idx
                fbody = []
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("|") or re.match(r"^[-*_]{3,}$", stripped):
                flush_para()
                continue
            cleaned = re.sub(r"^(?:>\s*|[-*+]\s+|\d+\.\s+)", "", stripped)
            para_lines.append(cleaned)
        else:
            if re.match(rf"^[ \t]*{re.escape(fchar)}{{{flen},}}[ \t]*$", line):
                blocks.append((findent, flang, fline, "\n".join(fbody)))
                in_fence = False
            else:
                fbody.append(line)
    flush_para()
    return prose, blocks


def _extract_markdown_headings(text: str) -> list[str]:
    """Return ATX and Setext headings outside fenced code blocks."""
    lines = text.splitlines()
    _, blocks = _split_prose_and_code(text)
    fenced_lines: set[int] = set()
    for _, _, start_line, body in blocks:
        end_line = start_line + len(body.splitlines()) + 1
        fenced_lines.update(range(start_line, end_line + 1))

    headings: list[str] = []
    for idx, line in enumerate(lines, start=1):
        if idx in fenced_lines:
            continue
        atx = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if atx:
            headings.append(atx.group(1))
            continue
        if idx < len(lines) and (idx + 1) not in fenced_lines:
            nxt = lines[idx].strip()
            if line.strip() and (re.match(r"^={2,}$", nxt) or re.match(r"^-{2,}$", nxt)):
                headings.append(line.strip())
    return headings


def _find_mmdc() -> str | None:
    if found := shutil.which("mmdc"):
        return found
    candidate = Path("/home/jmren/node_modules/.bin/mmdc")
    return str(candidate) if candidate.is_file() else None


class TestGhMdTocDocsAndCli(unittest.TestCase):
    """Validate Diataxis docs, STE rules, Mermaid diagrams, README parity, and offline CLI behavior."""

    def test_diataxis_structure_links_and_readme_bats_heading_parity(self) -> None:
        """Keep README headings compatible with tests/tests.bats and validate Diataxis structure/links."""
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(_extract_markdown_headings(readme_text), EXPECTED_README_HEADINGS)
        self.assertIn("sitemap.js", readme_text)
        self.assertNotIn("sitemap.s/blob", readme_text)

        self.assertTrue((DOCS_DIR / "index.md").is_file())
        for q in QUADRANTS:
            qdir = DOCS_DIR / q
            self.assertTrue((qdir / "index.md").is_file())
            self.assertTrue(any(p.name != "index.md" for p in qdir.glob("*.md")))

        for page in sorted((DOCS_DIR / "01-tutorials").glob("*.md")):
            if page.name == "index.md":
                continue
            txt = page.read_text(encoding="utf-8")
            self.assertIn("## Prerequisites", txt)
            self.assertIn("## Next Steps", txt)

        for page in sorted((DOCS_DIR / "03-reference").glob("*.md")):
            txt = page.read_text(encoding="utf-8")
            for banned in ("In this tutorial", "Let's ", "Step 1"):
                self.assertNotIn(banned, txt)

        for page in sorted((DOCS_DIR / "04-explanation").glob("*.md")):
            txt = page.read_text(encoding="utf-8")
            for banned in ("## Step 1", "## Rollback", "## Prerequisites"):
                self.assertNotIn(banned, txt)

        for md in [ROOT / "README.md", *sorted(DOCS_DIR.rglob("*.md"))]:
            text = md.read_text(encoding="utf-8")
            _, blocks = _split_prose_and_code(text)
            no_code = text
            for _, _, _, body in blocks:
                if body:
                    no_code = no_code.replace(body, "")
            for raw_target in LINK_RE.findall(no_code):
                target = raw_target.strip().strip("<>").split()[0]
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path_part = target.split("#", 1)[0]
                if path_part:
                    self.assertTrue((md.parent / path_part).resolve().exists(), f"Broken link in {md.name}: {raw_target}")

    def test_ste_procedural_and_english_only_compliance(self) -> None:
        """Enforce ASD-STE100 checks on 02-how-to-guides and English-only text across docs/script."""
        for page in sorted((DOCS_DIR / "02-how-to-guides").glob("*.md")):
            txt = page.read_text(encoding="utf-8")
            if page.name != "index.md":
                for section in ("**Prerequisites:**", "## Procedure", "## Verification", "## Rollback"):
                    self.assertIn(section, txt)
                self.assertTrue("WARNING:" in txt or "CAUTION:" in txt)
            prose, _ = _split_prose_and_code(txt)
            for para, is_note in prose:
                self.assertNotIn(";", para)
                self.assertFalse(FORBIDDEN_HOWTO_MODAL_RE.search(para))
                limit = 25 if is_note else 20
                for sent in [s.strip() for s in re.split(r"(?<=[.!?])\s+", para) if s.strip()]:
                    words = re.sub(r"`[^`]+`", "code", sent).split()
                    self.assertLessEqual(len(words), limit, f"Sentence > {limit} words in {page.name}: {sent}")

        for path in [ROOT / "gh-md-toc", ROOT / "README.md", *sorted(DOCS_DIR.rglob("*.md"))]:
            self.assertIsNone(FRENCH_LEAK_RE.search(path.read_text(encoding="utf-8")))

    def test_mermaid_diagrams_valid_and_zero_ascii_diagrams(self) -> None:
        """Verify zero ASCII box-arrow diagrams and valid column-0 Mermaid blocks via mmdc."""
        mmdc = _find_mmdc()
        mermaid_blocks: list[tuple[str, int, str]] = []
        for md in _iter_repo_markdowns():
            rel = md.relative_to(ROOT).as_posix()
            _, blocks = _split_prose_and_code(md.read_text(encoding="utf-8"))
            for indent, lang, line, body in blocks:
                if lang == "mermaid":
                    self.assertEqual(indent, "", f"Indented mermaid in {rel}:{line}")
                    mermaid_blocks.append((rel, line, body))
                else:
                    self.assertIsNone(MERMAID_HEAD_RE.match(body), f"Untagged mermaid in {rel}:{line}")
                    is_tree = bool(re.search(r"[├└]─", body)) and not BARE_ARROW_RE.search(body) and not BOX_CHAR_RE.search(body)
                    if not is_tree:
                        self.assertFalse(bool(BOX_CHAR_RE.search(body)) and bool(BARE_ARROW_RE.search(body)))

        self.assertGreaterEqual(len(mermaid_blocks), 2)
        if mmdc is not None:
            with tempfile.TemporaryDirectory() as tmpdir:
                for idx, (rel, line, code) in enumerate(mermaid_blocks):
                    in_f = Path(tmpdir) / f"d_{idx}.mmd"
                    out_f = Path(tmpdir) / f"d_{idx}.svg"
                    in_f.write_text(code + "\n", encoding="utf-8")
                    res = subprocess.run([mmdc, "-i", str(in_f), "-o", str(out_f)], capture_output=True, text=True, timeout=60)
                    self.assertEqual(res.returncode, 0, f"mmdc error in {rel}:{line}: {res.stderr}")

    def test_gh_md_toc_cli_and_offline_toc_execution(self) -> None:
        """Run bash -n, --help, --version, and offline local/STDIN/insert/error paths via curl PATH shim."""
        script_path = ROOT / "gh-md-toc"
        script_text = script_path.read_text(encoding="utf-8")
        self.assertNotIn("\r\n", script_text)
        self.assertIn("curl_rc=0", script_text)

        if os.name != "posix" or not shutil.which("bash"):
            self.skipTest("Offline bash execution checks run on POSIX/WSL bash")

        syn = subprocess.run(["bash", "-n", str(script_path)], capture_output=True, text=True, timeout=15)
        self.assertEqual(syn.returncode, 0, syn.stderr)

        hlp = subprocess.run(["bash", str(script_path), "--help"], capture_output=True, text=True, timeout=15)
        self.assertEqual(hlp.returncode, 0)
        self.assertIn("Usage:", hlp.stdout)
        self.assertIn("--insert", hlp.stdout)

        ver = subprocess.run(["bash", str(script_path), "--version"], capture_output=True, text=True, timeout=15)
        self.assertEqual(ver.returncode, 0)
        self.assertEqual(ver.stdout.splitlines()[0].strip(), "0.10.0")

        # Deterministic offline curl shim converting ATX headings to GitHub heading HTML.
        curl_shim_body = """#!/usr/bin/env python3
import os, re, sys
mode = os.environ.get("MOCK_CURL_MODE", "ok")
if mode == "net_err":
    sys.exit(6)
if mode == "rate_limit":
    print("API rate limit exceeded")
    sys.exit(0)
data_path = None
for arg in sys.argv[1:]:
    if arg.startswith("@"):
        data_path = arg[1:]
text = open(data_path, encoding="utf-8").read() if data_path else ""
for line in text.splitlines():
    m = re.match(r"^(#{1,6})\\s+(.+?)\\s*$", line)
    if m:
        lvl = len(m.group(1))
        title = m.group(2)
        slug = re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")
        print(f'<div class="markdown-heading"><h{lvl} class="heading-element">{title}</h{lvl}><a class="anchor" href="#{slug}"><span></span></a></div>')
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shim = tmp / "curl"
            shim.write_text(curl_shim_body, encoding="utf-8")
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            sample_md = tmp / "sample.md"
            sample_md.write_text(
                "# Project Overview\n\n<!--ts-->\n<!--te-->\n\n## Install\n## Usage\n### STDIN Mode\n",
                encoding="utf-8",
            )
            env = {**os.environ, "PATH": f"{tmp}:{os.environ.get('PATH', '')}", "TMPDIR": str(tmp)}

            # 1. Local file TOC generation
            res_local = subprocess.run(["bash", str(script_path), str(sample_md)], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(res_local.returncode, 0, res_local.stderr)
            self.assertIn("* [Project Overview](#project-overview)", res_local.stdout)
            self.assertIn("      * [STDIN Mode](#stdin-mode)", res_local.stdout)

            # 2. STDIN TOC generation
            res_stdin = subprocess.run(
                ["bash", str(script_path), "-"],
                input=sample_md.read_text(encoding="utf-8"),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(res_stdin.returncode, 0, res_stdin.stderr)
            self.assertIn("   * [Install](#install)", res_stdin.stdout)

            # 3. --indent 2 --insert --no-backup --hide-footer (with and without --skip-header)
            res_ins = subprocess.run(
                ["bash", str(script_path), "--indent", "2", "--insert", "--no-backup", "--hide-footer", str(sample_md)],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(res_ins.returncode, 0, res_ins.stderr)
            updated = sample_md.read_text(encoding="utf-8")
            self.assertIn("    * [STDIN Mode](#stdin-mode)", updated)
            self.assertEqual(list(tmp.glob("sample.md.orig.*")), [])
            self.assertEqual(list(tmp.glob("sample.md.toc.*")), [])

            # 4. Network failure propagation (regression check for curl_rc before rm -f)
            err_env = {**env, "MOCK_CURL_MODE": "net_err"}
            res_err = subprocess.run(["bash", str(script_path), str(sample_md)], env=err_env, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(res_err.returncode, 0)
            self.assertIn("github API", res_err.stdout + res_err.stderr)

            # 5. API rate limit exit
            rl_env = {**env, "MOCK_CURL_MODE": "rate_limit"}
            res_rl = subprocess.run(["bash", str(script_path), str(sample_md)], env=rl_env, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(res_rl.returncode, 0)
            self.assertIn("hourly limit", res_rl.stdout + res_rl.stderr)


if __name__ == "__main__":
    unittest.main()
