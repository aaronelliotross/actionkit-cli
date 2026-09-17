# actionkit-cli

A command-line interface for the [ActionKit](https://actionkit.com/) REST API.

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the actionkit command
uv tool install git+https://github.com/aaronelliotross/actionkit-cli.git
```

This installs the `actionkit` command into `~/.local/bin/`.

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
| `transaction` | Manage transactions                |
| `hash`        | ActionKit hash helpers             |

Any other ActionKit resource name works too — see
[Generic resource commands](#generic-resource-commands).

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

### Generic resource commands

ActionKit exposes over 200 REST resources; only a handful have a dedicated
command group. Any other resource name falls back to generic `create`, `list`
and `get` commands built on the uniform REST endpoints:

```bash
# List and inspect any resource
actionkit formfield list
actionkit formfield list form_id=3708 --limit 50
actionkit formfield get 3
actionkit orderrecurring list status=active --json

# Create a new instance from KEY=VALUE pairs
actionkit formfield create name=pronouns form_id:=3708
```

#### Values and types

Shell arguments are strings, so `create` (and `list` filters) use an
httpie-style syntax to express the other JSON types:

| Syntax       | Value sent                                  |
|--------------|---------------------------------------------|
| `key=value`  | the string `"value"` — always a string      |
| `key:=JSON`  | parsed as JSON: numbers, `true`, `null`, arrays, objects |
| `key=@PATH`  | the contents of `PATH`, as a string         |
| `key:=@PATH` | the contents of `PATH`, parsed as JSON      |

```bash
actionkit formfield create \
  name=pronouns \
  form_id:=3708 \
  ordering:=1 \
  required:=true \
  options_json:='["she/her", "he/him", "they/them"]' \
  help_text=@help.html
```

Because `key=value` never guesses, string data that looks like JSON survives
intact: `zip=01234` stays `"01234"` rather than becoming `1234`.

#### Building a body from a file

`--json` supplies a base body, which `KEY=VALUE` pairs then override. This
makes an existing payload reusable as a template:

```bash
actionkit formfield create --json field.json
actionkit formfield create --json field.json name=last_name ordering:=2
cat field.json | actionkit formfield create --json - name=last_name
```

#### Checking before you POST

`--dry-run` prints the assembled request body and sends nothing:

```bash
$ actionkit formfield create name=pronouns form_id:=3708 --dry-run
POST /rest/v1/formfield/
{
  "name": "pronouns",
  "form_id": 3708
}
```

A resource that doesn't exist is reported rather than raising a traceback,
and validation errors show the API's response body:

```
$ actionkit formfeild list
Error: No ActionKit resource 'formfeild' (GET .../rest/v1/formfeild/ returned 404).
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
uv run python -m black actionkit_cli/ tests/
```

Run this before committing.

### Tests

```bash
uv run pytest
```

### Project structure

```
actionkit_cli/
├── cli.py              # Entry point and Click group
├── client.py           # ActionKit REST API client (httpx)
├── config.py           # Environment variable loading
├── output.py           # Rich-based output formatting
├── params.py           # KEY=VALUE / KEY:=JSON argument parsing
└── commands/           # Command groups (one file per resource)
    ├── action.py
    ├── generic.py      # Fallback create/list/get for any resource
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
- Parse `KEY=VALUE` arguments with `parse_assignments()` from `params.py` rather than
  hand-rolling `str.partition("=")`, so typing works the same everywhere.
- A dedicated group is only worth adding when a resource needs typed options,
  validation or multi-step behaviour; otherwise the generic commands cover it.
