# scripts/scrape_manim_docs.py
# Uses _modules/ source pages — plain HTML, no JS, contains full
# docstrings + code examples for every class in the module.
#
# Run once: python scripts/scrape_manim_docs.py
# Output:   assets/manim_reference.txt

import re, time, pathlib, httpx

OUTPUT_PATH = pathlib.Path("assets/manim_reference.txt")
OUTPUT_PATH.parent.mkdir(exist_ok=True)

# These are the SOURCE pages — static HTML, no JS needed.
# Each page = one full module with all classes, signatures, and examples.
PAGES = [
    "https://docs.manim.community/en/stable/_modules/manim/animation/transform.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/fading.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/creation.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/movement.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/indication.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/growing.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/composition.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/rotation.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/line.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/polygram.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/text/text_mobject.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/text/tex_mobject.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/types/vectorized_mobject.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/three_d/three_dimensions.html",
    "https://docs.manim.community/en/stable/_modules/manim/scene/scene.html",
    "https://docs.manim.community/en/stable/_modules/manim/scene/three_d_scene.html",
    "https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/probability.html",
    "https://docs.manim.community/en/stable/_modules/manim/utils/value_tracker.html",
    "https://docs.manim.community/en/stable/_modules/manim/animation/transform_matching_parts.html",
    "https://docs.manim.community/en/stable/_modules/manim/scene/moving_camera_scene.html",
]

def extract_source(html: str) -> str:
    """
    These pages wrap source code in <div class="highlight-default notranslate">
    or <div role="main"> — extract just that block to get clean Python source
    with docstrings and examples, stripped of all nav chrome.
    """
    # Try to grab just the source code block
    match = re.search(
        r'<div[^>]*class="[^"]*highlight[^"]*"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    if not match:
        # Fallback: grab the main content area
        match = re.search(
            r'<div[^>]*role="main"[^>]*>(.*?)</div>\s*</div>',
            html, re.DOTALL
        )
    raw = match.group(1) if match else html

    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', '', raw)
    # Decode common HTML entities
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')
    # Collapse whitespace while preserving newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()

def scrape_page(url: str, client: httpx.Client) -> str:
    try:
        r = client.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        text = extract_source(r.text)
        module_name = url.split('/_modules/')[-1].replace('.html', '').replace('/', '.')
        # Cap at 12000 chars per module — source pages are denser/cleaner
        return f"\n\n{'='*60}\nMODULE: {module_name}\n{'='*60}\n{text[:12000]}"
    except Exception as e:
        print(f"  SKIP {url.split('/')[-1]}: {e}")
        return ""

def main():
    print(f"Scraping {len(PAGES)} Manim source pages...")
    chunks = []
    with httpx.Client(headers={"User-Agent": "Mozilla/5.0"}) as client:
        for i, url in enumerate(PAGES):
            name = url.split('/_modules/')[-1].replace('.html', '')
            print(f"  [{i+1}/{len(PAGES)}] {name}")
            chunk = scrape_page(url, client)
            if chunk:
                chunks.append(chunk)
            time.sleep(0.4)

    output = "\n".join(chunks)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    kb = OUTPUT_PATH.stat().st_size // 1024
    print(f"\nDone. {len(chunks)}/{len(PAGES)} pages → {OUTPUT_PATH} ({kb} KB)")
    print("\nSpot-check: open the file and search for 'class Transform' —")
    print("you should see the full Python source with docstrings and Examples blocks.")

if __name__ == "__main__":
    main()