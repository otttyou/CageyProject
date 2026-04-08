"""Output rendering: terminal (rich) and charts (plotly)."""

from cagey.output.charts import generate_charts
from cagey.output.terminal import (
    render_author_panels,
    render_results_table,
    render_summary_dashboard,
)

__all__ = [
    "render_results_table",
    "render_author_panels",
    "render_summary_dashboard",
    "generate_charts",
]
