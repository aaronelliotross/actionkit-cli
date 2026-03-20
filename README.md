# actionkit-cli

A command-line interface for the [ActionKit](https://actionkit.com/) REST API.

## Installation

Requires Python 3.13+.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone <repo-url>
cd actionkit-cli
uv sync
```

### Configuration

Copy the example environment file and fill in your ActionKit credentials:

```bash
cp .env.example .env
```

```env
ACTIONKIT_BASE_URL=https://your-instance.actionkit.com
ACTIONKIT_USERNAME=your-api-username
ACTIONKIT_PASSWORD=your-api-password
```

If you use [direnv](https://direnv.net/), run `direnv allow` to automatically activate the virtual environment and load `.env`.

Otherwise, source the venv manually:

```bash
source .venv/bin/activate
```

## Usage

```bash
actionkit --help
```

### Commands

| Command       | Description                        |
|---------------|------------------------------------|
| `user`        | Manage users                       |
| `page`        | Manage pages                       |
| `action`      | Manage actions                     |
| `mailer`      | Manage mailings                    |
| `report`      | Run saved reports and SQL queries  |
| `translation` | Manage translation strings         |

### Examples

```bash
# List users from Germany
actionkit user list --country DE

# Search for a user by email
actionkit user search user@example.com

# List petition pages
actionkit page list --type petition

# Run a saved report
actionkit report run my_report -p start_date=2026-01-01

# Run an ad-hoc SQL query
actionkit report sql "SELECT id, email FROM core_user LIMIT 10"

# Set a single translation
actionkit translation set nl donate_button "Doneer nu"

# Set multiple translations from a JSON file
actionkit translation set nl @translations.json

# Get a specific translation value
actionkit translation get nl donate_button

# Create an action with custom fields
actionkit action create --page my_petition --email user@example.com -f source=homepage
```

## Development

### Setup

```bash
uv sync
cp .env.example .env    # add your API credentials
direnv allow             # or: source .venv/bin/activate
```

### Formatting

This project uses [Black](https://black.readthedocs.io/) for code formatting:

```bash
uv run black actionkit_cli/
```

Run this before committing.

### Project structure

```
actionkit_cli/
├── cli.py              # Entry point and Click group
├── client.py           # ActionKit REST API client (httpx)
├── config.py           # Environment variable loading
├── output.py           # Rich-based output formatting
└── commands/           # Command groups (one file per resource)
    ├── action.py
    ├── mailer.py
    ├── page.py
    ├── report.py
    ├── translation.py
    └── user.py
```

### Adding a new command

1. Create a new file in `actionkit_cli/commands/` with a `@click.group()` function.
2. Import and register it in `cli.py` with `cli.add_command()`.
3. Use `@click.pass_obj` to receive the API client.
4. Use the helpers in `output.py` (`print_json`, `print_table`, `print_list_response`) for consistent output.

### Conventions

- Each command group maps to an ActionKit REST API resource.
- List commands should support `--limit`, `--offset`, and `--order-by` options.
- Destructive commands should use `@click.confirmation_option`.
- Use `client.list()` for paginated listing and `client.detail()` for single-resource retrieval.
