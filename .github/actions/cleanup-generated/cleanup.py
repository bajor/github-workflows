"""Delete only tracked, owned generated material. Never traverse symlinks."""

import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile


def git(*args):
    return subprocess.check_output(["git", "--literal-pathspecs", *args])


def raccoon_catalog():
    root = Path("raccoon-artifacts")
    if root.is_symlink():
        raise ValueError("raccoon-artifacts must not be a symlink")
    if not root.exists():
        return None
    catalog_file = root / "catalog.json"
    if catalog_file.is_symlink() or not catalog_file.is_file():
        raise ValueError("Refusing cleanup without a regular Raccoon catalog")
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or set(catalog) != {"version", "repository", "artifacts"}:
        raise ValueError("Unrecognized Raccoon catalog")
    if type(catalog["version"]) is not int or catalog["version"] != 1:
        raise ValueError("Unsupported Raccoon catalog version")
    expected = os.environ.get("GITHUB_REPOSITORY", "")
    if not expected or not isinstance(catalog["repository"], str) or catalog["repository"].lower() != expected.lower():
        raise ValueError("Catalog belongs to a different repository")
    if not isinstance(catalog["artifacts"], list):
        raise ValueError("Invalid catalog artifacts")
    seen = set()
    for item in catalog["artifacts"]:
        if not isinstance(item, dict) or set(item) != {"pr", "manifest"}:
            raise ValueError("Invalid PR entry")
        number = item["pr"]
        if type(number) is not int or number < 1 or number in seen or item["manifest"] != f"pr-{number}/manifest.json":
            raise ValueError("Invalid or duplicate PR manifest path")
        seen.add(number)
    return catalog


def main():
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:
        raise ValueError("Cleanup requires a clean index")
    tracked = [os.fsdecode(path) for path in git("ls-files", "-z", "--", "visual-explanations", "raccoon-artifacts").split(b"\0") if path]
    enabled = os.environ.get("DELETE_RACCOON_ARTIFACTS", "false") == "true"
    # Validate ownership before staging any deletion, including the legacy SVGs.
    catalog = raccoon_catalog() if enabled else None
    owned = {f"pr-{item['pr']}" for item in catalog["artifacts"]} if catalog else set()
    paths = []
    for path in tracked:
        parts = PurePosixPath(path).parts
        review_svg = len(parts) > 1 and parts[0] == "visual-explanations" and path.endswith(".svg")
        generated_pr = len(parts) > 1 and parts[0] == "raccoon-artifacts" and parts[1] in owned
        if review_svg or generated_pr:
            paths.append(path)
    temporary = None
    if catalog is not None and catalog["artifacts"]:
        if "raccoon-artifacts/catalog.json" not in tracked:
            raise ValueError("Refusing to stage an untracked catalog")
        git("diff", "--exit-code", "--", "raccoon-artifacts/catalog.json")
        catalog["artifacts"] = []
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir="raccoon-artifacts", prefix=".catalog-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(catalog, indent=2) + "\n")
    try:
        for path in paths:
            print(f"Delete tracked generated path: {path!r}", flush=True)
        if paths:
            subprocess.run(["git", "--literal-pathspecs", "rm", "--pathspec-from-file=-", "--pathspec-file-nul"],
                           input=b"\0".join(os.fsencode(path) for path in paths) + b"\0", check=True)
        if temporary is not None:
            os.replace(temporary, "raccoon-artifacts/catalog.json")
            git("add", "--", "raccoon-artifacts/catalog.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Removed {len(paths)} tracked generated files.")


if __name__ == "__main__":
    main()
