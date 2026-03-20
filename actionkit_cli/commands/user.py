"""User commands."""

import click

from actionkit_cli.output import print_json, print_list_response

USER_COLUMNS = [
    "id",
    "email",
    "first_name",
    "last_name",
    "city",
    "state",
    "country",
    "created_at",
]


@click.group()
def user():
    """Manage ActionKit users."""
    pass


@user.command("list")
@click.option("--limit", "-l", default=20, help="Number of results (max 100).")
@click.option("--offset", "-o", default=0, help="Result offset for pagination.")
@click.option("--order-by", default="-created_at", help="Field to sort by.")
@click.option("--state", help="Filter by US state.")
@click.option("--country", help="Filter by country.")
@click.option("--source", help="Filter by source.")
@click.pass_obj
def list_users(client, limit, offset, order_by, state, country, source):
    """List users."""
    filters = {}
    if state:
        filters["state"] = state
    if country:
        filters["country"] = country
    if source:
        filters["source"] = source

    data = client.list("user", limit=limit, offset=offset, order_by=order_by, **filters)
    print_list_response(data, USER_COLUMNS, title="Users")


@user.command("get")
@click.argument("user_id", type=int)
@click.pass_obj
def get_user(client, user_id):
    """Get a single user by ID."""
    data = client.detail("user", user_id)
    print_json(data)


@user.command("search")
@click.argument("email")
@click.pass_obj
def search_user(client, email):
    """Search for a user by email address."""
    data = client.list("user", email=email)
    objects = data.get("objects", [])
    if not objects:
        click.echo(f"No user found with email: {email}")
        return
    print_json(objects[0])


@user.command("update")
@click.argument("user_id", type=int)
@click.option("--first-name", help="First name.")
@click.option("--last-name", help="Last name.")
@click.option("--city", help="City.")
@click.option("--state", help="State.")
@click.option("--country", help="Country.")
@click.option("--zip", "zip_code", help="Zip/postal code.")
@click.pass_obj
def update_user(client, user_id, first_name, last_name, city, state, country, zip_code):
    """Update a user's fields."""
    fields = {}
    if first_name is not None:
        fields["first_name"] = first_name
    if last_name is not None:
        fields["last_name"] = last_name
    if city is not None:
        fields["city"] = city
    if state is not None:
        fields["state"] = state
    if country is not None:
        fields["country"] = country
    if zip_code is not None:
        fields["zip"] = zip_code

    if not fields:
        click.echo("No fields to update. Use --help to see options.")
        return

    data = client.patch(f"user/{user_id}", fields)
    click.echo(f"User {user_id} updated.")
    print_json(data)
