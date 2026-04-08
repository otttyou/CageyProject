"""Plotly-based interactive HTML charts for Cagey analysis results."""

from __future__ import annotations

from pathlib import Path

from cagey.analysis.models import AnalysisResult, SubAuditionCategory
from cagey.pipeline.sorter import AuthorStats

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False


def generate_charts(
    results: list[AnalysisResult],
    author_stats: dict[str, AuthorStats],
    output_dir: Path,
    open_browser: bool = False,
) -> list[Path]:
    """Generate all four charts and save them as HTML files.

    Returns the list of paths written.
    """
    if not _HAS_PLOTLY:
        raise ImportError(
            "plotly is required for chart generation. "
            "Install it with: pip install plotly"
        )

    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    paths.append(_sentiment_timeline(results, charts_dir, open_browser))
    paths.append(_subaudition_heatmap(results, author_stats, charts_dir, open_browser))
    paths.append(_sentiment_distribution(author_stats, charts_dir, open_browser))
    paths.append(_confidence_scatter(results, charts_dir, open_browser))
    return paths


# ─────────────────────────────────────────────────────────────────
# Chart 1 — Sentiment Timeline
# ─────────────────────────────────────────────────────────────────

def _sentiment_timeline(
    results: list[AnalysisResult],
    out: Path,
    open_browser: bool,
) -> Path:
    import plotly.graph_objects as go  # noqa: PLC0415

    authors = sorted({r.message.author for r in results})
    colours = _author_colours(authors)

    fig = go.Figure()
    for author in authors:
        msgs = sorted(
            [r for r in results if r.message.author == author],
            key=lambda r: r.message.timestamp,
        )
        fig.add_trace(
            go.Scatter(
                x=[r.message.timestamp for r in msgs],
                y=[r.sentiment.score for r in msgs],
                mode="lines+markers",
                name=author,
                line={"color": colours[author]},
                marker={"size": 6},
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Score: %{y:.2f}<br>"
                    "Tone: %{customdata[1]}<br>"
                    "<i>%{customdata[2]}</i><extra></extra>"
                ),
                customdata=[
                    [r.message.author, r.sentiment.emotional_tone, r.message.content[:80]]
                    for r in msgs
                ],
            )
        )

    fig.update_layout(
        title="Sentiment Timeline by Author",
        xaxis_title="Time",
        yaxis_title="Sentiment Score",
        yaxis={"range": [-1.1, 1.1]},
        template="plotly_dark",
        legend_title="Author",
    )
    fig.add_hline(y=0, line_dash="dot", line_color="grey", opacity=0.5)

    path = out / "sentiment_timeline.html"
    fig.write_html(str(path), auto_open=open_browser)
    return path


# ─────────────────────────────────────────────────────────────────
# Chart 2 — Sub-Audition Heatmap
# ─────────────────────────────────────────────────────────────────

def _subaudition_heatmap(
    results: list[AnalysisResult],
    author_stats: dict[str, AuthorStats],
    out: Path,
    open_browser: bool,
) -> Path:
    import plotly.graph_objects as go  # noqa: PLC0415

    authors = sorted(author_stats.keys())
    categories = [c for c in SubAuditionCategory if c != SubAuditionCategory.NONE]
    cat_labels = [c.display_name for c in categories]

    # Build count matrix [author × category]
    z = []
    for author in authors:
        row = []
        counts = author_stats[author].sub_audition_counts
        for cat in categories:
            row.append(counts.get(cat.value, 0))
        z.append(row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=cat_labels,
            y=authors,
            colorscale="Reds",
            hovertemplate="<b>%{y}</b> → %{x}: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Sub-Audition Frequency (Author × Category)",
        xaxis_title="Sub-Audition Category",
        yaxis_title="Author",
        template="plotly_dark",
    )

    path = out / "subaudition_heatmap.html"
    fig.write_html(str(path), auto_open=open_browser)
    return path


# ─────────────────────────────────────────────────────────────────
# Chart 3 — Sentiment Distribution Stacked Bar
# ─────────────────────────────────────────────────────────────────

def _sentiment_distribution(
    author_stats: dict[str, AuthorStats],
    out: Path,
    open_browser: bool,
) -> Path:
    import plotly.graph_objects as go  # noqa: PLC0415

    authors = sorted(author_stats.keys())
    labels = ["positive", "negative", "neutral", "mixed"]
    colours_map = {
        "positive": "#2ecc71",
        "negative": "#e74c3c",
        "neutral": "#95a5a6",
        "mixed": "#f39c12",
    }

    fig = go.Figure()
    for label in labels:
        y_vals = []
        for author in authors:
            dist = author_stats[author].sentiment_distribution
            total = author_stats[author].message_count or 1
            y_vals.append(dist.get(label, 0) / total * 100)

        fig.add_trace(
            go.Bar(
                name=label.capitalize(),
                x=authors,
                y=y_vals,
                marker_color=colours_map[label],
                hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        title="Sentiment Distribution by Author (normalised %)",
        xaxis_title="Author",
        yaxis_title="Percentage of messages",
        template="plotly_dark",
        legend_title="Sentiment",
    )

    path = out / "sentiment_distribution.html"
    fig.write_html(str(path), auto_open=open_browser)
    return path


# ─────────────────────────────────────────────────────────────────
# Chart 4 — Sub-Audition Confidence Scatter
# ─────────────────────────────────────────────────────────────────

def _confidence_scatter(
    results: list[AnalysisResult],
    out: Path,
    open_browser: bool,
) -> Path:
    import plotly.graph_objects as go  # noqa: PLC0415

    categories = [c for c in SubAuditionCategory if c != SubAuditionCategory.NONE]
    cat_colours = _category_colours(categories)

    fig = go.Figure()
    for cat in categories:
        cat_results = [
            r for r in results
            if r.primary_sub_audition and r.primary_sub_audition.category == cat
        ]
        if not cat_results:
            continue

        fig.add_trace(
            go.Scatter(
                x=[r.sentiment.score for r in cat_results],
                y=[r.primary_sub_audition.confidence for r in cat_results],  # type: ignore[union-attr]
                mode="markers",
                name=cat.display_name,
                marker={"color": cat_colours[cat], "size": 8, "opacity": 0.8},
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Score: %{x:.2f} | Confidence: %{y:.0%}<br>"
                    "<i>%{customdata[1]}</i><extra></extra>"
                ),
                customdata=[
                    [
                        r.message.author,
                        r.message.content[:60],
                    ]
                    for r in cat_results
                ],
            )
        )

    fig.update_layout(
        title="Sub-Audition Confidence vs Sentiment Score",
        xaxis_title="Sentiment Score",
        yaxis_title="Sub-Audition Confidence",
        xaxis={"range": [-1.1, 1.1]},
        yaxis={"range": [-0.05, 1.05]},
        template="plotly_dark",
        legend_title="Category",
    )
    fig.add_vline(x=0, line_dash="dot", line_color="grey", opacity=0.4)

    path = out / "confidence_scatter.html"
    fig.write_html(str(path), auto_open=open_browser)
    return path


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

_PALETTE = [
    "#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
]


def _author_colours(authors: list[str]) -> dict[str, str]:
    return {a: _PALETTE[i % len(_PALETTE)] for i, a in enumerate(authors)}


def _category_colours(cats) -> dict:
    return {c: _PALETTE[i % len(_PALETTE)] for i, c in enumerate(cats)}
