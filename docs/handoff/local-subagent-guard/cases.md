# 判定の例（design.md §8 K3・K4 の正本）

- 1 行 1 例。`\n` は改行 1 文字を表す（それ以外の `\` はそのまま）。
- 「止める例」は担当（agent_id あり）の Bash・Monitor の command で、止める（exit 2）。「通す例」は exit 0。
- 設計者の試作（/tmp/CC報告ファイル/local-subagent-guard/proto-v4-judge.py）に当てた結果: 止める例 139・通す例 120、誤り 0（proto-v4-out.txt）。
- test_guard.sh はこの全例を入れる。例を足すときはこの文書と試験の両方に足す。

## 止める例

```
git commit -m x
git -C /a commit
git -c a=b push
cd /a && git push
bash -c 'git push'
echo $(git push)
git merge x
git rebase main
git tag v1
gh pr create
gh pr merge 1
gh pr comment 1 -b x
gh api -X POST repos/a/b/issues
gh api repos/a/b/pulls -f title=x
bash scripts/gh-pr-merge-safe.sh --merge
bash scripts/gh-pr-create-safe.sh --base main
claude -p x
codex exec x
~/.local/bin/claude -p hi
git -P push
git -C/a push
git --work-tree /a commit
git checkout -- .
git clean -fd
git stash
git switch x
git branch -D x
git branch newb
git worktree add /x
git restore .
git reset --hard
git add .
gh secret set X
gh variable set X
gh label create x
gh pr update-branch 1
gh issue delete 1
gh gist create f
gh repo sync
gh run delete 1
gh api graphql -f query='mutation{x}'
xargs git push
eval "git push"
git tag -a v1 -m x
git pull
git cherry-pick a
git config user.name x
/usr/bin/git push
git commit -m "$(cat <<EOF\nmsg\nEOF\n)"
git -C "$WT" commit -m x
git -C ${WT} commit -m x
git "push"
git 'push' origin x
gh api "repos/a/b/issues" -f title=x
gh api repos/${O}/${R}/issues -f title=x
gh api "repos/a/b/issues" -X POST
gh "pr" create
git -c "user.name=x" commit -m y
gh pr view 1 --jq "$(git push)"
gh issue list --search "$(claude -p hi)"
command claude -p hi
npx @anthropic-ai/claude-code -p hi
git symbolic-ref -d HEAD
git branch "newb"
git fetch origin +HEAD:refs/heads/main
gh api -XPOST repos/a
gh api graphql -f query=@m.graphql
git worktree add --detach /tmp/x HEAD
git
gh
env FOO=1 git push
FOO=1 git push
sudo git push
time git push
nohup git push &
gh pr review 1 --approve
gh api --method=post repos/a
git fetch origin main:main
find . -name x -exec git add {} +
command git push
bunx @openai/codex
gh -R o/r pr create
bash scripts/dev/executor-preflight.sh
./scripts/dev/executor-preflight.sh || exit 1
python3 scripts/dev/perm-change.py x
node scripts/check-process-artifacts.js
cd /a && ./x.sh
~/kb/scripts/save.sh m
env A=1 bash x.sh
find . -name "*.sh" -exec bash {} \;
xargs -n1 python3 x.py
python3 -m pip install x
npm run build
npx tsx a.ts
make deploy
sh -c "./scripts/x.sh"
timeout 10 ./x.sh
sudo -u a ./x.sh
xargs sh -c "git push"
bash -lc "git commit -m x"
zsh -c "gh pr merge 1"
source scripts/dev/executor-preflight.sh
. ./scripts/dev/executor-preflight.sh
cat scripts/x.sh | bash
git show HEAD:scripts/x.sh | sh
echo 'git push' | bash
python3 - < scripts/dev/perm-change.py
bash - < scripts/x.sh
bash < scripts/x.sh
find . -name x.sh -exec ./x.sh {} \;
find . -name x.sh -exec {} \;
xargs -I {} ./x.sh {}
uv run scripts/x.py
bash<x.sh
git -c core.pager='git push' log
GIT_PAGER='sh x.sh' git log
git -c alias.x='!git push' x
gh api graphql -f query="$(cat m.graphql)"
bash <<'EOF'\ngit push\nEOF
bash <<< "git push"
cat <<EOF | bash\ngit push\nEOF
git -c core.fsmonitor=x status
GIT_EXTERNAL_DIFF=x git diff
export GIT_PAGER=x
env GIT_SSH_COMMAND=x git fetch
rg --pre ./x.sh foo
git ls-remote --upload-pack=x origin
nice -n 10 ./x.sh
timeout -s KILL 10 ./x.sh
find . -execdir {} \;
claude
echo x | python3
git --config-env=core.pager=X log
bash scripts/x.sh 2>&1 | tail
python3 scripts/x.py > /tmp/o.txt 2>&1
python3 < scripts/x.py
(cd /a && git push)
git log && git push
gh api graphql -F q=@x -f query='{a}'
```

## 通す例

```
git log
git status
git diff origin/main
git -C /a log
git fetch
gh pr view 1
gh pr list
gh api repos/a/b/pulls
ls
cat x
grep "git push" f
git log --grep "commit"
git merge-base origin/main HEAD
git merge-tree a b
git commit-graph verify
git tag -l
git tag --contains HEAD
gh api graphql -f query='{viewer{login}}'
gh api -X GET repos/a/b/pulls -F per_page=100
gh api repos/a/b --jq .x | jq -f x
git branch
git branch -a
git branch --contains HEAD
git stash list
git worktree list
git remote -v
git config --get user.name
which claude
gh pr checks 1
git rev-parse HEAD
git ls-remote origin
git show origin/main:x
ls ~/.claude/agents
gh auth status
git -C /a diff --stat origin/main...HEAD
gh run view 1 --log
pgrep -f claude
du -sh ~/.cache/claude
git config get user.name
git remote --verbose
gh pr -R o/r view 1
git reflog --all
git tag -v v1
gh api --method=get repos/a -f x=1
git --no-pager log
git log --format="%H {x}"
git -C "/a b" log
gh api repos/a/b/pulls/1/files --paginate --jq ".[].filename"
command -v claude
type claude
ps aux | grep claude
git log --format="%h|%s" -5
git fetch origin main
git -C "$WT" status --short
gh pr view 1 --json title --jq ".title"
gh api "repos/a/b/pulls?per_page=100"
git diff "$(git merge-base origin/main HEAD)"
echo "$(git rev-parse HEAD)"
cd "$WT" && git log --oneline -3
for f in a b; do git log -1 -- "$f"; done
git show "HEAD:docs/x.md" | head
python3 -c "print(1)"
python3 - <<EOF\nprint(1)\nEOF
python3 -m json.tool x.json
npm ls
npm view react version
node -e "console.log(1)"
/usr/bin/env python3 -c "1"
/bin/ls -la
jq .x f.json | wc -l
sqlite3 a.db "select 1"
wc -l scripts/x.sh
diff a.py b.py
find scripts -name "*.sh" | wc -l
grep -rn "gh pr create\|gh pr merge" scripts/
grep -E "git|gh" f
rg "claude|codex" docs
git grep -n "git push\|gh pr" -- scripts
grep "a; git push" f
python3 <<'EOF'\nprint(1)\nEOF
python3 <<EOF\nimport json\nprint(1)\nEOF
claude --version
npm ls -g @anthropic-ai/claude-code
jq . ~/.config/claude
echo '$(git push)'
git log --oneline | grep -E 'fix|gh'
jq -r '.[] | select(.agent_id) | .tool_name' f.jsonl
python3 -c "import json; d=json.load(open('a.json')); print(len(d))"
git branch -vv
git branch -r --list 'origin/release/*'
git tag --sort=-v:refname
git stash show -p stash@{0}
git worktree list --porcelain
git remote get-url origin
git ls-files | xargs wc -l
timeout 30 gh pr checks 1
gh api repos/a/b/pulls/1/reviews
gh pr diff 1 | head
awk -F'|' '{print $2}' f
sed -n '1,5p' f
git log --since="2 days ago" --format='%h %s'
cd ~/worktrees/salesanchor/x && git status --short | head
python3 /tmp/x.py
python3 /private/tmp/claude-501/s/x.py a
cd ~/x/claude
git log | cat
git -c core.quotepath=false log
python3 - <<'EOF'\nimport subprocess\nEOF
python3 <<'EOF'\nx = "gh"\nprint(x)\nEOF
find . -name '*.py' -exec wc -l {} +
find . -exec grep -l gh {} \;
ls | xargs -I {} cat {}
codex --help
git -C "$WT" log --format='%h' | head -3
gh pr view 1 --json body --jq .body > /tmp/b.txt
node -e 'x' < /dev/null
python3 < /tmp/x.py
git diff --stat 2>/dev/null
sqlite3 a.db 'select 1' | head
grep -c 'agent_id' f.jsonl
```
