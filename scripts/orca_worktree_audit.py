#!/usr/bin/env python3
"""
orca_worktree_audit.py — Orca worktree の .opencode/node_modules 共有状態を点検する

背景: knowledge/decisions/worktree_overhead_policy.md
Orca は orca.yaml の worktree.sharedDirectories で .opencode/node_modules を
worktree 間で共有（junction）する。ただし primary checkout に
.opencode/node_modules が無い端末では、Orca は警告なく共有をスキップし、
worktree ごとに約52MBを複製する。このスクリプトはその「サイレントな逆戻り」を
検知し、必要なら primary に用意する（--fix）。

使い方:
    python scripts/orca_worktree_audit.py                 # cwd の repo を点検
    python scripts/orca_worktree_audit.py --repo <path>
    python scripts/orca_worktree_audit.py --fix           # primary に node_modules を用意

終了コード: 0=問題なし / 1=未共有のworktreeあり or primary欠落
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_reparse_point(p: Path) -> bool:
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def dir_size_bytes(p: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def mb(n: int) -> str:
    return f"{n / 1048576:.1f}MB"


def ensure_primary(primary_nm: Path, config_nm: Path) -> bool:
    if primary_nm.exists():
        return True
    if not config_nm.is_dir():
        print(f"  [fix不可] {config_nm} が無い。opencode を1回起動して .opencode を初期化してください")
        return False
    primary_nm.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(config_nm, primary_nm)
    print(f"  [fix] {primary_nm} を {config_nm} から作成（{mb(dir_size_bytes(primary_nm))}）")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--workspaces", default=str(Path.home() / "orca" / "workspaces"))
    ap.add_argument("--fix", action="store_true", help="primary に .opencode/node_modules を用意")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    primary_nm = repo / ".opencode" / "node_modules"
    config_nm = Path.home() / ".config" / "opencode" / "node_modules"

    problems = 0
    print(f"repo      : {repo}")
    print(f"primary nm: {primary_nm}  exists={primary_nm.exists()}"
          + (f"  reparse={is_reparse_point(primary_nm)}" if primary_nm.exists() else ""))
    if not primary_nm.exists():
        problems += 1
        print("  → primary に .opencode/node_modules が無い。この端末では worktree 共有が効かない（サイレントに52MB複製）")
        if args.fix:
            if ensure_primary(primary_nm, config_nm):
                problems -= 1

    ws_root = Path(args.workspaces) / repo.name
    if not ws_root.is_dir():
        print(f"worktrees : {ws_root} が無い（Orca worktree未作成）")
        return 1 if problems else 0

    print(f"worktrees : {ws_root}")
    for wt in sorted(p for p in ws_root.iterdir() if p.is_dir()):
        nm = wt / ".opencode" / "node_modules"
        if not nm.exists():
            print(f"  - {wt.name}: (node_modules なし)")
            continue
        if is_reparse_point(nm):
            print(f"  - {wt.name}: 共有(junction) ok")
        else:
            problems += 1
            print(f"  - {wt.name}: 複製(未共有・{mb(dir_size_bytes(nm))}) ★要確認（共有が効いていない）")

    if problems:
        print(f"\n判定: 要確認 {problems} 件（共有が効いていない worktree / primary欠落）")
        return 1
    print("\n判定: OK（primaryあり・全worktreeで共有）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
