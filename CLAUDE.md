# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A CLI tool for the ActionKit REST API, built with Click, httpx, and Rich. Installed as the `actionkit` command.

## Development Setup

```bash
uv sync                  # install dependencies
cp .env.example .env     # configure API credentials
direnv allow             # activates venv and loads .env
```

Requires Python 3.13+. Uses direnv with `.envrc` to activate the venv and load `.env`.

## Commands

```bash
uv run actionkit --help          # run the CLI
uv run black actionkit_cli/      # format code
```

No tests exist yet.

## Architecture

**Entry point**: `actionkit_cli/cli.py` defines the Click group and a `LazyClient` that defers API authentication until first use. The client is passed via `@click.pass_obj`.

**API client**: `actionkit_cli/client.py` — thin httpx wrapper around ActionKit's REST API (`/rest/v1/`). Provides `get`, `post`, `put`, `patch`, `delete`, `list`, and `detail` methods. All mutating methods handle empty response bodies.

**Commands**: Each file in `actionkit_cli/commands/` defines a Click group (user, page, action, mailer, report, translation) registered in `cli.py`. Commands follow a consistent pattern: Click decorators for args/options, `@click.pass_obj` to receive the client, call client methods, output via `print_json` or `print_list_response`.

**Output**: `actionkit_cli/output.py` — Rich-based formatting with `print_json`, `print_table`, and `print_list_response` (handles ActionKit's paginated response format with `meta`/`objects`).

## ActionKit API Notes

- Resources are accessed at `/rest/v1/{resource}/` (trailing slash required — handled by client)
- List responses use `{"meta": {...}, "objects": [...]}` format
- The `language` resource stores translations as a JSON-encoded string in its `translations` field, not a native dict
- Resource references use URI strings like `/rest/v1/page/123/`

## Adding a New Command Group

1. Create `actionkit_cli/commands/{name}.py` with a `@click.group()` function
2. Register it in `cli.py`: import and `cli.add_command()`
