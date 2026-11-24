# CLI Options, Tokens, and Markers

## Command Modes and Flags

`gh_toc_app` inspects arguments sequentially in the order listed below:

| Flag / Argument | Position Order | Default | Behavior |
| :--- | :--- | :--- | :--- |
| `--help` or no args | Position 1 | — | Print help text and return `0` |
| `--version` | Position 1 | `0.10.0` | Print script version, host metadata, and tool versions |
| `--indent <NUM>` | Position 1 (must precede other flags) | `3` | Spaces per nested heading level (`(level - 1) * indent`) |
| `-` | After optional `--indent` | — | Read Markdown from STDIN into `$TMPDIR/tmp.XXXXXX` |
| `--insert` | After optional `--indent` | `no` | Replace lines between `<!--ts-->` and `<!--te-->` in local file(s) |
| `--no-backup` | After `--insert` | `no` | Remove `.orig.<ts>` and `.toc.<ts>` backup files (implies `--insert`) |
| `--hide-footer` | After `--no-backup` | `no` | Omit footer HTML comments inside `<!--ts-->..<!--te-->` (implies `--insert`) |
| `--skip-header` | After `--hide-footer` | `no` | Strip content up to `<!--te-->` before rendering local file |
| `<src> [src ...]` | Trailing arguments | — | One or more local file paths or `http://` / `https://` URLs |

## Authentication, Markers, and Dependencies

| Item | Type / Value | Lookup / Rule |
| :--- | :--- | :--- |
| `GH_TOC_TOKEN` | Environment variable | Primary `Authorization: token ...` header for `https://api.github.com/markdown/raw` |
| `token.txt` | File next to `gh-md-toc` | Fallback token file read when `GH_TOC_TOKEN` is unset (`.gitignore` excludes `token.txt`) |
| `<!--ts-->` / `<!--te-->` | HTML comment markers | Required exact lines (`grep -Fxq`) when `--insert` or `--skip-header` is active |
| `DOCKER` (`Dockerfile`) | `debian` image | Installs `curl` only; sets `ENTRYPOINT ["./gh-md-toc"]` |
| Runtime binaries | External tools | `bash`, `curl` or `wget`, GNU `awk` (`mawk` unsupported), `grep`, `sed` |

## Exit Conditions and Diagnostics

| Message | Trigger Condition | Exit Code |
| :--- | :--- | :--- |
| `XXNetworkErrorXX` / `Parsing local markdown file requires access to github API` | `curl` fails against `https://api.github.com/markdown/raw` | `1` |
| `XXRateLimitXX` / `You exceeded the hourly limit` | GitHub API responds with `API rate limit exceeded` | `1` |
| `You don't have <!--ts--> or <!--te--> in your file...exiting` | `--insert` invoked on file lacking `<!--ts-->` or `<!--te-->` | `1` |
| `Could not load remote document.` | `gh_toc_load` (`curl`/`wget`) fails (`PIPESTATUS[0] != 0`) | `1` |
