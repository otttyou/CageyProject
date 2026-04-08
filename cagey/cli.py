"""Cagey CLI — three commands: analyze, report, validate."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="cagey",
    help=(
        "Cagey — analyze workplace chat communications for sentiment and "
        "sub-auditions using Claude."
    ),
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)


# ─────────────────────────────────────────────────────────────────────────────
# cagey analyze
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def analyze(
    input_file: Path = typer.Argument(..., help="Chat export file (JSON, CSV, or TXT)."),
    format: str = typer.Option("auto", "--format", "-f", help="Input format: auto|json|csv|txt."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model to use."),
    sort_by: str = typer.Option(
        "sentiment", "--sort-by", "-s",
        help="Sort key: author|sentiment|time|subaudition|confidence.",
    ),
    ascending: bool = typer.Option(False, "--ascending/--descending", help="Sort order."),
    filter_author: Optional[str] = typer.Option(
        None, "--filter-author", help="Only show messages from this author (substring match)."
    ),
    filter_category: Optional[str] = typer.Option(
        None, "--filter-category",
        help="Only show messages with this sub-audition category.",
    ),
    min_confidence: float = typer.Option(
        0.0, "--min-confidence", help="Hide sub-auditions below this confidence threshold."
    ),
    charts: bool = typer.Option(False, "--charts/--no-charts", help="Generate HTML charts."),
    save_json: bool = typer.Option(
        False, "--save-json/--no-save-json", help="Save full results as JSON report."
    ),
    output_dir: Path = typer.Option(
        Path("./cagey_output"), "--output-dir", "-o", help="Where to save output files."
    ),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Concurrent API calls."),
) -> None:
    """Analyze a chat export file and display sorted results."""
    from cagey.analysis.models import AnalysisResult
    from cagey.config import load_settings
    from cagey.output.terminal import render_author_panels, render_results_table, render_summary_dashboard
    from cagey.pipeline.runner import PipelineRunner
    from cagey.pipeline.sorter import SortKey, Sorter

    settings = _load_settings_or_exit()
    runner = PipelineRunner(settings, model=model)

    console.rule("[bold cyan]Cagey — Analyzing[/]")
    console.print(f"  File:  [bold]{input_file}[/]")
    console.print(f"  Model: [bold]{runner.client.model}[/]")
    console.print()

    try:
        results = runner.run_with_progress(input_file, format=format, concurrency=concurrency)
    except FileNotFoundError as exc:
        err_console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1)
    except Exception as exc:
        err_console.print(f"[red]Analysis failed:[/] {exc}")
        raise typer.Exit(1)

    # Sort + filter
    sort_key = _parse_sort_key(sort_by)
    sorter = Sorter()
    sorted_results = sorter.sort(
        results,
        primary=sort_key,
        ascending=ascending,
        filter_author=filter_author,
        filter_category=filter_category,
        min_confidence=min_confidence,
    )
    author_stats = sorter.aggregate_by_author(results)

    # Render table
    table = render_results_table(sorted_results, sort_key=sort_key)
    console.print(table)

    # Per-author panels
    panels = render_author_panels(author_stats)
    for panel in panels:
        console.print(panel)

    # Summary dashboard
    render_summary_dashboard(results, author_stats, usage=runner.usage, model=runner.client.model)

    # Save JSON report
    if save_json:
        report_path = PipelineRunner.save_report(results, output_dir)
        console.print(f"[green]Report saved:[/] {report_path}")

    # Generate charts
    if charts:
        _generate_charts_or_warn(results, author_stats, output_dir, open_browser=True)


# ─────────────────────────────────────────────────────────────────────────────
# cagey report
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def report(
    report_file: Path = typer.Argument(..., help="Path to a previously saved JSON report."),
    sort_by: str = typer.Option("sentiment", "--sort-by", "-s", help="Sort key."),
    ascending: bool = typer.Option(False, "--ascending/--descending"),
    filter_author: Optional[str] = typer.Option(None, "--filter-author"),
    filter_category: Optional[str] = typer.Option(None, "--filter-category"),
    min_confidence: float = typer.Option(0.0, "--min-confidence"),
    charts: bool = typer.Option(False, "--charts/--no-charts"),
    output_dir: Path = typer.Option(Path("./cagey_output"), "--output-dir", "-o"),
) -> None:
    """Re-render a saved JSON report (no API calls)."""
    from cagey.output.terminal import render_author_panels, render_results_table, render_summary_dashboard
    from cagey.pipeline.runner import PipelineRunner
    from cagey.pipeline.sorter import SortKey, Sorter

    if not report_file.exists():
        err_console.print(f"[red]Report file not found:[/] {report_file}")
        raise typer.Exit(1)

    try:
        results = PipelineRunner.load_report(report_file)
    except Exception as exc:
        err_console.print(f"[red]Failed to load report:[/] {exc}")
        raise typer.Exit(1)

    sort_key = _parse_sort_key(sort_by)
    sorter = Sorter()
    sorted_results = sorter.sort(
        results,
        primary=sort_key,
        ascending=ascending,
        filter_author=filter_author,
        filter_category=filter_category,
        min_confidence=min_confidence,
    )
    author_stats = sorter.aggregate_by_author(results)

    console.rule("[bold cyan]Cagey — Saved Report[/]")
    table = render_results_table(sorted_results, sort_key=sort_key)
    console.print(table)

    panels = render_author_panels(author_stats)
    for panel in panels:
        console.print(panel)

    render_summary_dashboard(results, author_stats)

    if charts:
        _generate_charts_or_warn(results, author_stats, output_dir, open_browser=True)


# ─────────────────────────────────────────────────────────────────────────────
# cagey validate
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def validate(
    input_file: Path = typer.Argument(..., help="Chat export file to validate."),
    format: str = typer.Option("auto", "--format", "-f", help="Input format: auto|json|csv|txt."),
    preview: int = typer.Option(10, "--preview", "-n", help="Number of messages to preview."),
) -> None:
    """Parse a chat file and preview messages — no API calls made."""
    from cagey.ingest.base import ParseError
    from cagey.pipeline.runner import PipelineRunner

    try:
        messages = PipelineRunner.validate_only(input_file, format=format)
    except FileNotFoundError as exc:
        err_console.print(f"[red]File not found:[/] {exc}")
        raise typer.Exit(1)
    except ParseError as exc:
        err_console.print(f"[red]Parse error:[/] {exc}")
        raise typer.Exit(1)

    console.rule("[bold cyan]Cagey — Validate[/]")
    console.print(f"[green]✓[/] Parsed [bold]{len(messages)}[/] messages from [bold]{input_file}[/]")
    console.print()

    table = Table(show_lines=True, header_style="bold cyan", expand=True)
    table.add_column("#", justify="right", min_width=3)
    table.add_column("Author", min_width=10, max_width=18)
    table.add_column("Timestamp", min_width=18)
    table.add_column("Channel")
    table.add_column("Content", min_width=30)

    for i, msg in enumerate(messages[:preview], 1):
        table.add_row(
            str(i),
            msg.author,
            msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            msg.channel or "—",
            msg.content[:80] + ("…" if len(msg.content) > 80 else ""),
        )

    console.print(table)
    if len(messages) > preview:
        console.print(f"[dim]… and {len(messages) - preview} more messages.[/]")

    console.print()
    console.print(
        f"[bold green]Ready.[/] Run [cyan]cagey analyze {input_file}[/] to start analysis."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_settings_or_exit():
    from cagey.config import load_settings

    try:
        return load_settings()
    except Exception as exc:
        err_console.print(
            f"[red]Configuration error:[/] {exc}\n"
            "Make sure ANTHROPIC_API_KEY is set (copy .env.example → .env and fill it in)."
        )
        raise typer.Exit(1)


def _parse_sort_key(sort_by: str):
    from cagey.pipeline.sorter import SortKey

    mapping = {
        "author": SortKey.AUTHOR,
        "sentiment": SortKey.SENTIMENT_SCORE,
        "time": SortKey.TIMESTAMP,
        "subaudition": SortKey.SUB_AUDITION,
        "confidence": SortKey.CONFIDENCE,
    }
    key = mapping.get(sort_by.lower())
    if key is None:
        err_console.print(
            f"[yellow]Unknown sort key:[/] {sort_by!r}. "
            f"Valid options: {', '.join(mapping)}. Defaulting to 'sentiment'."
        )
        return mapping["sentiment"]
    return key


def _generate_charts_or_warn(results, author_stats, output_dir, open_browser):
    from cagey.output.charts import generate_charts

    try:
        paths = generate_charts(results, author_stats, output_dir, open_browser=open_browser)
        for p in paths:
            console.print(f"[green]Chart saved:[/] {p}")
    except ImportError as exc:
        console.print(f"[yellow]Charts skipped:[/] {exc}")
    except Exception as exc:
        console.print(f"[yellow]Chart generation failed:[/] {exc}")


if __name__ == "__main__":
    app()
