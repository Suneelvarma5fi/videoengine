"""
Template Resolver — loads template definitions from JSON and produces BlockLayout.

Templates live in  <project_root>/templates/<name>.json
Each template JSON may include nested "highlight" and "block_config" objects.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .models import BlockConfig, BlockLayout, HighlightConfig, TemplateConfig

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # project root
    "templates",
)


def load_template(name: str, templates_dir: Optional[str] = None) -> TemplateConfig:
    """Load a TemplateConfig from a JSON file by template name."""
    directory = templates_dir or _TEMPLATES_DIR
    path = os.path.join(directory, f"{name}.json")

    if not os.path.exists(path):
        available = _list_available(directory)
        raise ValueError(
            f"Template '{name}' not found at {path}.\n"
            f"Available templates: {available}"
        )

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Pop nested objects before passing remaining keys as flat kwargs
    highlight_data    = data.pop("highlight", {})
    block_config_data = data.pop("block_config", {})

    return TemplateConfig(
        highlight=HighlightConfig(**highlight_data),
        block_config=BlockConfig(**block_config_data),
        **data,
    )


def resolve_layout(template: TemplateConfig) -> BlockLayout:
    """Derive a BlockLayout from a TemplateConfig (no block-specific state)."""
    return BlockLayout(
        position=template.position,
        alignment=template.alignment,
        font_family=template.font_family,
        font_size=template.font_size,
        base_color=template.base_color,
        background_color=template.background_color,
        highlight_color=template.highlight_color,
        highlight_mode=template.highlight.mode,
        transition_in_ms=template.highlight.transition_in_ms,
        transition_out_ms=template.highlight.transition_out_ms,
        max_lines=template.max_lines,
    )


def _list_available(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    return [
        f[:-5]  # strip .json
        for f in os.listdir(directory)
        if f.endswith(".json")
    ]
