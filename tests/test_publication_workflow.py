"""Keep shared publication and Pages contracts explicit in this connector."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _workflow(name: str):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def _actions_on(workflow: dict):
    # PyYAML's YAML 1.1 reader represents the Actions ``on`` key as True.
    return workflow["on"] if "on" in workflow else workflow[True]


def test_pages_publishes_spec_dashboard_and_dispatches_manual_refresh():
    workflow = _workflow("pages.yml")
    publisher = workflow["jobs"]["publish-pages"]
    actions = _actions_on(workflow)
    push = actions["push"]

    assert publisher["uses"] == (
        "Knuckles-Team/pipelines/.github/workflows/pages_pipeline.yml@main"
    )
    assert publisher["with"] == {
        "content_source": "docs",
        "spec_dashboard_enabled": True,
        "spec_dashboard_config": ".config/spec-dashboard.json",
    }
    assert "workflow_dispatch" in actions
    assert {
        "docs/**",
        "mkdocs.yml",
        "README.md",
        "specs/**",
        ".config/spec-dashboard.json",
        ".github/workflows/pages.yml",
    } <= set(push["paths"])

    config = json.loads((ROOT / ".config/spec-dashboard.json").read_text())
    assert config == {
        "version": 1,
        "sources": [{"glob": "specs/*/status.json", "kind": "spec"}],
    }


def test_legacy_docs_publisher_is_removed_and_release_flags_remain_canonical():
    assert not (ROOT / ".github/workflows/docs.yml").exists()
    jobs = _workflow("pipeline.yml")["jobs"]
    pypi = jobs["publish-pypi"]
    docker = jobs["publish-docker"]

    assert pypi["uses"] == (
        "Knuckles-Team/pipelines/.github/workflows/python_pipeline.yml@main"
    )
    assert pypi["with"] == {"connector": True}
    assert docker["uses"] == (
        "Knuckles-Team/pipelines/.github/workflows/container_pipeline.yml@main"
    )
    assert docker["with"] == {"render_connector": True}
    assert docker["needs"] == "publish-pypi"


def test_development_skill_has_real_delivery_contract_and_actual_tests():
    skill = ROOT / "salesforce_agent/skills/salesforce-agent-development/SKILL.md"
    content = skill.read_text()

    assert "name: salesforce-agent-development" in content
    assert "## Rapid delivery: the 5-minute contract" in content
    assert "tests/test_salesforce_mcp_validation.py" in content
    assert "tests/test_fleet_name.py" in content
    assert "SALESFORCE_ALLOW_DESTRUCTIVE" in content
