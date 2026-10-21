---
title: Git
color: "#f05032"
blurb: Everyday Git commands, from setup to fixing mistakes.
---
## Setup
- `git config --global user.name "Your Name"` : set the name on your commits
- `git config --global user.email "you@example.com"` : set the email on your commits
- `git config --global init.defaultBranch main` : new repos start on main
- `git config --list --show-origin` : see every setting and where it comes from

## Start a repo
- `git init` : turn the current folder into a repo
- `git clone <url>` : copy a remote repo to your computer
- `git clone --depth 1 <url>` : clone only the latest commit (fast)

## Daily work
- `git status -sb` : short status with the branch name
- `git add <file>` : stage one file
- `git add -A` : stage everything, including deletions
- `git add -p` : choose changes piece by piece
- `git commit -m "message"` : commit what's staged
- `git commit --amend` : change the last commit (message or content)
- `git diff` : unstaged changes
- `git diff --staged` : what will go into the next commit

## Branches
- `git branch` : list local branches
- `git switch -c <name>` : create a branch and switch to it
- `git switch <name>` : switch branch
- `git branch -d <name>` : delete a merged branch
- `git branch -m <new>` : rename the current branch
- `git merge <branch>` : merge a branch into the current one
- `git rebase main` : replay your commits on top of main

## Remotes
- `git remote -v` : list remotes
- `git remote add origin <url>` : connect a remote
- `git push -u origin <branch>` : push and track a new branch
- `git pull --rebase` : get updates without a merge commit
- `git fetch --prune` : update and drop deleted remote branches

## History
- `git log --oneline --graph --all` : compact history of every branch
- `git log -p <file>` : every change to one file
- `git show <commit>` : what a commit changed
- `git blame <file>` : who last changed each line
- `git log -S "text"` : commits that added or removed some text

## Undo
- `git restore <file>` : throw away unstaged changes to a file
- `git restore --staged <file>` : unstage a file, keep the changes
- `git reset --soft HEAD~1` : undo the last commit, keep its changes staged
- `git reset --hard HEAD~1` : delete the last commit and its changes (careful)
- `git revert <commit>` : new commit that undoes an old one (safe for shared branches)
- `git reflog` : find "lost" commits after a bad reset

## Stash
- `git stash push -m "wip"` : put changes aside
- `git stash list` : see stashes
- `git stash pop` : bring the latest stash back

## Tags
- `git tag v1.0.0` : tag the current commit
- `git push origin --tags` : push tags

## Cleanup
- `git clean -nd` : preview untracked files that would be deleted
- `git clean -fd` : delete untracked files and folders (careful)
