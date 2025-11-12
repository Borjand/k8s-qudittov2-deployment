from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re

# -----------------------------------------------------------------------------
# Allowed naming pattern for identifiers:
#   - letters (upper/lower), digits, hyphen (-), underscore (_)
#   - This is intentionally more relaxed than Kubernetes DNS-1123 because
#     you requested underscores to be allowed (DNS-1123 would forbid them).
#   - If later you want to align to DNS-1123, just tighten the regex here.
# -----------------------------------------------------------------------------
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _name(v: str, what: str) -> str:
    """Validate allowed characters in identifiers (guidance-level error message)."""
    if not NAME_RE.match(v):
        raise ValueError(
            f"{what} must include only letters, digits, hyphen (-) and underscore (_): {v!r}"
        )
    return v


class SinglePlacement(BaseModel):
    """Placement for one Quditto component (controller or orchestrator)."""
    nodek8s: str

    @field_validator("nodek8s")
    @classmethod
    def _v_nodek8s(cls, v: str) -> str:
        # Kubernetes node name you intend to target for this component.
        # We validate against the relaxed pattern defined above.
        return _name(v, "nodek8s")


class QNode(BaseModel):
    """Definition of a Quditto node with its target Kubernetes node."""
    name: str
    nodek8s: str

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        # qnode identifier; must be unique across the qnodes list.
        return _name(v, "qnode.name")

    @field_validator("nodek8s")
    @classmethod
    def _v_nodek8s(cls, v: str) -> str:
        # target Kubernetes node for this qnode.
        return _name(v, "qnode.nodek8s")


class QudittoDeploySpec(BaseModel):
    """
    Declarative spec for deploying Quditto components onto an existing Kubernetes cluster.

    This model *only* validates YAML structure and naming conventions.
    There is *no* cluster/Helm interaction here — we keep the CLI decoupled and safe.
    """
    namespace: Optional[str] = None
    qcontroller: SinglePlacement
    # If you always need to force an orchestrator node, make this non-optional.
    qorchestrator: Optional[SinglePlacement] = None
    qnodes: List[QNode] = Field(default_factory=list)

    @field_validator("namespace")
    @classmethod
    def _v_namespace(cls, v: Optional[str]) -> Optional[str]:
        # Namespace is optional; if provided, validate with the relaxed pattern.
        if v is None:
            return v
        return _name(v, "namespace")

    @field_validator("qnodes")
    @classmethod
    def _unique_names(cls, items: List[QNode]) -> List[QNode]:
        # Ensure qnode names are unique to avoid ambiguous releases later on.
        seen = set()
        for it in items:
            if it.name in seen:
                raise ValueError(f"duplicated qnode name: {it.name}")
            seen.add(it.name)
        return items
