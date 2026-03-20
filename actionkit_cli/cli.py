"""ActionKit CLI entry point."""

import click

from actionkit_cli.client import ActionKitClient
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


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """Command-line interface for the ActionKit API."""
    ctx.ensure_object(dict)
    ctx.obj = LazyClient()


@cli.result_callback()
@click.pass_context
def cleanup(ctx, result, **kwargs):
    ctx.obj.close()


# Import and register command groups
from actionkit_cli.commands import action, mailer, page, report, translation, user  # noqa: E402

cli.add_command(user.user)
cli.add_command(page.page)
cli.add_command(action.action)
cli.add_command(mailer.mailer)
cli.add_command(report.report)
cli.add_command(translation.translation)
