"""ActionKit CLI entry point."""

import click

from actionkit_cli.client import ActionKitClient
from actionkit_cli.commands.generic import ResourceGroup, attach_generic_commands
from actionkit_cli.config import load_config


class LazyClient(ActionKitClient):
    """Client that defers connection until first use."""

    _initialized = False

    def __init__(self):
        pass

    def _ensure_init(self):
        if not self._initialized:
            config = load_config()
            super().__init__(
                base_url=config["base_url"],
                username=config["username"],
                password=config["password"],
            )
            self._initialized = True

    def get(self, *args, **kwargs):
        self._ensure_init()
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self._ensure_init()
        return super().post(*args, **kwargs)

    def put(self, *args, **kwargs):
        self._ensure_init()
        return super().put(*args, **kwargs)

    def patch(self, *args, **kwargs):
        self._ensure_init()
        return super().patch(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._ensure_init()
        return super().delete(*args, **kwargs)

    def close(self):
        if self._initialized:
            super().close()


@click.group(cls=ResourceGroup)
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """Command-line interface for the ActionKit API.

    Resources without a dedicated command group below still support the
    generic `create`, `list` and `get` commands, e.g. `actionkit formfield list`.
    """
    if ctx.obj is None:
        ctx.obj = LazyClient()


@cli.result_callback()
@click.pass_context
def cleanup(ctx, result, **kwargs):
    ctx.obj.close()


# Import and register command groups
from actionkit_cli.commands import (  # noqa: E402
    action,
    hash,
    mailer,
    page,
    report,
    transaction,
    translation,
    user,
)

# Groups that map one-to-one onto a REST resource also get the generic
# commands they don't define themselves (e.g. `user create`). `report`,
# `translation` and `hash` do not map onto a resource of the same name.
for _group, _resource in [
    (user.user, "user"),
    (page.page, "page"),
    (action.action, "action"),
    (mailer.mailer, "mailer"),
    (transaction.transaction, "transaction"),
]:
    cli.add_command(attach_generic_commands(_group, _resource))

cli.add_command(report.report)
cli.add_command(translation.translation)
cli.add_command(hash.hash)
