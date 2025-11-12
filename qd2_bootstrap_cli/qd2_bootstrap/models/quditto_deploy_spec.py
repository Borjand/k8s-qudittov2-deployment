from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
import re

# ---------------------------------------------------------------------------
# Relaxed identifier: letters (any case), digits, hyphen (-), underscore (_)
# ---------------------------------------------------------------------------
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

def _name(v: str, what: str) -> str:
    """Validate identifiers against the relaxed pattern."""
    if not NAME_RE.match(v):
        raise ValueError(
            f"{what} must include only letters, digits, hyphen (-) and underscore (_): {v!r}"
        )
    return v


class ComponentRef(BaseModel):
    """
    One deployable component: placement params + chart reference + optional values.
    """
    nodek8s: str
    chart: str
    version: Optional[str] = None
    values: Dict = Field(default_factory=dict)

    @field_validator("nodek8s")
    @classmethod
    def _v_nodek8s(cls, v: str) -> str:
        return _name(v, "nodek8s")

    @field_validator("chart")
    @classmethod
    def _v_chart(cls, v: str) -> str:
        return _name(v, "chart")


class QNodeRef(ComponentRef):
    """A Quditto node also carries a logical unique name."""
    name: str

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _name(v, "qnode.name")


class ChartsConfig(BaseModel):
    """Global chart source (classic Helm repo)."""
    repo: str


class QudittoSetup(BaseModel):
    """
    Top-level grouping for Quditto components.
    Each child is optional; CLI deploys only present ones.
    """
    qcontroller: Optional[ComponentRef] = None
    qorchestrator: Optional[ComponentRef] = None
    qnodes: List[QNodeRef] = Field(default_factory=list)

    @field_validator("qnodes")
    @classmethod
    def _unique_qnode_names(cls, items: List[QNodeRef]) -> List[QNodeRef]:
        seen = set()
        for it in items:
            if it.name in seen:
                raise ValueError(f"duplicated qnode name: {it.name}")
            seen.add(it.name)
        return items


class QudittoDeploySpec(BaseModel):
    """
    Declarative spec; only validates structure and naming.
    No Kubernetes/Helm calls here.
    """
    namespace: Optional[str] = None
    charts: ChartsConfig
    qudittoSetup: QudittoSetup

    @field_validator("namespace")
    @classmethod
    def _v_ns(cls, v: Optional[str]) -> Optional[str]:
        return _name(v, "namespace") if v else v
