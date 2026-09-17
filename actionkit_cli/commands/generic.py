"""Generic commands available for any ActionKit resource.

Resources with a hand-written command group (user, page, ...) keep it. Any
other first word on the command line is treated as a resource name and gets
`create`, `list` and `get` built from the REST API's uniform endpoints.
"""

import contextlib
import json as jsonlib

import click
import httpx

from actionkit_cli.output import print_json, print_list_response
from actionkit_cli.params import parse_assignments

API_PREFIX = "rest/v1/"
MAX_COLUMNS = 8


def normalize_resource(name: str) -> str:
    """Accept `field`, `/field/` or a pasted `/rest/v1/field/`."""
    resource = name.strip("/")
    if resource.startswith(API_PREFIX):
        resource = resource[len(API_PREFIX) :]
    return resource.strip("/")


def _describe(exc: httpx.HTTPStatusError, resource: str) -> str:
    response = exc.response
    request = response.request
    if response.status_code == 404:
        return (
            f"No ActionKit resource {resource!r} "
            f"({request.method} {request.url} returned 404)."
        )
    try:
        body = jsonlib.dumps(response.json(), indent=2)
    except ValueError:
        body = response.text
    return f"{response.status_code} from {request.method} {request.url}\n{body}"


@contextlib.contextmanager
def api_errors(resource: str):
    """Turn API error responses into readable CLI errors."""
    try:
        yield
    except httpx.HTTPStatusError as exc:
        raise click.ClickException(_describe(exc, resource))


def derive_columns(objects: list[dict]) -> list[str]:
    """Pick table columns for a resource we have no column list for."""
    seen = []
    for obj in objects:
        for key in obj:
            if key not in seen:
                seen.append(key)
    if "id" in seen:
        seen.insert(0, seen.pop(seen.index("id")))
    return seen[:MAX_COLUMNS]


def _body(assignments, json_input) -> dict:
    data = {}
    if json_input is not None:
        try:
            base = jsonlib.load(json_input)
        except ValueError as exc:
            raise click.BadParameter(f"Invalid JSON input: {exc}")
        if not isinstance(base, dict):
            raise click.BadParameter("JSON input must be an object.")
        data.update(base)
    data.update(parse_assignments(assignments))
    return data


def make_resource_group(resource: str) -> click.Group:
    """Build a command group for an arbitrary ActionKit resource."""

    @click.command("create")
    @click.argument("assignments", nargs=-1, metavar="KEY=VALUE")
    @click.option(
        "--json",
        "json_input",
        type=click.File("r"),
        help="Read the base body from a JSON file, or - for stdin.",
    )
    @click.option(
        "--dry-run", is_flag=True, help="Print the request body without sending it."
    )
    @click.pass_obj
    def create(client, assignments, json_input, dry_run):
        """Create a new instance from KEY=VALUE pairs.

        KEY=VALUE is always a string, KEY:=JSON is parsed as JSON, and
        KEY=@PATH reads the value from a file. Pairs override --json.
        """
        data = _body(assignments, json_input)
        if not data:
            raise click.UsageError(
                "Nothing to create. Give KEY=VALUE pairs, or --json FILE."
            )
        if dry_run:
            click.echo(f"POST /rest/v1/{resource}/")
            print_json(data)
            return
        with api_errors(resource):
            result = client.post(resource, data)
        print_json(result)

    @click.command("list")
    @click.argument("filters", nargs=-1, metavar="KEY=VALUE")
    @click.option("--limit", "-l", default=20, help="Number of results (max 100).")
    @click.option("--offset", "-o", default=0, help="Result offset for pagination.")
    @click.option("--order-by", help="Field to sort by.")
    @click.option("--json", "as_json", is_flag=True, help="Print the raw response.")
    @click.pass_obj
    def list_(client, filters, limit, offset, order_by, as_json):
        """List instances, filtered by KEY=VALUE pairs."""
        with api_errors(resource):
            data = client.list(
                resource,
                limit=limit,
                offset=offset,
                order_by=order_by,
                **parse_assignments(filters),
            )
        if as_json:
            print_json(data)
            return
        print_list_response(
            data, derive_columns(data.get("objects", [])), title=resource
        )

    @click.command("get")
    @click.argument("resource_id", type=int)
    @click.pass_obj
    def get(client, resource_id):
        """Get a single instance by ID."""
        with api_errors(resource):
            print_json(client.detail(resource, resource_id))

    group = click.Group(
        name=resource,
        help=f"Work with the {resource!r} resource via the generic REST endpoints.",
        commands=[create, list_, get],
    )
    return group


class ResourceGroup(click.Group):
    """A group that falls back to generic commands for unknown resources."""

    def get_command(self, ctx, name):
        command = super().get_command(ctx, name)
        if command is not None:
            return command
        if name.startswith("-"):
            return None
        resource = normalize_resource(name)
        if not resource:
            return None
        return make_resource_group(resource)


def attach_generic_commands(group: click.Group, resource: str) -> click.Group:
    """Give a hand-written group the generic commands it doesn't define itself.

    A group's own commands always win; this only fills the gaps, so that e.g.
    `user create` works while `user list` keeps its typed options.
    """
    for command in make_resource_group(resource).commands.values():
        if command.name not in group.commands:
            group.add_command(command)
    return group
