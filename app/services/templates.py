from functools import lru_cache
from pathlib import Path

from app.render.spec import TemplateSpec

TPL_DIR = Path("templates")


@lru_cache
def load(template_id: str) -> TemplateSpec:
    path = TPL_DIR / template_id / "spec.json"
    return TemplateSpec.model_validate_json(path.read_text())


@lru_cache
def all_templates() -> tuple[TemplateSpec, ...]:
    return tuple(load(p.parent.name) for p in sorted(TPL_DIR.glob("*/spec.json")))
