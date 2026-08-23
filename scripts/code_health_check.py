#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhronisisCode health check - 5 inspections
Exit 0 if all PASS, exit 1 if any FAIL. Never crash on missing files.
"""
import argparse
import json
import sys
from pathlib import Path

# --- root resolution (cwd independent) ---
def resolve_root() -> Path:
    # scripts/code_health_check.py -> repo root is parents[1]
    try:
        return Path(__file__).resolve().parents[1]
    except Exception:
        return Path.cwd()

ROOT = resolve_root()

# --- color ---
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"

def should_color(no_color: bool) -> bool:
    if no_color:
        return False
    # honor NO_COLOR env and non-tty
    import os
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()

def colorize(text: str, color: str, use_color: bool) -> str:
    if use_color:
        return f"{color}{text}{COLOR_RESET}"
    return text

# --- check result ---
class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str):
        self.name = name
        self.passed = passed
        self.detail = detail

    def to_dict(self):
        return {"name": self.name, "passed": self.passed, "status": "PASS" if self.passed else "FAIL", "detail": self.detail}

# 1. conductor_profile_lite
def check_conductor_profile(root: Path) -> CheckResult:
    name = "1. conductor_profile_lite"
    path = root / "knowledge" / "conductor_profile_lite.md"
    try:
        if not path.exists():
            return CheckResult(name, False, f"missing: {path.relative_to(root)}")
        if not path.is_file():
            return CheckResult(name, False, f"not a file: {path}")
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            return CheckResult(name, False, f"read error: {e}")
        if len(text.strip()) == 0:
            return CheckResult(name, False, "file is empty (reference broken)")
        # reference broken: check for expected heading/content
        # expect at least one of these keywords
        keywords = ["コンダクター", "判断OS", "conductor"]
        has_heading = any(k in text for k in keywords) or text.lstrip().startswith("#")
        if not has_heading:
            return CheckResult(name, False, "no heading/keyword found (possible reference broken)")
        # also check size reasonable
        if len(text) < 50:
            return CheckResult(name, False, f"too small ({len(text)} chars), likely broken")
        return CheckResult(name, True, f"found {path.relative_to(root)} ({len(text)} chars)")
    except Exception as e:
        return CheckResult(name, False, f"exception: {e}")

# 2. hooks
def check_hooks(root: Path) -> CheckResult:
    name = "2. hooks dependencies"
    expected = [
        "hooks/python_run.sh",
        "hooks/utf8_check.py",
        "hooks/handover_check.py",
        "hooks/lock_acquire.py",
        "hooks/lock_check.py",
        "hooks/lock_release.py",
    ]
    try:
        missing = []
        found = []
        for rel in expected:
            p = root / rel
            if p.exists() and p.is_file():
                found.append(rel)
            else:
                missing.append(rel)
        if missing:
            return CheckResult(name, False, f"missing {len(missing)}/{len(expected)}: {', '.join(missing)} | found: {', '.join(found) if found else 'none'}")
        return CheckResult(name, True, f"all {len(expected)} hooks present")
    except Exception as e:
        return CheckResult(name, False, f"exception: {e}")

# 3. 6 gods profiles
def check_agents(root: Path) -> CheckResult:
    name = "3. 6 gods profiles"
    gods = ["gaia", "hermes", "artemis", "daedalus", "metis", "athena"]
    try:
        missing = []
        found = []
        for g in gods:
            p = root / "shared" / "phronisis_code" / "agents" / g / "profile.md"
            if p.exists() and p.is_file():
                found.append(g)
            else:
                missing.append(g)
        if missing:
            return CheckResult(name, False, f"missing profiles: {', '.join(missing)} | found: {', '.join(found) if found else 'none'}")
        return CheckResult(name, True, f"all 6 profiles present ({', '.join(found)})")
    except Exception as e:
        return CheckResult(name, False, f"exception: {e}")

# 4. opencode.json
def check_opencode(root: Path) -> CheckResult:
    name = "4. opencode.json"
    path = root / "opencode.json"
    try:
        if not path.exists():
            return CheckResult(name, False, "missing opencode.json")
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return CheckResult(name, False, f"invalid JSON: {e}")
        except Exception as e:
            return CheckResult(name, False, f"read error: {e}")
        if "agent" not in data:
            return CheckResult(name, False, 'missing "agent" key')
        agents = data["agent"]
        if not isinstance(agents, dict):
            return CheckResult(name, False, '"agent" is not an object')
        count = len(agents)
        expected = 8
        agent_list = ", ".join(sorted(agents.keys()))
        if count != expected:
            return CheckResult(name, False, f"agent count {count} != expected {expected} ({agent_list})")
        # also check each has minimal fields
        for k, v in agents.items():
            if not isinstance(v, dict):
                return CheckResult(name, False, f"agent {k} is not an object")
        return CheckResult(name, True, f"valid JSON, {count} agents ({agent_list})")
    except Exception as e:
        return CheckResult(name, False, f"exception: {e}")

# 5. templates
def check_templates(root: Path) -> CheckResult:
    name = "5. tasks/_template fields"
    brief_path = root / "tasks" / "_template" / "brief.md"
    log_path = root / "tasks" / "_template" / "log.md"
    try:
        issues = []
        details = []
        # brief.md checks
        try:
            if not brief_path.exists():
                issues.append("brief.md missing")
            else:
                text = brief_path.read_text(encoding="utf-8")
                # required keywords
                need_brief = ["成功基準", "軌跡"]
                for kw in need_brief:
                    if kw not in text:
                        issues.append(f"brief.md missing '{kw}'")
                if not issues or "brief.md missing" not in issues:
                    details.append(f"brief.md {len(text)} chars")
                # table header check
                if "論点" not in text or "選んだ案" not in text:
                    issues.append("brief.md missing 軌跡表 header")
        except Exception as e:
            issues.append(f"brief.md read error: {e}")

        # log.md checks
        try:
            if not log_path.exists():
                issues.append("log.md missing")
            else:
                text = log_path.read_text(encoding="utf-8")
                need_log = ["自己検証", "Hayato"]
                for kw in need_log:
                    if kw not in text:
                        issues.append(f"log.md missing '{kw}'")
                details.append(f"log.md {len(text)} chars")
        except Exception as e:
            issues.append(f"log.md read error: {e}")

        if issues:
            return CheckResult(name, False, "; ".join(issues) + (" | " + ", ".join(details) if details else ""))
        return CheckResult(name, True, "; ".join(details) + " | required fields present")
    except Exception as e:
        return CheckResult(name, False, f"exception: {e}")

def run_all_checks(root: Path):
    checks = []
    for fn in [check_conductor_profile, check_hooks, check_agents, check_opencode, check_templates]:
        try:
            r = fn(root)
        except Exception as e:
            r = CheckResult(fn.__name__, False, f"unhandled exception: {e}")
        checks.append(r)
    return checks

def main(argv=None):
    parser = argparse.ArgumentParser(description="PhronisisCode health check - 5 inspections")
    parser.add_argument("--verbose", action="store_true", help="show details for all checks")
    parser.add_argument("--json", dest="json_output", action="store_true", help="output machine-readable JSON")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    args = parser.parse_args(argv)

    root = ROOT
    checks = run_all_checks(root)

    # JSON mode
    if args.json_output:
        out = {
            "root": str(root),
            "checks": [c.to_dict() for c in checks],
            "summary": {
                "total": len(checks),
                "passed": sum(1 for c in checks if c.passed),
                "failed": sum(1 for c in checks if not c.passed),
                "overall": "PASS" if all(c.passed for c in checks) else "FAIL",
            },
        }
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.exit(0 if all(c.passed for c in checks) else 1)

    use_color = should_color(args.no_color)
    all_pass = all(c.passed for c in checks)

    # header
    header = "PhronisisCode Health Check"
    print(colorize(header, COLOR_BOLD, use_color))
    print(colorize(f"Root: {root}", COLOR_BOLD, use_color) if args.verbose else f"Root: {root}")
    print("-" * 48)

    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        col = COLOR_GREEN if c.passed else COLOR_RED
        line = f"[{status}] {c.name}"
        print(colorize(line, col, use_color))
        # detail: show always for FAIL, or if verbose
        if not c.passed or args.verbose:
            print(f"      {c.detail}")

    print("-" * 48)
    passed = sum(1 for c in checks if c.passed)
    failed = len(checks) - passed
    summary = f"Summary: {passed}/{len(checks)} PASS"
    if failed:
        summary += f", {failed} FAIL"
    col = COLOR_GREEN if all_pass else COLOR_RED
    print(colorize(summary, col, use_color))
    overall = "ALL PASS" if all_pass else "SOME FAIL"
    print(colorize(f"Overall: {overall}", col, use_color))

    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()
