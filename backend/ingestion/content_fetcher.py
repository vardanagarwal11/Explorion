"""
Technical content fetcher for the ingestion pipeline.

Handles blogs, documentation pages, and raw technical text.
Converts any technical content into structured sections for
the visualization pipeline.

Supported inputs:
- Blog/article URL → fetch + extract main content
- Documentation URL → fetch + extract content
- Raw text/markdown → parse directly

Uses BeautifulSoup for HTML extraction (already a project dependency).
"""

import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from models.paper import Section, Equation, ParsedContent
from models.content import (
    ContentType,
    ContentMeta,
    TechnicalContentMeta,
    StructuredContent,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# URL Content Fetching
# ═══════════════════════════════════════════════════════════

async def fetch_url_content(url: str) -> tuple[str, str, Optional[str]]:
    """
    Fetch content from a URL and extract the main article text.
    
    Returns:
        Tuple of (title, content_markdown, author)
    """
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "arXivisual/1.0 (content analyzer)"}
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        # Explicitly decode as UTF-8 to avoid Windows charmap codec errors
        html = response.content.decode("utf-8", errors="replace")
    
    soup = BeautifulSoup(html, "lxml")

    # ── Paywall / login-wall detection ──────────────────────────────────────
    # Detect pages that require authentication or are paywalled before we
    # waste an LLM call on navigation junk.
    _PAYWALL_SIGNALS = [
        "sign in to continue", "log in to read", "subscribe to read",
        "purchase this article", "purchase access", "full text available",
        "institutional access", "create free account", "buy this article",
        "ieee account", "this content is not available",
    ]
    page_text_lower = soup.get_text(separator=" ", strip=True).lower()
    for signal in _PAYWALL_SIGNALS:
        if signal in page_text_lower:
            raise ValueError(
                f"Content at {url!r} appears to be paywalled or requires login "
                f"(detected: '{signal}'). Please provide a publicly accessible URL, "
                f"an arXiv ID, or paste the text directly."
            )
    # ────────────────────────────────────────────────────────────────────────

    # Extract title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    # Try og:title for cleaner title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"]
    
    # Try to find a <h1> tag as the best title
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(strip=True)
        if h1_text and len(h1_text) < 200:
            title = h1_text
    
    # Extract author
    author = None
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        author = author_meta["content"]
    
    # Extract main content
    content = _extract_main_content(soup)

    # ── Minimum content quality guard ────────────────────────────────────
    word_count = len(content.split())
    if word_count < 150:
        raise ValueError(
            f"Fetched content from {url!r} is too short ({word_count} words). "
            f"The page may be paywalled, require JavaScript, or be a redirect. "
            f"Try pasting the article text directly instead."
        )
    # ────────────────────────────────────────────────────────────────────

    logger.info(f"Fetched URL content: '{title}' ({len(content)} chars, {word_count} words)")
    return title, content, author


def _extract_main_content(soup: BeautifulSoup) -> str:
    """
    Extract the main article content from an HTML page.
    
    Tries multiple strategies to find the article body:
    1. <article> tag
    2. <main> tag
    3. [role="main"] attribute
    4. Common article class names
    5. Largest text-containing div
    
    Returns markdown-formatted text.
    """
    # Remove noise elements
    for tag in soup.find_all(["nav", "header", "footer", "aside", "script", 
                              "style", "noscript", "iframe", "form"]):
        tag.decompose()
    
    # Remove cookie banners, ads, etc.
    for selector in [".cookie", ".advertisement", ".ad-", "#cookie", ".sidebar",
                     ".nav", ".footer", ".header", ".menu", ".popup", ".modal"]:
        for el in soup.select(selector):
            el.decompose()
    
    # Strategy 1: <article> tag
    article = soup.find("article")
    if article:
        return _html_to_markdown(article)
    
    # Strategy 2: <main> tag
    main = soup.find("main")
    if main:
        return _html_to_markdown(main)
    
    # Strategy 3: role="main"
    main_role = soup.find(attrs={"role": "main"})
    if main_role:
        return _html_to_markdown(main_role)
    
    # Strategy 4: Common class names
    for class_name in ["article", "post", "entry", "content", "post-content",
                       "article-content", "entry-content", "blog-post",
                       "markdown-body", "prose"]:
        content = soup.find(class_=class_name)
        if content:
            return _html_to_markdown(content)
    
    # Strategy 5: Largest text-containing div
    best_div = None
    best_text_len = 0
    for div in soup.find_all("div"):
        text = div.get_text(strip=True)
        if len(text) > best_text_len and len(text) > 200:
            best_text_len = len(text)
            best_div = div
    
    if best_div:
        return _html_to_markdown(best_div)
    
    # Fallback: just get all text from body
    body = soup.find("body")
    if body:
        return body.get_text(separator="\n", strip=True)
    
    return soup.get_text(separator="\n", strip=True)


def _html_to_markdown(element) -> str:
    """
    Convert an HTML element to simple markdown.
    
    Handles: headings, paragraphs, code blocks, lists, links, emphasis.
    """
    lines = []
    
    for child in element.children:
        if not hasattr(child, 'name') or child.name is None:
            # Text node
            text = str(child).strip()
            if text:
                lines.append(text)
            continue
        
        tag = child.name
        
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            text = child.get_text(strip=True)
            if text:
                lines.append(f"\n{'#' * level} {text}\n")
        
        elif tag == "p":
            text = child.get_text(strip=True)
            if text:
                lines.append(f"\n{text}\n")
        
        elif tag == "pre":
            code = child.get_text()
            # Try to detect language from class
            code_tag = child.find("code")
            lang = ""
            if code_tag:
                classes = code_tag.get("class", [])
                for cls in classes:
                    if cls.startswith("language-"):
                        lang = cls.replace("language-", "")
                        break
                code = code_tag.get_text()
            lines.append(f"\n```{lang}\n{code}\n```\n")
        
        elif tag == "code":
            text = child.get_text(strip=True)
            if text and "\n" not in text:
                lines.append(f"`{text}`")
            else:
                lines.append(f"\n```\n{text}\n```\n")
        
        elif tag in {"ul", "ol"}:
            for i, li in enumerate(child.find_all("li", recursive=False)):
                prefix = f"{i + 1}." if tag == "ol" else "-"
                text = li.get_text(strip=True)
                if text:
                    lines.append(f"{prefix} {text}")
            lines.append("")
        
        elif tag == "blockquote":
            text = child.get_text(strip=True)
            if text:
                lines.append(f"> {text}\n")
        
        elif tag in {"strong", "b"}:
            text = child.get_text(strip=True)
            if text:
                lines.append(f"**{text}**")
        
        elif tag in {"em", "i"}:
            text = child.get_text(strip=True)
            if text:
                lines.append(f"*{text}*")
        
        elif tag == "a":
            text = child.get_text(strip=True)
            href = child.get("href", "")
            if text and href:
                lines.append(f"[{text}]({href})")
            elif text:
                lines.append(text)
        
        elif tag == "img":
            alt = child.get("alt", "image")
            src = child.get("src", "")
            if src:
                lines.append(f"![{alt}]({src})")
        
        elif tag in {"div", "section", "span"}:
            # Recurse into container elements
            inner = _html_to_markdown(child)
            if inner.strip():
                lines.append(inner)
        
        elif tag == "br":
            lines.append("")
        
        elif tag == "hr":
            lines.append("\n---\n")
        
        elif tag == "table":
            # Simple table extraction
            text = child.get_text(separator=" | ", strip=True)
            if text:
                lines.append(f"\n{text}\n")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Text/Markdown Parsing
# ═══════════════════════════════════════════════════════════

def parse_markdown_to_sections(text: str, title: str = "Technical Content") -> list[Section]:
    """
    Parse markdown text into structured sections.
    
    Splits on headings (# H1, ## H2, etc.) and preserves hierarchy.
    Falls back to paragraph-based splitting if no headings found.
    """
    sections = []
    
    # Split by headings
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    matches = list(heading_pattern.finditer(text))
    
    if matches:
        # Add content before first heading as an intro section
        first_start = matches[0].start()
        if first_start > 0:
            intro_text = text[:first_start].strip()
            if intro_text and len(intro_text) > 50:
                sections.append(Section(
                    id=f"content-intro",
                    title="Introduction",
                    level=1,
                    content=intro_text,
                ))
        
        # Each heading starts a new section
        for i, match in enumerate(matches):
            level = len(match.group(1))
            heading = match.group(2).strip()
            
            # Content extends to next heading or end of text
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            
            if content and len(content) > 30:
                sections.append(Section(
                    id=f"content-{i + 1}",
                    title=heading,
                    level=level,
                    content=content,
                ))
    else:
        # No headings — split by paragraphs (group every ~500 chars)
        paragraphs = text.split("\n\n")
        current_content = []
        current_length = 0
        section_num = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            current_content.append(para)
            current_length += len(para)
            
            if current_length >= 500:
                section_num += 1
                sections.append(Section(
                    id=f"content-{section_num}",
                    title=f"Part {section_num}",
                    level=1,
                    content="\n\n".join(current_content),
                ))
                current_content = []
                current_length = 0
        
        # Last section
        if current_content:
            section_num += 1
            sections.append(Section(
                id=f"content-{section_num}",
                title=f"Part {section_num}" if section_num > 1 else title,
                level=1,
                content="\n\n".join(current_content),
            ))
    
    # Extract equations from content
    for section in sections:
        equations = _extract_equations(section.content)
        if equations:
            section = Section(
                id=section.id,
                title=section.title,
                level=section.level,
                content=section.content,
                summary=section.summary,
                equations=[Equation(latex=eq, context="", is_inline=False) for eq in equations],
                parent_id=section.parent_id,
            )
    
    # Filter short/empty sections
    sections = [s for s in sections if len(s.content) > 30]
    
    logger.info(f"Parsed {len(sections)} sections from markdown content")
    return sections


def _extract_equations(text: str) -> list[str]:
    """Extract LaTeX equations from text ($$...$$ and \\[...\\] blocks)."""
    equations = []
    
    # Display math: $$...$$
    for match in re.finditer(r'\$\$(.+?)\$\$', text, re.DOTALL):
        equations.append(match.group(1).strip())
    
    # Display math: \[...\]
    for match in re.finditer(r'\\\[(.+?)\\\]', text, re.DOTALL):
        equations.append(match.group(1).strip())
    
    return equations


# ═══════════════════════════════════════════════════════════
# Main Entry Points
# ═══════════════════════════════════════════════════════════

async def ingest_technical_content(
    url: Optional[str] = None,
    text: Optional[str] = None,
    title: Optional[str] = None,
) -> StructuredContent:
    """
    Main entry point: ingest technical content from URL or raw text.
    
    Args:
        url: URL of blog/docs/article to fetch and parse
        text: Raw markdown or text to parse directly
        title: Optional title (auto-detected from URL if not provided)
        
    Returns:
        StructuredContent ready for the visualization pipeline
        
    Raises:
        ValueError: If neither url nor text provided
    """
    if not url and not text:
        raise ValueError("Either 'url' or 'text' must be provided")
    
    author = None
    fetched_at = None
    source_type = "text"
    has_code_blocks = False
    has_equations = False
    
    if url:
        logger.info(f"Fetching technical content from: {url}")
        source_type = "url"
        fetched_title, content, author = await fetch_url_content(url)
        title = title or fetched_title or "Technical Content"
        text = content
        fetched_at = datetime.utcnow()
    
    # Parse into sections
    sections = parse_markdown_to_sections(text, title or "Technical Content")
    
    # Detect content features
    has_code_blocks = bool(re.search(r'```', text))
    has_equations = bool(re.search(r'\$\$.+?\$\$|\\\[.+?\\\]', text, re.DOTALL))
    word_count = len(text.split())
    
    # Generate content ID
    content_id = f"content:{hashlib.sha256((url or text[:200]).encode()).hexdigest()[:12]}"
    
    # Build metadata
    tech_meta = TechnicalContentMeta(
        source_url=url,
        title=title or "Technical Content",
        author=author,
        source_type=source_type,
        word_count=word_count,
        has_code_blocks=has_code_blocks,
        has_equations=has_equations,
        fetched_at=fetched_at,
    )
    
    content_meta = ContentMeta(
        content_type=ContentType.TECHNICAL_CONTENT,
        content_id=content_id,
        title=title or "Technical Content",
        description=text[:300] + "..." if len(text) > 300 else text,
        source_url=url,
        content_meta=tech_meta,
    )
    
    result = StructuredContent(
        meta=content_meta,
        sections=sections,
    )
    
    logger.info(
        f"Ingested technical content: '{title}' — "
        f"{len(sections)} sections, {word_count} words"
    )
    return result
