import logging
import json
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.style import Style
from ..schema import CompiledResearchReport

logger = logging.getLogger(__name__)

class ReportFormatter:
    """Renders the CompiledResearchReport into terminal panels using the rich library."""
    
    def __init__(self):
        self.console = Console()

    def render(self, report: CompiledResearchReport, json_output: bool = False):
        """Displays the report in the requested format.
        
        Args:
            report: The CompiledResearchReport Pydantic object.
            json_output: True to dump raw JSON, False for beautiful terminal layout.
        """
        if json_output:
            self.console.print(report.model_dump_json(indent=2))
            return

        # RENDER TERMINAL GRAPHICS
        self.console.print()
        title_text = Text(report.title.upper(), style="bold magenta", justify="center")
        self.console.print(Panel(title_text, subtitle=f"Generated At: {report.timestamp}", border_style="cyan"))
        self.console.print()

        # 1. Executive Intelligence Matrix
        matrix_table = Table(title="Executive Intelligence Matrix", border_style="blue", show_header=True, expand=True)
        matrix_table.add_column("Axioms (Established Facts)", style="green", ratio=1)
        matrix_table.add_column("Fresh Variables (Unconfirmed Search Fetches)", style="yellow", ratio=1)
        
        axioms = report.executive_intelligence_matrix.axioms
        fresh = report.executive_intelligence_matrix.fresh_variables
        
        max_rows = max(len(axioms), len(fresh))
        for i in range(max_rows):
            ax_val = axioms[i] if i < len(axioms) else ""
            fr_val = fresh[i] if i < len(fresh) else ""
            matrix_table.add_row(ax_val, fr_val)
            
        self.console.print(matrix_table)
        self.console.print()

        # 2. Factual Triple Trace
        trace_table = Table(title="Factual Triple Trace", border_style="green", show_header=True, expand=True)
        trace_table.add_column("Tracer ID", style="dim", width=12)
        trace_table.add_column("Subject", style="bold cyan")
        trace_table.add_column("Predicate", style="magenta")
        trace_table.add_column("Object", style="bold yellow")
        trace_table.add_column("Confidence Score", style="bold white", justify="right")
        
        for record in report.factual_triple_trace.records:
            # Map score to color
            score = record.confidence
            color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
            confidence_str = f"[{color}]{score:.2f}[/{color}]"
            
            trace_table.add_row(
                record.relationship_id[:8],
                record.source_name,
                record.predicate,
                record.target_name,
                confidence_str
            )
            
        self.console.print(trace_table)
        self.console.print()

        # 3. Divergence & Contradiction Matrix
        div_table = Table(title="Divergence & Contradiction Matrix", border_style="red", show_header=True, expand=True)
        div_table.add_column("Entity / Relation", style="bold magenta", width=30)
        div_table.add_column("Contradiction Summary", style="red", ratio=2)
        div_table.add_column("Conflicting Sources", style="dim cyan", ratio=1)
        
        for record in report.divergence_contradiction_matrix.contradictions:
            sources_str = "\n".join(record.conflicting_sources)
            div_table.add_row(
                record.entity_or_relation,
                record.contradiction_summary,
                sources_str
            )
            
        self.console.print(div_table)
        self.console.print()

        # 4. Temporal Stability Indices
        stab_table = Table(title="Temporal Stability Indices", border_style="yellow", show_header=True, expand=True)
        stab_table.add_column("Entity Relationship Linkage", style="bold cyan", ratio=2)
        stab_table.add_column("Age", style="magenta", justify="right")
        stab_table.add_column("Stability Index", style="bold white", justify="right")
        
        for record in report.temporal_stability_indices.stabilities:
            # Format age
            age_s = record.age_seconds
            if age_s < 60:
                age_str = f"{int(age_s)}s"
            elif age_s < 3600:
                age_str = f"{int(age_s // 60)}m"
            elif age_s < 86400:
                age_str = f"{int(age_s // 3600)}h"
            else:
                age_str = f"{int(age_s // 86400)}d"
                
            stability = record.stability_index
            color = "green" if stability >= 0.8 else "yellow" if stability >= 0.5 else "red"
            bar_len = int(stability * 10)
            bar_str = "█" * bar_len + "░" * (10 - bar_len)
            
            stab_table.add_row(
                record.entity_or_relation,
                age_str,
                f"[{color}]{bar_str} {stability:.2f}[/{color}]"
            )
            
        self.console.print(stab_table)
        self.console.print()

        # 5. Knowledge-Gap Footprint
        gap_table = Table(title="Knowledge-Gap Footprint", border_style="cyan", show_header=True, expand=True)
        gap_table.add_column("Missing Node / Relationship", style="bold yellow", width=30)
        gap_table.add_column("Context Reason", style="white", ratio=2)
        gap_table.add_column("Priority", style="bold", justify="center", width=12)
        
        for record in report.knowledge_gap_footprint.missing_structures:
            prio = record.priority.upper()
            if prio == "HIGH":
                prio_str = "[bold red]HIGH[/bold red]"
            elif prio == "MEDIUM":
                prio_str = "[bold yellow]MEDIUM[/bold yellow]"
            else:
                prio_str = "[bold blue]LOW[/bold blue]"
                
            gap_table.add_row(
                record.missing_entity,
                record.context,
                prio_str
            )
            
        self.console.print(gap_table)
        self.console.print()
        self.console.print(Panel(Text("Autonomous Research End.", style="bold green", justify="center"), border_style="green"))
        self.console.print()
