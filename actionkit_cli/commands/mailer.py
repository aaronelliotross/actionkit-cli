"""Mailer commands."""

import click

from actionkit_cli.output import print_json, print_list_response

MAILER_COLUMNS = ["id", "subject", "status", "from_line", "created_at"]


@click.group()
def mailer():
    """Manage ActionKit mailings."""
    pass


@mailer.command("list")
@click.option("--limit", "-l", default=20, help="Number of results (max 100).")
@click.option("--offset", "-o", default=0, help="Result offset for pagination.")
@click.option("--order-by", default="-created_at", help="Field to sort by.")
@click.option("--status", help="Filter by status (e.g. draft, sending, completed).")
@click.pass_obj
def list_mailers(client, limit, offset, order_by, status):
    """List mailings."""
    filters = {}
    if status:
        filters["status"] = status

    data = client.list(
        "mailer", limit=limit, offset=offset, order_by=order_by, **filters
    )
    print_list_response(data, MAILER_COLUMNS, title="Mailings")


@mailer.command("get")
@click.argument("mailer_id", type=int)
@click.pass_obj
def get_mailer(client, mailer_id):
    """Get a single mailing by ID."""
    data = client.detail("mailer", mailer_id)
    print_json(data)


@mailer.command("status")
@click.argument("mailer_id", type=int)
@click.pass_obj
def mailer_status(client, mailer_id):
    """Check the status of a mailing."""
    data = client.get(f"mailer/{mailer_id}/status")
    print_json(data)


@mailer.command("queue")
@click.argument("mailer_id", type=int)
@click.confirmation_option(
    prompt="Are you sure you want to queue this mailing for sending?"
)
@click.pass_obj
def queue_mailer(client, mailer_id):
    """Queue a mailing for sending."""
    data = client.post(f"mailer/{mailer_id}/queue")
    click.echo(f"Mailing {mailer_id} queued for sending.")
    print_json(data)


@mailer.command("proof")
@click.argument("mailer_id", type=int)
@click.option("--to", "proof_to", required=True, help="Email address to send proof to.")
@click.pass_obj
def proof_mailer(client, mailer_id, proof_to):
    """Send a proof/test email for a mailing."""
    data = client.post(f"mailer/{mailer_id}/proofs", {"proof_to": proof_to})
    click.echo(f"Proof sent to {proof_to}.")
    print_json(data)
