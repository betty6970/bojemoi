#!/usr/bin/env python3
import click
import httpx
import asyncio
from rich.console import Console

console = Console()

@click.group()
@click.option("--url", default="http://localhost:8000", help="Orchestrator URL")
@click.pass_context
def cli(ctx, url):
    """Bojemoi Orchestrator CLI"""
    ctx.obj = {"url": url}

@cli.command()
@click.pass_context
def status(ctx):
    """Check orchestrator status"""
    url = ctx.obj["url"]
    try:
        response = httpx.get(f"{url}/status")
        data = response.json()
        console.print("[green]Orchestrator Status:[/green]")
        for key, value in data.items():
            status = "✓" if value in [True, "running"] else "✗"
            console.print(f"  {status} {key}: {value}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument("vm_name")
@click.pass_context
def deploy_vm(ctx, vm_name):
    """Deploy a VM"""
    url = ctx.obj["url"]
    try:
        response = httpx.post(f"{url}/deploy/vm/{vm_name}")
        console.print(f"[green]✓[/green] Deployment started: {vm_name}")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")

if __name__ == "__main__":
    cli()

