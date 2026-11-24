# Insert and Automate TOC with Tokens

This guide tells how to authenticate `gh-md-toc` with a GitHub token and insert TOC blocks in place.

**Prerequisites:**

- You must have `bash`, `curl` or `wget`, `awk`, `grep`, and `sed` installed.
- You must add `<!--ts-->` and `<!--te-->` marker lines to your target Markdown file.
- You must have a GitHub personal access token when you exceed hourly unauthenticated limits.

WARNING: DO NOT COMMIT `token.txt` TO VERSION CONTROL. COMMITTED TOKENS CAN EXPOSE ACCOUNT CREDENTIALS TO PUBLIC USERS.

CAUTION: PASS `--no-backup` ONLY AFTER YOU VERIFY CLEAN GIT STATUS. THE SCRIPT OVERWRITES LINES BETWEEN MARKERS IN PLACE.

## Procedure

1. Export the GitHub token in your shell session instead of plaintext files when possible.

   ```bash
   export GH_TOC_TOKEN="your_github_token"
   ```

2. If a workflow requires a file token, confirm `token.txt` is listed in `.gitignore`.

   ```bash
   git check-ignore -q token.txt && echo "Ignored safely."
   ```

3. Confirm that the target Markdown file contains both TOC markers.

   ```bash
   grep -Fxq "<!--ts-->" README.md && grep -Fxq "<!--te-->" README.md
   ```

4. Check option order before execution (`--indent` before `--insert`, `--no-backup`, and `--hide-footer`).

   ```bash
   ./gh-md-toc --indent 3 --insert --no-backup --hide-footer README.md
   ```

NOTE: The `gh_toc_app` function checks CLI flags in fixed sequence and stops flag checks at the first unrecognized argument.

## Verification

1. Inspect the updated lines between `<!--ts-->` and `<!--te-->`.

   ```bash
   sed -n '/<!--ts-->/,/<!--te-->/p' README.md
   ```

2. Run syntax validation if you modify `gh-md-toc` locally.

   ```bash
   bash -n ./gh-md-toc
   ```

## Rollback

If an in-place update without `--no-backup` leaves unwanted changes, restore the `.orig.*` backup file:

```bash
ls -1 README.md.orig.* README.md.toc.*
cp README.md.orig.<timestamp> README.md
rm -f README.md.orig.<timestamp> README.md.toc.<timestamp>
```

If you used `--no-backup`, restore the tracked file with Git:

```bash
git checkout -- README.md
```

## References

- Option matrix and marker rules: [CLI Options, Tokens, and Markers](../03-reference/01-cli-options-tokens-and-markers.md)
- API parser design: [GitHub API Architecture and Option Design](../04-explanation/01-github-api-parsing-and-option-design.md)
