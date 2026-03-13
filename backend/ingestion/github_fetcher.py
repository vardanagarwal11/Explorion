"""
GitHub repository fetcher for the ingestion pipeline.

Fetches repo metadata, file structure, and key file contents from the
GitHub REST API (v3). Works with or without a personal access token:
- Without: 60 requests/hour (fine for occasional use)
- With GITHUB_TOKEN: 5,000 requests/hour

Ignored paths: node_modules, dist, build, .git, __pycache__, vendor,
              .venv, .env, .next, coverage, binaries, images, etc.
"""

import asyncio
import logging
import os
import re
from typing import Optional

import httpx

from models.content import GitHubFileMeta, GitHubRepoMeta

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Directories to skip entirely
IGNORED_DIRS = {
    "node_modules", "dist", "build", ".git", "__pycache__", ".venv",
    "venv", "env", ".env", "vendor", ".next", ".nuxt", "coverage",
    ".idea", ".vscode", ".github", ".husky", "target", "out",
    ".cache", ".parcel-cache", ".turbo", "tmp", "temp", ".tox",
    "eggs", ".eggs", "bower_components", ".sass-cache",
}

# File extensions to skip
IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".class", ".o", ".a", ".so", ".dll", ".exe",
    ".bin", ".dat", ".db", ".sqlite", ".log", ".lock",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".mp4", ".mp3", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".map", ".min.js", ".min.css",
    ".DS_Store", ".gitkeep",
}

# Config/entry files we always want to read content of
KEY_FILE_PATTERNS = [
    "README.md", "readme.md", "README.rst",
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "go.sum", "Gemfile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample",
    "Makefile", "justfile",
    "requirements.txt", "Pipfile",
    "tsconfig.json", "next.config.js", "next.config.ts",
    "vite.config.ts", "vite.config.js",
    "webpack.config.js", "rollup.config.js",
    "tailwind.config.js", "tailwind.config.ts",
    "app.py", "main.py", "index.py", "server.py",
    "index.ts", "index.js", "app.ts", "app.js", "main.ts", "main.js",
    "manage.py", "wsgi.py", "asgi.py",
]

# Source file extensions we'll read content for (limited by size)
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".ex", ".exs", ".ml", ".hs",
    ".md", ".rst", ".txt", ".yaml", ".yml", ".toml", ".json",
    ".html", ".css", ".scss", ".less", ".vue", ".svelte",
    ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".graphql", ".proto",
    ".tf", ".hcl",
}

# Max file size to read (100KB)
MAX_FILE_SIZE = 100_000

# Max number of source files to read content for
MAX_SOURCE_FILES = 40

# Max tree entries to process
MAX_TREE_ENTRIES = 500


# ═══════════════════════════════════════════════════════════
# URL Parsing
# ═══════════════════════════════════════════════════════════

GITHUB_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[a-zA-Z0-9\-_.]+)/"
    r"(?P<repo>[a-zA-Z0-9\-_.]+)"
    r"(?:/tree/(?P<branch>[^/]+)(?:/(?P<path>.+))?)?"
    r"(?:\.git)?$"
)


def parse_github_url(url: str) -> dict:
    """
    Parse a GitHub URL into owner, repo, branch, and path.
    
    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/tree/branch
      - https://github.com/owner/repo/tree/branch/path/to/dir
      - github.com/owner/repo
    
    Returns:
        dict with keys: owner, repo, branch (optional), path (optional)
    
    Raises:
        ValueError: If the URL doesn't match GitHub patterns
    """
    # Clean up the URL
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    
    match = GITHUB_URL_PATTERN.match(url)
    if not match:
        raise ValueError(
            f"Invalid GitHub URL: '{url}'. "
            f"Expected format: https://github.com/owner/repo"
        )
    
    return {
        "owner": match.group("owner"),
        "repo": match.group("repo"),
        "branch": match.group("branch"),
        "path": match.group("path"),
    }


# ═══════════════════════════════════════════════════════════
# GitHub API Client
# ═══════════════════════════════════════════════════════════

def _get_headers() -> dict:
    """Build GitHub API request headers."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "arXivisual/1.0",
    }
    token = GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _api_get(client: httpx.AsyncClient, endpoint: str) -> dict | list | None:
    """
    Make an authenticated GET request to the GitHub API.
    
    Returns parsed JSON or None if not found.
    Raises on rate limit or server errors.
    """
    url = f"{GITHUB_API}{endpoint}" if endpoint.startswith("/") else endpoint
    
    response = await client.get(url, headers=_get_headers())
    
    if response.status_code == 404:
        return None
    
    if response.status_code == 403:
        # Check for rate limit
        remaining = response.headers.get("X-RateLimit-Remaining", "?")
        reset = response.headers.get("X-RateLimit-Reset", "?")
        raise RuntimeError(
            f"GitHub API rate limit hit (remaining: {remaining}, resets at: {reset}). "
            f"Set GITHUB_TOKEN env var for higher limits."
        )
    
    response.raise_for_status()
    return response.json()


async def _api_get_raw(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch raw file content from GitHub."""
    headers = _get_headers()
    headers["Accept"] = "application/vnd.github.v3.raw"
    
    response = await client.get(url, headers=headers)
    
    if response.status_code == 404:
        return None
    response.raise_for_status()
    # Explicitly decode as UTF-8 to avoid Windows charmap codec errors
    return response.content.decode("utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════
# Fetch Functions
# ═══════════════════════════════════════════════════════════

async def fetch_repo_metadata(
    owner: str,
    repo: str,
) -> GitHubRepoMeta:
    """
    Fetch repository metadata from the GitHub API.
    
    Fetches: description, languages, stars, forks, topics, license, 
    default branch, creation date, and README content.
    
    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        
    Returns:
        GitHubRepoMeta with all available metadata
        
    Raises:
        ValueError: If repo not found
        RuntimeError: If rate limited
    """
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Fetch repo info and languages in parallel
        repo_task = _api_get(client, f"/repos/{owner}/{repo}")
        langs_task = _api_get(client, f"/repos/{owner}/{repo}/languages")
        
        repo_data, languages = await asyncio.gather(repo_task, langs_task)
        
        if not repo_data:
            raise ValueError(f"Repository not found: {owner}/{repo}")
        
        # Fetch README content
        readme_content = ""
        try:
            readme_data = await _api_get(client, f"/repos/{owner}/{repo}/readme")
            if readme_data and "download_url" in readme_data:
                readme_text = await _api_get_raw(client, readme_data["download_url"])
                if readme_text:
                    readme_content = readme_text
        except Exception as e:
            logger.warning(f"Could not fetch README for {owner}/{repo}: {e}")
        
        # Determine primary language
        primary_language = None
        if languages:
            primary_language = max(languages, key=languages.get) if languages else None
        
        # Extract license
        license_name = None
        if repo_data.get("license") and repo_data["license"].get("spdx_id"):
            license_name = repo_data["license"]["spdx_id"]
        
        return GitHubRepoMeta(
            owner=owner,
            name=repo,
            full_name=f"{owner}/{repo}",
            url=f"https://github.com/{owner}/{repo}",
            description=repo_data.get("description", "") or "",
            default_branch=repo_data.get("default_branch", "main"),
            languages=languages or {},
            primary_language=primary_language,
            stars=repo_data.get("stargazers_count", 0),
            forks=repo_data.get("forks_count", 0),
            topics=repo_data.get("topics", []),
            license=license_name,
            created_at=repo_data.get("created_at"),
            updated_at=repo_data.get("updated_at"),
            readme_content=readme_content,
        )


def _should_ignore(path: str) -> bool:
    """Check if a file/dir path should be ignored."""
    parts = path.split("/")
    
    # Check directory names
    for part in parts:
        if part in IGNORED_DIRS:
            return True
    
    # Check file extension
    filename = parts[-1]
    for ext in IGNORED_EXTENSIONS:
        if filename.endswith(ext):
            return True
    
    # Ignore dotfiles (except key ones like .env.example)
    if filename.startswith(".") and filename not in {".env.example", ".env.sample", ".gitignore"}:
        return True
    
    return False


def _is_key_file(path: str) -> bool:
    """Check if a file is a key config/entry file we want to read."""
    filename = path.split("/")[-1]
    return filename in KEY_FILE_PATTERNS


def _is_source_file(path: str) -> bool:
    """Check if a file is a source file we might want to read."""
    filename = path.split("/")[-1]
    _, ext = os.path.splitext(filename)
    return ext.lower() in SOURCE_EXTENSIONS


async def fetch_repo_tree(
    owner: str,
    repo: str,
    branch: Optional[str] = None,
    focus_path: Optional[str] = None,
) -> list[GitHubFileMeta]:
    """
    Fetch the file tree for a repository using the Git Trees API.
    
    Uses recursive mode for efficiency (single API call for the whole tree).
    Filters out ignored directories, binary files, and noise.
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch to fetch (defaults to repo's default branch)
        focus_path: Optional subdirectory to focus on
    
    Returns:
        List of GitHubFileMeta objects (without content)
    """
    ref = branch or "HEAD"
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        tree_data = await _api_get(
            client, 
            f"/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
        )
        
        if not tree_data or "tree" not in tree_data:
            logger.warning(f"Could not fetch tree for {owner}/{repo}@{ref}")
            return []
        
        files = []
        for item in tree_data["tree"][:MAX_TREE_ENTRIES]:
            path = item.get("path", "")
            
            # Filter
            if _should_ignore(path):
                continue
            
            # Focus path filter
            if focus_path and not path.startswith(focus_path):
                continue
            
            # Only include files (blobs), not directories (trees)
            if item.get("type") != "blob":
                continue
            
            # Detect language from extension
            _, ext = os.path.splitext(path)
            lang_map = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".jsx": "React JSX", ".tsx": "React TSX", ".go": "Go",
                ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
                ".c": "C", ".cpp": "C++", ".cs": "C#", ".swift": "Swift",
                ".kt": "Kotlin", ".scala": "Scala", ".html": "HTML",
                ".css": "CSS", ".scss": "SCSS", ".vue": "Vue",
                ".svelte": "Svelte", ".md": "Markdown", ".json": "JSON",
                ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
                ".sql": "SQL", ".sh": "Shell", ".dockerfile": "Dockerfile",
            }
            language = lang_map.get(ext.lower())
            
            files.append(GitHubFileMeta(
                path=path,
                name=path.split("/")[-1],
                size=item.get("size", 0),
                language=language,
            ))
        
        logger.info(f"Fetched tree: {len(files)} files from {owner}/{repo}")
        return files


async def fetch_key_files(
    owner: str,
    repo: str,
    tree: list[GitHubFileMeta],
    branch: Optional[str] = None,
) -> list[GitHubFileMeta]:
    """
    Fetch content for key config files and top-priority source files.
    
    Priority order:
    1. Key config/entry files (package.json, main.py, etc.)
    2. Source files at shallow depth (root and first-level dirs)
    3. Source files that look like entry points (main, app, index, server)
    
    Args:
        owner: Repository owner
        repo: Repository name
        tree: File tree from fetch_repo_tree
        branch: Branch to fetch from
    
    Returns:
        List of GitHubFileMeta with content populated
    """
    ref = branch or "HEAD"
    
    # Categorize files
    key_files = []
    shallow_sources = []
    entry_point_sources = []
    
    for f in tree:
        if f.size > MAX_FILE_SIZE:
            continue
        
        if _is_key_file(f.path):
            key_files.append(f)
        elif _is_source_file(f.path):
            depth = f.path.count("/")
            name_lower = f.name.lower().replace(".py", "").replace(".ts", "").replace(".js", "")
            
            if name_lower in {"main", "app", "index", "server", "wsgi", "asgi", "manage"}:
                entry_point_sources.append(f)
            elif depth <= 1:
                shallow_sources.append(f)
    
    # Build fetch list (respect MAX_SOURCE_FILES)
    to_fetch = key_files.copy()
    remaining = MAX_SOURCE_FILES - len(to_fetch)
    
    for f in entry_point_sources:
        if remaining <= 0:
            break
        if f not in to_fetch:
            to_fetch.append(f)
            remaining -= 1
    
    for f in shallow_sources:
        if remaining <= 0:
            break
        if f not in to_fetch:
            to_fetch.append(f)
            remaining -= 1
    
    logger.info(f"Fetching content for {len(to_fetch)} key files from {owner}/{repo}")
    
    # Fetch file contents in parallel (batched to avoid rate limits)
    BATCH_SIZE = 10
    result_files = []
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i in range(0, len(to_fetch), BATCH_SIZE):
            batch = to_fetch[i:i + BATCH_SIZE]
            
            tasks = [
                _api_get_raw(
                    client,
                    f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{f.path}"
                )
                for f in batch
            ]
            
            contents = await asyncio.gather(*tasks, return_exceptions=True)
            
            for f, content in zip(batch, contents):
                if isinstance(content, Exception):
                    logger.warning(f"Could not fetch {f.path}: {content}")
                    continue
                if content is not None:
                    result_files.append(GitHubFileMeta(
                        path=f.path,
                        name=f.name,
                        size=f.size,
                        language=f.language,
                        content=content,
                    ))
    
    return result_files


def extract_dependencies(key_files: list[GitHubFileMeta]) -> dict[str, list[str]]:
    """
    Extract dependency names from config files.
    
    Supports: package.json (npm), pyproject.toml (pip), requirements.txt (pip),
              Cargo.toml (cargo), go.mod (go), Gemfile (ruby)
    """
    deps: dict[str, list[str]] = {}
    
    for f in key_files:
        if not f.content:
            continue
        
        try:
            if f.name == "package.json":
                import json
                pkg = json.loads(f.content)
                npm_deps = list(pkg.get("dependencies", {}).keys())
                npm_deps += list(pkg.get("devDependencies", {}).keys())
                if npm_deps:
                    deps["npm"] = npm_deps
                    
            elif f.name == "requirements.txt":
                pip_deps = []
                for line in f.content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name (before any version spec)
                        pkg_name = re.split(r'[><=!~\[]', line)[0].strip()
                        if pkg_name:
                            pip_deps.append(pkg_name)
                if pip_deps:
                    deps["pip"] = pip_deps
                    
            elif f.name == "pyproject.toml":
                # Simple TOML parsing for dependencies
                pip_deps = []
                in_deps = False
                for line in f.content.splitlines():
                    if "dependencies" in line and "=" in line:
                        in_deps = True
                        continue
                    if in_deps:
                        if line.strip().startswith("]"):
                            in_deps = False
                            continue
                        # Extract quoted package name
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            pkg_name = re.split(r'[><=!~\[]', match.group(1))[0].strip()
                            if pkg_name:
                                pip_deps.append(pkg_name)
                if pip_deps:
                    deps["pip"] = pip_deps
                    
            elif f.name == "go.mod":
                go_deps = []
                for line in f.content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("//") and not line.startswith("module") and not line.startswith("go "):
                        parts = line.split()
                        if parts and parts[0] not in {"require", "(", ")"}:
                            go_deps.append(parts[0])
                if go_deps:
                    deps["go"] = go_deps
                    
        except Exception as e:
            logger.warning(f"Error parsing dependencies from {f.name}: {e}")
    
    return deps


# ═══════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════

async def fetch_github_repo(
    url: str,
    branch: Optional[str] = None,
    focus_path: Optional[str] = None,
) -> GitHubRepoMeta:
    """
    Main entry point: fetch all metadata and content for a GitHub repository.
    
    Pipeline:
    1. Parse URL → owner/repo
    2. Fetch repo metadata (description, stars, languages, README)
    3. Fetch file tree (filtered)
    4. Fetch key file contents (configs, entry points)
    5. Extract dependencies
    
    Args:
        url: GitHub repository URL
        branch: Optional specific branch
        focus_path: Optional subdirectory to focus analysis on
        
    Returns:
        GitHubRepoMeta with complete metadata, tree, and key file contents
        
    Raises:
        ValueError: If URL invalid or repo not found
        RuntimeError: If rate limited
    """
    # Step 1: Parse URL
    parsed = parse_github_url(url)
    owner = parsed["owner"]
    repo = parsed["repo"]
    url_branch = parsed.get("branch")
    url_path = parsed.get("path")
    
    # URL-specified branch/path can be overridden by explicit args
    branch = branch or url_branch
    focus_path = focus_path or url_path
    
    logger.info(f"Fetching GitHub repo: {owner}/{repo} (branch={branch}, path={focus_path})")
    
    # Step 2: Fetch metadata
    meta = await fetch_repo_metadata(owner, repo)
    
    # Use specified branch or repo's default
    effective_branch = branch or meta.default_branch
    meta.branch = effective_branch
    
    # Step 3: Fetch tree
    tree = await fetch_repo_tree(owner, repo, effective_branch, focus_path)
    meta.tree = tree
    
    # Step 4: Fetch key file contents
    key_files = await fetch_key_files(owner, repo, tree, effective_branch)
    meta.key_files = key_files
    
    # Step 5: Extract dependencies
    meta.dependencies = extract_dependencies(key_files)
    
    logger.info(
        f"GitHub fetch complete: {owner}/{repo} — "
        f"{len(tree)} files, {len(key_files)} key files, "
        f"{sum(len(d) for d in meta.dependencies.values())} dependencies"
    )
    
    return meta
