"""Isolated multi-output Boolean-oracle sharing primitives for E6-MSO.

This module is deliberately outside :mod:`src`.  It does not change the
scalar ``synthesize(...)`` contract.  The MVP represents a vector Boolean
function by one algebraic-normal-form (ANF) set per output and emits the
reversible oracle

    |x, y, 0> -> |x, y xor f(x), 0>.

Selected shared actions are realised as compute--fanout--uncompute blocks.
One ancilla is sufficient for a shared monomial.  A semi-affine expression
``m(x) * (c xor xor_j x_j)`` uses two reusable ancillas.  The emitter never
uses more than two ancillas and exhaustively rejects overlapping term/output
footprints, so a covered ANF term cannot be toggled twice accidentally.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from numbers import Integral
from typing import Iterable, Sequence, TypeAlias

from src.bool_func import QuantumCircuit


FootprintEntry: TypeAlias = tuple[int, int]


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    converted = int(value)
    if converted < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return converted


def _canonical_targets(targets: Iterable[int]) -> tuple[int, ...]:
    raw = tuple(targets)
    converted = tuple(_integer(value, "target", minimum=0) for value in raw)
    if len(set(converted)) != len(converted):
        raise ValueError("shared-action targets must be unique")
    canonical = tuple(sorted(converted))
    if len(canonical) < 2:
        raise ValueError("a shared action requires at least two output targets")
    return canonical


def targets_to_mask(targets: Iterable[int]) -> int:
    """Encode output targets as an LSB-indexed action feature mask."""

    canonical = _canonical_targets(targets)
    return sum(1 << target for target in canonical)


def target_mask_to_targets(target_mask: int) -> tuple[int, ...]:
    """Decode an action target mask, requiring genuine shared fanout."""

    mask = _integer(target_mask, "target_mask", minimum=0)
    targets = tuple(index for index in range(mask.bit_length()) if mask & (1 << index))
    return _canonical_targets(targets)


def _target_subsets(targets: Iterable[int], min_fanout: int) -> tuple[tuple[int, ...], ...]:
    """Return every eligible target subset in ascending target-mask order."""

    available_mask = targets_to_mask(targets)
    masks: list[int] = []
    subset = available_mask
    while subset:
        if subset.bit_count() >= min_fanout:
            masks.append(subset)
        subset = (subset - 1) & available_mask
    return tuple(target_mask_to_targets(mask) for mask in sorted(masks))


def _old_to_new_permutation(
    old_to_new: Sequence[int] | Iterable[int], output_count: int
) -> tuple[int, ...]:
    permutation = tuple(
        _integer(value, "output permutation entry", minimum=0) for value in old_to_new
    )
    if len(permutation) != output_count or set(permutation) != set(range(output_count)):
        raise ValueError(
            "output permutation must map every old output index to one unique new index"
        )
    return permutation


def _old_to_new_input_permutation(
    old_to_new: Sequence[int] | Iterable[int], input_count: int
) -> tuple[int, ...]:
    permutation = tuple(
        _integer(value, "input permutation entry", minimum=0)
        for value in old_to_new
    )
    if len(permutation) != input_count or set(permutation) != set(range(input_count)):
        raise ValueError(
            "input permutation must map every old input index to one unique new index"
        )
    return permutation


def permute_monomial_inputs(
    monomial: int,
    old_to_new: Sequence[int] | Iterable[int],
    *,
    input_count: int,
) -> int:
    """Relabel one monomial mask by an old-input to new-input bijection."""

    mask = _integer(monomial, "monomial", minimum=0)
    if mask >= 1 << input_count:
        raise ValueError("monomial is outside the declared input domain")
    permutation = _old_to_new_input_permutation(old_to_new, input_count)
    result = 0
    for old, new in enumerate(permutation):
        if mask & (1 << old):
            result |= 1 << new
    return result


def xor_monomial_sets(*items: Iterable[int]) -> frozenset[int]:
    """Return the GF(2) symmetric difference of monomial-mask collections."""

    result: set[int] = set()
    for item in items:
        for raw_term in item:
            term = _integer(raw_term, "monomial", minimum=0)
            if term in result:
                result.remove(term)
            else:
                result.add(term)
    return frozenset(result)


def expand_semi_affine(
    base_monomial: int,
    affine_mask: int,
    affine_const: bool = False,
) -> frozenset[int]:
    """Expand ``base * (const xor variables(mask))`` in the Boolean ring.

    Multiplication is bitwise union of monomial supports.  Terms are toggled,
    rather than appended, because repeated monomials cancel over GF(2).  This
    detail matters when the base and affine-variable masks overlap.
    """

    base = _integer(base_monomial, "base_monomial", minimum=0)
    affine = _integer(affine_mask, "affine_mask", minimum=0)
    if not isinstance(affine_const, bool):
        raise TypeError("affine_const must be bool")

    terms: set[int] = set()

    def toggle(term: int) -> None:
        if term in terms:
            terms.remove(term)
        else:
            terms.add(term)

    if affine_const:
        toggle(base)
    remaining = affine
    while remaining:
        variable = remaining & -remaining
        toggle(base | variable)
        remaining ^= variable
    return frozenset(terms)


def _anf_from_truth_table(input_count: int, truth_table: int) -> frozenset[int]:
    width = 1 << input_count
    if truth_table < 0 or truth_table >= (1 << width):
        raise ValueError(
            f"truth table must fit exactly within 2**{input_count} Boolean values"
        )
    coefficients = [(truth_table >> x) & 1 for x in range(width)]
    for variable in range(input_count):
        bit = 1 << variable
        for mask in range(width):
            if mask & bit:
                coefficients[mask] ^= coefficients[mask ^ bit]
    return frozenset(mask for mask, coefficient in enumerate(coefficients) if coefficient)


@dataclass(frozen=True)
class VectorANF:
    """A vector Boolean function represented by one ANF monomial set/output."""

    input_count: int
    outputs: tuple[frozenset[int], ...]

    def __post_init__(self) -> None:
        input_count = _integer(self.input_count, "input_count", minimum=1)
        canonical_outputs = tuple(
            frozenset(_integer(term, "monomial", minimum=0) for term in terms)
            for terms in self.outputs
        )
        if not canonical_outputs:
            raise ValueError("VectorANF requires at least one output coordinate")
        maximum_mask = (1 << input_count) - 1
        for output_index, terms in enumerate(canonical_outputs):
            invalid = tuple(sorted(term for term in terms if term > maximum_mask))
            if invalid:
                raise ValueError(
                    f"output {output_index} contains monomial masks outside the "
                    f"{input_count}-variable domain: {invalid}"
                )
        object.__setattr__(self, "input_count", input_count)
        object.__setattr__(self, "outputs", canonical_outputs)

    @property
    def output_count(self) -> int:
        return len(self.outputs)

    @classmethod
    def from_truth_tables(
        cls,
        input_count: int,
        truth_tables: Sequence[int] | Iterable[int],
    ) -> "VectorANF":
        n = _integer(input_count, "input_count", minimum=1)
        tables = tuple(_integer(value, "truth_table", minimum=0) for value in truth_tables)
        if not tables:
            raise ValueError("truth_tables must contain at least one coordinate")
        return cls(n, tuple(_anf_from_truth_table(n, table) for table in tables))

    @classmethod
    def from_boolean_functions(cls, functions: Sequence[object]) -> "VectorANF":
        """Build from BooleanFunction-shaped objects without changing scalar APIs."""

        functions = tuple(functions)
        if not functions:
            raise ValueError("functions must contain at least one coordinate")
        first_n = _integer(getattr(functions[0], "n"), "functions[0].n", minimum=1)
        tables: list[int] = []
        for index, function in enumerate(functions):
            n = _integer(getattr(function, "n"), f"functions[{index}].n", minimum=1)
            if n != first_n:
                raise ValueError("all Boolean functions must have the same input width")
            tables.append(
                _integer(
                    getattr(function, "truth_table"),
                    f"functions[{index}].truth_table",
                    minimum=0,
                )
            )
        return cls.from_truth_tables(first_n, tables)

    @classmethod
    def from_value_table(
        cls,
        input_count: int,
        output_count: int,
        values: Sequence[int] | Iterable[int],
    ) -> "VectorANF":
        """Build from integer outputs ``S(0), S(1), ...`` in LSB bit order."""

        n = _integer(input_count, "input_count", minimum=1)
        m = _integer(output_count, "output_count", minimum=1)
        values = tuple(_integer(value, "value", minimum=0) for value in values)
        if len(values) != 1 << n:
            raise ValueError(f"value table must contain exactly {1 << n} entries")
        if any(value >= 1 << m for value in values):
            raise ValueError(f"every value must fit within output_count={m} bits")
        truth_tables = []
        for output in range(m):
            table = 0
            for x, value in enumerate(values):
                table |= ((value >> output) & 1) << x
            truth_tables.append(table)
        return cls.from_truth_tables(n, truth_tables)

    def evaluate_bits(self, x: int) -> tuple[int, ...]:
        x = _integer(x, "x", minimum=0)
        if x >= 1 << self.input_count:
            raise ValueError("x is outside the VectorANF input domain")
        return tuple(
            sum((x & monomial) == monomial for monomial in terms) & 1
            for terms in self.outputs
        )

    def evaluate_value(self, x: int) -> int:
        return sum(bit << index for index, bit in enumerate(self.evaluate_bits(x)))

    def evaluate(self, x: int) -> tuple[int, ...]:
        """Alias for :meth:`evaluate_bits`."""

        return self.evaluate_bits(x)

    def permute_outputs(
        self, old_to_new: Sequence[int] | Iterable[int]
    ) -> "VectorANF":
        """Relabel outputs using an explicit old-index to new-index bijection."""

        permutation = _old_to_new_permutation(old_to_new, self.output_count)
        permuted: list[frozenset[int] | None] = [None] * self.output_count
        for old, new in enumerate(permutation):
            permuted[new] = self.outputs[old]
        return VectorANF(
            self.input_count,
            tuple(terms for terms in permuted if terms is not None),
        )

    def permute_inputs(
        self, old_to_new: Sequence[int] | Iterable[int]
    ) -> "VectorANF":
        """Relabel input variables while preserving every output coordinate."""

        permutation = _old_to_new_input_permutation(
            old_to_new, self.input_count
        )
        return VectorANF(
            self.input_count,
            tuple(
                frozenset(
                    permute_monomial_inputs(
                        term,
                        permutation,
                        input_count=self.input_count,
                    )
                    for term in terms
                )
                for terms in self.outputs
            ),
        )


@dataclass(frozen=True)
class MonomialSharedAction:
    """Compute one monomial once and fan it out to two or more outputs."""

    monomial: int
    targets: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "monomial", _integer(self.monomial, "monomial"))
        object.__setattr__(self, "targets", _canonical_targets(self.targets))

    @property
    def kind(self) -> str:
        return "monomial"

    @property
    def target_mask(self) -> int:
        """LSB-indexed output subset carried by the action identity."""

        return sum(1 << target for target in self.targets)

    @property
    def polynomial_terms(self) -> frozenset[int]:
        return frozenset({self.monomial})

    @property
    def footprint(self) -> frozenset[FootprintEntry]:
        return frozenset((target, self.monomial) for target in self.targets)

    @property
    def ancilla_required(self) -> int:
        return 1

    @classmethod
    def from_target_mask(
        cls, monomial: int, target_mask: int
    ) -> "MonomialSharedAction":
        return cls(monomial, target_mask_to_targets(target_mask))

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "monomial": self.monomial,
            "targets": list(self.targets),
            "target_mask": self.target_mask,
            "polynomial_terms": sorted(self.polynomial_terms),
            "footprint": [list(item) for item in sorted(self.footprint)],
            "ancilla_required": self.ancilla_required,
        }


@dataclass(frozen=True)
class SemiAffineSharedAction:
    """Share ``base * (const xor variables(mask))`` across outputs."""

    base_monomial: int
    affine_mask: int
    affine_const: bool
    targets: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "base_monomial", _integer(self.base_monomial, "base_monomial")
        )
        object.__setattr__(self, "affine_mask", _integer(self.affine_mask, "affine_mask"))
        if not isinstance(self.affine_const, bool):
            raise TypeError("affine_const must be bool")
        object.__setattr__(self, "targets", _canonical_targets(self.targets))
        if not self.polynomial_terms:
            raise ValueError("the semi-affine expression cancels to the zero polynomial")

    @property
    def kind(self) -> str:
        return "semi_affine"

    @property
    def target_mask(self) -> int:
        """LSB-indexed output subset carried by the action identity."""

        return sum(1 << target for target in self.targets)

    @property
    def polynomial_terms(self) -> frozenset[int]:
        return expand_semi_affine(
            self.base_monomial, self.affine_mask, self.affine_const
        )

    @property
    def footprint(self) -> frozenset[FootprintEntry]:
        return frozenset(
            (target, term) for target in self.targets for term in self.polynomial_terms
        )

    @property
    def ancilla_required(self) -> int:
        return 2

    @classmethod
    def from_target_mask(
        cls,
        base_monomial: int,
        affine_mask: int,
        affine_const: bool,
        target_mask: int,
    ) -> "SemiAffineSharedAction":
        return cls(
            base_monomial,
            affine_mask,
            affine_const,
            target_mask_to_targets(target_mask),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "base_monomial": self.base_monomial,
            "affine_mask": self.affine_mask,
            "affine_const": self.affine_const,
            "targets": list(self.targets),
            "target_mask": self.target_mask,
            "polynomial_terms": sorted(self.polynomial_terms),
            "footprint": [list(item) for item in sorted(self.footprint)],
            "ancilla_required": self.ancilla_required,
        }


SharedAction: TypeAlias = MonomialSharedAction | SemiAffineSharedAction


def permute_action_outputs(
    action: SharedAction,
    old_to_new: Sequence[int] | Iterable[int],
    *,
    output_count: int,
) -> SharedAction:
    """Relabel an action consistently with :meth:`VectorANF.permute_outputs`."""

    permutation = _old_to_new_permutation(old_to_new, output_count)
    targets = tuple(sorted(permutation[target] for target in action.targets))
    if isinstance(action, MonomialSharedAction):
        return MonomialSharedAction(action.monomial, targets)
    if isinstance(action, SemiAffineSharedAction):
        return SemiAffineSharedAction(
            action.base_monomial,
            action.affine_mask,
            action.affine_const,
            targets,
        )
    raise TypeError("unsupported E6 shared-action type")


def permute_action_inputs(
    action: SharedAction,
    old_to_new: Sequence[int] | Iterable[int],
    *,
    input_count: int,
) -> SharedAction:
    """Relabel an action consistently with :meth:`VectorANF.permute_inputs`."""

    permutation = _old_to_new_input_permutation(old_to_new, input_count)
    if isinstance(action, MonomialSharedAction):
        return MonomialSharedAction(
            permute_monomial_inputs(
                action.monomial, permutation, input_count=input_count
            ),
            action.targets,
        )
    if isinstance(action, SemiAffineSharedAction):
        return SemiAffineSharedAction(
            permute_monomial_inputs(
                action.base_monomial, permutation, input_count=input_count
            ),
            permute_monomial_inputs(
                action.affine_mask, permutation, input_count=input_count
            ),
            action.affine_const,
            action.targets,
        )
    raise TypeError("unsupported E6 shared-action type")


def action_polynomial_terms(action: SharedAction) -> frozenset[int]:
    if not isinstance(action, (MonomialSharedAction, SemiAffineSharedAction)):
        raise TypeError("unsupported E6 shared-action type")
    return action.polynomial_terms


def action_footprint(action: SharedAction) -> frozenset[FootprintEntry]:
    return action.footprint


def actions_conflict(left: SharedAction, right: SharedAction) -> bool:
    """Return whether two actions would cover the same output/ANF term."""

    return bool(action_footprint(left) & action_footprint(right))


def footprint_conflicts(actions: Sequence[SharedAction]) -> tuple[tuple[bool, ...], ...]:
    actions = tuple(actions)
    return tuple(
        tuple(index != other and actions_conflict(action, actions[other]) for other in range(len(actions)))
        for index, action in enumerate(actions)
    )


def validate_shared_action(vector: VectorANF, action: SharedAction) -> None:
    maximum_mask = (1 << vector.input_count) - 1
    terms = action_polynomial_terms(action)
    if any(term > maximum_mask for term in terms):
        raise ValueError("shared action contains a monomial outside the input domain")
    if isinstance(action, SemiAffineSharedAction):
        if action.base_monomial > maximum_mask or action.affine_mask > maximum_mask:
            raise ValueError("semi-affine masks are outside the input domain")
    for target, term in action_footprint(action):
        if target >= vector.output_count:
            raise ValueError(f"shared-action target {target} is outside the output domain")
        if term not in vector.outputs[target]:
            raise ValueError(
                f"shared action is not contained in output {target}: missing ANF term {term}"
            )


def enumerate_monomial_shared_actions(
    vector: VectorANF,
    *,
    min_fanout: int = 2,
) -> tuple[MonomialSharedAction, ...]:
    fanout = _integer(min_fanout, "min_fanout", minimum=2)
    appearances: dict[int, list[int]] = {}
    for output, terms in enumerate(vector.outputs):
        for term in terms:
            appearances.setdefault(term, []).append(output)
    actions = [
        MonomialSharedAction(term, target_subset)
        for term, targets in sorted(appearances.items())
        if len(targets) >= fanout
        for target_subset in _target_subsets(targets, fanout)
    ]
    return tuple(sorted(actions, key=lambda action: (action.monomial, action.target_mask)))


def enumerate_semi_affine_shared_actions(
    vector: VectorANF,
    *,
    min_fanout: int = 2,
    max_affine_weight: int = 3,
) -> tuple[SemiAffineSharedAction, ...]:
    """Enumerate small genuine semi-affine actions for development fixtures.

    The exhaustive generator is intentionally bounded to affine factors with
    at most ``max_affine_weight`` variable/constant terms.  Equivalent GF(2)
    expansions are deduplicated; this is an MVP candidate generator, not an AI
    policy head or a production-scale search routine.
    """

    fanout = _integer(min_fanout, "min_fanout", minimum=2)
    maximum_weight = _integer(max_affine_weight, "max_affine_weight", minimum=2)
    width = 1 << vector.input_count
    best_by_expansion: dict[frozenset[int], tuple[int, int, bool, tuple[int, ...]]] = {}
    for base in range(width):
        for affine_mask in range(width):
            for affine_const in (False, True):
                factor_weight = affine_mask.bit_count() + int(affine_const)
                if not 2 <= factor_weight <= maximum_weight:
                    continue
                terms = expand_semi_affine(base, affine_mask, affine_const)
                if len(terms) < 2:
                    continue
                targets = tuple(
                    output
                    for output, output_terms in enumerate(vector.outputs)
                    if terms <= output_terms
                )
                if len(targets) < fanout:
                    continue
                candidate = (base, affine_mask, affine_const, targets)
                previous = best_by_expansion.get(terms)
                if previous is None or candidate[:3] < previous[:3]:
                    best_by_expansion[terms] = candidate

    actions = []
    for terms, (base, affine_mask, affine_const, targets) in best_by_expansion.items():
        for target_subset in _target_subsets(targets, fanout):
            action = SemiAffineSharedAction(
                base, affine_mask, affine_const, target_subset
            )
            if action.polynomial_terms != terms:  # pragma: no cover - construction invariant
                raise RuntimeError("semi-affine expansion changed during enumeration")
            actions.append(action)
    return tuple(
        sorted(
            actions,
            key=lambda action: (
                tuple(sorted(action.polynomial_terms)),
                action.target_mask,
                action.base_monomial,
                action.affine_mask,
                action.affine_const,
            ),
        )
    )


@dataclass(frozen=True)
class SharedOracleLayout:
    input_wires: tuple[int, ...]
    output_wires: tuple[int, ...]
    ancilla_wires: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {key: list(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class SharedOracleProgram:
    vector: VectorANF
    actions: tuple[SharedAction, ...]
    residual_outputs: tuple[frozenset[int], ...]
    covered_footprint: frozenset[FootprintEntry]
    circuit: QuantumCircuit
    layout: SharedOracleLayout
    ancilla_count: int
    max_ancilla: int

    @property
    def gate_count(self) -> int:
        return len(self.circuit.gates)

    @property
    def explicit_workspace_peak(self) -> int:
        """Whole-program peak of reusable E6 workspace wires (never per action)."""

        return self.ancilla_count

    def to_dict(self) -> dict[str, object]:
        return {
            "input_count": self.vector.input_count,
            "output_count": self.vector.output_count,
            "actions": [action.to_dict() for action in self.actions],
            "residual_outputs": [sorted(terms) for terms in self.residual_outputs],
            "covered_footprint": [list(item) for item in sorted(self.covered_footprint)],
            "layout": self.layout.to_dict(),
            "ancilla_count": self.ancilla_count,
            "explicit_workspace_peak": self.explicit_workspace_peak,
            "max_ancilla": self.max_ancilla,
            "gate_count": self.gate_count,
            "resource_contract": {
                "layer": "abstract_logical_X_CNOT_MCT",
                "explicit_workspace_peak_is_whole_program": True,
                "explicit_workspace_peak_limit": 2,
                "mct_decomposition_implicit_ancillas_included": False,
                "exact_hardware_resource_claim": False,
            },
        }


def _variables(mask: int) -> list[int]:
    return [index for index in range(mask.bit_length()) if mask & (1 << index)]


def _toggle_monomial(circuit: QuantumCircuit, monomial: int, target: int) -> None:
    circuit.add_mct(_variables(monomial), target)


def _emit_shared_action(
    circuit: QuantumCircuit,
    action: SharedAction,
    output_wires: tuple[int, ...],
    ancilla_wires: tuple[int, ...],
) -> None:
    if isinstance(action, MonomialSharedAction):
        shared_wire = ancilla_wires[0]
        _toggle_monomial(circuit, action.monomial, shared_wire)
        for target in action.targets:
            circuit.add_cnot(shared_wire, output_wires[target])
        _toggle_monomial(circuit, action.monomial, shared_wire)
        return

    affine_wire, product_wire = ancilla_wires[:2]
    if action.affine_const:
        circuit.add_x(affine_wire)
    for variable in _variables(action.affine_mask):
        circuit.add_cnot(variable, affine_wire)
    circuit.add_mct(_variables(action.base_monomial) + [affine_wire], product_wire)
    for target in action.targets:
        circuit.add_cnot(product_wire, output_wires[target])
    circuit.add_mct(_variables(action.base_monomial) + [affine_wire], product_wire)
    for variable in reversed(_variables(action.affine_mask)):
        circuit.add_cnot(variable, affine_wire)
    if action.affine_const:
        circuit.add_x(affine_wire)


def emit_compute_fanout_uncompute(
    vector: VectorANF,
    actions: Sequence[SharedAction] | Iterable[SharedAction] = (),
    *,
    max_ancilla: int = 2,
) -> SharedOracleProgram:
    """Emit selected sharing blocks plus direct residual ANF terms.

    The selected action footprints must be pairwise disjoint and contained in
    the vector ANF.  The same one- or two-wire ancilla workspace is reused
    sequentially across blocks.
    """

    maximum = _integer(max_ancilla, "max_ancilla", minimum=0)
    if maximum > 2:
        raise ValueError("E6-MSO MVP fixes max_ancilla at no more than 2")
    selected = tuple(actions)
    for action in selected:
        validate_shared_action(vector, action)

    covered: set[FootprintEntry] = set()
    for action in selected:
        overlap = covered & action_footprint(action)
        if overlap:
            raise ValueError(
                "selected shared actions have a footprint conflict: "
                f"{tuple(sorted(overlap))}"
            )
        covered.update(action_footprint(action))

    required = max((action.ancilla_required for action in selected), default=0)
    if required > maximum:
        raise ValueError(
            f"selected actions require {required} ancillas, exceeding max_ancilla={maximum}"
        )
    if required > 2:  # pragma: no cover - guarded by the closed action types
        raise RuntimeError("E6-MSO action exceeded the fixed two-ancilla contract")

    n = vector.input_count
    m = vector.output_count
    layout = SharedOracleLayout(
        input_wires=tuple(range(n)),
        output_wires=tuple(range(n, n + m)),
        ancilla_wires=tuple(range(n + m, n + m + required)),
    )
    circuit = QuantumCircuit(n + m + required)
    for action in selected:
        _emit_shared_action(circuit, action, layout.output_wires, layout.ancilla_wires)

    residual = tuple(
        frozenset(
            term
            for term in terms
            if (output, term) not in covered
        )
        for output, terms in enumerate(vector.outputs)
    )
    for output, terms in enumerate(residual):
        target_wire = layout.output_wires[output]
        for term in sorted(terms):
            _toggle_monomial(circuit, term, target_wire)

    return SharedOracleProgram(
        vector=vector,
        actions=selected,
        residual_outputs=residual,
        covered_footprint=frozenset(covered),
        circuit=circuit,
        layout=layout,
        ancilla_count=required,
        max_ancilla=maximum,
    )


emit_shared_oracle = emit_compute_fanout_uncompute


@dataclass(frozen=True)
class VectorOracleSemanticVerification:
    ok: bool
    assignments_checked: int
    expected_assignments: int
    input_mismatches: int
    output_mismatches: int
    ancilla_mismatches: int
    ancilla_reset: bool
    arbitrary_y_covered: bool
    max_ancilla_observed: int
    first_failure: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def verify_vector_oracle_semantics(
    program: SharedOracleProgram,
    *,
    max_assignments: int = 1 << 16,
) -> VectorOracleSemanticVerification:
    """Exhaustively verify every ``x`` and every initial output register ``y``."""

    limit = _integer(max_assignments, "max_assignments", minimum=1)
    vector = program.vector
    expected_assignments = 1 << (vector.input_count + vector.output_count)
    if expected_assignments > limit:
        raise ValueError(
            "exhaustive semantic verification refused: "
            f"{expected_assignments} assignments exceed max_assignments={limit}"
        )
    if program.ancilla_count > 2:
        raise ValueError("program violates the fixed two-ancilla E6-MSO contract")
    expected_qubits = vector.input_count + vector.output_count + program.ancilla_count
    if program.circuit.n_qubits != expected_qubits:
        raise ValueError("program circuit width does not match its declared layout")

    input_mismatches = 0
    output_mismatches = 0
    ancilla_mismatches = 0
    first_failure: dict[str, object] | None = None
    checked = 0
    for x in range(1 << vector.input_count):
        x_bits = [(x >> bit) & 1 for bit in range(vector.input_count)]
        function_bits = vector.evaluate_bits(x)
        for y in range(1 << vector.output_count):
            y_bits = [(y >> bit) & 1 for bit in range(vector.output_count)]
            initial = x_bits + y_bits + [0] * program.ancilla_count
            observed = program.circuit.simulate(initial)
            expected_outputs = [
                y_bit ^ function_bit
                for y_bit, function_bit in zip(y_bits, function_bits)
            ]
            observed_inputs = observed[: vector.input_count]
            observed_outputs = observed[
                vector.input_count : vector.input_count + vector.output_count
            ]
            observed_ancillas = observed[-program.ancilla_count :] if program.ancilla_count else []
            input_bad = observed_inputs != x_bits
            output_bad = observed_outputs != expected_outputs
            ancilla_bad = any(observed_ancillas)
            input_mismatches += int(input_bad)
            output_mismatches += int(output_bad)
            ancilla_mismatches += int(ancilla_bad)
            checked += 1
            if first_failure is None and (input_bad or output_bad or ancilla_bad):
                first_failure = {
                    "x": x,
                    "y": y,
                    "initial": initial,
                    "observed": observed,
                    "expected_outputs": expected_outputs,
                }

    ok = not (input_mismatches or output_mismatches or ancilla_mismatches)
    return VectorOracleSemanticVerification(
        ok=ok,
        assignments_checked=checked,
        expected_assignments=expected_assignments,
        input_mismatches=input_mismatches,
        output_mismatches=output_mismatches,
        ancilla_mismatches=ancilla_mismatches,
        ancilla_reset=ancilla_mismatches == 0,
        arbitrary_y_covered=checked == expected_assignments,
        max_ancilla_observed=program.ancilla_count,
        first_failure=first_failure,
    )


verify_exhaustive_oracle_semantics = verify_vector_oracle_semantics


__all__ = [
    "FootprintEntry",
    "MonomialSharedAction",
    "SemiAffineSharedAction",
    "SharedAction",
    "SharedOracleLayout",
    "SharedOracleProgram",
    "VectorANF",
    "VectorOracleSemanticVerification",
    "action_footprint",
    "action_polynomial_terms",
    "actions_conflict",
    "emit_compute_fanout_uncompute",
    "emit_shared_oracle",
    "enumerate_monomial_shared_actions",
    "enumerate_semi_affine_shared_actions",
    "expand_semi_affine",
    "footprint_conflicts",
    "permute_action_outputs",
    "target_mask_to_targets",
    "targets_to_mask",
    "validate_shared_action",
    "verify_exhaustive_oracle_semantics",
    "verify_vector_oracle_semantics",
    "xor_monomial_sets",
]
