import subprocess
import sys

from harnessos.installation import check, setup


def make_bundle(path):
    (path / "instructions").mkdir(parents=True)
    (path / "instructions/AGENTS.md").write_text("# Shared HarnessOS instructions\n")
    (path / "adapters/cursor").mkdir(parents=True)
    (path / "adapters/cursor/harnessos.mdc").write_text("---\nalwaysApply: true\n---\n")
    (path / "skills/network-audit").mkdir(parents=True)
    (path / "skills/network-audit/SKILL.md").write_text(
        "---\nname: network-audit\ndescription: Audit network scanners\n---\n"
    )


def test_nested_bundle_setup_links_from_consumer_root_and_is_idempotent(tmp_path):
    project = tmp_path / "network-scanner"
    project.mkdir()
    bundle = project / "harnessos"
    make_bundle(bundle)

    result = setup(project)
    assert result.ok
    assert {"AGENTS.md", "CLAUDE.md", ".agents/skills/network-audit",
            ".opencode/skills/network-audit", ".claude/skills/network-audit",
            ".cursor/rules/harnessos.mdc"} <= set(result.created)
    assert (project / "AGENTS.md").resolve() == (bundle / "instructions/AGENTS.md").resolve()
    assert (project / ".opencode/skills/network-audit/SKILL.md").read_text().startswith("---")
    assert check(project).ok

    second = setup(project)
    assert second.ok
    assert not second.created
    assert len(second.present) == 6


def test_setup_preserves_project_instruction_and_same_named_skill(tmp_path):
    project = tmp_path / "project"
    bundle = project / "harnessos"
    project.mkdir()
    make_bundle(bundle)
    (project / "AGENTS.md").write_text("# Project-owned rules\n")
    existing_skill = project / ".agents/skills/network-audit"
    existing_skill.mkdir(parents=True)
    (existing_skill / "SKILL.md").write_text("# Project skill\n")

    result = setup(project)
    assert not result.ok
    assert any("AGENTS.md" in conflict for conflict in result.conflicts)
    assert any(".agents/skills/network-audit" in conflict for conflict in result.conflicts)
    assert (project / "AGENTS.md").read_text() == "# Project-owned rules\n"
    assert (existing_skill / "SKILL.md").read_text() == "# Project skill\n"
    assert (project / "CLAUDE.md").is_symlink()
    assert (project / ".opencode/skills/network-audit").is_symlink()


def test_global_package_defaults_and_cli_setup_check_end_to_end(tmp_path):
    project = tmp_path / "clean-project"
    project.mkdir()
    setup_command = [sys.executable, "-m", "harnessos.cli", "setup", "--repo", str(project)]
    installed = subprocess.run(setup_command, capture_output=True, text=True, check=False)
    assert installed.returncode == 0, installed.stderr
    assert "CREATED AGENTS.md" in installed.stdout

    checked = subprocess.run([sys.executable, "-m", "harnessos.cli", "check", "--repo", str(project)],
                             capture_output=True, text=True, check=False)
    assert checked.returncode == 0, checked.stderr
    assert "HarnessOS check complete" in checked.stdout
    assert (project / "AGENTS.md").resolve().name == "AGENTS.md"


def test_invalid_explicit_bundle_does_not_silently_use_global_defaults(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    invalid_bundle = tmp_path / "not-harnessos"
    invalid_bundle.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "harnessos.cli", "setup", "--repo", str(project),
         "--bundle", str(invalid_bundle)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert "Not a HarnessOS bundle" in result.stderr
    assert not (project / "AGENTS.md").exists()
