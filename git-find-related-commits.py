#!/usr/bin/env python3

"""
https://stackoverflow.com/questions/66731069/how-to-find-pairs-groups-of-most-related-commits
"""

from __future__ import annotations
from typing import List, Optional
import git
import contextlib
import sys
import better_exchook


_TmpBranchName = "tmp-find-related-commits"


class GitHelper:
  def __init__(self, repo_dir: str):
    self.repo = git.Repo(repo_dir)
    self.main_branch = "origin/master"
    self.local_branch = self.repo.active_branch
    assert self.local_branch.name != _TmpBranchName

  def get_base_commit(self) -> git.Commit:
    """
    Returns:
    On some branch, return the base commit which is in the main branch (e.g. origin/master).
    """
    return self.repo.merge_base(self.main_branch, self.local_branch)[0]

  def get_commit_list(self) -> List[git.Commit]:
    """
    Returns:
    All the commits starting from the main branch.
    """
    return list(reversed(list(self.repo.iter_commits(f"{self.get_base_commit()}..{self.local_branch}"))))

  def test_commit_pair(self, commits: List[git.Commit]) -> Optional[int]:
    commit0 = commits[0]
    assert len(commit0.parents) == 1  # not implemented otherwise...
    commit0 = commit0.parents[0]
    # print(f"Start at {_format_commit(commit0)}")
    diff_counts = []
    with self.in_tmp_branch(commit0):
      for commit in commits:
        # print(f"Apply {_format_commit(commit)}")
        try:
          self.repo.git.cherry_pick(commit, "--keep-redundant-commits")
        except git.GitCommandError:
          return None
        diff_str = self.repo.git.diff(f"{commit0}..HEAD")
        diff_counts.append(_count_changed_lines(diff_str))
    return diff_counts[-1] - diff_counts[0]

  def test(self):
    commits = self.get_commit_list()
    print("All commits:")
    for commit in commits:
      print(f"  {_format_commit(commit)}")
    print("Iterate...")
    results = []
    for i in range(len(commits)):
      for j in range(i + 1, len(commits)):
        commit_pair = [commits[i], commits[j]]
        c = self.test_commit_pair(commit_pair)
        print("Commits:", [_format_commit(commit) for commit in commit_pair], "relative diff count:", c)
        if c is not None and c < 0:
          results.append((c, commit_pair))
    print("Done. Results:")
    results.sort()
    for c, commit_pair in results:
      print(c, "commits:", [_format_commit(commit) for commit in commit_pair])

  @contextlib.contextmanager
  def in_tmp_branch(self, commit: git.Commit) -> git.Head:
    repo = self.repo
    prev_active_branch = repo.active_branch
    tmp_branch = repo.create_head(_TmpBranchName, commit.hexsha, force=True)
    repo.git.checkout(tmp_branch)
    try:
      yield tmp_branch
    except git.GitCommandError as exc:
      print("Git exception occurred. Current git status:")
      print(repo.git.status())
      raise exc
    finally:
      repo.git.reset("--hard")
      repo.git.checkout(prev_active_branch)


def _format_commit(commit: git.Commit) -> str:
  return f"{commit} ({commit.message.splitlines()[0]})"


def _count_changed_lines(s: str) -> int:
  c = 0
  for line in s.splitlines():
    if line.startswith("+ ") or line.startswith("- "):
      c += 1
  return c


def main():
  helper = GitHelper(".")
  helper.test()
  # better_exchook.debug_shell(locals(), globals())


if __name__ == '__main__':
  better_exchook.install()
  try:
    main()
  except KeyboardInterrupt:
    print("KeyboardInterrupt")
    sys.exit(1)
