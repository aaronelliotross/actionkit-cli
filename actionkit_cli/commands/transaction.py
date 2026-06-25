"""Transaction commands."""

import click

from actionkit_cli.output import print_json, print_list_response

TRANSACTION_COLUMNS = [
    "id",
    "order",
    "account",
    "amount",
    "currency",
    "type",
    "status",
    "success",
    "created_at",
]


@click.group()
def transaction():
    """Manage ActionKit transactions (core_transaction)."""
    pass


@transaction.command("list")
@click.option("--limit", "-l", default=20, help="Number of results (max 100).")
@click.option("--offset", "-o", default=0, help="Result offset for pagination.")
@click.option("--order-by", default="-created_at", help="Field to sort by.")
@click.option("--order", "order_id", type=int, help="Filter by order ID.")
@click.option("--account", help="Filter by merchant account name.")
@click.option("--status", help="Filter by transaction status.")
@click.option("--type", "txn_type", help="Filter by transaction type (e.g. sale, refund).")
@click.pass_obj
def list_transactions(client, limit, offset, order_by, order_id, account, status, txn_type):
    """List transactions."""
    filters = {}
    if order_id:
        filters["order"] = order_id
    if account:
        filters["account"] = account
    if status:
        filters["status"] = status
    if txn_type:
        filters["type"] = txn_type

    data = client.list(
        "transaction", limit=limit, offset=offset, order_by=order_by, **filters
    )
    print_list_response(data, TRANSACTION_COLUMNS, title="Transactions")


@transaction.command("get")
@click.argument("transaction_id", type=int)
@click.pass_obj
def get_transaction(client, transaction_id):
    """Get a single transaction by ID."""
    data = client.detail("transaction", transaction_id)
    print_json(data)


@transaction.command("create")
@click.option("--order", "order_id", type=int, required=True, help="Order ID to attach this transaction to.")
@click.option("--account", required=True, help="Merchant account name.")
@click.option("--amount", required=True, help="Transaction amount (decimal).")
@click.option("--currency", default="USD", show_default=True, help="3-letter currency code.")
@click.option(
    "--type",
    "txn_type",
    default="sale",
    show_default=True,
    type=click.Choice(["sale", "refund", "credit", "auth", "void"], case_sensitive=False),
    help="Transaction type.",
)
@click.option(
    "--status",
    default="completed",
    show_default=True,
    help="Transaction status.",
)
@click.option("--success/--failed", default=True, help="Whether the transaction succeeded.")
@click.option("--test-mode", is_flag=True, help="Mark as a test-mode transaction.")
@click.option("--failure-code", help="Processor failure code (for failed transactions).")
@click.option("--failure-description", help="Failure description (for failed transactions).")
@click.option(
    "--field", "-f", multiple=True, help="Additional field as key=value (repeatable)."
)
@click.pass_obj
def create_transaction(
    client,
    order_id,
    account,
    amount,
    currency,
    txn_type,
    status,
    success,
    test_mode,
    failure_code,
    failure_description,
    field,
):
    """Create a transaction (core_transaction row)."""
    data = {
        "order": f"/rest/v1/order/{order_id}/",
        "account": account,
        "amount": amount,
        "currency": currency.upper(),
        "type": txn_type.lower(),
        "status": status,
        "success": success,
        "test_mode": test_mode,
    }
    if failure_code:
        data["failure_code"] = failure_code
    if failure_description:
        data["failure_description"] = failure_description

    for f in field:
        key, sep, value = f.partition("=")
        if not key or not sep:
            raise click.BadParameter(f"Invalid field format: {f!r}. Use key=value.")
        data[key] = value

    result = client.post("transaction", data)
    click.echo("Transaction created.")
    print_json(result)
