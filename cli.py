"""Command-line interface for SundayGraph"""

import asyncio
import click
from pathlib import Path
from loguru import logger

from src import SundayGraph


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to configuration file")
@click.pass_context
def cli(ctx, config):
    """SundayGraph - Agentic AI System with Ontology-Backed Graph"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.pass_context
def ingest(ctx, input_path):
    """Ingest data from file or directory"""
    config_path = ctx.obj.get("config")
    sg = SundayGraph(config_path=config_path)
    
    async def run():
        result = await sg.ingest_data(input_path)
        click.echo(f"Ingestion complete: {result}")
        sg.close()
    
    asyncio.run(run())


@cli.command()
@click.argument("query")
@click.option("--type", "-t", default="entity", help="Query type (entity, relation, neighbor, path)")
@click.pass_context
def query(ctx, query, type):
    """Query the knowledge graph"""
    config_path = ctx.obj.get("config")
    sg = SundayGraph(config_path=config_path)
    
    async def run():
        results = await sg.query(query, query_type=type)
        click.echo(f"Found {len(results)} results:")
        for i, result in enumerate(results[:10], 1):
            click.echo(f"{i}. {result}")
        sg.close()
    
    asyncio.run(run())


@cli.command()
@click.pass_context
def stats(ctx):
    """Get system statistics"""
    config_path = ctx.obj.get("config")
    sg = SundayGraph(config_path=config_path)
    
    async def run():
        stats = await sg.get_stats()
        click.echo("System Statistics:")
        click.echo(f"Graph: {stats['graph']}")
        click.echo(f"Ontology: {stats['ontology']}")
        sg.close()
    
    asyncio.run(run())


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to clear all data?")
@click.pass_context
def clear(ctx):
    """Clear all data from the graph"""
    config_path = ctx.obj.get("config")
    sg = SundayGraph(config_path=config_path)
    sg.clear()
    click.echo("Graph cleared")
    sg.close()


if __name__ == "__main__":
    cli()

