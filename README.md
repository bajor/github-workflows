# Shared GitHub workflows

## Remove merged generated artifacts

Existing callers of `delete-visual-explanation-svgs.yml` continue to remove only
tracked SVG files under `visual-explanations/`. Enable Raccoon in that same caller,
not a second competing cleanup workflow:

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
      REMOVE_VISUALS_MAIN: ${{ secrets.REMOVE_VISUALS_MAIN }}
```

The input deletes tracked `raccoon-artifacts/pr-N/` material listed by the catalog, including copied
source files, manifests and diagrams. It leaves an empty `catalog.json` so the
web reader can import an authoritative empty repository. Other files, untracked
notes and source outside the generated directories are not removed. Catalog
ownership and format are validated before any deletion; symlink catalogs are rejected.

Create a fine-grained PAT with repository Contents read/write. For a protected-main
ruleset, add its owner to the ruleset bypass list. Store it as `REMOVE_VISUALS_MAIN`. Grant the caller
`contents: write`. Do not put token values in YAML or documentation.

The workflow serializes each caller and never force-pushes. A concurrent source push
may safely reject the cleanup push; rerun the workflow if the next queued run
does not clean it. Bot-triggered runs are not excluded, but pushes made using
`GITHUB_TOKEN` do not trigger new push workflows. Automations merging with that
token must explicitly dispatch cleanup or use a PAT that triggers push workflows.
A second PAT-triggered cleanup is a no-op.

The format is the strict version-1 catalog owned by
[Raccoon MCP](https://github.com/bajor/raccoon-mcp/blob/cdcf9dc/src/contract.ts).
Unknown versions or fields fail closed. After a repository rename or transfer,
regenerate the catalog for the new repository identity before enabling cleanup.
Unlisted PR directories are preserved, not assumed to be generated.

The workflow pins its composite action to an immutable commit, so a caller pinned
to a workflow release does not silently run cleanup code from a later `main`.
When updating the cleanup script, commit it first, then update the workflow's
action SHA in a second commit in the same PR.

Deletion affects the current `main` tree, not Git history or snapshots already
imported into a browser. GitSync must synchronize, then the reader must re-import.

## Verification

Run `python3 -m unittest discover -s tests -v`, `actionlint`, and `git diff --check`.
