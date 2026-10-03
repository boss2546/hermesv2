# First-Time Setup (before anyone can run a single git command)

Read this when a teammate says something like "I want to join the project", "how do I get started", "it's asking for a username and password", or any git command fails with an auth error. This is the step almost every guide skips, and it's where total beginners get stuck first — walk them through it once, calmly, and they won't need it again.

## 1. Confirm the basics exist

Ask or check:
- Is Git installed? Run `git --version`. If it errors, they need to install it (macOS: `xcode-select --install` or install from git-scm.com; Windows: install "Git for Windows" from git-scm.com).
- Do they have a GitHub account? If not, they sign up at github.com first — needed before anything else.
- Have they been added to the repo? The repo owner needs to add them as a collaborator (repo → Settings → Collaborators on GitHub) or the org needs to add them to the team. Without this, clone/pull might work (if public) but push will fail with a permissions error.

## 2. Tell git who they are (one time per computer)

```
git config --global user.name "ชื่อจริงหรือชื่อที่ทีมรู้จัก"
git config --global user.email "อีเมลเดียวกับที่ใช้สมัคร GitHub"
```
This is what gets attached to every commit they make — without it, git will refuse to commit or use a generic placeholder that confuses everyone about who did what.

## 3. Set up authentication (the step that trips up almost everyone)

GitHub no longer accepts your account password when git asks for one over HTTPS. If a `git push` or `git clone` pops up asking for username + password and typing the real password fails, this is why. Two paths — recommend the first, it's simpler for beginners:

**Option A: Personal Access Token (PAT), used like a password**
1. On GitHub: profile picture → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token.
2. Give it "repo" scope, set an expiration.
3. Copy the token somewhere safe (it's shown once).
4. Next time git asks for a password over HTTPS, paste the token instead of the account password.
5. macOS/Windows will usually offer to remember it in the system keychain/credential manager after the first successful use — after that they won't be asked again.

**Option B: SSH key** (slightly more setup, no repeated prompts ever)
1. `ssh-keygen -t ed25519 -C "their email"` — accept defaults.
2. Copy the public key: `cat ~/.ssh/id_ed25519.pub`.
3. GitHub: Settings → SSH and GPG keys → New SSH key → paste it.
4. Use the SSH-style clone URL (`git@github.com:org/repo.git`) instead of the `https://` one.

If they already cloned with an `https://` URL and want to switch to SSH, or vice versa: `git remote set-url origin <new-url>`.

## 4. Sanity check

```
git clone <repo-url>
```
If this works without an auth prompt failing, or a subsequent `git push` succeeds, setup is done. Only need to do this once per computer, not per project.
