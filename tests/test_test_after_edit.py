"""Tests for hooks/test-after-edit.py — the run-tests-after-edit reporter.

Hermetic: builds a throwaway Python project whose test suite the hook runs with
this same interpreter (sys.executable / pytest), so no Node/Make/etc. is needed.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "hooks" / "test-after-edit.py"


def run(tool_input, tool_name="Edit", env_extra=None):
    payload = {"tool_name": tool_name, "tool_input": tool_input}
    env = dict(os.environ)
    env["FABLE_TEST_HOOK_DEBOUNCE"] = "0"  # don't let debounce swallow back-to-back tests
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps(payload), text=True,
                       capture_output=True, env=env)
    return p.stdout.strip()


def make_py_project(root, passing=True):
    (root / "pyproject.toml").write_text("[project]\nname = 'sample'\nversion = '0'\n",
                                         encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    body = ("def test_ok():\n    assert True\n" if passing
            else "def test_bad():\n    assert False\n")
    (tests / "test_sample.py").write_text(body, encoding="utf-8")
    src = root / "mod.py"
    src.write_text("x = 1\n", encoding="utf-8")
    return src


def test_passing_project_reports_passed(tmp_path):
    src = make_py_project(tmp_path, passing=True)
    out = run({"file_path": str(src)})
    assert "passed" in out, out


def test_failing_project_reports_failed(tmp_path):
    src = make_py_project(tmp_path, passing=False)
    out = run({"file_path": str(src)})
    assert "FAILED" in out, out


def test_doc_edit_is_skipped(tmp_path):
    f = tmp_path / "README.md"
    f.write_text("# doc\n", encoding="utf-8")
    assert run({"file_path": str(f)}) == ""


def test_project_without_tests_is_silent(tmp_path):
    f = tmp_path / "loose.py"
    f.write_text("x = 1\n", encoding="utf-8")
    assert run({"file_path": str(f)}) == ""


def test_disabled_via_env(tmp_path):
    src = make_py_project(tmp_path, passing=True)
    assert run({"file_path": str(src)}, env_extra={"FABLE_NO_TEST_HOOK": "1"}) == ""


def test_non_edit_tool_ignored(tmp_path):
    src = make_py_project(tmp_path, passing=True)
    assert run({"file_path": str(src)}, tool_name="Read") == ""
