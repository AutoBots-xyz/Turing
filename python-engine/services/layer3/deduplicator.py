import asyncio
from typing import List

from schemas.layer3 import SearchResult, MergedResult, SearchSource

# ---------------------------------------------------------------------------
# Configurable confidence boost per corroborating source type.
# Reflects the epistemic value of evidence from each domain — a patent +
# paper is worth more than 2 web results.
# ---------------------------------------------------------------------------
EVIDENCE_BOOST_MAP = {
    SearchSource.PATENT:    5.0,   # Deployed engineering solution → highest boost
    SearchSource.PAPER:     4.0,   # Peer-reviewed proof → very high boost
    SearchSource.WIKIPEDIA: 2.5,   # Community-validated knowledge → medium boost
    SearchSource.WEB:       1.0,   # Whitepapers / blogs → low boost
}

# ---------------------------------------------------------------------------
# Common English stopwords stripped before Jaccard similarity.
# Without this, words like "the", "of", "is" inflate similarity between
# completely unrelated summaries and cause over-merging (L3-4 fix).
# ---------------------------------------------------------------------------
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "used",
    "of", "in", "to", "for", "on", "at", "by", "with", "from", "as",
    "and", "or", "but", "not", "this", "that", "it", "its", "they",
    "their", "which", "who", "when", "where", "how", "what", "all",
    "also", "so", "into", "than", "then", "there", "these", "those",
    "such", "both", "each", "more", "other", "no", "nor", "up", "out",
})


def _meaningful_words(text: str) -> frozenset:
    """
    Tokenises text and strips stopwords so only domain-meaningful words
    contribute to the Jaccard similarity score.
    """
    return frozenset(
        w for w in text.lower().split()
        if w.isalpha() and w not in _STOPWORDS
    )


def _compute_similarity(a: SearchResult, b: SearchResult) -> float:
    """
    Calculates stopword-filtered Jaccard similarity between two result summaries.

    Fixes L3-4 (part 2): Raw word overlap without stopword removal inflates
    Jaccard to 0.25+ for completely unrelated summaries due to common English
    words. Filtering stopwords first ensures only meaningful domain words count.

    Returns a score between 0.0 and 1.0.
    """
    words_a = _meaningful_words(a.summary)
    words_b = _meaningful_words(b.summary)

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


async def deduplicate_and_merge(
    results: List[SearchResult],
    similarity_threshold: float = 0.50,
) -> List[MergedResult]:
    """
    Real semantic deduplication using stopword-filtered Jaccard similarity.

    Groups results that describe the same underlying mechanism (similarity ≥ threshold)
    into a single MergedResult. Different mechanisms remain separate MergedResult objects.

    Fixes L3-4 (threshold): Default was 0.25 — far too low. Common English words
    caused unrelated results to be merged. New default is 0.50 (meaningful word
    overlap), which matches the intent of the original 0.85 cosine similarity
    spec from Error.md (Jaccard ≈ cosine/1.5 for typical text).

    Fixes L3-4 (stopwords): Now strips stopwords before computing similarity so
    only domain-meaningful words count toward the Jaccard score.

    Fixes L3-2 error (was Error 2): Confidence boost is a weighted sum of evidence
    source types, not a flat arbitrary multiplier.
    """
    if not results:
        return []

    # --- Step 1: Cluster by stopword-filtered Jaccard similarity ---
    visited = [False] * len(results)
    groups: List[List[SearchResult]] = []

    for i, result_i in enumerate(results):
        if visited[i]:
            continue
        group = [result_i]
        visited[i] = True
        for j, result_j in enumerate(results):
            if visited[j]:
                continue
            similarity = _compute_similarity(result_i, result_j)
            if similarity >= similarity_threshold:
                group.append(result_j)
                visited[j] = True
        groups.append(group)

    # --- Step 2: Build a MergedResult for each cluster ---
    merged_results = []
    for group in groups:
        sources = list({r.source for r in group})
        base_confidence = max(r.confidence for r in group)

        # Configurable evidence boost based on source type epistemic value
        boost = sum(EVIDENCE_BOOST_MAP.get(s, 0.5) for s in sources)
        final_confidence = min(100.0, base_confidence + boost)

        # Use the highest-confidence result as primary
        primary = max(group, key=lambda r: r.confidence)

        # Richer merged summary — lists all contributing summaries
        merged_summary = primary.summary
        if len(group) > 1:
            other_summaries = [r.summary for r in group if r is not primary]
            merged_summary += " [Corroborated by: " + " | ".join(other_summaries) + "]"

        merged = MergedResult(
            title=primary.title,
            merged_summary=merged_summary,
            underlying_mechanism=primary.original_query.structural_description,
            sources=sources,
            source_results=group,
            confidence=final_confidence,
        )
        merged_results.append(merged)

    return merged_results
