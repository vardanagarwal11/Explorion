"""
GitHub repository analyzer for the ingestion pipeline.

Takes raw GitHubRepoMeta from the fetcher and produces structured
sections suitable for the visualization pipeline. Each section represents
a logical aspect of the repository that can be visualized:

1. Project Overview — purpose, problem solved, use case
2. Architecture — frontend/backend/services, data flow
3. Code Structure — major modules, class/function relationships
4. Core Logic — key algorithms, data processing
5. Tech Stack — languages, frameworks, dependencies
6. Setup & Usage — installation, environment, commands

Uses LLM to analyze code and generate summaries when available,
falls back to heuristic analysis otherwise.
"""

import logging
import os
import re
import uuid
from typing import Optional

from models.paper import Section, Equation
from models.content import (
    ContentType,
    ContentMeta,
    GitHubRepoMeta,
    StructuredContent,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Heuristic Analysis (No LLM required)
# ═══════════════════════════════════════════════════════════

def _detect_project_type(meta: GitHubRepoMeta) -> str:
    """Detect what kind of project this is from signals."""
    deps_flat = []
    for d in meta.dependencies.values():
        deps_flat.extend([x.lower() for x in d])
    
    tree_paths = [f.path.lower() for f in meta.tree]
    
    # Web frontend
    if any(d in deps_flat for d in ["react", "next", "vue", "svelte", "angular"]):
        if any(d in deps_flat for d in ["fastapi", "express", "django", "flask", "gin"]):
            return "full_stack_web"
        return "web_frontend"
    
    # Web backend  
    if any(d in deps_flat for d in ["fastapi", "flask", "django", "express", "gin", "actix", "rocket"]):
        return "web_backend"
    
    # CLI
    if any(d in deps_flat for d in ["click", "typer", "argparse", "cobra", "clap"]):
        return "cli_tool"
    
    # ML/AI
    if any(d in deps_flat for d in ["torch", "tensorflow", "transformers", "scikit-learn", "jax"]):
        return "ml_ai"
    
    # Library/SDK
    if any("setup.py" in p or "setup.cfg" in p for p in tree_paths):
        return "library"
    
    # Mobile
    if any(d in deps_flat for d in ["react-native", "flutter", "swift", "kotlin"]):
        return "mobile_app"
    
    # Data pipeline
    if any(d in deps_flat for d in ["airflow", "dagster", "prefect", "dbt", "spark"]):
        return "data_pipeline"
    
    return "general"


def _build_tree_summary(meta: GitHubRepoMeta, max_depth: int = 2) -> str:
    """Build a readable file tree summary."""
    lines = [f"📁 {meta.full_name}/"]
    
    # Group files by top-level directory
    dirs: dict[str, list[str]] = {"(root)": []}
    
    for f in meta.tree:
        parts = f.path.split("/")
        if len(parts) == 1:
            dirs["(root)"].append(f"  {f.name}")
        else:
            top_dir = parts[0]
            if top_dir not in dirs:
                dirs[top_dir] = []
            if len(parts) <= max_depth + 1:
                indent = "  " * len(parts)
                dirs[top_dir].append(f"{indent}{f.name}")
    
    # Root files first
    for line in dirs.get("(root)", [])[:10]:
        lines.append(line)
    
    # Then directories
    for dir_name, files in sorted(dirs.items()):
        if dir_name == "(root)":
            continue
        lines.append(f"  📂 {dir_name}/")
        for line in files[:8]:
            lines.append(line)
        if len(files) > 8:
            lines.append(f"    ... +{len(files) - 8} more files")
    
    return "\n".join(lines[:50])  # Cap at 50 lines


def _build_tech_stack_summary(meta: GitHubRepoMeta) -> str:
    """Build a technology stack summary."""
    parts = []
    
    # Languages
    if meta.languages:
        total = sum(meta.languages.values())
        lang_pcts = [
            f"{lang} ({bytes_count * 100 // total}%)"
            for lang, bytes_count in sorted(meta.languages.items(), key=lambda x: -x[1])[:6]
        ]
        parts.append(f"**Languages:** {', '.join(lang_pcts)}")
    
    # Dependencies by manager
    for manager, deps in meta.dependencies.items():
        label = {"npm": "Node.js", "pip": "Python", "go": "Go", "cargo": "Rust"}.get(manager, manager)
        top_deps = deps[:15]
        parts.append(f"**{label} Dependencies:** {', '.join(top_deps)}")
        if len(deps) > 15:
            parts.append(f"  ... +{len(deps) - 15} more")
    
    # Repo stats
    stats = []
    if meta.stars:
        stats.append(f"⭐ {meta.stars:,} stars")
    if meta.forks:
        stats.append(f"🍴 {meta.forks:,} forks")
    if meta.license:
        stats.append(f"📄 {meta.license}")
    if stats:
        parts.append(f"**Stats:** {' · '.join(stats)}")
    
    if meta.topics:
        parts.append(f"**Topics:** {', '.join(meta.topics[:10])}")
    
    return "\n\n".join(parts)


def _extract_architecture_from_tree(meta: GitHubRepoMeta) -> str:
    """Infer architecture from the directory structure."""
    top_dirs = set()
    for f in meta.tree:
        parts = f.path.split("/")
        if len(parts) > 1:
            top_dirs.add(parts[0])
    
    components = []
    
    # Common patterns
    pattern_map = {
        "frontend": "🖥️ Frontend",
        "client": "🖥️ Client",
        "web": "🌐 Web Interface",
        "app": "📱 App",
        "backend": "⚙️ Backend",
        "server": "⚙️ Server",
        "api": "🔌 API Layer",
        "routes": "🛣️ Routes",
        "controllers": "🎮 Controllers",
        "services": "🔧 Services",
        "models": "📊 Data Models",
        "db": "🗄️ Database",
        "database": "🗄️ Database",
        "migrations": "📦 DB Migrations",
        "tests": "🧪 Tests",
        "test": "🧪 Tests",
        "docs": "📚 Documentation",
        "config": "⚙️ Configuration",
        "utils": "🔨 Utilities",
        "lib": "📚 Library",
        "src": "📁 Source Code",
        "pkg": "📦 Packages",
        "cmd": "🚀 Commands/Entry Points",
        "internal": "🔒 Internal Modules",
        "public": "🌐 Public/Static Assets",
        "static": "📄 Static Files",
        "templates": "📝 Templates",
        "views": "👁️ Views",
        "components": "🧩 UI Components",
        "hooks": "🪝 React Hooks",
        "store": "📦 State Management",
        "middleware": "🔀 Middleware",
        "plugins": "🔌 Plugins",
        "agents": "🤖 AI Agents",
        "workers": "👷 Background Workers",
        "jobs": "⏰ Job Processing",
        "scripts": "📜 Scripts",
        "tools": "🔧 Tools",
        "rendering": "🎬 Rendering",
        "ingestion": "📥 Data Ingestion",
    }
    
    for dir_name in sorted(top_dirs):
        label = pattern_map.get(dir_name.lower())
        if label:
            components.append(f"- {label} (`{dir_name}/`)")
        elif dir_name not in {"__pycache__", ".git", "node_modules"}:
            components.append(f"- 📂 `{dir_name}/`")
    
    if components:
        return "## Detected Architecture\n\n" + "\n".join(components[:20])
    return "Architecture could not be automatically detected from directory structure."


def _extract_entry_points(meta: GitHubRepoMeta) -> str:
    """Identify entry points from key files."""
    entry_points = []
    
    for f in meta.key_files:
        if not f.content:
            continue
        
        # Python entry points
        if f.name in {"main.py", "app.py", "server.py", "manage.py", "wsgi.py", "asgi.py"}:
            # Extract the first docstring or main function
            lines = f.content.splitlines()[:30]
            preview = "\n".join(lines)
            entry_points.append(f"### `{f.path}` (Python Entry Point)\n\n```python\n{preview}\n```")
        
        # JS/TS entry points
        elif f.name in {"index.ts", "index.js", "app.ts", "app.js", "main.ts", "main.js", "server.ts", "server.js"}:
            lines = f.content.splitlines()[:30]
            preview = "\n".join(lines)
            lang = "typescript" if f.name.endswith(".ts") else "javascript"
            entry_points.append(f"### `{f.path}` ({lang.title()} Entry Point)\n\n```{lang}\n{preview}\n```")
    
    if entry_points:
        return "\n\n".join(entry_points[:5])
    return "No entry points detected."


# ═══════════════════════════════════════════════════════════
# Section Generation
# ═══════════════════════════════════════════════════════════

def analyze_repo_to_sections(meta: GitHubRepoMeta) -> list[Section]:
    """
    Convert a GitHub repository's metadata into structured sections
    suitable for the visualization pipeline.
    
    Generates 5–8 sections covering the key aspects of the repository:
    1. Overview & Purpose
    2. Architecture & System Design
    3. Code Structure & Modules
    4. Core Logic & Key Files
    5. Tech Stack & Dependencies
    6. Data Flow (if applicable)
    7. Setup & Configuration
    
    Args:
        meta: Complete GitHubRepoMeta from the fetcher
        
    Returns:
        List of Section objects ready for the visualization pipeline
    """
    sections: list[Section] = []
    project_type = _detect_project_type(meta)
    
    logger.info(f"Analyzing repo {meta.full_name} (detected type: {project_type})")
    
    # ─── Section 1: Overview & Purpose ───────────────────────
    overview_content = []
    overview_content.append(f"# {meta.name}")
    if meta.description:
        overview_content.append(f"\n{meta.description}")
    overview_content.append(f"\n**Project Type:** {project_type.replace('_', ' ').title()}")
    overview_content.append(f"**Primary Language:** {meta.primary_language or 'Unknown'}")
    
    if meta.readme_content:
        # Extract the first few paragraphs from README
        readme_lines = meta.readme_content.splitlines()
        intro_lines = []
        for line in readme_lines:
            if len(intro_lines) > 20:
                break
            intro_lines.append(line)
        if intro_lines:
            overview_content.append(f"\n## From README\n\n" + "\n".join(intro_lines))
    
    sections.append(Section(
        id=f"gh-{meta.name}-overview",
        title="Project Overview",
        level=1,
        content="\n".join(overview_content),
        summary=meta.description or f"Overview of the {meta.name} repository",
        parent_id=None,
    ))
    
    # ─── Section 2: Architecture ─────────────────────────────
    arch_content = _extract_architecture_from_tree(meta)
    
    # Add data flow for web apps
    if project_type in {"web_backend", "full_stack_web", "web_frontend"}:
        arch_content += "\n\n## Data Flow\n\n"
        arch_content += "User → Frontend → API → Backend Services → Database → Response → Frontend → User"
    elif project_type == "ml_ai":
        arch_content += "\n\n## ML Pipeline\n\n"
        arch_content += "Data → Preprocessing → Model Training → Evaluation → Inference → Output"
    elif project_type == "data_pipeline":
        arch_content += "\n\n## Pipeline Flow\n\n"
        arch_content += "Source → Extract → Transform → Load → Analytics"
    
    sections.append(Section(
        id=f"gh-{meta.name}-architecture",
        title="Architecture & System Design",
        level=1,
        content=arch_content,
        summary=f"System architecture and component layout of {meta.name}",
        parent_id=None,
    ))
    
    # ─── Section 3: Code Structure ───────────────────────────
    tree_summary = _build_tree_summary(meta)
    
    sections.append(Section(
        id=f"gh-{meta.name}-structure",
        title="Code Structure & Modules",
        level=1,
        content=f"## File Tree\n\n```\n{tree_summary}\n```\n\n"
                f"**Total files:** {len(meta.tree)}\n"
                f"**Key files loaded:** {len(meta.key_files)}",
        summary=f"File organization and module structure of {meta.name}",
        parent_id=None,
    ))
    
    # ─── Section 4: Core Logic & Key Files ───────────────────
    entry_points = _extract_entry_points(meta)
    
    # Also include other interesting source files
    other_code = []
    for f in meta.key_files:
        if not f.content:
            continue
        if f.name in {"main.py", "app.py", "server.py", "index.ts", "index.js", "app.ts", "app.js"}:
            continue  # Already shown in entry points
        if f.language and f.language not in {"JSON", "YAML", "TOML", "Markdown"}:
            lines = f.content.splitlines()[:25]
            preview = "\n".join(lines)
            ext = f.path.split(".")[-1] if "." in f.path else ""
            lang = {"py": "python", "js": "javascript", "ts": "typescript", "go": "go", "rs": "rust"}.get(ext, ext)
            other_code.append(f"### `{f.path}`\n\n```{lang}\n{preview}\n```")
    
    core_content = "## Entry Points\n\n" + entry_points
    if other_code:
        core_content += "\n\n## Other Key Source Files\n\n" + "\n\n".join(other_code[:5])
    
    sections.append(Section(
        id=f"gh-{meta.name}-core",
        title="Core Logic & Key Files",
        level=1,
        content=core_content,
        summary=f"Entry points, main logic, and key source files in {meta.name}",
        parent_id=None,
    ))
    
    # ─── Section 5: Tech Stack ───────────────────────────────
    tech_content = _build_tech_stack_summary(meta)
    
    sections.append(Section(
        id=f"gh-{meta.name}-techstack",
        title="Technology Stack & Dependencies",
        level=1,
        content=tech_content,
        summary=f"Languages, frameworks, and dependencies used in {meta.name}",
        parent_id=None,
    ))
    
    # ─── Section 6: Setup & Configuration ────────────────────
    setup_content = []
    
    for f in meta.key_files:
        if not f.content:
            continue
        if f.name in {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
            setup_content.append(f"### `{f.name}`\n\n```yaml\n{f.content[:1500]}\n```")
        elif f.name in {"Makefile", "justfile"}:
            setup_content.append(f"### `{f.name}`\n\n```makefile\n{f.content[:1500]}\n```")
        elif f.name in {".env.example", ".env.sample"}:
            setup_content.append(f"### `{f.name}`\n\n```\n{f.content[:1000]}\n```")
    
    if setup_content:
        sections.append(Section(
            id=f"gh-{meta.name}-setup",
            title="Setup & Configuration",
            level=1,
            content="\n\n".join(setup_content[:4]),
            summary=f"Build, deployment, and configuration files for {meta.name}",
            parent_id=None,
        ))
    
    # Set order indices
    for i, section in enumerate(sections):
        section.id = section.id  # Keep existing id
        # Pydantic models are immutable by default, so we create new ones
    
    # Rebuild with proper order indices
    ordered_sections = []
    for i, s in enumerate(sections):
        ordered_sections.append(Section(
            id=s.id,
            title=s.title,
            level=s.level,
            content=s.content,
            summary=s.summary,
            parent_id=s.parent_id,
            equations=s.equations,
            figures=s.figures,
            tables=s.tables,
        ))
    
    logger.info(f"Generated {len(ordered_sections)} sections for {meta.full_name}")
    return ordered_sections


# ═══════════════════════════════════════════════════════════
# Build StructuredContent
# ═══════════════════════════════════════════════════════════

def build_structured_content_from_repo(meta: GitHubRepoMeta) -> StructuredContent:
    """
    Convert a GitHubRepoMeta into a StructuredContent object.
    
    This is the final output format that the visualization pipeline
    consumes — identical interface to what papers produce.
    """
    sections = analyze_repo_to_sections(meta)
    
    content_meta = ContentMeta(
        content_type=ContentType.GITHUB_REPO,
        content_id=f"gh:{meta.full_name}",
        title=meta.name,
        description=meta.description or f"GitHub repository: {meta.full_name}",
        source_url=meta.url,
        repo_meta=meta,
    )
    
    return StructuredContent(
        meta=content_meta,
        sections=sections,
    )
