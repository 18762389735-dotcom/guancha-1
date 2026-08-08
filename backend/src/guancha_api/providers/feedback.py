from __future__ import annotations

from typing import Protocol

from guancha_api.schemas.contracts import BrewFeedbackAnalysisRequest, BrewFeedbackAnalysisResponse


class FeedbackReasoningProvider(Protocol):
    async def explain_brew_feedback(self, request: BrewFeedbackAnalysisRequest) -> BrewFeedbackAnalysisResponse: ...


class FakeFeedbackProvider:
    """Offline boundary: it interprets feedback only; deterministic rules enforce safety."""
    async def explain_brew_feedback(self, request: BrewFeedbackAnalysisRequest) -> BrewFeedbackAnalysisResponse:
        from guancha_api.application.brew_feedback_service import analyze_feedback
        return analyze_feedback(request)
