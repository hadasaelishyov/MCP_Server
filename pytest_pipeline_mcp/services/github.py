"""GitHub service helpers.

Thin wrappers for cloning repos, reading files, creating PRs, and posting comments.
Authentication via GITHUB_TOKEN (optional).
"""


from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .base import ErrorCode, ServiceResult


@dataclass(frozen=True)
class CloneResult:
    """Result of cloning a repository."""
    path: Path
    branch: str


@dataclass(frozen=True)
class PRInfo:
    """Information about a created pull request."""
    url: str
    number: int
    branch: str


@dataclass(frozen=True)
class CommentInfo:
    """Information about a posted comment."""
    url: str


class GitHubService:
    """GitHub operations used by services/tools (clone, file read, PR, comments, cleanup)."""

    def __init__(self, token: str | None = None):
        self._token = token or os.getenv("GITHUB_TOKEN")
        self._client = None  # Lazy initialization

    @property
    def has_token(self) -> bool:
        """Check if authentication token is available."""
        return self._token is not None

    def _get_client(self):
        """Get or create GitHub client (lazy initialization)."""
        if self._client is None:
            try:
                from github import Github
                self._client = Github(self._token) if self._token else Github()
            except ImportError:
                return None
        return self._client

    def _parse_repo_url(self, url: str) -> tuple[str, str] | None:
        """Parse GitHub URL to extract owner and repo name."""
        
        patterns = [
            r"github\.com[/:]([^/]+)/([^/.]+?)(?:\.git)?/?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)

        return None

    # =========================================================================
    # Clone Repository
    # =========================================================================

    def clone_repository(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> ServiceResult[CloneResult]:
        """Clone a GitHub repository to a temporary directory."""
        try:
            from git import Repo
        except ImportError:
            return ServiceResult.fail(
                ErrorCode.INTERNAL_ERROR,
                "GitPython not installed. Run: pip install gitpython"
            )

        # Validate URL
        if not self._parse_repo_url(repo_url):
            return ServiceResult.fail(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid GitHub URL: {repo_url}"
            )

        temp_dir = Path(tempfile.mkdtemp(prefix="pytest_gen_"))

        try:
            Repo.clone_from(
                repo_url,
                temp_dir,
                branch=branch,
                depth=1  # Shallow clone for speed
            )
            return ServiceResult.ok(CloneResult(path=temp_dir, branch=branch))

        except Exception as e:
            # Try 'master' if 'main' fails
            if branch == "main":
                try:
                    Repo.clone_from(
                        repo_url,
                        temp_dir,
                        branch="master",
                        depth=1
                    )
                    return ServiceResult.ok(CloneResult(path=temp_dir, branch="master"))
                except Exception:
                    pass

            # Cleanup on failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            return ServiceResult.fail(
                ErrorCode.GITHUB_CLONE_ERROR,
                f"Failed to clone repository: {str(e)}"
            )

    def cleanup_clone(self, path: Path) -> None:
        """Remove a cloned repository directory."""
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    # =========================================================================
    # Create Pull Request
    # =========================================================================

    def create_pull_request(
        self,
        repo_url: str,
        file_path: str,
        file_content: str,
        branch_name: str,
        commit_message: str,
        pr_title: str,
        pr_body: str
    ) -> ServiceResult[PRInfo]:
        """Create a pull request with a new/updated file."""
        
        if not self._token:
            return ServiceResult.fail(
                ErrorCode.GITHUB_AUTH_ERROR,
                "GitHub token required to create PRs. Set GITHUB_TOKEN environment variable."
            )

        parsed = self._parse_repo_url(repo_url)
        if not parsed:
            return ServiceResult.fail(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid GitHub URL: {repo_url}"
            )

        owner, repo_name = parsed

        client = self._get_client()
        if not client:
            return ServiceResult.fail(
                ErrorCode.INTERNAL_ERROR,
                "PyGithub not installed. Run: pip install PyGithub"
            )

        try:
            repo = client.get_repo(f"{owner}/{repo_name}")

            # Get default branch
            default_branch = repo.default_branch
            base_ref = repo.get_branch(default_branch)

            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_ref.commit.sha
            )

            # Create or update file
            try:
                contents = repo.get_contents(file_path, ref=branch_name)
                repo.update_file(
                    file_path,
                    commit_message,
                    file_content,
                    contents.sha,
                    branch=branch_name
                )
            except Exception:
                repo.create_file(
                    file_path,
                    commit_message,
                    file_content,
                    branch=branch_name
                )

            # Create PR
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=default_branch
            )

            return ServiceResult.ok(PRInfo(
                url=pr.html_url,
                number=pr.number,
                branch=branch_name
            ))

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return ServiceResult.fail(
                    ErrorCode.GITHUB_REPO_NOT_FOUND,
                    f"Repository not found or no access: {owner}/{repo_name}"
                )
            elif "401" in error_msg or "403" in error_msg:
                return ServiceResult.fail(
                    ErrorCode.GITHUB_AUTH_ERROR,
                    "Authentication failed. Check your GITHUB_TOKEN permissions."
                )
            else:
                return ServiceResult.fail(
                    ErrorCode.GITHUB_API_ERROR,
                    f"Failed to create PR: {error_msg}"
                )

    # =========================================================================
    # Post Comment
    # =========================================================================

    def post_comment(
        self,
        repo_url: str,
        pr_number: int,
        body: str
    ) -> ServiceResult[CommentInfo]:
        """Post a comment on a pull request."""
        
        if not self._token:
            return ServiceResult.fail(
                ErrorCode.GITHUB_AUTH_ERROR,
                "GitHub token required to post comments. Set GITHUB_TOKEN environment variable."
            )

        parsed = self._parse_repo_url(repo_url)
        if not parsed:
            return ServiceResult.fail(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid GitHub URL: {repo_url}"
            )

        owner, repo_name = parsed

        client = self._get_client()
        if not client:
            return ServiceResult.fail(
                ErrorCode.INTERNAL_ERROR,
                "PyGithub not installed. Run: pip install PyGithub"
            )

        try:
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            comment = pr.create_issue_comment(body)

            return ServiceResult.ok(CommentInfo(url=comment.html_url))

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return ServiceResult.fail(
                    ErrorCode.GITHUB_REPO_NOT_FOUND,
                    f"Repository or PR not found: {owner}/{repo_name}#{pr_number}"
                )
            else:
                return ServiceResult.fail(
                    ErrorCode.GITHUB_API_ERROR,
                    f"Failed to post comment: {error_msg}"
                )

    # =========================================================================
    # Get File Content
    # =========================================================================

    def get_file_content(
        self,
        repo_url: str,
        file_path: str,
        branch: str = "main"
    ) -> ServiceResult[str]:
        """Get content of a file from a repository."""
        
        parsed = self._parse_repo_url(repo_url)
        if not parsed:
            return ServiceResult.fail(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid GitHub URL: {repo_url}"
            )

        owner, repo_name = parsed

        client = self._get_client()
        if not client:
            return ServiceResult.fail(
                ErrorCode.INTERNAL_ERROR,
                "PyGithub not installed. Run: pip install PyGithub"
            )

        try:
            repo = client.get_repo(f"{owner}/{repo_name}")

            for try_branch in [branch, "main", "master"]:
                try:
                    content = repo.get_contents(file_path, ref=try_branch)
                    if hasattr(content, 'decoded_content'):
                        return ServiceResult.ok(
                            content.decoded_content.decode('utf-8')
                        )
                except Exception:
                    continue

            return ServiceResult.fail(
                ErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}"
            )

        except Exception as e:
            return ServiceResult.fail(
                ErrorCode.GITHUB_API_ERROR,
                f"Failed to get file: {str(e)}"
            )
