"""Install and validate HarnessOS instructions and skills in a repository."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class Bundle:
    root: Path
    instructions: Path
    skills: Path
    cursor_rule: Path


@dataclass
class InstallReport:
    bundle_source: str = ""
    created: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.conflicts


def resolve_bundle(repository: Path, bundle_path: Path | None = None) -> Bundle:
    """Choose an explicit, nested, checkout-local, or packaged HarnessOS bundle."""
    repository = repository.resolve()
    candidates: list[Path] = []
    if bundle_path is not None:
        candidates.append(bundle_path.expanduser().resolve())
        bundle = _bundle_at(candidates[0])
        if bundle is None:
            raise ValueError(f"Not a HarnessOS bundle (expected instructions/AGENTS.md, skills/, and adapters/cursor/harnessos.mdc): {candidates[0]}")
        return bundle
    else:
        candidates.extend((repository / "harnessos", repository))

    for candidate in candidates:
        bundle = _bundle_at(candidate)
        if bundle is not None:
            return bundle

    packaged = Path(__file__).resolve().parent / "defaults"
    bundle = _bundle_at(packaged)
    if bundle is None:
        raise FileNotFoundError(f"HarnessOS packaged instructions or skills are missing under {packaged}")
    return bundle


def setup(repository: Path, bundle_path: Path | None = None) -> InstallReport:
    """Link shared instructions and skills into paths recognized by supported agents.

    Existing project-authored files are never replaced. Same-named skill conflicts
    are reported individually while unrelated links are still installed.
    """
    repository = repository.expanduser().resolve()
    if not repository.is_dir():
        raise NotADirectoryError(f"Project root does not exist or is not a directory: {repository}")
    bundle = resolve_bundle(repository, bundle_path)
    report = InstallReport(bundle_source=str(bundle.root))

    for relative in (Path("AGENTS.md"), Path("CLAUDE.md")):
        _link(repository / relative, bundle.instructions, repository, report)

    for relative in (Path(".agents/skills"), Path(".opencode/skills"), Path(".claude/skills")):
        destination = repository / relative
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            report.conflicts.append(f"{relative}: cannot create skill directory ({exc})")
            continue
        for skill in sorted(bundle.skills.iterdir()):
            if not skill.is_dir():
                continue
            _link(destination / skill.name, skill, repository, report)

    _link(repository / ".cursor/rules/harnessos.mdc", bundle.cursor_rule, repository, report)
    return report


def check(repository: Path, bundle_path: Path | None = None) -> InstallReport:
    """Validate expected HarnessOS links without changing the project."""
    repository = repository.expanduser().resolve()
    bundle = resolve_bundle(repository, bundle_path)
    report = InstallReport(bundle_source=str(bundle.root))
    expected: list[tuple[Path, Path]] = [
        (repository / "AGENTS.md", bundle.instructions),
        (repository / "CLAUDE.md", bundle.instructions),
        (repository / ".cursor/rules/harnessos.mdc", bundle.cursor_rule),
    ]
    for relative in (Path(".agents/skills"), Path(".opencode/skills"), Path(".claude/skills")):
        for skill in sorted(bundle.skills.iterdir()):
            if skill.is_dir():
                expected.append((repository / relative / skill.name, skill))

    for destination, source in expected:
        if _points_to(destination, source):
            report.present.append(_display(destination, repository))
        else:
            report.conflicts.append(f"{_display(destination, repository)}: missing or not linked to {source}")
    return report


def _bundle_at(root: Path) -> Bundle | None:
    root = root.resolve()
    # A checked-out repo uses top-level skills; the installed package uses its
    # packaged defaults directory with the same stable layout.
    instructions = root / "instructions" / "AGENTS.md"
    skills = root / "skills"
    cursor_rule = root / "adapters" / "cursor" / "harnessos.mdc"
    if not cursor_rule.is_file() and root.name == "defaults":
        cursor_rule = root / "adapters" / "cursor" / "harnessos.mdc"
    if instructions.is_file() and skills.is_dir() and cursor_rule.is_file():
        return Bundle(root=root, instructions=instructions.resolve(), skills=skills.resolve(),
                      cursor_rule=cursor_rule.resolve())
    return None


def _link(destination: Path, source: Path, repository: Path, report: InstallReport) -> None:
    relative_name = _display(destination, repository)
    if _points_to(destination, source):
        report.present.append(relative_name)
        return
    if destination.exists() or destination.is_symlink():
        report.conflicts.append(f"{relative_name}: existing project content preserved")
        return
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        report.conflicts.append(f"{relative_name}: cannot create parent directory ({exc})")
        return
    # Relative links keep a vendored bundle portable when the project is moved.
    target = os.path.relpath(source, destination.parent)
    try:
        destination.symlink_to(target, target_is_directory=source.is_dir())
    except OSError as exc:
        report.conflicts.append(f"{relative_name}: unable to create symlink ({exc})")
        return
    report.created.append(relative_name)


def _points_to(destination: Path, source: Path) -> bool:
    return destination.is_symlink() and destination.resolve(strict=False) == source.resolve(strict=False)


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
