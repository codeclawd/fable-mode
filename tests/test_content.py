"""Guards on shipped prompt/skill content: the files injected into every
session must not point at files that do not exist on a user's machine."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_playbook_has_no_dead_personal_references():
    """The playbook is injected verbatim; an instruction to read a file that
    only ever existed on the author's machine sends every user's model on a
    failing Read. Provenance may be described, not pointed at."""
    text = (REPO / "FABLE_PLAYBOOK.md").read_text(encoding="utf-8")
    for needle in ("~/Downloads", "compare_models.py", "fable_dataset_delta.py",
                   "fable5_dataset_profile.json", "llm-bias-awareness.md",
                   "bundled `stop-slop`", "bundled `/code-review`"):
        assert needle not in text, f"dead reference in FABLE_PLAYBOOK.md: {needle}"


def test_fable_skill_fallback_is_reachable():
    """After install the skill is a lone SKILL.md under ~/.claude/skills/fable;
    'this skill's repository' does not exist there. The recovery path a user
    can actually take is `fable doctor` / re-running the installer."""
    text = (REPO / "skills" / "fable" / "SKILL.md").read_text(encoding="utf-8")
    assert "this skill's repository" not in text
    assert "fable doctor" in text
