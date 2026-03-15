from models.paper import Section

def group_sections_heuristically(sections: list[Section], max_sections: int = 6) -> list[Section]:
    """
    Intelligently groups a list of sections into a maximum of `max_sections` sections.
    Combines adjacent sections to maintain a balanced content length while respecting the maximum limit.
    """
    if not sections:
        return []
        
    if len(sections) <= max_sections:
        return sections
        
    # Calculate average target length per section based on total words + chars
    total_len = sum(len(s.content or "") + len(s.title or "") for s in sections)
    target_len = total_len / max_sections
    
    grouped_sections = []
    current_chunk = []
    current_len = 0
    
    for s in sections:
        s_len = len(s.content or "") + len(s.title or "")
        
        # If adding this section pushes us over the target length significantly, and we aren't empty
        if current_chunk and current_len + (s_len / 2) >= target_len and len(grouped_sections) < max_sections - 1:
            grouped_sections.append(_merge_sections_chunk(current_chunk, len(grouped_sections) + 1))
            current_chunk = [s]
            current_len = s_len
        else:
            current_chunk.append(s)
            current_len += s_len
            
    if current_chunk:
        # If we have reached exactly max_sections - 1, and we have a remainder, lump it together.
        grouped_sections.append(_merge_sections_chunk(current_chunk, len(grouped_sections) + 1))
        
    return grouped_sections

def _merge_sections_chunk(chunk: list[Section], index: int) -> Section:
    if len(chunk) == 1:
        return chunk[0]
        
    titles = [s.title.strip("*_ ") for s in chunk if s.title]
    combined_title = titles[0][:50]
    if len(chunk) > 1:
        combined_title += f" (Contains {len(chunk)} subsections)"
        
    combined_content = ""
    for s in chunk:
        combined_content += f"### {s.title}\n\n{s.content or ''}\n\n"
        
    combined_summary = "\n\n".join(s.summary for s in chunk if getattr(s, "summary", None))
        
    equations = []
    figures = []
    tables = []
    code_blocks = []
    
    for s in chunk:
        equations.extend(getattr(s, "equations", []) or [])
        figures.extend(getattr(s, "figures", []) or [])
        tables.extend(getattr(s, "tables", []) or [])
        code_blocks.extend(getattr(s, "code_blocks", []) or [])
        
    import uuid
    unique_suffix = uuid.uuid4().hex[:6]
    return Section(
        id=f"grouped-section-{index}-{unique_suffix}",
        title=combined_title,
        content=combined_content.strip(),
        summary=combined_summary if combined_summary else combined_content.strip(),
        equations=equations,
        figures=figures,
        tables=tables,
        code_blocks=code_blocks,
        level=1,
    )
