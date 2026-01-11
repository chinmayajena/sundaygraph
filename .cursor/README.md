# Cursor IDE Configuration

This folder contains Cursor IDE-specific configuration files for the SundayGraph project.

## Files

- `.cursorrules` (root) - Main rules file for Cursor AI assistant
- `.cursorignore` (root) - Files/directories to exclude from Cursor indexing
- `.cursor/context.md` - Additional project context and debugging tips
- `.cursor/README.md` - This file

## Usage

Cursor IDE will automatically:
- Read `.cursorrules` for project rules and patterns
- Respect `.cursorignore` to skip indexing large/unnecessary files
- Use context from `.cursor/context.md` for better understanding

## File Descriptions

### `.cursorrules`
Main configuration file containing:
- Project architecture principles
- Code style and conventions
- Key patterns (CodeAct, workspace isolation, etc.)
- Anti-patterns to avoid
- Common tasks and workflows

### `.cursorignore`
Similar to `.gitignore`, but for Cursor IDE:
- Excludes large files from indexing (CSV, JSON, PDF)
- Skips build artifacts and cache
- Ignores node_modules and virtual environments
- Improves Cursor performance

### `.cursor/context.md`
Additional context including:
- Project purpose and key decisions
- Common workflows
- Debugging tips
- Technology-specific notes
- Troubleshooting guide

## Customization

Edit these files as the project evolves:
- Update `.cursorrules` when adding new patterns
- Add to `.cursorignore` if new large file types appear
- Update `.cursor/context.md` with new workflows or issues
