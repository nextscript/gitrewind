"""GitRewind v1.2 – Reset a GitHub repository to a good commit.

Flow (identical to the old rollback.bat flow):
  1.  GitHub login       -> token in the browser, stored encrypted next to the app
  2.  Choose repository  -> dropdown of all repos for the signed-in user
  3.  Choose commits     -> dropdown (with search) of the commit history
  4.  Git check          -> git --version
  5.  Clone (if new)     -> git clone <REPO_URL> <REPO_DIR>
  6.  Fetch              -> git fetch --all --prune
  7.  Backup branch      -> git branch backup-before-rollback-<BRANCH>-<PROBLEM> origin/<BRANCH>
  8.  Reset locally      -> git checkout -B <BRANCH> <TARGET>
  9.  Update fork        -> git push --force-with-lease origin <BRANCH>

The GitHub token is stored encrypted next to the app
(git_rewind_secret.enc – Windows: DPAPI, otherwise Fernet), so that
no re-login is needed on the next start.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from pathlib import Path

from PyQt6.QtCore import QTime, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "GitRewind"
APP_VERSION = "v1.2"
if getattr(sys, "frozen", False):  # PyInstaller onefile: __file__ points to a temp extraction dir, the app sits next to the Exe
    APP_DIR = Path(sys.executable).resolve().parent
    ICON_PATH = Path(getattr(sys, "_MEIPASS", APP_DIR)) / "icon.png"
else:
    APP_DIR = Path(__file__).resolve().parent
    ICON_PATH = APP_DIR / "icon.png"

SECRET_FILE = APP_DIR / "git_rewind_secret.enc"
LOG_FILE = APP_DIR / "logs" / "protocoll.txt"
TOKEN_PAGE = "https://github.com/settings/tokens"

COMMIT_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")
MAX_COMMITS = 500

STYLE = """
QWidget {
    background-color: #09101f;
    color: #dbe7ff;
    font-family: "Segoe UI", "Inter", "Calibri", sans-serif;
    font-size: 13px;
}
#AppSurface {
    background-color: #081221;
    border: 1px solid rgba(68, 92, 143, 0.55);
    border-radius: 18px;
}
#Title { font-size: 25px; font-weight: 700; color: #ffffff; }
#VersionPill {
    color: #36e1da;
    background-color: rgba(21, 123, 128, 0.22);
    border: 1px solid rgba(54, 225, 218, 0.30);
    border-radius: 12px;
    padding: 6px 12px;
    font-weight: 600;
}
#HeaderSession { color: #dce8ff; font-size: 12px; }
#SectionTitle { color: #ffffff; font-size: 15px; font-weight: 700; }
#SectionSubTitle { color: #9db0d5; font-size: 11px; }
#PageTitle { color: #ffffff; font-size: 20px; font-weight: 700; }
#PageSubTitle { color: #b5c6e8; font-size: 11px; }
#HeaderCard, #SidebarCard, #MainCard, #FooterCard, #LoginCard, #LogCard {
    background-color: rgba(10, 21, 42, 0.92);
    border: 1px solid rgba(62, 85, 132, 0.55);
    border-radius: 16px;
}
#SidebarCard {
    background-color: rgba(8, 18, 34, 0.95);
}
#SideNav {
    text-align: left;
    padding: 16px 18px;
    font-size: 14px;
    font-weight: 600;
    color: #d6e6ff;
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 14px;
}
#SideNav:hover {
    background-color: rgba(29, 55, 92, 0.45);
    border-color: rgba(76, 156, 255, 0.20);
}
#SideNav:checked {
    color: #35e5dc;
    background-color: rgba(37, 99, 118, 0.28);
    border: 1px solid rgba(53, 229, 220, 0.22);
}
#LogoutBtn {
    color: #ff7c92;
    background-color: rgba(38, 20, 39, 0.75);
    border: 1px solid rgba(193, 82, 115, 0.55);
    border-radius: 14px;
    padding: 12px 20px;
    font-weight: 600;
}
#LogoutBtn:hover { background-color: rgba(59, 28, 47, 0.95); }
#StepCard {
    background-color: rgba(11, 23, 45, 0.95);
    border: 1px solid rgba(58, 81, 126, 0.55);
    border-radius: 18px;
}
#MiniCardOk {
    background-color: rgba(14, 55, 58, 0.18);
    border: 1px solid rgba(37, 211, 182, 0.28);
    border-radius: 16px;
}
#MiniCardWarn {
    background-color: rgba(61, 21, 37, 0.14);
    border: 1px solid rgba(255, 91, 132, 0.24);
    border-radius: 16px;
}
#StepBadge {
    color: #d9ffff;
    background-color: rgba(44, 183, 180, 0.22);
    border: 2px solid rgba(44, 183, 180, 0.85);
    border-radius: 22px;
    font-size: 21px;
    font-weight: 700;
}
QLabel { color: #d8e4fa; background: transparent; }
QLineEdit, QComboBox {
    background-color: rgba(5, 14, 29, 0.92);
    border: 1px solid rgba(57, 82, 130, 0.72);
    border-radius: 14px;
    padding: 12px 14px;
    min-height: 32px;
    color: #f2f6ff;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #68a1ff; }
QLineEdit:disabled, QLineEdit:read-only { color: #7d90b7; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    background-color: #0d1930;
    border: 1px solid rgba(72, 100, 160, 0.9);
    selection-background-color: #3d72ff;
    selection-color: #ffffff;
    outline: none;
}
#CommitTrigger {
    text-align: left;
    padding: 14px 16px;
    min-height: 34px;
    color: #ffffff;
    background-color: rgba(4, 15, 31, 0.94);
    border: 1px solid rgba(57, 82, 130, 0.74);
    border-radius: 14px;
    font-weight: 500;
}
#CommitTrigger:hover { border: 1px solid rgba(104, 161, 255, 0.90); }
#CommitPopup {
    background-color: rgba(9, 18, 36, 0.98);
    border: 1px solid rgba(90, 120, 182, 0.85);
    border-radius: 14px;
}
#CommitSearch {
    background-color: rgba(3, 11, 24, 0.92);
    border: 1px solid rgba(57, 82, 130, 0.74);
    border-radius: 12px;
    padding: 10px 12px;
}
#CommitList {
    border: none;
    background-color: transparent;
    outline: none;
    padding: 4px;
}
#CommitList::item {
    padding: 8px 10px;
    border-radius: 10px;
    color: #dce7ff;
}
#CommitList::item:selected { background-color: rgba(68, 114, 255, 0.95); color: #ffffff; }
#CommitList::item:hover { background-color: rgba(32, 56, 102, 0.80); }
QPushButton {
    background-color: rgba(17, 31, 58, 0.98);
    border: 1px solid rgba(57, 82, 130, 0.72);
    border-radius: 14px;
    padding: 11px 16px;
    color: #e5efff;
}
QPushButton:hover { background-color: rgba(28, 48, 85, 0.98); }
QPushButton:disabled { color: #7f90b0; background-color: rgba(16, 25, 44, 0.92); }
#StartBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(63, 120, 255, 1.0),
        stop:1 rgba(92, 78, 255, 1.0));
    color: #eef2ff;
    font-size: 17px;
    font-weight: 700;
    border: none;
    padding: 14px 24px;
}
#StartBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(79, 133, 255, 1.0),
        stop:1 rgba(111, 96, 255, 1.0));
}
#StartBtn:disabled {
    background: rgba(67, 79, 122, 0.85);
    color: #aab7d9;
}
#GhostBtn {
    background-color: rgba(14, 24, 44, 0.88);
    color: #dbe7ff;
}
#Log {
    background-color: rgba(6, 14, 28, 0.98);
    border: 1px solid rgba(57, 82, 130, 0.70);
    border-radius: 14px;
    color: #dfe9ff;
    font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
    font-size: 12px;
}
#FooterStatus {
    color: #e6f2ff;
    font-weight: 600;
}
#FooterConn {
    color: #ecf6ff;
    font-weight: 600;
}
#StatusDotGreen { color: #33e598; font-size: 18px; font-weight: 700; }
#StatusDotBlue { color: #5b8cff; font-size: 18px; font-weight: 700; }
#StatusDotRed { color: #ff6f91; font-size: 18px; font-weight: 700; }
"""


# ---------------------------------------------------------------- Helper functions


def build_repo_url(user: str, repo: str) -> str:
    """Build the REPO_URL from GitHub user + repo name (always in sync)."""
    if not user or not repo:
        return ""
    return f"https://github.com/{user}/{repo}.git"


def repo_path_for(repo_dir: str) -> Path:
    """Repo folder: absolute or relative to this app's folder."""
    p = Path(repo_dir)
    if not p.is_absolute():
        p = APP_DIR / p
    return p


def inject_token(url: str, token: str) -> str:
    """Inject the token into a GitHub HTTPS URL (other URLs are left unchanged)."""
    if token and url.startswith("https://github.com"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


def mask(line: str, token: str) -> str:
    """Reliably remove GitHub tokens from log lines."""
    if token:
        line = line.replace(token, "****")
    line = re.sub(r"github_pat_[A-Za-z0-9_]+", "github_pat_****", line)
    line = re.sub(r"gh[pousr]_[A-Za-z0-9]+", "gh*_****", line)
    return line


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Run git, returns (return code, stdout+stderr)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return 127, "Git was not found."
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------------------------------------------------------- Token storage


def _dpapi(blob: bytes, protect: bool) -> bytes:
    """Windows DPAPI: encrypt/decrypt data for the current user."""
    import ctypes

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_ulong),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(blob, len(blob))
    src = _DataBlob(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    dst = _DataBlob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)):
        raise RuntimeError(f"DPAPI failed (error code {ctypes.get_last_error()})")
    out = ctypes.string_at(dst.pbData, dst.cbData)
    kernel32.LocalFree(dst.pbData)
    return out


def _fernet():
    """Fernet fallback without Windows DPAPI (e.g. Linux/macOS)."""
    from cryptography.fernet import Fernet

    key = APP_DIR / "git_rewind.key"
    if not key.exists():
        key.write_bytes(Fernet.generate_key())
        try:
            os.chmod(key, 0o600)
        except OSError:
            pass
    return Fernet(key.read_bytes())


def save_secret(token: str, login: str) -> None:
    """Save the token + login encrypted next to the app."""
    payload = json.dumps({"token": token, "login": login}).encode("utf-8")
    blob = _dpapi(payload, True) if os.name == "nt" else _fernet().encrypt(payload)
    SECRET_FILE.write_bytes(blob)


def load_secret() -> dict | None:
    """Load the stored secret; None if missing or on read errors."""
    if not SECRET_FILE.exists():
        return None
    try:
        blob = SECRET_FILE.read_bytes()
        plain = _dpapi(blob, False) if os.name == "nt" else _fernet().decrypt(blob)
        data = json.loads(plain)
        return data if data.get("token") else None
    except Exception:
        return None


def delete_secret() -> None:
    SECRET_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------- GitHub API


def gh_get(path: str, token: str):
    """GET against the GitHub API, returns the JSON."""
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "git-rewind",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub responded with HTTP {exc.code} (path: {path})") from exc
    except Exception as exc:
        raise RuntimeError(f"No connection to GitHub: {exc}") from exc


def list_repos(token: str) -> list[dict]:
    """All repos of the signed-in user (first 100)."""
    return gh_get("/user/repos?per_page=100&type=all&sort=updated", token)


def parse_commits(items: list) -> list[tuple[str, str, str, str]]:
    """GitHub commit list -> [(sha, author, date, subject)] for the dropdowns."""
    out = []
    for it in items:
        sha = it.get("sha", "")
        meta = it.get("commit", {}) or {}
        author = (meta.get("author") or {}).get("name", "").strip() or "?"
        date = (meta.get("author") or {}).get("date", "")[:10]
        subject = (meta.get("message") or "").strip().split("\n")[0][:60]
        out.append((sha, author, date, subject))
    return out


def fetch_all_branches(token: str, user: str, repo: str) -> list[dict]:
    """Fetch all branches of the selected repository."""
    got: list[dict] = []
    page = 1
    while True:
        items = gh_get(f"/repos/{user}/{repo}/branches?per_page=100&page={page}", token)
        if not isinstance(items, list) or not items:
            break
        got.extend(items)
        if len(items) < 100:
            break
        page += 1
    return got


def fetch_all_commits(token: str, user: str, repo: str, branch: str) -> list[dict]:
    """Fetch up to MAX_COMMITS commits from one branch."""
    got: list[dict] = []
    page = 1
    encoded_branch = urllib.parse.quote(branch, safe="")
    while len(got) < MAX_COMMITS:
        items = gh_get(
            f"/repos/{user}/{repo}/commits"
            f"?sha={encoded_branch}&per_page=100&page={page}",
            token,
        )
        if not isinstance(items, list) or not items:
            break
        got.extend(items)
        if len(items) < 100:
            break
        page += 1
    return got[:MAX_COMMITS]


def verify_token(token: str) -> tuple[bool, str]:
    """Check the token against GitHub. Returns (ok, login name or error message)."""
    try:
        data = gh_get("/user", token)
        return True, str(data.get("login", ""))
    except Exception as exc:
        return False, str(exc)


def check_repo_push_permission(token: str, owner: str, repo: str) -> tuple[bool, str]:
    """Check whether the token can push to the selected repository."""
    try:
        data = gh_get(f"/repos/{owner}/{repo}", token)
        permissions = data.get("permissions") or {}
        if permissions.get("push") is True:
            return True, ""
        return False, (
            "The saved GitHub token does not have write access to this repository. "
            "A fine-grained token must grant access to the repository and "
            "'Contents: Read and write' must be set."
        )
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------- Threads


class TokenCheckWorker(QThread):
    """Verifies a GitHub token in the background (auto-login + manual login)."""

    done = pyqtSignal(bool, str)  # (ok, login name or error message)

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def run(self):
        ok, info = verify_token(self.token)
        self.done.emit(ok, info)


class ApiWorker(QThread):
    """Runs a GitHub API function in the background."""

    done = pyqtSignal(object, str)  # (result, error message)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self):
        try:
            self.done.emit(self._fn(*self._args), "")
        except Exception as exc:
            self.done.emit(None, str(exc))


class GitWorker(QThread):
    """Runs the git steps in a thread (the GUI stays interactive)."""

    log = pyqtSignal(str)
    done = pyqtSignal(bool, str)  # (ok, "local" or "push" | error message)

    def __init__(self, cfg: dict, push: bool):
        super().__init__()
        self.cfg = cfg
        self.push = push
        self._tok = cfg.get("token", "")

    def _emit(self, line: str):
        self.log.emit(mask(line, self._tok))

    def _git(
        self,
        args: list[str],
        cwd: Path | None = None,
        header: str | None = None,
    ) -> tuple[int, str]:
        """Run a git step and log it; returns (return code, output)."""
        self._emit(header or f"$ git {' '.join(args)}")
        rc, out = run_git(args, cwd)
        for line in out.splitlines():
            self._emit(f"  {line}")
        return rc, out

    @staticmethod
    def _short_error(out: str) -> str:
        """Most important error line: the last "fatal:" line, else "remote:", else the last line."""
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        for needle in ("fatal:", "remote:"):
            for ln in reversed(lines):
                if ln.startswith(needle):
                    return ln
        return lines[-1] if lines else "no output received"

    def _fail(self, action: str, out: str) -> str:
        return f"ERROR: {action} failed.\n{self._short_error(out)}"

    @staticmethod
    def _classify_push_error(out: str) -> tuple[str, str]:
        """Classify the push error as auth, permissions, ruleset, or unknown."""
        lower = out.lower()
        branch_markers = (
            "gh006", "gh013", "protected branch",
            "repository rule violations", "ruleset",
            "force push", "force-push",
        )
        auth_markers = (
            "401", "bad credentials", "authentication failed",
            "invalid username or token",
        )
        permission_markers = (
            "403", "permission denied", "denied to",
            "write access to repository not granted",
        )
        if any(x in lower for x in branch_markers):
            return "branch_protection", "GitHub branch protection or a ruleset is blocking the force push."
        if any(x in lower for x in auth_markers):
            return "authentication", "The GitHub token is invalid, expired, or revoked."
        if any(x in lower for x in permission_markers):
            return "permission", "The GitHub token does not have sufficient write access."
        return "unknown", "The push failed due to an unknown git error."

    def run(self):
        try:
            if self.push:
                self._phase_push()
            else:
                self._phase_local()
        except Exception as exc:
            self.done.emit(False, f"ERROR: {exc}")

    def _phase_local(self):
        cfg = self.cfg
        path = cfg["repo_path"]
        good = cfg["good"]
        branch = cfg["branch"]

        self._emit("=" * 62)
        self._emit(f"{APP_NAME} {APP_VERSION} - Rollback")
        self._emit(f"Repo:      {cfg['repo']}")
        self._emit(f"Branch:    {branch}")
        self._emit(f"Target:    {good}")
        self._emit(f"Problem:   {cfg['broken']}")
        self._emit(f"Folder:    {path}")
        self._emit("=" * 62)
        self._emit("")

        rc, out = self._git(["--version"], header="Checking git…")
        if rc != 0:
            self._emit("ERROR: git was not found - please install it.")
            self.done.emit(False, "ERROR: git was not found.")
            return

        if not (path / ".git").exists():
            self._emit("")
            self._emit("Cloning the repository…")
            path.mkdir(parents=True, exist_ok=True)
            rc, out = self._git(["clone", inject_token(cfg["url"], self._tok), str(path)])
            if rc != 0:
                self.done.emit(False, self._fail("Clone", out))
                return

        self._sync_origin(path)

        self._emit("")
        auth_url = inject_token(cfg["url"], self._tok)
        rc, out = self._git(
            ["fetch", auth_url, "--prune", "+refs/heads/*:refs/remotes/origin/*"],
            cwd=path,
            header="Loading the GitHub state…",
        )
        if rc != 0:
            self.done.emit(False, self._fail("Fetch (GitHub connection)", out))
            return

        remote_ref = f"refs/remotes/origin/{branch}"
        rc_ref, _ = run_git(["show-ref", "--verify", "--quiet", remote_ref], cwd=path)
        if rc_ref != 0:
            self.done.emit(False, f"ERROR: remote branch '{branch}' no longer exists.")
            return

        rc, _ = run_git(["merge-base", "--is-ancestor", good, remote_ref], cwd=path)
        if rc != 0:
            self.done.emit(False, f"ERROR: target commit {good[:12]} is not reachable from branch '{branch}'.")
            return

        rc, _ = run_git(["merge-base", "--is-ancestor", cfg["broken"], remote_ref], cwd=path)
        if rc != 0:
            self.done.emit(
                False,
                f"ERROR: problem commit {cfg['broken'][:12]} is not reachable from branch '{branch}'.",
            )
            return

        self._emit("")
        self._emit("Saving the current state as a backup branch…")
        safe_branch = re.sub(r"[^A-Za-z0-9._-]+", "-", branch)
        backup_branch = f"backup-before-rollback-{safe_branch}-{cfg['broken'][:12]}"
        rc_check, _ = run_git(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{backup_branch}"],
            cwd=path,
        )
        if rc_check == 0:
            self._emit("Backup branch already exists - keeping the existing backup.")
        else:
            rc, out = self._git(["branch", backup_branch, remote_ref], cwd=path)
            if rc != 0:
                self.done.emit(False, self._fail("Create backup branch", out))
                return
        self._emit("")

        rc, out = self._git(["checkout", "-B", branch, good], cwd=path)
        if rc != 0:
            self.done.emit(False, self._fail(f"Checkout of {good[:7]}", out))
            return

        self._emit("")
        self._emit("=" * 62)
        self._emit(f"Local branch '{branch}' was successfully reset to {good}.")
        self._emit("=" * 62)
        self.done.emit(True, "local")

    def _sync_origin(self, path: Path):
        """Keep origin without a token; authentication happens per git call only."""
        url = self.cfg["url"]
        rc, out = run_git(["remote", "get-url", "origin"], cwd=path)
        if rc != 0:
            self._git(["remote", "add", "origin", url], cwd=path)
        elif out.strip() != url:
            self._git(["remote", "set-url", "origin", url], cwd=path)

    def _phase_push(self):
        cfg = self.cfg
        path = cfg["repo_path"]
        branch = cfg["branch"]
        remote_ref = f"refs/remotes/origin/{branch}"
        auth_url = inject_token(cfg["url"], self._tok)

        self._emit("")
        self._emit("Updating the remote state before the push…")
        rc, out = self._git(
            ["fetch", auth_url, f"{branch}:{remote_ref}"],
            cwd=path,
            header=f"Updating remote {branch}…",
        )
        if rc != 0:
            self.done.emit(False, self._fail("Update remote state", out))
            return

        rc_sha, lease_sha = run_git(["rev-parse", remote_ref], cwd=path)
        lease_sha = lease_sha.strip() if rc_sha == 0 else ""
        if not lease_sha:
            self.done.emit(False, f"ERROR: the remote state of origin/{branch} could not be determined.")
            return

        self._emit("")
        self._emit("Pushing with --force-with-lease (updating the fork)…")
        rc, out = self._git(
            ["push", f"--force-with-lease={branch}:{lease_sha}", auth_url, f"{branch}:{branch}"],
            cwd=path,
            header=f"git push --force-with-lease <GitHub> {branch}:{branch}",
        )
        if rc != 0:
            error_type, explanation = self._classify_push_error(out)
            self._emit("ERROR: push failed - " + self._short_error(out))
            common = (
                "\n\nThe local rollback was completed successfully."
                "\nThe remote branch on GitHub was NOT changed."
            )
            if error_type == "permission":
                if self._tok.startswith("github_pat_"):
                    hint = common + (
                        "\n\nFine-grained token detected. Check:"
                        "\n• Repository access: grant access to this repository"
                        "\n• Repository permissions: Contents = Read and write"
                        "\nThen sign out of GitRewind and sign back in."
                    )
                else:
                    hint = common + "\n\n" + explanation
            elif error_type == "branch_protection":
                hint = common + (
                    f"\n\nGitHub is blocking the force push to branch '{branch}' via branch protection or a ruleset."
                    "\nCheck Repository -> Settings -> Rules / Branches."
                )
            elif error_type == "authentication":
                hint = common + (
                    "\n\nThe token is invalid, expired, or revoked."
                    "\nPlease sign out of GitRewind and sign back in."
                )
            else:
                hint = common + "\n\n" + explanation
            self.done.emit(False, self._fail("Push", out) + hint)
            return

        self._emit("")
        self._emit(f"Branch '{branch}' was successfully reset to {cfg['good']}.")
        self.done.emit(True, "push")


# ---------------------------------------------------------------- UI components


class GitIcon(QWidget):
    """App logo: icon.png next to the app, scaled."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(64, 64)
        self._pixmap = QPixmap(str(ICON_PATH))
        if not self._pixmap.isNull():
            self._pixmap = self._pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

    def paintEvent(self, _event):
        if not self._pixmap.isNull():
            p = QPainter(self)
            p.drawPixmap(0, 0, self._pixmap)


class CommitField(QWidget):
    """Compact commit selector with search in an overlay popup."""

    MAX_HEIGHT = 320

    def __init__(self, placeholder: str = "Select a commit…"):
        super().__init__()
        self._entries: list[tuple[str, str]] = []
        self._matches: list[tuple[str, str]] = []
        self._sha = ""
        self._overlay: QWidget | None = None
        self._box: QFrame | None = None
        self._list: QListWidget | None = None
        self._search_popup: QLineEdit | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.trigger = QPushButton("—")
        self.trigger.setObjectName("CommitTrigger")
        self.trigger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trigger.clicked.connect(self.toggle)
        self.trigger.setToolTip(placeholder)
        row.addWidget(self.trigger, 1)

    def set_items(self, entries: list[tuple[str, str]]):
        self._entries = list(entries)
        self.filter(self._search_popup.text() if self._search_popup else "")

    def clear_selection(self):
        self._sha = ""
        self._entries = []
        self._matches = []
        if self._search_popup is not None:
            self._search_popup.clear()
        self._update_trigger()
        self._rebuild_list()

    def filter(self, text: str):
        t = text.strip().lower()
        self._matches = [
            (sha, label)
            for sha, label in self._entries
            if (not t) or (t in label.lower()) or (t in sha.lower())
        ]
        self._update_trigger()
        self._rebuild_list()

    def current_sha(self) -> str:
        return self._sha

    def select_index(self, index: int):
        if 0 <= index < len(self._entries):
            self._sha = self._entries[index][0]
            self._update_trigger()

    def setEnabled(self, enabled: bool):
        self._close_popup()
        super().setEnabled(enabled)

    def toggle(self):
        if self._overlay is not None and self._overlay.isVisible():
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        win = self.window()
        if self._overlay is None or self._overlay.parent() is not win:
            self._build_overlay(win)
        tl = win.mapFromGlobal(self.mapToGlobal(self.rect().topLeft()))
        bl = win.mapFromGlobal(self.mapToGlobal(self.rect().bottomLeft()))
        h = max(160, min(self.MAX_HEIGHT, win.height() - bl.y() - 16))
        self._overlay.setGeometry(0, bl.y(), win.width(), win.height() - bl.y())
        self._box.move(tl.x(), 0)
        self._box.resize(self.width(), h)
        self._rebuild_list()
        self._overlay.show()
        self._overlay.raise_()
        if self._search_popup is not None:
            self._search_popup.setFocus()
            self._search_popup.selectAll()

    def _build_overlay(self, win: QWidget):
        self._overlay = QWidget(win)
        self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._overlay.mousePressEvent = self._click_away
        self._overlay.keyPressEvent = self._key_away

        self._box = QFrame(self._overlay)
        self._box.setObjectName("CommitPopup")
        box_lay = QVBoxLayout(self._box)
        box_lay.setContentsMargins(10, 10, 10, 10)
        box_lay.setSpacing(8)

        self._search_popup = QLineEdit(self._box)
        self._search_popup.setObjectName("CommitSearch")
        self._search_popup.setPlaceholderText("Search commits…")
        self._search_popup.textChanged.connect(self.filter)
        box_lay.addWidget(self._search_popup)

        self._list = QListWidget(self._box)
        self._list.setObjectName("CommitList")
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.itemClicked.connect(self._on_item)
        box_lay.addWidget(self._list, 1)

    def _click_away(self, _event):
        self._close_popup()

    def _key_away(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._close_popup()

    def _on_item(self, item: QListWidgetItem):
        self._sha = item.data(Qt.ItemDataRole.UserRole) or ""
        self._update_trigger()
        self._close_popup()

    def _update_trigger(self):
        label = next((l for s, l in self._entries if s == self._sha), "")
        self.trigger.setText(label or "Select a commit…")

    def _rebuild_list(self):
        if self._list is None:
            return
        self._list.blockSignals(True)
        self._list.clear()
        for sha, label in self._matches:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, sha)
            self._list.addItem(item)
            if sha == self._sha:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)

    def _close_popup(self):
        if self._overlay is not None:
            self._overlay.hide()


class LoginPanel(QWidget):
    """Login view."""

    authenticated = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 30, 40, 30)
        outer.setSpacing(0)
        outer.addStretch(1)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setMaximumWidth(860)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(28, 28, 28, 28)
        cv.setSpacing(16)

        title = QLabel("Connect to GitHub")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Sign in with your GitHub Personal Access Token. "
            "Fine-grained tokens need at least Metadata: Read and Contents: Read and write."
        )
        subtitle.setObjectName("PageSubTitle")
        subtitle.setWordWrap(True)
        cv.addWidget(title)
        cv.addWidget(subtitle)

        self.btn_browser = QPushButton("Open GitHub in the browser")
        self.btn_browser.setObjectName("GhostBtn")
        self.btn_browser.clicked.connect(self._open_browser)
        cv.addWidget(self.btn_browser)

        row = QHBoxLayout()
        row.setSpacing(12)
        # The token field is a bit taller; the button stays compact. Both are vertically centered.
        TOKEN_H = 52
        BUTTON_H = 54
        self.ed_token = QLineEdit()
        self.ed_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_token.setPlaceholderText("Enter your GitHub token …")
        self.ed_token.setFixedHeight(TOKEN_H)
        self.btn_login = QPushButton("Verify + save")
        self.btn_login.setObjectName("StartBtn")
        self.btn_login.setFixedHeight(BUTTON_H)
        self.btn_login.setStyleSheet("font-size: 15px; padding: 10px 24px;")
        self.btn_login.clicked.connect(self._on_login)
        row.addWidget(self.ed_token, 1, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.btn_login, 0, Qt.AlignmentFlag.AlignVCenter)
        cv.addLayout(row)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("PageSubTitle")
        self.lbl_status.setWordWrap(True)
        cv.addWidget(self.lbl_status)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        self._check_worker: TokenCheckWorker | None = None
        # Keep QThread objects alive until the thread has really finished.
        # Otherwise PyQt can crash with "QThread: Destroyed while thread is still running".
        self._thread_refs: list[QThread] = []

    def _track_thread(self, worker: QThread) -> None:
        self._thread_refs.append(worker)

        def cleanup() -> None:
            if worker in self._thread_refs:
                self._thread_refs.remove(worker)
            worker.deleteLater()

        worker.finished.connect(cleanup)

    def set_busy(self, busy: bool):
        self.btn_browser.setEnabled(not busy)
        self.btn_login.setEnabled(not busy)
        self.ed_token.setEnabled(not busy)

    def set_status(self, text: str, error: bool = False):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet("color: #ff8aa3;" if error else "")

    def _open_browser(self):
        webbrowser.open(TOKEN_PAGE)
        self.set_status("GitHub opened in the browser - create a token and paste it here.")

    def _on_login(self):
        token = self.ed_token.text().strip()
        if len(token) < 10:
            QMessageBox.warning(self, "Token", "Please enter a valid GitHub token (at least 10 characters).")
            return
        self.set_busy(True)
        self.set_status("Verifying the token…")
        self._check_worker = TokenCheckWorker(token)
        self._track_thread(self._check_worker)
        self._check_worker.done.connect(self.check_finished)
        self._check_worker.start()

    def check_finished(self, ok: bool, info: str):
        self._check_worker = None
        if not ok:
            self.set_busy(False)
            self.set_status(info, error=True)
            return
        token = self.ed_token.text().strip()
        try:
            save_secret(token, info)
        except Exception as exc:
            QMessageBox.critical(self, "Saving failed", str(exc))
            self.set_busy(False)
            return
        self.set_status(f"Signed in as {info} - token saved securely.")
        self.authenticated.emit(info, token)


class MainPanel(QWidget):
    """Main app view, including the rollback page and the log page."""

    start_clicked = pyqtSignal()
    validate_clicked = pyqtSignal()
    repo_changed = pyqtSignal(str)
    branch_changed = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._auto_dir = ""
        self.ed_user = QLineEdit()
        self.ed_user.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.pages = QStackedWidget()
        root.addWidget(self.pages)

        # Rollback page
        self.page_roll = QWidget()
        rv = QVBoxLayout(self.page_roll)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(14)

        shell = QFrame()
        shell.setObjectName("MainCard")
        sv = QVBoxLayout(shell)
        sv.setContentsMargins(28, 26, 28, 22)
        sv.setSpacing(16)

        title = QLabel("Create a new rollback")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Return to a previous state in 3 simple steps.")
        subtitle.setObjectName("PageSubTitle")
        sv.addWidget(title)
        sv.addWidget(subtitle)

        sv.addWidget(self._build_repo_step())
        sv.addWidget(self._build_commit_step())
        sv.addWidget(self._build_action_step())
        sv.addStretch(1)

        rv.addWidget(shell, 1)
        self.pages.addWidget(self.page_roll)

        # Log page
        self.page_log = QWidget()
        lv = QVBoxLayout(self.page_log)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        log_shell = QFrame()
        log_shell.setObjectName("LogCard")
        logv = QVBoxLayout(log_shell)
        logv.setContentsMargins(28, 26, 28, 22)
        logv.setSpacing(12)
        log_title = QLabel("Log")
        log_title.setObjectName("PageTitle")
        log_sub = QLabel("All actions, git steps, and error messages.")
        log_sub.setObjectName("PageSubTitle")
        logv.addWidget(log_title)
        logv.addWidget(log_sub)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("Log")
        self.log.setMinimumHeight(580)
        logv.addWidget(self.log, 1)
        lv.addWidget(log_shell, 1)
        self.pages.addWidget(self.page_log)

        self.set_status("ready")
        self._save_log_file()

    def _build_repo_step(self) -> QFrame:
        card = QFrame()
        card.setObjectName("StepCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(18)

        badge = QLabel("1")
        badge.setObjectName("StepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(44, 44)
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)

        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("Select the repository")
        t.setObjectName("SectionTitle")
        s = QLabel("Choose the repository directory")
        s.setObjectName("SectionSubTitle")
        left.addWidget(t)
        left.addWidget(s)
        left.addStretch(1)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(8)
        self.combo_repo = QComboBox()
        self.combo_repo.currentIndexChanged.connect(self._on_repo_selected)
        self.combo_repo.setMinimumWidth(360)
        self.combo_branch = QComboBox()
        self.combo_branch.setMinimumWidth(360)
        self.combo_branch.setEnabled(False)
        self.combo_branch.currentIndexChanged.connect(self._on_branch_selected)
        self.ed_path = QLineEdit()
        self.ed_path.setReadOnly(True)
        self.ed_path.setPlaceholderText("Repo path (auto)")
        repo_label = QLabel("Repository")
        repo_label.setObjectName("SectionSubTitle")
        branch_label = QLabel("Branch")
        branch_label.setObjectName("SectionSubTitle")
        right.addWidget(repo_label)
        right.addWidget(self.combo_repo)
        right.addWidget(branch_label)
        right.addWidget(self.combo_branch)
        right.addWidget(self.ed_path)
        lay.addLayout(right, 1)
        return card

    def _build_commit_step(self) -> QFrame:
        card = QFrame()
        card.setObjectName("StepCard")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(16)

        head = QHBoxLayout()
        head.setSpacing(18)
        badge = QLabel("2")
        badge.setObjectName("StepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(44, 44)
        head.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("Select the commits")
        t.setObjectName("SectionTitle")
        s = QLabel("Choose the good state and the broken state.")
        s.setObjectName("SectionSubTitle")
        left.addWidget(t)
        left.addWidget(s)
        head.addLayout(left, 1)
        outer.addLayout(head)

        grid = QHBoxLayout()
        grid.setSpacing(14)

        left_box = QFrame()
        left_box.setObjectName("MiniCardOk")
        lv = QVBoxLayout(left_box)
        lv.setContentsMargins(18, 18, 18, 18)
        lv.setSpacing(10)
        l1 = QLabel("Target commit")
        l1.setObjectName("SectionTitle")
        l2 = QLabel("The commit you want to roll back to.")
        l2.setObjectName("SectionSubTitle")
        self.commit_ziel = CommitField()
        lv.addWidget(l1)
        lv.addWidget(l2)
        lv.addSpacing(6)
        lv.addWidget(self.commit_ziel)

        right_box = QFrame()
        right_box.setObjectName("MiniCardWarn")
        rv = QVBoxLayout(right_box)
        rv.setContentsMargins(18, 18, 18, 18)
        rv.setSpacing(10)
        r1 = QLabel("Problem commit")
        r1.setObjectName("SectionTitle")
        r2 = QLabel("The commit that is causing the problems.")
        r2.setObjectName("SectionSubTitle")
        self.commit_prob = CommitField()
        rv.addWidget(r1)
        rv.addWidget(r2)
        rv.addSpacing(6)
        rv.addWidget(self.commit_prob)

        grid.addWidget(left_box, 1)
        grid.addWidget(right_box, 1)
        outer.addLayout(grid)
        return card

    def _build_action_step(self) -> QFrame:
        card = QFrame()
        card.setObjectName("StepCard")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(18)
        badge = QLabel("3")
        badge.setObjectName("StepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(44, 44)
        head.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        left = QVBoxLayout()
        left.setSpacing(2)
        t = QLabel("Start the rollback")
        t.setObjectName("SectionTitle")
        s = QLabel("Start the rollback process.")
        s.setObjectName("SectionSubTitle")
        left.addWidget(t)
        left.addWidget(s)
        head.addLayout(left, 1)
        outer.addLayout(head)

        btnrow = QHBoxLayout()
        btnrow.setSpacing(12)
        self.btn_start = QPushButton("⟲   Start rollback")
        self.btn_start.setObjectName("StartBtn")
        self.btn_start.setMinimumHeight(52)
        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_validate = QPushButton("Validate parameters")
        self.btn_validate.setObjectName("GhostBtn")
        self.btn_validate.setMinimumHeight(52)
        self.btn_validate.clicked.connect(self.validate_clicked)
        btnrow.addWidget(self.btn_start, 1)
        btnrow.addWidget(self.btn_validate)
        outer.addLayout(btnrow)

        return card

    def show_page(self, name: str):
        self.pages.setCurrentWidget(self.page_log if name == "log" else self.page_roll)

    def set_user(self, login: str):
        self.ed_user.setText(login)

    def set_repos(self, repos: list[dict]):
        self.combo_repo.blockSignals(True)
        self.combo_repo.clear()
        for r in repos:
            name = r.get("name", "")
            if not name:
                continue
            label = f"{name} (Fork)" if r.get("fork") else name
            self.combo_repo.addItem(
                label,
                {
                    "name": name,
                    "default_branch": r.get("default_branch", ""),
                },
            )
        self.combo_repo.blockSignals(False)

    def repo_selected(self) -> str:
        data = self.combo_repo.currentData()
        if isinstance(data, dict):
            return data.get("name", "")
        return ""

    def repo_default_branch(self) -> str:
        data = self.combo_repo.currentData()
        if isinstance(data, dict):
            return data.get("default_branch", "")
        return ""

    def set_branches(self, branches: list[dict], default_branch: str = ""):
        self.combo_branch.blockSignals(True)
        self.combo_branch.clear()
        main_index = -1
        repo_default_index = -1

        for branch in branches:
            name = str(branch.get("name", "")).strip()
            if not name:
                continue
            self.combo_branch.addItem(name, name)
            current_index = self.combo_branch.count() - 1
            if name == "main":
                main_index = current_index
            if name == default_branch:
                repo_default_index = current_index

        if self.combo_branch.count():
            if main_index >= 0:
                self.combo_branch.setCurrentIndex(main_index)
            elif repo_default_index >= 0:
                self.combo_branch.setCurrentIndex(repo_default_index)
            else:
                self.combo_branch.setCurrentIndex(0)
            self.combo_branch.setEnabled(True)
        else:
            self.combo_branch.setEnabled(False)

        self.combo_branch.blockSignals(False)

    def branch_selected(self) -> str:
        return self.combo_branch.currentData() or ""

    def set_commits(self, entries: list[tuple[str, str]]):
        self.commit_ziel.set_items(entries)
        self.commit_prob.set_items(entries)
        self.commit_ziel.select_index(1 if len(entries) > 1 else 0)
        self.commit_prob.select_index(0)

    def clear_commits(self):
        self.commit_ziel.clear_selection()
        self.commit_prob.clear_selection()

    def set_busy(self, busy: bool):
        self.btn_start.setEnabled(not busy)
        self.btn_validate.setEnabled(not busy)
        self.combo_repo.setEnabled(not busy)
        self.combo_branch.setEnabled(not busy and self.combo_branch.count() > 0)
        self.commit_ziel.setEnabled(not busy)
        self.commit_prob.setEnabled(not busy)

    def append_log(self, msg: str):
        ts = QTime.currentTime().toString("HH:mm:ss")
        self.log.append(f'<span style="color:#5b8cff">[{ts}]</span> {html.escape(msg)}')
        self._save_log_file()

    def set_status(self, kind: str):
        """Just pass the status on to the footer; there is no safety-check area anymore."""
        self.status_changed.emit(kind)

    def _save_log_file(self):
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            LOG_FILE.write_text(self.log.toPlainText(), encoding="utf-8")
        except OSError:
            pass

    def _on_repo_selected(self, _index: int):
        name = self.repo_selected()
        if not name:
            return
        self._auto_dir = name
        self._update_path()
        self.repo_changed.emit(name)

    def _on_branch_selected(self, _index: int):
        branch = self.branch_selected()
        if not branch:
            return
        self.branch_changed.emit(branch)

    def _update_path(self):
        if self._auto_dir:
            self.ed_path.setText(str(repo_path_for(self._auto_dir)))

    def validate(self) -> tuple[dict, list[str]]:
        errs: list[str] = []
        user = self.ed_user.text().strip()
        repo = self.repo_selected()
        branch = self.branch_selected()
        d = self._auto_dir
        good = self.commit_ziel.current_sha()
        broken = self.commit_prob.current_sha()
        if not user:
            errs.append("GitHub user is missing (no login).")
        if not repo:
            errs.append("No repository selected.")
        if not branch:
            errs.append("No branch selected.")
        if not good:
            errs.append("Target commit (good) not selected.")
        elif not COMMIT_RE.fullmatch(good):
            errs.append("Target commit is invalid (hex expected).")
        if not broken:
            errs.append("Problem commit (broken) not selected.")
        elif not COMMIT_RE.fullmatch(broken):
            errs.append("Problem commit is invalid (hex expected).")
        if good and broken and good == broken:
            errs.append("Target and problem commits are identical - the rollback would be pointless.")
        cfg = {
            "user": user,
            "repo": repo,
            "branch": branch,
            "repo_dir": d,
            "repo_path": repo_path_for(d) if d else None,
            "url": build_repo_url(user, repo),
            "good": good,
            "broken": broken,
        }
        return cfg, errs


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setFixedSize(1300, 1080)

        self._api_worker: ApiWorker | None = None
        self._auth_worker: TokenCheckWorker | None = None
        self._worker: GitWorker | None = None
        self._cfg: dict | None = None
        self._token = ""
        self._login_name = ""
        self._repo_push_allowed = False
        self._repo_permission_error = ""
        self._force_close = False
        # Reference the running QThreads additionally until finished() has been emitted.
        self._thread_refs: list[QThread] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        app_surface = QFrame()
        app_surface.setObjectName("AppSurface")
        surface_layout = QVBoxLayout(app_surface)
        surface_layout.setContentsMargins(16, 16, 16, 16)
        surface_layout.setSpacing(12)

        # Header
        header = QFrame()
        header.setObjectName("HeaderCard")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 16, 16, 16)
        head.setSpacing(12)
        head.addWidget(GitIcon())
        brand_col = QVBoxLayout()
        brand_col.setSpacing(3)
        top_brand = QHBoxLayout()
        top_brand.setSpacing(10)
        name = QLabel(APP_NAME)
        name.setObjectName("Title")
        ver = QLabel(APP_VERSION)
        ver.setObjectName("VersionPill")
        top_brand.addWidget(name)
        top_brand.addWidget(ver, 0, Qt.AlignmentFlag.AlignVCenter)
        top_brand.addStretch(1)
        brand_col.addLayout(top_brand)
        head.addLayout(brand_col)
        head.addStretch(1)
        self.lbl_session = QLabel("Not signed in")
        self.lbl_session.setObjectName("HeaderSession")
        head.addWidget(self.lbl_session)
        self.btn_logout = QPushButton("Sign out")
        self.btn_logout.setObjectName("LogoutBtn")
        self.btn_logout.clicked.connect(self.on_logout)
        self.btn_logout.setEnabled(False)
        head.addWidget(self.btn_logout)
        surface_layout.addWidget(header)

        # Content stack (login / app)
        self.login_panel = LoginPanel()
        self.main_panel = MainPanel()
        self.main_panel.status_changed.connect(self._set_app_status)
        self.login_panel.authenticated.connect(self.on_authenticated)
        self.main_panel.start_clicked.connect(self.on_start)
        self.main_panel.validate_clicked.connect(self.on_validate)
        self.main_panel.repo_changed.connect(self.on_repo_changed)
        self.main_panel.branch_changed.connect(self.on_branch_changed)

        self.app_shell = QWidget()
        shell_row = QHBoxLayout(self.app_shell)
        shell_row.setContentsMargins(0, 0, 0, 0)
        shell_row.setSpacing(12)

        sidebar = QFrame()
        sidebar.setObjectName("SidebarCard")
        sidebar.setFixedWidth(270)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(14, 20, 14, 20)
        sv.setSpacing(10)
        self.btn_nav_rollback = QPushButton("⟲   Rollback")
        self.btn_nav_rollback.setObjectName("SideNav")
        self.btn_nav_rollback.setCheckable(True)
        self.btn_nav_rollback.setChecked(True)
        self.btn_nav_logs = QPushButton("☰   Log")
        self.btn_nav_logs.setObjectName("SideNav")
        self.btn_nav_logs.setCheckable(True)
        self.btn_nav_rollback.clicked.connect(lambda: self.switch_section("rollback"))
        self.btn_nav_logs.clicked.connect(lambda: self.switch_section("log"))
        sv.addWidget(self.btn_nav_rollback)
        sv.addWidget(self.btn_nav_logs)
        sv.addStretch(1)
        shell_row.addWidget(sidebar)
        shell_row.addWidget(self.main_panel, 1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.login_panel)
        self.stack.addWidget(self.app_shell)
        surface_layout.addWidget(self.stack, 1)

        # Footer
        footer = QFrame()
        footer.setObjectName("FooterCard")
        fv = QHBoxLayout(footer)
        fv.setContentsMargins(16, 12, 16, 12)
        fv.setSpacing(10)
        self.lbl_footer_status = QLabel("● Ready")
        self.lbl_footer_status.setObjectName("FooterStatus")
        fv.addWidget(self.lbl_footer_status)
        fv.addStretch(1)
        self.lbl_footer_conn = QLabel("GitHub not connected")
        self.lbl_footer_conn.setObjectName("FooterConn")
        fv.addWidget(self.lbl_footer_conn)
        surface_layout.addWidget(footer)

        outer.addWidget(app_surface, 1)
        self._set_app_status("ready")
        self._set_connected(False)
        self._startup_login()

    def _track_thread(self, worker: QThread) -> None:
        self._thread_refs.append(worker)

        def cleanup() -> None:
            if worker in self._thread_refs:
                self._thread_refs.remove(worker)
            worker.deleteLater()

        worker.finished.connect(cleanup)

    def switch_section(self, name: str):
        self.btn_nav_rollback.setChecked(name == "rollback")
        self.btn_nav_logs.setChecked(name == "log")
        self.main_panel.show_page(name)

    def _set_connected(self, connected: bool):
        if connected:
            self.lbl_footer_conn.setText("GitHub connected  ✓")
            self.lbl_footer_conn.setStyleSheet("color: #dffdf5; font-weight: 600;")
        else:
            self.lbl_footer_conn.setText("GitHub not connected")
            self.lbl_footer_conn.setStyleSheet("color: #ffb3c1; font-weight: 600;")

    def _set_app_status(self, kind: str):
        mapping = {
            "ready": ("● Ready", "#39e39a"),
            "busy": ("● Running…", "#6aa3ff"),
            "error": ("● Error", "#ff7594"),
            "done": ("● Done", "#39e39a"),
        }
        text, color = mapping[kind]
        self.lbl_footer_status.setText(text)
        self.lbl_footer_status.setStyleSheet(f"color: {color}; font-weight: 700;")

    # -- Login -----------------------------------------------------------

    def _startup_login(self):
        secret = load_secret()
        if not secret:
            self.login_panel.set_status("\nNo saved login found - please sign in.")
            return
        self.login_panel.set_busy(True)
        self.login_panel.set_status("Verifying the saved login…")
        self._auth_worker = TokenCheckWorker(secret["token"])
        self._track_thread(self._auth_worker)
        self._auth_worker.done.connect(self._on_auth_check)
        self._auth_worker.start()

    def _on_auth_check(self, ok: bool, info: str):
        self._auth_worker = None
        if not ok:
            self.login_panel.set_busy(False)
            if "HTTP 401" in info:
                delete_secret()
                self.login_panel.set_status("The saved token is invalid - please sign in again.", error=True)
            else:
                self.login_panel.set_status("GitHub unreachable - the saved login is kept.", error=True)
            return
        secret = load_secret() or {}
        self.on_authenticated(info, secret.get("token", ""))

    def on_authenticated(self, login: str, token: str):
        self._login_name = login
        self._token = token
        self._repo_push_allowed = False
        self._repo_permission_error = ""
        self.main_panel.set_user(login)
        self.lbl_session.setText(f"Signed in as: {login}")
        self.btn_logout.setEnabled(True)
        self.main_panel.append_log("Connection to GitHub established.")
        if token.startswith("github_pat_"):
            self.main_panel.append_log(
                "Note: fine-grained token - the target repo needs at least Contents: Read and write for the push."
            )
        self.stack.setCurrentWidget(self.app_shell)
        self.switch_section("rollback")
        self._set_connected(True)
        self.load_repos()

    def on_logout(self):
        delete_secret()
        self._token = ""
        self._login_name = ""
        self._repo_push_allowed = False
        self._repo_permission_error = ""
        self.login_panel.ed_token.clear()
        self.login_panel.set_busy(False)
        self.login_panel.set_status("Signed out - please sign in again.")
        self.stack.setCurrentWidget(self.login_panel)
        self.lbl_session.setText("Not signed in")
        self.btn_logout.setEnabled(False)
        self._set_connected(False)

    # -- GitHub API: repos + commits --------------------------------------

    def load_repos(self):
        if self._api_worker is not None and self._api_worker.isRunning():
            return
        self.main_panel.set_status("busy")
        self.main_panel.append_log("Loading the repository list…")
        self._api_worker = ApiWorker(list_repos, self._token)
        self._track_thread(self._api_worker)
        self._api_worker.done.connect(self._on_repos)
        self._api_worker.start()

    def _on_repos(self, repos, err: str):
        self._api_worker = None
        if err or not repos:
            self.main_panel.set_status("error")
            self.main_panel.append_log(f"Could not load the repository list: {err or 'empty response'}")
            return
        self.main_panel.set_repos(repos)
        self.main_panel.set_status("ready")
        self.main_panel.append_log(f"Repository list loaded ({len(repos)} repos).")
        name = self.main_panel.repo_selected()
        if name:
            self.main_panel._auto_dir = name
            self.main_panel._update_path()
            self.on_repo_changed(name)

    def on_repo_changed(self, name: str):
        self.main_panel.clear_commits()
        self.main_panel.combo_branch.blockSignals(True)
        self.main_panel.combo_branch.clear()
        self.main_panel.combo_branch.setEnabled(False)
        self.main_panel.combo_branch.blockSignals(False)
        self.main_panel.append_log(f"Repository '{name}' selected.")
        self._repo_push_allowed = False
        self._repo_permission_error = ""
        if self._api_worker is not None and self._api_worker.isRunning():
            return
        self.main_panel.set_status("busy")
        self.main_panel.set_busy(True)
        self.main_panel.append_log("Checking the push permission…")
        self._api_worker = ApiWorker(check_repo_push_permission, self._token, self._login_name, name)
        self._track_thread(self._api_worker)
        self._api_worker.done.connect(lambda result, err, repo=name: self._on_repo_permission_checked(repo, result, err))
        self._api_worker.start()

    def _on_repo_permission_checked(self, name: str, result, err: str):
        self._api_worker = None
        if name != self.main_panel.repo_selected():
            self.main_panel.set_busy(False)
            return
        if err or result is None:
            self._repo_push_allowed = False
            self._repo_permission_error = err or "Could not check the push permission."
            self.main_panel.append_log(f"Could not check the push permission: {self._repo_permission_error}")
        else:
            allowed, message = result
            self._repo_push_allowed = bool(allowed)
            self._repo_permission_error = message or ""
            self.main_panel.append_log("Push permission: OK" if allowed else "Push permission: MISSING")
            if not allowed and self._token.startswith("github_pat_"):
                self.main_panel.append_log("Fine-grained token: grant access to the repository and set Contents to Read and write.")

        self.main_panel.set_status("busy")
        self.main_panel.append_log("Loading branches…")
        self._api_worker = ApiWorker(fetch_all_branches, self._token, self._login_name, name)
        self._track_thread(self._api_worker)
        self._api_worker.done.connect(lambda result, err, repo=name: self._on_branches(repo, result, err))
        self._api_worker.start()

    def _on_branches(self, repo: str, branches, err: str):
        self._api_worker = None
        if err or branches is None:
            self.main_panel.set_status("error")
            self.main_panel.set_busy(False)
            self.main_panel.append_log(f"Could not load branches: {err}")
            return
        if repo != self.main_panel.repo_selected():
            self.main_panel.set_busy(False)
            return
        default_branch = self.main_panel.repo_default_branch()
        self.main_panel.set_branches(branches, default_branch=default_branch)
        self.main_panel.append_log(f"Branch list loaded ({len(branches)} branches).")
        branch = self.main_panel.branch_selected()
        if branch:
            self.main_panel.set_busy(False)
            self.on_branch_changed(branch)
        else:
            self.main_panel.set_status("error")
            self.main_panel.set_busy(False)
            self.main_panel.append_log("The repository contains no selectable branch.")

    def on_branch_changed(self, branch: str):
        repo = self.main_panel.repo_selected()
        if not repo or not branch:
            return
        self.main_panel.clear_commits()
        if self._api_worker is not None and self._api_worker.isRunning():
            return
        self.main_panel.set_status("busy")
        self.main_panel.set_busy(True)
        self.main_panel.append_log(f"Branch '{branch}' selected.")
        self.main_panel.append_log(f"Loading commit history for branch '{branch}'…")
        self._api_worker = ApiWorker(fetch_all_commits, self._token, self._login_name, repo, branch)
        self._track_thread(self._api_worker)
        self._api_worker.done.connect(
            lambda items, err, expected_repo=repo, expected_branch=branch: self._on_commits_for_branch(
                expected_repo,
                expected_branch,
                items,
                err,
            )
        )
        self._api_worker.start()

    def _on_commits_for_branch(self, repo: str, branch: str, items, err: str):
        self._api_worker = None
        if repo != self.main_panel.repo_selected():
            self.main_panel.set_busy(False)
            return
        if branch != self.main_panel.branch_selected():
            self.main_panel.set_busy(False)
            return
        if err or items is None:
            self.main_panel.set_status("error")
            self.main_panel.set_busy(False)
            self.main_panel.append_log(f"Could not load commit history for branch '{branch}': {err}")
            return
        entries = [(sha, f"{sha[:7]} [{author}] {date}: {subject}") for sha, author, date, subject in parse_commits(items)]
        self.main_panel.set_commits(entries)
        self.main_panel.set_status("ready")
        self.main_panel.set_busy(False)
        self.main_panel.append_log(f"Commit history for branch '{branch}' loaded ({len(entries)} commits).")

    # -- Validate + start ---------------------------------------------------

    def on_validate(self):
        cfg, errs = self.main_panel.validate()
        if not self._repo_push_allowed:
            errs.append(self._repo_permission_error or "The selected repository is missing push permission.")
        if errs:
            QMessageBox.warning(self, "Validate parameters", "\n".join(errs))
            self.main_panel.append_log("Validate parameters: errors found.")
        else:
            QMessageBox.information(self, "Validate parameters", "All parameters valid - push permission: OK.")
            self.main_panel.append_log("Validate parameters: all valid - push permission OK.")

    def on_start(self):
        cfg, errs = self.main_panel.validate()
        if not self._repo_push_allowed:
            errs.append(self._repo_permission_error or "The selected repository is missing push permission.")
        if errs:
            QMessageBox.warning(self, "Rollback not possible", "\n".join(errs))
            return
        answer = QMessageBox.warning(
            self,
            "Confirm rollback",
            (
                f"Repository: {cfg['user']}/{cfg['repo']}\n"
                f"Branch: {cfg['branch']}\n"
                f"Target: {cfg['good'][:12]}\n"
                f"Problem: {cfg['broken'][:12]}\n\n"
                "The selected branch will be rewritten on GitHub "
                "using --force-with-lease.\n\n"
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._cfg = {**cfg, "token": self._token}
        self.main_panel.append_log("Rollback started…")
        self.main_panel.set_status("busy")
        self.main_panel.set_busy(True)
        self._start_worker(GitWorker(self._cfg, push=False))

    def _start_worker(self, worker: GitWorker):
        self._worker = worker
        self._track_thread(worker)
        worker.log.connect(self.main_panel.append_log)
        worker.done.connect(self._on_git_done)
        worker.start()

    def _on_git_done(self, ok: bool, info: str):
        self._worker = None
        if not ok:
            self.main_panel.set_status("error")
            self.main_panel.append_log(info)
            self.main_panel.set_busy(False)
            QMessageBox.critical(self, "Error", info)
            return
        if info == "local":
            self.main_panel.append_log("Local rollback finished - updating the fork (push)…")
            self._start_worker(GitWorker(self._cfg, push=True))
        else:
            self.main_panel.set_status("done")
            self.main_panel.set_busy(False)

    # -- Close window ----------------------------------------------------

    def closeEvent(self, event):
        if self._force_close:
            event.accept()
            return
        active = (
            self._worker is not None and self._worker.isRunning()
        ) or (
            self._api_worker is not None and self._api_worker.isRunning()
        ) or (
            self._auth_worker is not None and self._auth_worker.isRunning()
        )
        if active:
            if (
                QMessageBox.question(
                    self,
                    "Still running…",
                    "An operation is still running. Quit now?\nThe running git step will finish in the background.",
                )
                == QMessageBox.StandardButton.Yes
            ):
                self._force_close = True
                self.close()
                return
            event.ignore()
            return
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#08111f"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#d8dee9"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#0a1526"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#d8dee9"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#16243e"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#d8dee9"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#5b8cff"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#7184aa"))
    app.setPalette(pal)
    app.setApplicationName(APP_NAME)

    win = MainWindow()
    _icon = QIcon(str(ICON_PATH))
    if not _icon.isNull():
        win.setWindowIcon(_icon)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
