# ./valueagents/evidence/extractors/__init__.py
"""Evidence Extractors — Phase 2 W1.6

4 个 analyst 各 1 个提取器：
  - market        (framework="technical")
  - social        (framework="sentiment")
  - news          (framework="news")
  - fundamentals  (framework="fundamental")
"""

from .market import extract_market_evidence
from .social import extract_social_evidence
from .news import extract_news_evidence
from .fundamentals import extract_fundamentals_evidence

__all__ = [
    "extract_market_evidence",
    "extract_social_evidence",
    "extract_news_evidence",
    "extract_fundamentals_evidence",
]