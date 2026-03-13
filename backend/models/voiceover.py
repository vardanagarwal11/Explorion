"""Voiceover validation models."""

from pydantic import BaseModel, Field


class VoiceoverValidationOutput(BaseModel):
    """Output from strict voiceover script validation."""

    is_valid: bool = Field(..., description="Whether narration quality checks passed")
    issues_found: list[str] = Field(default_factory=list, description="Voiceover quality issues")
    score_alignment: float = Field(..., ge=0.0, le=1.0, description="Narration-to-concept/scene alignment score")
    score_educational: float = Field(..., ge=0.0, le=1.0, description="Educational clarity score")
    needs_regeneration: bool = Field(False, description="If True, regenerate with voiceover feedback")

    def get_feedback_message(self) -> str:
        """Return compact feedback message for regeneration."""
        if self.is_valid:
            return ""

        lines = [
            "VOICEOVER QUALITY ISSUES DETECTED - Regenerate with better narration.",
            f"Alignment score: {self.score_alignment:.2f}",
            f"Educational score: {self.score_educational:.2f}",
        ]
        for issue in self.issues_found:
            lines.append(f"- {issue}")
        return "\n".join(lines)
