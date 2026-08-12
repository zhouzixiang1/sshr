"""Stable serialization of the selected factorisation Plan."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.contracts.codec import canonical_hex
from src.factor_plan import Plan, verify_plan_anf


PLAN_TRACE_SCHEMA = "xa.plan-trace.v1"


@dataclass(frozen=True)
class PlanNodeTrace:
    node_id: str
    parent_id: str | None
    edge: str
    kind: str
    terms_hex: tuple[str, ...]
    factor_hex: str
    affine_const: bool
    resource_cost: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlanTrace:
    schema_version: str
    root_id: str
    nodes: tuple[PlanNodeTrace, ...]

    @classmethod
    def from_plan(cls, plan: Plan) -> "PlanTrace":
        if not isinstance(plan, Plan):
            raise TypeError("plan must be src.factor_plan.Plan")
        verification = verify_plan_anf(plan)
        if not verification.ok:
            raise ValueError(
                f"cannot serialize invalid Plan: {verification.mismatches} ANF mismatch(es)"
            )

        nodes: list[PlanNodeTrace] = []

        def visit(node: Plan, node_id: str, parent_id: str | None, edge: str) -> None:
            if node.kind not in {"direct", "factor", "linear_factor"}:
                raise ValueError(f"unsupported plan kind: {node.kind!r}")
            if node.kind == "direct":
                if node.group is not None or node.rest is not None:
                    raise ValueError("direct Plan nodes cannot have children")
            elif node.group is None or node.rest is None:
                raise ValueError(f"{node.kind} Plan nodes require group and rest children")

            nodes.append(
                PlanNodeTrace(
                    node_id=node_id,
                    parent_id=parent_id,
                    edge=edge,
                    kind=node.kind,
                    terms_hex=tuple(canonical_hex(term) for term in sorted(node.terms)),
                    factor_hex=canonical_hex(int(node.factor)),
                    affine_const=bool(node.affine_const),
                    resource_cost={key: int(value) for key, value in asdict(node.cost).items()},
                )
            )
            if node.group is not None:
                visit(node.group, f"{node_id}.group", node_id, "group")
            if node.rest is not None:
                visit(node.rest, f"{node_id}.rest", node_id, "rest")

        visit(plan, "root", None, "root")
        trace = cls(schema_version=PLAN_TRACE_SCHEMA, root_id="root", nodes=tuple(nodes))
        trace.validate()
        return trace

    def validate(self) -> None:
        if self.schema_version != PLAN_TRACE_SCHEMA:
            raise ValueError(f"unsupported PlanTrace schema: {self.schema_version!r}")
        if not self.nodes:
            raise ValueError("PlanTrace must contain at least one node")
        by_id = {node.node_id: node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise ValueError("PlanTrace node ids must be unique")
        if self.root_id not in by_id:
            raise ValueError("PlanTrace root_id is missing")
        root = by_id[self.root_id]
        if root.parent_id is not None or root.edge != "root":
            raise ValueError("PlanTrace root must have parent_id=None and edge='root'")
        for node in self.nodes:
            if node.node_id == self.root_id:
                continue
            if node.parent_id not in by_id:
                raise ValueError(f"PlanTrace node {node.node_id!r} has missing parent")
            if node.edge not in {"group", "rest"}:
                raise ValueError(f"PlanTrace node {node.node_id!r} has invalid edge")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "root_id": self.root_id,
            "nodes": [node.to_dict() for node in self.nodes],
        }
