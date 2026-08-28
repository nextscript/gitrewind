<p align="center"><img src="https://github.com/nextscript/gitrewind/raw/refs/heads/main/GitRewind_icon_animated.svg" width="350" height="350"></p>

GitRewind

GitRewind is a graphical rollback tool for GitHub repositories. It helps you undo a broken commit by deliberately resetting a selected branch to an earlier, working commit and then pushing it to GitHub with --force-with-lease.

> **Important:** GitRewind rewrites the commit history of the selected target branch. Only use this tool if you understand that a rollback can remove newer commits from the visible history of that branch.

────────

<details>
<summary><h3>1. What is GitRewind?</h3></summary>

GitRewind is a desktop application with a graphical interface for Git rollbacks.

The tool connects to your GitHub account with a GitHub Personal Access Token, loads your repositories and branches, and lets you set an earlier commit as the new state of the selected branch.

The basic flow is:

```text
log in to GitHub
    ↓
select a repository
    ↓
select a branch (`main` by default, if available)
    ↓
load the commit history of the selected branch
    ↓
select a good target commit
    ↓
select the broken/problematic commit
    ↓
create a local backup
    ↓
set the selected branch locally to the target commit
    ↓
refresh the remote state
    ↓
git push --force-with-lease
```

GitRewind deliberately uses --force-with-lease instead of a blind --force, so the push is rejected if the remote branch has changed unexpectedly.

────────

</details>
<details>

<summary><h3>2. What is the tool for?</h3></summary>

GitRewind is meant for situations in which a new commit has broken a repository and you want to get back quickly to a previously working state.

Typical examples:

• A new commit causes errors or crashes.
• A large change should be completely rolled back.
• A selected branch should point exactly at a known working commit again.
• You want to perform the rollback without manual Git commands.
• You want to automatically keep a local backup branch before the rollback.

The tool is not a replacement for normal reverts. If you do not want to rewrite the history, or if several people are working on the same branch at the same time, a plain git revert is often the safer option.

────────

</details>
<details>
<summary><h3>3. How does GitRewind work?</h3></summary>

GitHub connection

After startup, you sign in with a GitHub Personal Access Token.

GitRewind uses the GitHub API, among other things, to:

• verify the token
• load the repository list
• load the repository branches
• load the commit history of the selected branch
• check the repository permissions

The commit history is loaded via the GitHub API. The current application loads up to 500 commits.

Branch selection

After selecting a repository, GitRewind loads its available branches.

If main exists, it is selected automatically. If there is no main branch, GitRewind selects the repository’s configured default branch. If that cannot be determined, the first available branch is selected.

```text
Selection priority:

main
  ↓ if unavailable
repository default branch
  ↓ if unavailable
first available branch
```

Commit selection is branch-specific. Changing the branch clears the previous commit selections before loading the new branch history. This prevents commits from another branch from accidentally being used for a rollback.

Local rollback

After you select the target commit, GitRewind performs the following steps (in effect):

```bash
git fetch
git branch backup-before-rollback-<BRANCH>-<COMMIT>
git checkout -B <BRANCH> <COMMIT>
```

If the local repository folder does not exist yet, the repository is cloned beforehand.

Push to GitHub

git checkout -B <BRANCH> <TARGET-COMMIT>

Then the selected branch is updated with a protected force push:

```bash
git push --force-with-lease ...
```

--force-with-lease is safer than a plain --force, because Git checks whether the expected remote state is still current.

Backup

Before the rollback, a local backup branch is created:

```text
backup-before-rollback-<BRANCH>-<PROBLEM-COMMIT>
```

If this branch already exists, the existing backup is kept.

────────

</details>
<details>
<summary><h3>4. What do I need to use GitRewind?</h3></summary>

General requirements

You need:

• a GitHub account
• access to at least one GitHub repository
• a GitHub Personal Access Token
• Git on the machine
• an internet connection to GitHub
• Python 3.10 or newer
• PyQt6

Python 3.10 or newer is required because the code uses modern Python type notation such as Path | None.

Python dependencies

Install at least:

```bash
pip install PyQt6
```

On macOS and Linux, the Python package keyring is additionally used for the system’s secure key storage:

```bash
pip install keyring
```

On Linux, the following is typically additionally required for the Secret Service:

```bash
pip install secretstorage
```

GitRewind does not use a self-generated encryption key stored next to the application for this.

Git must be installed separately and be reachable from the command line:

```bash
git --version
```

If this command works, GitRewind can usually find Git as well.

────────

</details>
<details>
<summary><h3>5. What should I consider regarding the GitHub API token?</h3></summary>

GitHub calls these credentials Personal Access Tokens (PAT).

A Fine-Grained Personal Access Token is recommended for GitRewind, because it lets you limit access to specific repositories and permissions.

Recommended fine-grained settings

Under:

```text
GitHub
→ Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
```

you should configure the following:

Repository access

Safest:

```text
Only select repositories
```

and then select only the repositories that GitRewind is actually allowed to manage.

Repository permissions

For normal operation:

|Permission|Setting       |
|----------|--------------|
|Metadata  |Read          |
|Contents  |Read and write|

Metadata: Read is required for repository metadata and repository queries. Contents: Read and write is the key permission for write operations on repository contents and Git references. [GitHub, Permissions required for fine-grained personal access tokens, https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens]

Workflow files

If the state you are resetting to changes files under:

```text
.github/workflows/
```

the following additional permission may be required:

```text
Workflows: Read and write
```

GitHub treats workflow-related write operations separately. [GitHub, Permissions required for fine-grained personal access tokens, https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens]

Unneeded permissions

GitRewind does not need blanket write permissions for its normal purpose:

• Actions
• Issues
• Discussions
• Deployments
• Secrets
• Administration
• Codespaces
• Dependabot
• Pages
• Repository Hooks

Only grant the permissions that are really needed.

Branch protection and rulesets

Even with a correctly scoped token, GitHub can block the rollback if the selected branch is protected against force pushes by branch protection or a ruleset.

In that case you must check the repository rules:

```text
Repository
→ Settings
→ Rules
→ Rulesets
```

or:

```text
Repository
→ Settings
→ Branches
```

GitRewind does not disable such protection mechanisms automatically.

────────

</details>
<details>
<summary><h3>6. On which operating systems can GitRewind run?</h3></summary>

The Python/PyQt6 code is designed for the following desktop systems:

• Windows
• Linux
• macOS

Windows

Windows is currently the best integrated platform, especially for storing the GitHub token.

Linux

Linux works if the following components are available:

• Python
• PyQt6
• Git
• cryptography

Depending on the desktop environment, additional Qt system packages may be required.

macOS

macOS also requires:

• Python
• PyQt6
• Git
• cryptography

────────

</details>
<details>
<summary><h3>7. How safe is it to enter my GitHub API key there?</h3></summary>

Summary

GitRewind stores the GitHub Personal Access Token in the secure key storage of the operating system, platform-specific:

|Operating system|Storage                               |
|----------------|--------------------------------------|
|Windows         |Windows DPAPI                         |
|macOS           |Apple Keychain via `keyring`          |
|Linux           |Secret Service / KWallet via `keyring`|

On macOS and Linux, the GitHub token is not stored next to GitRewind together with a self-owned encryption key.

────────

Windows – DPAPI

On Windows, GitRewind uses the Windows Data Protection API (DPAPI) via CryptProtectData.

DPAPI protects the stored data through the Windows user context. The encrypted data usually cannot simply be copied to another user or machine and decrypted there.

[Microsoft, CryptProtectData function, https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata]

GitRewind stores only the DPAPI-protected data locally.

────────

macOS – Apple Keychain

On macOS, the GitHub token is stored in the Apple Keychain via the Python package keyring.

The actual token is therefore not stored in plaintext and not together with its own decryption key in the GitRewind folder.

Apple Keychain is the protected storage intended by the operating system for passwords, tokens, and other credentials.

[Apple, Keychain Services, https://developer.apple.com/documentation/security/keychain-services]

A local metadata file that GitRewind may create contains not the GitHub token itself, but only the information needed to locate the stored entry.

────────

Linux – Secret Service / KWallet

On Linux, GitRewind also uses keyring.

Depending on the desktop environment, the token is stored, for example, in:

• GNOME Keyring / Secret Service
• KDE KWallet
• another compatible secure keyring backend

The actual token is not stored as a regular file in the GitRewind directory.

The following may additionally be required for the Secret Service:

```bash
pip install secretstorage
```

On a typical Linux desktop, a working Secret Service or keyring must also be available.

If no secure keyring is available, GitRewind does not fall back to an insecure file fallback. Instead, storage is refused and an error message is shown.

────────

No more git_rewind.key for normal operation

The previous variant used a local Fernet key on Linux/macOS:

```text
git_rewind.key
```

This solution is no longer the intended storage method.

With the current secure architecture:

```text
Windows → DPAPI
macOS   → Apple Keychain
Linux   → Secret Service / KWallet
```

This means that on macOS/Linux there is no self-owned key next to the application that could be used to decrypt the token directly.

────────

How secure is that?

For a local desktop application, this architecture is sensible and clearly better than:

```text
encrypt the token
+
store the decryption key in the same app folder
```

The protection is nevertheless not absolute.

No local key storage can reliably protect a token when:

• your user account has already been fully compromised
• malware is running under your user account
• an attacker has administrator/root access to the running system
• an attacker gains access to your unlocked user key storage

Therefore, the GitHub token should additionally always be created according to the principle of least privilege.

Recommended:

```text
Repository access:
select only the repositories that GitRewind really needs

Repository permissions:
Metadata → Read
Contents → Read and write
```

────────

Additional protection measures in GitRewind

GitRewind additionally tries to:

• mask GitHub tokens in log output
• not store the token persistently in the Git remote URL (.git/config)
• use the token only for authenticated GitHub calls
• not use an insecure file fallback on Linux/macOS
• remove the token from the secure key storage on logout

Still:

> A GitHub Personal Access Token is an access key. Never publish it in a repository, screenshot, log, or chat.

────────

</details>
<details>
<summary><h3>8. How do I use GitRewind?</h3></summary>

Step 1 – Install the prerequisites

First check Git:

```bash
git --version
```

Then install the Python dependencies:

```bash
pip install PyQt6
```

Additionally on macOS/Linux:

```bash
pip install keyring
```

On Linux, typically additionally for the Secret Service:

```bash
pip install secretstorage
```

────────

Step 2 – Create a GitHub token

Open in GitHub:

```text
Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
```

Create a new token.

Recommended settings:

```text
Repository access:
Only select repositories
→ select the desired repositories

Repository permissions:
Metadata → Read
Contents → Read and write
```

────────

Step 3 – Start GitRewind

Start:

```bash
python git_rewind_gui.py
```

────────

Step 4 – Sign in to GitHub

1. Enter the GitHub token in GitRewind.
2. Press “Verify + save”.
3. GitRewind checks the token.
4. On successful sign-in, the token is stored encrypted locally.

────────

Step 5 – Select a repository

Select in the repository dropdown the repository that should be reset.

GitRewind then loads:

• repository information
• push permissions
• available branches

────────

Step 6 – Select a branch

Select the branch that should be rolled back.

If a branch named main exists, GitRewind selects it automatically by default.

The automatic selection priority is:

```text
1. main
2. Repository default branch
3. First available branch
```

This means that repositories using master, develop, or another default branch still work correctly when no main branch exists.

After the branch is selected, GitRewind loads only the commit history belonging to that branch.

If you switch to another branch, the old commit selections are cleared and the commit history for the newly selected branch is loaded.

────────

Step 7 – Select the target commit

Under:

```text
Target commit (good)
```

select the commit to which the repository should be reset.

Example:

```text
A = working commit
B = broken commit
```

Then:

```text
Target commit = A
```

────────

Step 8 – Select the problem commit

Under:

```text
Problem commit (broken)
```

select the commit that represents the broken state.

This commit is used, among other things, for the name of the local backup branch.

────────

Step 9 – Optional: validate parameters

Press:

```text
Validate parameters
```

GitRewind checks, among other things:

• GitHub login
• repository
• selected branch
• target commit
• problem commit
• basic push permission

────────

Step 10 – Start the rollback

Press:

```text
Start rollback
```

GitRewind performs the rollback.

It does the following:

1. Checks Git.
2. Clones the repository if needed.
3. Loads the current GitHub state.
4. Creates a local backup branch.
5. Sets the selected branch to the target commit.
6. Checks the remote state of that branch again.
7. Pushes the selected branch to GitHub with --force-with-lease.

────────

Step 11 – Check the result

After a successful completion, you should check on GitHub whether the selected branch now points to the desired commit.

Additionally check locally:

```bash
git log --oneline -10
```

────────

Important notes

No automatic git pull

If Git reports:

```text
Your branch is behind 'origin/<BRANCH>'
```

that is not automatically an error during a rollback.

A git pull would re-include the commit you are trying to remove.

Force push changes the branch history

The rollback sets the selected branch directly to an earlier commit.

This means that newer commits are no longer part of the normal history of that branch.

Collaboration with others

If multiple people are working on the repository at the same time, you should coordinate the rollback in advance.

Other local clones may no longer match the new remote history after the selected branch has been rewritten.

The backup stays local

The backup branch created by GitRewind is a local safety anchor. Check it before deleting local repository data.

────────

Troubleshooting

HTTP 403 / Permission denied

Example:

```text
Permission to OWNER/REPO.git denied
HTTP 403
```

Check:

```text
Fine-grained token
→ Repository access
→ repository selected

Repository permissions
→ Contents
→ Read and write
```

────────

Token invalid

With:

```text
401
Bad credentials
Authentication failed
```

Check the token on GitHub, or regenerate it, and sign in again with GitRewind.

────────

Force push is blocked

With messages like:

```text
GH006
GH013
protected branch
repository rule violations
```

check the branch protection or GitHub rulesets.

────────

Git was not found

Check:

```bash
git --version
```

If the command does not work, install Git and then start GitRewind again.

────────

Security recommendation

For GitRewind, you should use a separate fine-grained token dedicated to this tool.

Recommended:

```text
Repository access:
only the repositories you need

Permissions:
Metadata → Read
Contents → Read and write
```

The fewer permissions the token has, the lower the potential damage if it is compromised.

────────

</details>
