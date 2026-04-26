import os
import base64
import httpx
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class GitHubTool:
    """Wraps the GitHub REST API for PR reading and comment posting."""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    # ── Method 1 ────────────────────────────────────────
    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list:
        """
        Fetch all changed files in a PR with their diffs.
        Returns a list of dicts — each has filename, status, patch (the diff).
        """
        url = f"{self.base}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = httpx.get(url, headers=self.headers)
        response.raise_for_status()
        files = response.json()

        # Return only the fields we need
        return [
            {
                "filename": f.get("filename"),
                "status":   f.get("status"),      # added / modified / deleted
                "changes":  f.get("changes"),      # total lines changed
                "patch":    f.get("patch", ""),    # the actual diff text
            }
            for f in files
        ]

    # ── Method 2 ────────────────────────────────────────
    def get_file_content(self, owner: str, repo: str,
                         filepath: str, ref: str = "main") -> str:
        """
        Fetch the full content of a file from the repo.
        Useful for agents to see the complete file, not just the diff.
        """
        url = f"{self.base}/repos/{owner}/{repo}/contents/{filepath}"
        response = httpx.get(url, headers=self.headers, params={"ref": ref})
        response.raise_for_status()
        data = response.json()

        # GitHub returns content as base64 encoded
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content

    # ── Method 3 ────────────────────────────────────────
    def post_review_comment(self, owner: str, repo: str, pr_number: int,
                            body: str, path: str, line: int,
                            commit_sha: str) -> dict:
        """
        Post an inline review comment on a specific line of the PR diff.
        This is how agents leave feedback directly on the code.
        """
        url = f"{self.base}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        data = {
            "body":        body,
            "path":        path,
            "line":        line,
            "side":        "RIGHT",   # RIGHT = new version of the file
            "commit_id":   commit_sha
        }
        response = httpx.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    # ── Method 4 ────────────────────────────────────────
    def post_pr_summary(self, owner: str, repo: str,
                        pr_number: int, body: str) -> dict:
        """
        Post a top-level summary comment on the PR (not inline).
        The orchestrator uses this to post the final review summary.
        """
        url = f"{self.base}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        response = httpx.post(url, headers=self.headers, json={"body": body})
        response.raise_for_status()
        return response.json()

    # ── Method 5 ────────────────────────────────────────
    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> dict:
        """
        Fetch PR metadata — title, author, base branch, head SHA.
        The head SHA is needed when posting inline comments.
        """
        url = f"{self.base}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = httpx.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        return {
            "title":      data.get("title"),
            "author":     data.get("user", {}).get("login"),
            "base_branch":data.get("base", {}).get("ref"),
            "head_sha":   data.get("head", {}).get("sha"),   # needed for comments
            "pr_number":  pr_number,
            "owner":      owner,
            "repo":       repo,
        }