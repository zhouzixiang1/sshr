"""Atomic, checksum-verified artifact bundles for experiments."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from src.contracts.codec import canonical_json_bytes, sha256_bytes, sha256_file


BUNDLE_MANIFEST_SCHEMA = "xa.artifact-bundle.v1"
MANIFEST_NAME = "artifacts.manifest.json"
CHECKSUM_NAME = "checksums.sha256"


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError("artifact path must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith(("/", "\\")):
        raise ValueError("artifact path must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("artifact path must not contain empty, '.' or '..' segments")
    if "\\" in value:
        raise ValueError("artifact paths must use POSIX separators")
    if path.as_posix() in {MANIFEST_NAME, CHECKSUM_NAME}:
        raise ValueError(f"{path.as_posix()} is reserved by the bundle format")
    return path


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


@dataclass(frozen=True)
class ArtifactRef:
    role: str
    relative_path: str
    media_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class BundleVerification:
    ok: bool
    errors: tuple[str, ...]
    artifacts: tuple[ArtifactRef, ...]


class ArtifactBundleWriter:
    """Create one immutable run directory without implicit overwrite."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        if self.run_dir.exists():
            raise FileExistsError(f"artifact bundle already exists: {self.run_dir}")
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self._refs: list[ArtifactRef] = []
        self._roles: set[str] = set()
        self._paths: set[str] = set()
        self._finalized = False

    def add_bytes(
        self,
        role: str,
        relative_path: str,
        payload: bytes,
        media_type: str = "application/octet-stream",
    ) -> ArtifactRef:
        if self._finalized:
            raise RuntimeError("artifact bundle is already finalized")
        if not isinstance(role, str) or not role:
            raise ValueError("artifact role must be a non-empty string")
        if role in self._roles:
            raise ValueError(f"duplicate artifact role: {role}")
        safe_path = _safe_relative_path(relative_path).as_posix()
        if safe_path in self._paths:
            raise ValueError(f"duplicate artifact path: {safe_path}")
        if not isinstance(payload, bytes):
            raise TypeError("artifact payload must be bytes")
        if not isinstance(media_type, str) or not media_type:
            raise ValueError("media_type must be a non-empty string")

        destination = self.run_dir.joinpath(*PurePosixPath(safe_path).parts)
        _atomic_write(destination, payload)
        ref = ArtifactRef(
            role=role,
            relative_path=safe_path,
            media_type=media_type,
            size_bytes=len(payload),
            sha256=sha256_bytes(payload),
        )
        self._refs.append(ref)
        self._roles.add(role)
        self._paths.add(safe_path)
        return ref

    def add_text(
        self,
        role: str,
        relative_path: str,
        text: str,
        media_type: str = "text/plain; charset=utf-8",
    ) -> ArtifactRef:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return self.add_bytes(role, relative_path, normalized.encode("utf-8"), media_type)

    def add_json(self, role: str, relative_path: str, value: Any) -> ArtifactRef:
        return self.add_bytes(
            role,
            relative_path,
            canonical_json_bytes(value),
            "application/json",
        )

    def finalize(self, *, bundle_metadata: dict[str, Any] | None = None) -> tuple[ArtifactRef, ...]:
        if self._finalized:
            raise RuntimeError("artifact bundle is already finalized")
        refs = tuple(sorted(self._refs, key=lambda ref: ref.relative_path))
        manifest = {
            "schema_version": BUNDLE_MANIFEST_SCHEMA,
            "bundle_metadata": bundle_metadata or {},
            "artifacts": [asdict(ref) for ref in refs],
        }
        manifest_payload = canonical_json_bytes(manifest)
        _atomic_write(self.run_dir / MANIFEST_NAME, manifest_payload)

        checksum_paths = [ref.relative_path for ref in refs] + [MANIFEST_NAME]
        checksum_lines = [
            f"{sha256_file(self.run_dir.joinpath(*PurePosixPath(path).parts))}  {path}"
            for path in checksum_paths
        ]
        _atomic_write(
            self.run_dir / CHECKSUM_NAME,
            ("\n".join(checksum_lines) + "\n").encode("utf-8"),
        )
        self._finalized = True
        return refs


def _parse_checksums(path: Path, errors: list[str]) -> dict[str, str]:
    checksums: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {CHECKSUM_NAME}: {exc}")
        return checksums
    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        try:
            digest, relative_path = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed checksum line {line_number}")
            continue
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            errors.append(f"invalid SHA-256 on checksum line {line_number}")
            continue
        try:
            safe_path = _safe_relative_path(relative_path).as_posix()
        except ValueError as exc:
            # The bundle manifest itself is a reserved but expected checksum target.
            if relative_path == MANIFEST_NAME:
                safe_path = relative_path
            else:
                errors.append(f"unsafe checksum path on line {line_number}: {exc}")
                continue
        if safe_path in checksums:
            errors.append(f"duplicate checksum path: {safe_path}")
            continue
        checksums[safe_path] = digest
    return checksums


def verify_bundle(
    run_dir: str | Path,
    *,
    required_roles: Iterable[str] = (),
) -> BundleVerification:
    root = Path(run_dir)
    errors: list[str] = []
    refs: list[ArtifactRef] = []
    manifest_path = root / MANIFEST_NAME
    checksum_path = root / CHECKSUM_NAME
    if not root.is_dir():
        return BundleVerification(False, (f"bundle directory is missing: {root}",), ())
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return BundleVerification(False, (f"cannot read {MANIFEST_NAME}: {exc}",), ())
    if manifest.get("schema_version") != BUNDLE_MANIFEST_SCHEMA:
        errors.append("unsupported or missing artifact bundle schema")

    seen_roles: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw in enumerate(manifest.get("artifacts", [])):
        try:
            ref = ArtifactRef(
                role=str(raw["role"]),
                relative_path=_safe_relative_path(str(raw["relative_path"])).as_posix(),
                media_type=str(raw["media_type"]),
                size_bytes=int(raw["size_bytes"]),
                sha256=str(raw["sha256"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid artifact record {index}: {exc}")
            continue
        if ref.role in seen_roles:
            errors.append(f"duplicate artifact role in manifest: {ref.role}")
        if ref.relative_path in seen_paths:
            errors.append(f"duplicate artifact path in manifest: {ref.relative_path}")
        seen_roles.add(ref.role)
        seen_paths.add(ref.relative_path)
        refs.append(ref)

        file_path = root.joinpath(*PurePosixPath(ref.relative_path).parts)
        if not file_path.is_file():
            errors.append(f"artifact is missing: {ref.relative_path}")
            continue
        if file_path.stat().st_size != ref.size_bytes:
            errors.append(f"artifact size mismatch: {ref.relative_path}")
        if sha256_file(file_path) != ref.sha256:
            errors.append(f"artifact SHA-256 mismatch: {ref.relative_path}")

    missing_roles = sorted(set(required_roles) - seen_roles)
    if missing_roles:
        errors.append(f"missing required artifact roles: {', '.join(missing_roles)}")

    checksums = _parse_checksums(checksum_path, errors)
    expected_checksum_paths = seen_paths | {MANIFEST_NAME}
    if set(checksums) != expected_checksum_paths:
        missing = sorted(expected_checksum_paths - set(checksums))
        extra = sorted(set(checksums) - expected_checksum_paths)
        if missing:
            errors.append(f"missing checksum entries: {', '.join(missing)}")
        if extra:
            errors.append(f"unexpected checksum entries: {', '.join(extra)}")
    for relative_path, expected in checksums.items():
        target = root / relative_path
        if target.is_file() and sha256_file(target) != expected:
            errors.append(f"checksum mismatch: {relative_path}")

    allowed_files = seen_paths | {MANIFEST_NAME, CHECKSUM_NAME}
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    extras = sorted(actual_files - allowed_files)
    if extras:
        errors.append(f"unlisted artifact files: {', '.join(extras)}")

    return BundleVerification(not errors, tuple(errors), tuple(refs))
