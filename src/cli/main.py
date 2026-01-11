"""Main CLI entry point for SundayGraph."""

import click
from pathlib import Path


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """SundayGraph - SemanticOps for Snowflake Semantic Views."""
    pass


# Import and add command groups (lazy import to avoid dependency issues)
def _register_commands():
    """Register CLI commands."""
    from .snowflake import snowflake_group
    cli.add_command(snowflake_group)


# Register commands
_register_commands()


if __name__ == "__main__":
    cli()
