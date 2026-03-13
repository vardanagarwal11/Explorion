"""Spatial validation models for detecting positioning issues in Manim code."""

from pydantic import BaseModel, Field


class PositionInfo(BaseModel):
    """Extracted position information from code."""
    
    element_name: str = Field(..., description="Variable name of the element")
    line_number: int = Field(..., description="Line number in code")
    x_position: float | None = Field(None, description="Estimated X position")
    y_position: float | None = Field(None, description="Estimated Y position")
    position_method: str = Field(..., description="Method used (move_to, shift, next_to, etc.)")
    raw_code: str = Field(..., description="The positioning code")


class BoundsIssue(BaseModel):
    """An element that may be out of screen bounds."""
    
    element_name: str = Field(..., description="Variable name of the element")
    line_number: int = Field(..., description="Line number in code")
    issue: str = Field(..., description="Description of the bounds issue")
    suggested_fix: str = Field(..., description="How to fix the issue")


class OverlapIssue(BaseModel):
    """Two elements that may be overlapping."""
    
    element1: str = Field(..., description="First element name")
    element2: str = Field(..., description="Second element name")
    line1: int = Field(..., description="Line number of first element positioning")
    line2: int = Field(..., description="Line number of second element positioning")
    issue: str = Field(..., description="Description of the overlap")
    suggested_fix: str = Field(..., description="How to fix the overlap")


class SpacingIssue(BaseModel):
    """A positioning call missing proper spacing."""
    
    line_number: int = Field(..., description="Line number in code")
    issue: str = Field(..., description="Description of the spacing issue")
    suggested_fix: str = Field(..., description="How to fix the spacing")


class SpatialValidatorOutput(BaseModel):
    """Output from the Spatial Validator."""
    
    has_spatial_issues: bool = Field(..., description="Whether any spatial issues were found")
    out_of_bounds: list[BoundsIssue] = Field(default_factory=list, description="Elements possibly off-screen")
    potential_overlaps: list[OverlapIssue] = Field(default_factory=list, description="Elements that may overlap")
    spacing_issues: list[SpacingIssue] = Field(default_factory=list, description="Missing buff/spacing parameters")
    suggestions: list[str] = Field(default_factory=list, description="General improvement suggestions")
    needs_regeneration: bool = Field(False, description="If True, code should be regenerated with spatial feedback")
    
    def get_feedback_message(self) -> str:
        """Generate a feedback message for the generator to fix issues."""
        if not self.has_spatial_issues:
            return ""
        
        lines = ["SPATIAL ISSUES DETECTED - Please fix the following:"]
        
        if self.out_of_bounds:
            lines.append("\n## Out of Bounds Issues:")
            for issue in self.out_of_bounds:
                lines.append(f"- Line {issue.line_number}: {issue.issue}")
                lines.append(f"  Fix: {issue.suggested_fix}")
        
        if self.potential_overlaps:
            lines.append("\n## Overlap Issues:")
            for issue in self.potential_overlaps:
                lines.append(f"- Lines {issue.line1}/{issue.line2}: {issue.issue}")
                lines.append(f"  Fix: {issue.suggested_fix}")
        
        if self.spacing_issues:
            lines.append("\n## Spacing Issues:")
            for issue in self.spacing_issues:
                lines.append(f"- Line {issue.line_number}: {issue.issue}")
                lines.append(f"  Fix: {issue.suggested_fix}")
        
        lines.append("\n## General Spatial Best Practices:")
        lines.append("- Use buff parameter with next_to(): element.next_to(other, DOWN, buff=0.5)")
        lines.append("- Use arrange() for groups: VGroup(a, b, c).arrange(DOWN, buff=0.3)")
        lines.append("- Stay within safe area: x in [-6, 6], y in [-3.5, 3.5]")
        lines.append("- Clear scene before new content: self.play(FadeOut(*self.mobjects))")
        
        return "\n".join(lines)
