# Tutorial 01: Generate TOC for Local and STDIN Files

In this tutorial, you check `gh-md-toc` CLI options and generate a Table of Contents for a throwaway local Markdown file inside `/tmp`.

## Prerequisites

- Bash (`bash --version`)
- `curl` or `wget`, plus `awk`, `grep`, and `sed`
- Optional `GH_TOC_TOKEN` exported when testing live against `https://api.github.com/markdown/raw` (avoids anonymous hourly rate limits)

## Step 1 — Check Script Syntax and Built-In Help

Run syntax, help, and version verification in your repository clone:

```bash
bash -n ./gh-md-toc
./gh-md-toc --help
./gh-md-toc --version
```

Expected version line:

```text
0.10.0
```

## Step 2 — Create a Sample Markdown Sandbox File

Create a temporary Markdown file with `<!--ts-->` and `<!--te-->` markers so `--insert` updates safely:

```bash
cat > /tmp/sample-toc-demo.md <<'EOF'
# Project Overview

<!--ts-->
<!--te-->

## Install
## Usage
### STDIN Mode
EOF
```

## Step 3 — Generate from STDIN and Insert In-Place

Pipe the file into `./gh-md-toc -` first, then insert the generated TOC cleanly with `--insert --no-backup --hide-footer`:

```bash
cat /tmp/sample-toc-demo.md | ./gh-md-toc -
./gh-md-toc --insert --no-backup --hide-footer /tmp/sample-toc-demo.md
cat /tmp/sample-toc-demo.md
```

Expected marker output inside `/tmp/sample-toc-demo.md`:

```markdown
<!--ts-->
* [Project Overview](#project-overview)
   * [Install](#install)
   * [Usage](#usage)
      * [STDIN Mode](#stdin-mode)
<!--te-->
```

## Step 4 — Remove the Sandbox File

Clean up `/tmp/sample-toc-demo.md`:

```bash
rm -f /tmp/sample-toc-demo.md
```

## Next Steps

- Automate token-authenticated CI runs with [Insert and Automate TOC with Tokens](../02-how-to-guides/01-insert-and-automate-toc-with-tokens.md).
- Inspect all options and marker details in [CLI Options, Tokens, and Markers](../03-reference/01-cli-options-tokens-and-markers.md).
- Read why GitHub API rendering is used in [GitHub API Parsing and Option Design](../04-explanation/01-github-api-parsing-and-option-design.md).
