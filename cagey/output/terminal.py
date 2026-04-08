"""Rich-based terminal rendering for Cagey analysis results."""

from __future__ import annotations

from collections import Counter

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cagey.analysis.models import AnalysisResult, SubAuditionCategory
from cagey.analysis.client import UsageSummary
from cagey.pipeline.sorter import AuthorStats, SortKey

console = Console()

# Colour map: sentiment label → rich colour
_SENTIMENT_COLOUR = {
    "positive": "green",
    "negative": "red",
    "mixed": "yellow",
    "neutral": "white",
}

# Sub-audition categories → short emoji tag for compact display
_SA_TAG = {
    SubAuditionCategory.POWER_PLAY: "[bold red]⚡[/]",
    SubAuditionCategory.PASSIVE_AGGRESSION: "[bold yellow]😤[/]",
    SubAuditionCategory.DEFLECTION: "[bold cyan]↩[/]",
    SubAuditionCategory.ALLIANCE_SEEKING: "[bold blue]🤝[/]",
    SubAuditionCategory.URGENCY_SIGNALING: "[bold magenta]⏰[/]",
    SubAuditionCategory.APPROVAL_SEEKING: "[bold green]👍[/]",
    SubAuditionCategory.THREAT_IMPLICIT: "[bold red]⚠[/]",
    SubAuditionCategory.SARCASM: "[bold yellow]😏[/]",
    SubAuditionCategory.DISMISSAL: "[bold grey50]🚫[/]",
    SubAuditionCategory.NONE: "[grey50]—[/]",
}


def _score_bar(score: float, width: int = 10) -> str:
    """Render a unicode block bar for a sentiment score in [-1, 1]."""
    normalised = (score + 1.0) / 2.0  # 0..1
    filled = round(normalised * width)
    colour = "green" if score >= 0.1 else "red" if score <= -0.1 else "white"
    bar = "█" * filled + "░" * (width - filled)
    return f"[{colour}]{bar}[/]"


def render_results_table(
    results: list[AnalysisResult],
    sort_key: SortKey = SortKey.SENTIMENT_SCORE,
    title: str = "Cagey — Analysis Results",
) -> Table:
    """Build a rich Table with one row per message."""
    table = Table(
        title=title,
        show_lines=True,
        expand=True,
        header_style="bold cyan",
    )
    table.add_column("Author", style="bold", min_width=10, max_width=18)
    table.add_column("Time", min_width=16, max_width=19)
    table.add_column("Sentiment", min_width=9)
    table.add_column("Score", justify="right", min_width=6)
    table.add_column("Sub-Audition", min_width=16)
    table.add_column("Conf", justify="right", min_width=5)
    table.add_column("Trigger phrase", min_width=18, max_width=32)
    table.add_column("Summary", min_width=24)

    for r in results:
        sent_colour = _SENTIMENT_COLOUR.get(r.sentiment.label, "white")
        sentiment_cell = Text(r.sentiment.label.upper(), style=f"bold {sent_colour}")
        score_cell = f"{r.sentiment.score:+.2f}"
        ts = r.message.timestamp.strftime("%Y-%m-%d %H:%M")

        primary = r.primary_sub_audition
        if primary:
            sa_tag = _SA_TAG.get(primary.category, "")
            sa_cell = f"{sa_tag} {primary.category.display_name}"
            conf_cell = f"{primary.confidence:.0%}"
            trigger = f'"{primary.quoted_trigger[:28]}"' if primary.quoted_trigger else "—"
        else:
            sa_cell = "[grey50]none[/]"
            conf_cell = "—"
            trigger = "—"

        # Dim the row if analysis failed
        row_style = "dim" if r.error else ""

        table.add_row(
            r.message.author,
            ts,
            sentiment_cell,
            score_cell,
            sa_cell,
            conf_cell,
            trigger,
            r.summary or "—",
            style=row_style,
        )

    return table


def render_author_panels(
    author_stats: dict[str, AuthorStats],
    max_authors: int = 10,
) -> list[Panel]:
    """Return one rich Panel per author with their stats summary."""
    panels = []
    for author, s in list(author_stats.items())[:max_authors]:
        bar = _score_bar(s.avg_sentiment)
        top_sas = s.sub_audition_counts.most_common(3)

        lines = [
            f"[bold]Messages:[/] {s.message_count}",
            f"[bold]Avg sentiment:[/] {bar} {s.avg_sentiment:+.2f}",
            "",
            "[bold]Sentiment distribution:[/]",
        ]
        for label, count in sorted(s.sentiment_distribution.items()):
            pct = count / s.message_count * 100 if s.message_count else 0
            colour = _SENTIMENT_COLOUR.get(label, "white")
            lines.append(f"  [{colour}]{label.upper()}[/] {count} ({pct:.0f}%)")

        if top_sas:
            lines += ["", "[bold]Top sub-auditions:[/]"]
            for cat_val, cnt in top_sas:
                cat = SubAuditionCategory(cat_val)
                tag = _SA_TAG.get(cat, "")
                lines.append(f"  {tag} {cat.display_name}: {cnt}")

        panel = Panel(
            "\n".join(lines),
            title=f"[bold cyan]{author}[/]",
            expand=False,
            border_style="cyan",
        )
        panels.append(panel)
    return panels


def render_summary_dashboard(
    results: list[AnalysisResult],
    author_stats: dict[str, AuthorStats],
    usage: UsageSummary | None = None,
    model: str = "",
) -> None:
    """Print an overview dashboard to the console."""
    total = len(results)
    failed = sum(1 for r in results if r.error)
    avg_score = sum(r.sentiment.score for r in results) / total if total else 0.0

    # Top sub-auditions across all messages
    all_sa: Counter = Counter()
    for r in results:
        if r.primary_sub_audition:
            all_sa[r.primary_sub_audition.category.display_name] += 1

    # Build overview panel
    overview_lines = [
        f"[bold]Total messages:[/] {total}",
        f"[bold]Failed:[/] {failed}",
        f"[bold]Avg sentiment:[/] {_score_bar(avg_score)} {avg_score:+.2f}",
        f"[bold]Authors:[/] {len(author_stats)}",
    ]
    if model:
        overview_lines.append(f"[bold]Model:[/] {model}")
    if usage:
        overview_lines.append(f"[bold]Tokens used:[/] {usage.total_tokens:,}")
        overview_lines.append(f"[bold]API calls:[/] {usage.calls:,}")

    if all_sa:
        overview_lines += ["", "[bold]Top sub-auditions (all):[/]"]
        for name, cnt in all_sa.most_common(5):
            overview_lines.append(f"  {name}: {cnt}")

    overview_panel = Panel(
        "\n".join(overview_lines),
        title="[bold]Overview[/]",
        border_style="blue",
        expand=False,
    )

    # Per-author sentiment bar chart (unicode)
    author_lines = ["[bold]Author[/]".ljust(20) + "  [bold]Avg Sentiment[/]"]
    for author, s in sorted(author_stats.items(), key=lambda kv: kv[1].avg_sentiment):
        bar = _score_bar(s.avg_sentiment, width=14)
        name = author[:18].ljust(18)
        author_lines.append(f"{name}  {bar} {s.avg_sentiment:+.2f}")

    author_panel = Panel(
        "\n".join(author_lines),
        title="[bold]Per-Author Sentiment[/]",
        border_style="magenta",
        expand=False,
    )

    console.print()
    console.print(Columns([overview_panel, author_panel], equal=False, expand=False))
    console.print()
