"""Report commands."""

import json

import click

from actionkit_cli.output import print_json, print_table


@click.group()
def report():
    """Run ActionKit reports."""
    pass


@report.command("run")
@click.argument("short_name")
@click.option(
    "--param", "-p", multiple=True, help="Report parameter as key=value (repeatable)."
)
@click.option("--limit", "-l", default=100, help="Max rows to return.")
@click.option("--raw", is_flag=True, help="Print raw JSON instead of a table.")
@click.pass_obj
def run_report(client, short_name, param, limit, raw):
    """Run a saved report by short name."""
    params = {}
    for p in param:
        key, _, value = p.partition("=")
        if not key or not _:
            raise click.BadParameter(f"Invalid param format: {p!r}. Use key=value.")
        params[key] = value

    data = client.post(f"report/run/{short_name}", params or None)

    if raw:
        print_json(data)
        return

    rows = data if isinstance(data, list) else data.get("results", data.get("rows", []))
    if not rows:
        click.echo("Report returned no results.")
        return

    if isinstance(rows[0], dict):
        columns = list(rows[0].keys())
        print_table(rows, columns, title=f"Report: {short_name}")
    else:
        print_json(data)


@report.command("sql")
@click.argument("query")
@click.option("--raw", is_flag=True, help="Print raw JSON instead of a table.")
@click.pass_obj
def run_sql(client, query, raw):
    """Run an ad-hoc SQL query."""
    data = client.post("report/run/sql", {"query": query})

    if raw:
        print_json(data)
        return

    rows = data if isinstance(data, list) else data.get("results", data.get("rows", []))
    if not rows:
        click.echo("Query returned no results.")
        return

    if isinstance(rows[0], dict):
        columns = list(rows[0].keys())
        print_table(rows, columns, title="SQL Query Results")
    else:
        print_json(data)
