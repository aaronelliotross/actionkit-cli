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
uv run python -m black actionkit_cli/ tests/   # format code
uv run pytest                                  # run tests
```

Note: the `black` console script in `.venv/bin` has a stale shebang; invoke it
as `python -m black`.

## Architecture

**Entry point**: `actionkit_cli/cli.py` defines the Click group and a `LazyClient` that defers API authentication until first use. The client is passed via `@click.pass_obj`. The root group uses `ResourceGroup`, which falls back to generic commands for unrecognised resource names. `cli()` only builds a `LazyClient` when `ctx.obj` is unset, so tests can inject a stub via `CliRunner().invoke(cli, args, obj=stub)`.

**API client**: `actionkit_cli/client.py` — thin httpx wrapper around ActionKit's REST API (`/rest/v1/`). Provides `get`, `post`, `put`, `patch`, `delete`, `list`, and `detail` methods. All mutating methods handle empty response bodies.

**Commands**: Each file in `actionkit_cli/commands/` defines a Click group (user, page, action, mailer, report, translation, gdpr) registered in `cli.py`. Commands follow a consistent pattern: Click decorators for args/options, `@click.pass_obj` to receive the client, call client methods, output via `print_json` or `print_list_response`.

**Generic commands**: `actionkit_cli/commands/generic.py` — ActionKit exposes 200+ resources but only a few have hand-written groups. `ResourceGroup.get_command` treats any unknown first word as a resource name and builds a group with `create`, `list` and `get` on the fly, so `actionkit formfield create name=x` works without any per-resource code. `api_errors()` converts `httpx.HTTPStatusError` into readable messages (404 names the resource; other statuses show the response body).

**Argument parsing**: `actionkit_cli/params.py` — `parse_assignments()` turns `KEY=VALUE` arguments into a request body. `key=value` is always a string, `key:=JSON` is parsed as JSON, and `key=@PATH` reads from a file. Use this instead of hand-rolling `partition("=")`.

**Output**: `actionkit_cli/output.py` — Rich-based formatting with `print_json`, `print_table`, and `print_list_response` (handles ActionKit's paginated response format with `meta`/`objects`).

## ActionKit API Notes

- Resources are accessed at `/rest/v1/{resource}/` (trailing slash required — handled by client)
- List responses use `{"meta": {...}, "objects": [...]}` format
- The `language` resource stores translations as a JSON-encoded string in its `translations` field, not a native dict
- Resource references use URI strings like `/rest/v1/page/123/`

## Adding a New Command Group

Most resources need no code at all — the generic fallback already gives them
`create`, `list` and `get`. Add a dedicated group only when a resource needs
typed options, validation or multi-step behaviour.

1. Create `actionkit_cli/commands/{name}.py` with a `@click.group()` function
2. Register it in `cli.py`: import and `cli.add_command()`

A registered group shadows the generic fallback for that name, so it should
provide its own `create`/`list`/`get` if those still make sense.
