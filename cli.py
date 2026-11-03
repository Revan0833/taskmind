#!/usr/bin/env python3
"""
Interactive Command Line Interface for Task Management Agent
Vector database: ChromaDB (project notes) | Embedding: all-MiniLM-L6-v2
Tools: Task CRUD API, Date Parser, Priority Classifier
"""

import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from backend.agent import get_task_agent
from backend.task_crud import get_task_crud
from backend.vector_store import get_vector_store
from backend.date_parser import get_date_parser
from backend.priority_classifier import get_priority_classifier

console = Console()

def display_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║         TASK MANAGEMENT AGENT — WORKSHOP PREPARATION              ║
    ║   ChromaDB (all-MiniLM-L6-v2) | Task CRUD | Date Parser | Priority ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    console.print(f"[bold cyan]{banner}[/bold cyan]")

def show_tasks_table():
    crud = get_task_crud()
    tasks = crud.list_tasks()
    if not tasks:
        console.print("[yellow]No tasks in database yet. Ask the agent to generate some![/yellow]\n")
        return

    table = Table(title="📋 Current Workshop Tasks", title_style="bold magenta")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Title", style="bold white", width=30)
    table.add_column("Priority", width=10)
    table.add_column("Category", width=16)
    table.add_column("Due Date", width=22)
    table.add_column("Status", width=12)

    for t in tasks:
        p_color = {
            "Urgent": "bold red",
            "High": "bold yellow",
            "Medium": "cyan",
            "Low": "dim white"
        }.get(t.priority, "white")

        s_color = {
            "completed": "bold green",
            "in_progress": "bold blue",
            "pending": "yellow"
        }.get(t.status, "white")

        table.add_row(
            t.id,
            t.title,
            f"[{p_color}]{t.priority}[/{p_color}]",
            t.category,
            t.due_date,
            f"[{s_color}]{t.status}[/{s_color}]"
        )

    console.print(table)
    console.print()

def show_notes_table():
    vstore = get_vector_store()
    notes = vstore.list_all_notes()
    table = Table(title="🧠 ChromaDB Workshop Project Notes", title_style="bold green")
    table.add_column("ID", style="dim", width=16)
    table.add_column("Title", style="bold white", width=32)
    table.add_column("Category", width=16)
    table.add_column("Tags", style="dim cyan", width=24)

    for n in notes:
        table.add_row(n.id, n.title, n.category, ", ".join(n.tags))

    console.print(table)
    console.print()

def run_cli():
    display_banner()
    agent = get_task_agent()
    crud = get_task_crud()

    console.print("[dim]Commands: [bold]tasks[/bold] (view tasks), [bold]notes[/bold] (view ChromaDB notes), [bold]clear[/bold] (wipe tasks), [bold]exit[/bold] (quit)[/dim]\n")

    sample_prompt = (
        "Create tasks for preparing the workshop: order catering with vegan and peanut allergy options, "
        "test the AV equipment in room 302, get the speaker slides, and print the attendee badges by next Wednesday."
    )
    console.print(Panel(f"[bold]Default Workshop Scenario Prompt:[/bold]\n{sample_prompt}\n\n[dim]Press Enter to use this prompt, or type your own request below:[/dim]", border_style="cyan"))

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]User[/bold green]")
            if not user_input.strip():
                user_input = sample_prompt

            cmd = user_input.strip().lower()
            if cmd in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting Task Management Agent. Goodbye![/yellow]")
                break
            elif cmd == "tasks":
                show_tasks_table()
                continue
            elif cmd == "notes":
                show_notes_table()
                continue
            elif cmd == "clear":
                crud.clear_all()
                console.print("[green]All tasks cleared.[/green]")
                continue

            console.print("\n[dim cyan]⚡ Processing request with ChromaDB semantic search & AI tools...[/dim cyan]")
            response = agent.process_request(user_input)

            # Display Agent Thought & Tool Steps
            for s in response.steps:
                console.print(f"  [bold cyan]✓[/bold cyan] [bold]{s.name}[/bold]: {s.details}")

            console.print()
            console.print(Panel(response.reply, title="🤖 Agent Response", border_style="blue"))

            if response.proposal and response.proposal.proposed_tasks:
                prop_table = Table(title="📝 Proposed Structured Tasks (Awaiting Confirmation)", border_style="yellow")
                prop_table.add_column("#", style="dim", width=4)
                prop_table.add_column("Title", style="bold white", width=28)
                prop_table.add_column("Priority", width=10)
                prop_table.add_column("Due Date", width=22)
                prop_table.add_column("Category", width=14)
                prop_table.add_column("ChromaDB Context References", width=30)

                for idx, item in enumerate(response.proposal.proposed_tasks, 1):
                    prop_table.add_row(
                        str(idx),
                        item.title,
                        item.priority,
                        item.due_date,
                        item.category,
                        ", ".join(item.source_notes) if item.source_notes else "General"
                    )
                console.print(prop_table)

                # Confirmation Gate
                confirmed = Confirm.ask("\n[bold yellow]👉 Do you confirm creating these tasks in the database?[/bold yellow]", default=True)
                if confirmed:
                    final_response = agent.confirm_and_create_tasks(response.proposal.proposed_tasks)
                    console.print(Panel(final_response.reply, title="🎉 Database Updated", border_style="green"))
                    show_tasks_table()
                else:
                    console.print("[red]❌ Task creation cancelled by user. No database changes made.[/red]")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Interrupted. Exiting.[/yellow]")
            break

if __name__ == "__main__":
    run_cli()
