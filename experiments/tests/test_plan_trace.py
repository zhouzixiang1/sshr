"""Selected-Plan trace schema and deterministic ordering tests."""

from __future__ import annotations

from src.contracts.codec import canonical_json_bytes
from src.contracts.search import PLAN_TRACE_SCHEMA, PlanTrace
from src.factor_plan import Plan
from src.resource_model import ResourceCost


def _direct(terms: set[int], cost: int = 0) -> Plan:
    return Plan("direct", frozenset(terms), ResourceCost(T=cost, gates=len(terms)))


def test_direct_plan_trace_is_canonical() -> None:
    first = PlanTrace.from_plan(_direct({0x10, 0x2, 0x1}, cost=4))
    second = PlanTrace.from_plan(_direct({0x1, 0x10, 0x2}, cost=4))

    assert first.schema_version == PLAN_TRACE_SCHEMA
    assert first.root_id == "root"
    assert first.nodes[0].terms_hex == ("0x1", "0x2", "0x10")
    assert canonical_json_bytes(first.to_dict()) == canonical_json_bytes(second.to_dict())


def test_factor_plan_trace_uses_stable_preorder_ids() -> None:
    group = _direct({0x2}, cost=1)
    rest = _direct({0x4}, cost=2)
    plan = Plan(
        "factor",
        frozenset({0x3, 0x4}),
        ResourceCost(T=9, CNOT=7, gates=3),
        factor=0x1,
        group=group,
        rest=rest,
    )

    trace = PlanTrace.from_plan(plan)
    assert [node.node_id for node in trace.nodes] == ["root", "root.group", "root.rest"]
    assert [node.edge for node in trace.nodes] == ["root", "group", "rest"]
    assert trace.nodes[0].factor_hex == "0x1"


def test_linear_factor_plan_trace_preserves_affine_constant() -> None:
    group = _direct({0x2})
    rest = _direct({0x8})
    plan = Plan(
        "linear_factor",
        frozenset({0x3, 0x6, 0x8}),
        ResourceCost(gates=4),
        factor=0x5,
        group=group,
        rest=rest,
        affine_const=False,
    )

    trace = PlanTrace.from_plan(plan)
    assert trace.nodes[0].kind == "linear_factor"
    assert trace.nodes[0].factor_hex == "0x5"
    assert trace.nodes[0].affine_const is False
