# Shared GitHub workflows

## Remove merged generated artifacts

Existing callers of `delete-visual-explanation-svgs.yml` continue to remove only
tracked SVG files under `visual-explanations/`. Raccoon cleanup is opt-in:

```yaml
name: Clean merged generated artifacts
on:
  push:
    branches: [main]
permissions:
  contents: write
jobs:
  cleanup:
    uses: bajor/github-workflows/.github/workflows/delete-visual-explanation-svgs.yml@main
    with:
      delete-raccoon-artifacts: true
    secrets:
      REMOVE_VISUALS_MAIN: ${{ secrets.REMOVE_VISUALS_MAIN || github.token }}
```

The input deletes tracked `raccoon-artifacts/pr-N/` material, including copied
source files, manifests and diagrams. It leaves an empty `catalog.json` so the
web reader can import an authoritative empty repository. Other files, untracked
notes and source outside the generated directories are not removed. Catalog
ownership and format are validated before any deletion; symlink catalogs are rejected.

Use the built-in token only when `main` allows it. For a protected-main ruleset,
create a fine-grained PAT with repository Contents read/write, add its owner to
the ruleset bypass list, and store it as `REMOVE_VISUALS_MAIN`. Grant the caller
`contents: write`. Do not put token values in YAML or documentation.

The workflow serializes cleanups and never force-pushes. A concurrent source push
may safely reject the cleanup push; rerun the workflow if the next queued run
does not clean it. Bot-triggered runs are allowed; a second run is a no-op rather
than an actor-based exemption that would leave bot-merged artifacts behind.

Deletion affects the current `main` tree, not Git history or snapshots already
imported into a browser. GitSync must synchronize, then the reader must re-import.

## Verification

Run `python3 -m unittest discover -s tests -v`, `actionlint`, and `git diff --check`.
