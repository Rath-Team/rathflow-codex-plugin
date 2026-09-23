#!/usr/bin/env python3
"""Self-contained structure check for this plugin repository.

Works without the Codex skill directory, so CI can run it. The official
`validate_plugin.py` from the plugin-creator skill is still the source of
truth during local development; run it too when it is available.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
REQUIRED_MANIFEST = ("name", "version", "description", "author", "skills")
REQUIRED_INTERFACE = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
)
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_json(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"missing file: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON ({exc})")
        return {}


def check_skill(skill_md: Path, errors: list[str]) -> None:
    match = FRONTMATTER.match(skill_md.read_text(encoding="utf-8"))
    if not match:
        errors.append(f"{skill_md}: missing YAML frontmatter")
        return
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    for key in ("name", "description"):
        if not fields.get(key):
            errors.append(f"{skill_md}: frontmatter is missing '{key}'")
    declared = fields.get("name")
    if declared and declared != skill_md.parent.name:
        errors.append(
            f"{skill_md}: frontmatter name '{declared}' != directory '{skill_md.parent.name}'"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin_path", help="Path to the plugin root directory")
    parser.add_argument(
        "--marketplace",
        default=str(DEFAULT_MARKETPLACE),
        help="Path to the marketplace.json that lists this plugin",
    )
    args = parser.parse_args()

    plugin_root = Path(args.plugin_path).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest = load_json(plugin_root / ".codex-plugin" / "plugin.json", errors)
    for key in REQUIRED_MANIFEST:
        if not manifest.get(key):
            errors.append(f"plugin.json: missing required field '{key}'")
    if manifest.get("name") != plugin_root.name:
        errors.append(
            f"plugin.json name '{manifest.get('name')}' != directory '{plugin_root.name}'"
        )
    version = manifest.get("version") or ""
    if "+codex." in version:
        warnings.append(
            f'plugin.json version "{version}" carries a local cachebuster; '
            "release versions should be plain semver"
        )
    interface = manifest.get("interface") or {}
    for key in REQUIRED_INTERFACE:
        if not interface.get(key):
            errors.append(f"plugin.json: missing interface.{key}")
    for key in ("logo", "composerIcon", "screenshots"):
        value = interface.get(key)
        for item in value if isinstance(value, list) else [value]:
            if item and not (plugin_root / item).is_file():
                errors.append(f"plugin.json: interface.{key} points at a missing file: {item}")

    skills_dir = plugin_root / "skills"
    if not skills_dir.is_dir():
        errors.append(f"missing skills directory: {skills_dir}")
    else:
        skill_dirs = [item for item in sorted(skills_dir.iterdir()) if item.is_dir()]
        if not skill_dirs:
            errors.append(f"{skills_dir}: no skills found")
        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"{skill_dir}: missing SKILL.md")
                continue
            check_skill(skill_md, errors)

    mcp_ref = manifest.get("mcpServers")
    if mcp_ref:
        mcp_source = plugin_root / mcp_ref
        if not mcp_source.is_file():
            errors.append(f"plugin.json: mcpServers points at a missing file: {mcp_ref}")
        else:
            servers = (load_json(mcp_source, errors) or {}).get("mcpServers")
            if not isinstance(servers, dict) or not servers:
                errors.append(f"{mcp_source}: 'mcpServers' must be a non-empty object")
            else:
                for name, spec in servers.items():
                    if not isinstance(spec, dict) or not (spec.get("command") or spec.get("url")):
                        errors.append(f"{mcp_source}: server '{name}' needs 'command' or 'url'")

    marketplace_path = Path(args.marketplace).expanduser().resolve()
    marketplace = load_json(marketplace_path, errors)
    if marketplace:
        if not marketplace.get("name"):
            errors.append(f"{marketplace_path}: missing 'name'")
        entries = marketplace.get("plugins")
        if not isinstance(entries, list) or not entries:
            errors.append(f"{marketplace_path}: 'plugins' must be a non-empty list")
        else:
            names = [entry.get("name") for entry in entries if isinstance(entry, dict)]
            if manifest.get("name") not in names:
                errors.append(
                    f"{marketplace_path}: no entry for plugin '{manifest.get('name')}'"
                )
            for entry in entries:
                if not isinstance(entry, dict):
                    errors.append(f"{marketplace_path}: plugin entries must be objects")
                    continue
                source = (entry.get("source") or {}).get("path")
                if not source:
                    errors.append(f"{marketplace_path}: entry '{entry.get('name')}' has no source.path")
                    continue
                resolved = (marketplace_path.parents[2] / source).resolve()
                if not resolved.is_dir():
                    errors.append(
                        f"{marketplace_path}: entry '{entry.get('name')}' path does not exist: {source}"
                    )
                policy = entry.get("policy") or {}
                for key in ("installation", "authentication"):
                    if not policy.get(key):
                        errors.append(
                            f"{marketplace_path}: entry '{entry.get('name')}' missing policy.{key}"
                        )
                if not entry.get("category"):
                    errors.append(
                        f"{marketplace_path}: entry '{entry.get('name')}' missing category"
                    )

    for warning in warnings:
        print(f"warning: {warning}")
    for message in errors:
        print(f"error: {message}")
    if errors:
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {plugin_root} ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
