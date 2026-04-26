# jira-cli Reference

A CLI skill for Atlassian Jira using `@pchuri/jira-cli`. Use this when the user wants to work with Jira issues, comments, remote links, projects, boards, or sprints from an agent or terminal workflow.

Use the `jira` command for:

- Reading and exporting Jira issues
- Searching and listing issues with filters or JQL
- Creating, editing, and deleting issues
- Adding, listing, editing, and deleting comments
- Adding, listing, updating, and deleting remote links, such as GitHub PRs, CI runs, dashboards, or docs
- Listing projects, project components, project versions, boards, and sprints

Prefer read-only inspection first. Only perform writes when the user clearly asks for a change.

## Installation

Install globally:

```sh
npm install -g @pchuri/jira-cli
jira --help
```

Or use without global installation:

```sh
npx @pchuri/jira-cli --help
```

For local development from source:

```sh
git clone https://github.com/pchuri/jira-cli.git
cd jira-cli
npm install
npm link
jira --help
```

## Configuration

Preferred for agents — environment variables, so the agent does not need an interactive prompt:

| Variable | Description | Example |
|---|---|---|
| `JIRA_HOST` | Jira host, usually without protocol | `your-company.atlassian.net` |
| `JIRA_API_TOKEN` | Jira API token | `ATATT3x...` |
| `JIRA_USERNAME` | Email/username for Basic auth. Omit for bearer-token mode. | `user@company.com` |
| `JIRA_API_VERSION` | Jira REST API version: `auto`, `2`, or `3` | `auto` |
| `JIRA_DOMAIN` | Legacy host variable | `your-company.atlassian.net` |
| `JIRA_CLI_CONFIG_PATH` | Optional config file path override | `/tmp/jira-config.json` |
| `NO_COLOR` | Disable ANSI colors for easier parsing | `1` |

Bearer-token style, recommended by the CLI docs:

```sh
export JIRA_HOST="your-company.atlassian.net"
export JIRA_API_TOKEN="your-api-token"
export JIRA_API_VERSION="auto"
```

Basic-auth style, when username/email is required:

```sh
export JIRA_HOST="your-company.atlassian.net"
export JIRA_USERNAME="user@company.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_API_VERSION="auto"
```

Legacy environment-variable style:

```sh
export JIRA_DOMAIN="your-company.atlassian.net"
export JIRA_USERNAME="user@company.com"
export JIRA_API_TOKEN="your-api-token"
export JIRA_API_VERSION="auto"
```

Non-interactive CLI configuration:

```sh
# Bearer auth
jira config --server https://your-company.atlassian.net --token "$JIRA_API_TOKEN"

# Basic auth
jira config --server https://your-company.atlassian.net \
  --username user@company.com \
  --token "$JIRA_API_TOKEN"
```

Set individual config values:

```sh
jira config set server https://your-company.atlassian.net
jira config set token "$JIRA_API_TOKEN"
jira config set username user@company.com
jira config set apiVersion auto
```

Verify configuration:

```sh
jira config --show
jira issue view PROJ-123
```

Configuration file locations:

| Platform | Path |
|---|---|
| macOS | `~/Library/Preferences/jira-cli/config.json` |
| Linux | `~/.config/jira-cli/config.json` |
| Windows | `%APPDATA%\jira-cli\config.json` |

Global flags:

```sh
jira --config <path> <command>   # use a specific config file
jira --verbose <command>         # verbose output
jira --no-color <command>        # disable color output
```

## API Version Behavior

`JIRA_API_VERSION=auto` is the default and safest setting. In auto mode, the CLI tries Jira REST API v3 first and falls back to v2 if needed.

Override only when necessary:

```sh
jira config set apiVersion auto
jira config set apiVersion 3
jira config set apiVersion 2

export JIRA_API_VERSION=auto
```

## Core Identifiers

| Identifier | Meaning | Example |
|---|---|---|
| Issue key | Jira issue ID shown in URLs and boards | `PROJ-123` |
| Project key | Jira project key | `PROJ` |
| Board ID | Numeric Jira agile board ID | `42` |
| Comment ID | Numeric comment ID returned by comment commands | `12345` |
| Remote link ID | Numeric link ID returned by remote-link commands | `12345` |
| Global ID | Stable remote-link identifier used for upsert-like behavior | `https://github.com/org/repo/pull/42` |
| JQL | Jira Query Language string | `project = PROJ AND status = "In Progress"` |

## Output Formats

| Command area | Useful formats |
|---|---|
| `jira issue view` | terminal output, `--format markdown`, `--output <path>` |
| `jira issue comment list` | `--format table`, `--format json` |
| `jira issue remote-link list` | `--format table`, `--format json` |

For agents, prefer:

```sh
jira --no-color issue view PROJ-123 --format markdown
jira --no-color issue comment list PROJ-123 --format json
jira --no-color issue remote-link list PROJ-123 --format json
```

---

## Commands Reference

### `config`

Configure or inspect CLI credentials and API behavior.

```sh
jira config [--server <url>] [--username <email>] [--token <token>]
jira config --show
jira config set <key> <value>
```

Examples:

```sh
jira config --server https://your-company.atlassian.net --token "$JIRA_API_TOKEN"
jira config --server https://your-company.atlassian.net --username user@company.com --token "$JIRA_API_TOKEN"
jira config set apiVersion auto
jira config --show
```

---

### `issue view <key>`

View details for a single issue. Alias: `issue show`.

```sh
jira issue view <key> [--format terminal|markdown] [--output <path>]
```

Examples:

```sh
jira issue view PROJ-123
jira issue view PROJ-123 --format markdown
jira issue view PROJ-123 --format markdown --output ./PROJ-123.md
jira issue show PROJ-123
```

Agent guidance:

- Use `--format markdown` when the agent needs to read or summarize an issue.
- Use `--output <path>` when the user wants a local file or when the issue content will be edited before reuse.

---

### `issue list`

List/search issues with filters or JQL.

```sh
jira issue list [options]
```

Common options:

| Option | Description |
|---|---|
| `--project <key>` | Filter by project key |
| `--assignee <user>` | Filter by assignee |
| `--reporter <user>` | Filter by reporter |
| `--status <status>` | Filter by status |
| `--type <type>` | Filter by issue type |
| `--priority <level>` | Filter by priority |
| `--created <date>` | Filter by created date |
| `--updated <date>` | Filter by updated date |
| `--jql <query>` | Use a JQL query |
| `--limit <number>` | Limit result count |

Examples:

```sh
jira issue list
jira issue list --project PROJ --limit 20
jira issue list --assignee john.doe --status "In Progress"
jira issue list --project PROJ --assignee john.doe --status "To Do"
jira issue list --jql "project = PROJ AND status = 'In Progress'" --limit 10
jira issue list --jql "assignee = currentUser() AND resolution = Unresolved" --limit 20
```

Older/alternate style also appears in examples:

```sh
jira issue --list --project PROJ
jira issue --list --status "In Progress"
```

Agent guidance:

- Prefer `issue list` for the current command style.
- Always quote statuses and JQL containing spaces.
- Use `--limit` to avoid overly large output.
- Use JQL when the user asks for complex filtering, such as open bugs assigned to a team member, updated since a date, or unresolved issues in a project.

---

### `issue create`

Create a new issue.

```sh
jira issue create --project <key> --type <type> --summary <text> [options]
```

Required:

| Option | Description |
|---|---|
| `--project <key>` | Project key, e.g. `PROJ` |
| `--type <type>` | Issue type, e.g. `Bug`, `Story`, `Task` |
| `--summary <text>` | Issue summary/title |

Optional:

| Option | Description |
|---|---|
| `--description <text>` | Inline description |
| `--description-file <path>` | Read description from file |
| `--assignee <user>` | Assignee username/account value accepted by Jira |
| `--priority <level>` | Priority level |

Examples:

```sh
jira issue create --project PROJ --type Bug --summary "Login fails"

jira issue create --project PROJ --type Bug \
  --summary "Login fails" \
  --description "User cannot log in after submitting valid credentials."

jira issue create --project PROJ --type Story \
  --summary "Add payment retry feature" \
  --description-file ./feature-spec.md

jira issue create --project PROJ --type Bug \
  --summary "Critical checkout bug" \
  --description-file ./bug-report.md \
  --assignee john.doe \
  --priority High
```

Agent guidance:

- For multi-line content, write a temporary Markdown file and use `--description-file <path>`.
- Do not use both `--description` and `--description-file`.
- If the user gives only a vague request, ask for or infer project, issue type, and summary before creating.
- After creation, capture the returned issue key and URL.

---

### `issue edit <key>`

Edit an existing issue. Alias: `issue update`.

```sh
jira issue edit <key> [options]
```

At least one of these options is required:

| Option | Description |
|---|---|
| `--summary <text>` | New summary |
| `--description <text>` | New inline description |
| `--description-file <path>` | New description from file |
| `--assignee <user>` | New assignee |
| `--priority <level>` | New priority |

Examples:

```sh
jira issue edit PROJ-123 --summary "Updated summary"
jira issue edit PROJ-123 --assignee john.doe --priority High
jira issue edit PROJ-123 --description "Updated description"
jira issue edit PROJ-123 --description-file ./updated-spec.md
jira issue update PROJ-123 --priority Highest
```

Agent guidance:

- Inspect the issue first with `jira issue view <key> --format markdown` before making substantial edits.
- For description replacement, use `--description-file` to avoid shell quoting problems.
- This command updates fields, not workflow transitions. Do not claim it can move issues between statuses unless the CLI adds transition support.

---

### `issue delete <key>`

Delete an issue. Requires `--force`.

```sh
jira issue delete <key> --force
```

Example:

```sh
jira issue delete PROJ-123 --force
```

Agent guidance:

- Only use when the user explicitly requests deletion.
- Read the issue first and restate the issue key/summary before deletion when practical.
- Use `--force` only after clear user intent, because it bypasses confirmation.

---

### `issue comment add <key> [text]`

Add a comment to an issue. Alias group: `issue c`.

```sh
jira issue comment add <key> [text] [--file <path>] [--internal]
```

Examples:

```sh
jira issue comment add PROJ-123 "Review completed"

jira issue comment add PROJ-123 "Build status:
- Unit tests: passed
- Integration tests: passed
- Deployment: pending"

jira issue comment add PROJ-123 --file ./review-notes.md
jira issue comment add PROJ-123 "Internal note" --internal
jira issue c add PROJ-123 "Quick comment"
```

Agent guidance:

- For multi-line comments, prefer `--file <path>`.
- Do not use both direct text and `--file`.
- Use `--internal` only when the user asks for an internal/private team-visible comment and the Jira instance supports it.

---

### `issue comment list <key>`

List comments on an issue.

```sh
jira issue comment list <key> [--format table|json]
```

Examples:

```sh
jira issue comment list PROJ-123
jira issue comment list PROJ-123 --format json
jira issue c list PROJ-123
```

Agent guidance:

- Use `--format json` when extracting comment IDs or summarizing comment history.

---

### `issue comment edit <commentId> [text]`

Edit an existing comment by comment ID.

```sh
jira issue comment edit <commentId> [text] [--file <path>]
```

Examples:

```sh
jira issue comment edit 12345 "Updated comment text"
jira issue comment edit 12345 --file ./updated-notes.md
```

Agent guidance:

- First list comments with `jira issue comment list <key> --format json` to identify the correct comment ID.
- Do not use both direct text and `--file`.

---

### `issue comment delete <commentId>`

Delete a comment by comment ID. Requires `--force`.

```sh
jira issue comment delete <commentId> --force
```

Example:

```sh
jira issue comment delete 12345 --force
```

Agent guidance:

- Only use when the user explicitly requests deletion.
- First list comments and verify the target comment ID.

---

### `issue remote-link list <key>`

List remote links attached to an issue. Alias group: `issue rl`.

```sh
jira issue remote-link list <key> [--format table|json] [--global-id <id>]
```

Examples:

```sh
jira issue remote-link list PROJ-123
jira issue remote-link list PROJ-123 --format json
jira issue remote-link list PROJ-123 --global-id https://github.com/org/repo/pull/42
jira issue rl list PROJ-123
```

Agent guidance:

- Use `--format json` when extracting link IDs.
- Use `--global-id` to check whether a link already exists before adding it.

---

### `issue remote-link add <key>`

Attach an external resource to a Jira issue.

```sh
jira issue remote-link add <key> --url <url> --title <title> [options]
```

Required:

| Option | Description |
|---|---|
| `--url <url>` | External resource URL |
| `--title <title>` | Display title |

Optional:

| Option | Description |
|---|---|
| `--global-id <id>` | Stable identifier; useful for upsert behavior |
| `--relationship <rel>` | Relationship label, e.g. `relates to` |
| `--summary <text>` | Summary shown under the link title |
| `--icon-url <url>` | 16x16 icon URL |
| `--icon-title <title>` | Icon alt text |

Examples:

```sh
jira issue remote-link add PROJ-123 \
  --url https://github.com/org/repo/pull/42 \
  --title "org/repo#42"

jira issue remote-link add PROJ-123 \
  --url https://github.com/org/repo/pull/42 \
  --title "org/repo#42" \
  --global-id https://github.com/org/repo/pull/42 \
  --relationship "relates to"

jira issue rl add PROJ-123 --url https://example.com --title "Example"
```

Agent guidance:

- When linking GitHub PRs, CI jobs, dashboards, or docs, set `--global-id` equal to the stable URL to avoid duplicates and enable Jira upsert behavior.
- If a user asks to “link this PR to the Jira ticket,” use this command.

---

### `issue remote-link update <key> <linkId>`

Update an existing remote link.

```sh
jira issue remote-link update <key> <linkId> [options]
```

At least one option is required:

| Option | Description |
|---|---|
| `--url <url>` | New URL |
| `--title <title>` | New title |
| `--relationship <rel>` | New relationship |
| `--summary <text>` | New summary |
| `--icon-url <url>` | New icon URL |
| `--icon-title <title>` | New icon alt text |

Examples:

```sh
jira issue remote-link update PROJ-123 12345 --title "Updated title"
jira issue remote-link update PROJ-123 12345 --url https://example.com/new
```

Agent guidance:

- First list remote links with `--format json` to identify the target link ID.

---

### `issue remote-link delete <key> <linkId>`

Delete a remote link. Requires `--force`.

```sh
jira issue remote-link delete <key> <linkId> --force
```

Example:

```sh
jira issue remote-link delete PROJ-123 12345 --force
```

Agent guidance:

- Only use when the user explicitly requests deletion.
- First list remote links and verify the target link ID.

---

### `project list`

List Jira projects.

```sh
jira project list [--type <type>] [--category <category>]
```

Examples:

```sh
jira project list
jira project list --type software
jira project list --category Platform
```

---

### `project view <key>`

View project details.

```sh
jira project view <key>
```

Example:

```sh
jira project view PROJ
```

---

### `project components <key>`

List components for a project.

```sh
jira project components <key>
```

Example:

```sh
jira project components PROJ
```

---

### `project versions <key>`

List versions/releases for a project.

```sh
jira project versions <key>
```

Example:

```sh
jira project versions PROJ
```

---

### `sprint boards`

List available Jira boards.

```sh
jira sprint boards
```

Example:

```sh
jira sprint boards
```

Agent guidance:

- Run this first when the user asks about sprints but does not provide a board ID.

---

### `sprint list`

List sprints, usually for a specific board.

```sh
jira sprint list [--board <id>] [--state <state>] [--active]
```

Examples:

```sh
jira sprint list --board 123
jira sprint list --board 123 --state active
jira sprint list --board 123 --active
```

Agent guidance:

- Provide `--board <id>` when multiple boards exist.
- Use `--state active` or `--active` for current sprint-only queries.

---

### `sprint active`

List active sprints.

```sh
jira sprint active [--board <id>]
```

Example:

```sh
jira sprint active --board 123
```

---

## Common Agent Workflows

### Inspect a Jira issue

```sh
jira --no-color issue view PROJ-123 --format markdown
jira --no-color issue comment list PROJ-123 --format json
jira --no-color issue remote-link list PROJ-123 --format json
```

Use this before summarizing an issue, preparing an update, or deciding whether a remote link/comment already exists.

### Search assigned work

```sh
jira --no-color issue list --jql "assignee = currentUser() AND resolution = Unresolved" --limit 20
```

### Triage open bugs in a project

```sh
jira --no-color issue list \
  --jql "project = PROJ AND issuetype = Bug AND resolution = Unresolved ORDER BY priority DESC, updated DESC" \
  --limit 25
```

### Export an issue for local review

```sh
jira issue view PROJ-123 --format markdown --output ./PROJ-123.md
```

### Create an issue from a Markdown description

```sh
cat > /tmp/jira-description.md <<'MD'
## Problem
Describe the issue here.

## Expected Behavior
Describe the expected behavior here.

## Actual Behavior
Describe the actual behavior here.

## Evidence
- Logs:
- Screenshots:
MD

jira issue create --project PROJ --type Bug \
  --summary "Clear, specific bug summary" \
  --description-file /tmp/jira-description.md \
  --priority High
```

### Update an issue description safely

```sh
jira issue view PROJ-123 --format markdown --output /tmp/PROJ-123-before.md

cat > /tmp/PROJ-123-description.md <<'MD'
Updated description here.
MD

jira issue edit PROJ-123 --description-file /tmp/PROJ-123-description.md
```

### Add a review comment from a file

```sh
cat > /tmp/jira-comment.md <<'MD'
Review completed.

Findings:
- Item 1
- Item 2

Next step:
- Owner to confirm acceptance criteria.
MD

jira issue comment add PROJ-123 --file /tmp/jira-comment.md
```

### Link a GitHub PR to a Jira issue

```sh
jira issue remote-link add PROJ-123 \
  --url https://github.com/org/repo/pull/42 \
  --title "org/repo#42" \
  --global-id https://github.com/org/repo/pull/42 \
  --relationship "relates to"
```

### Check whether a PR link already exists

```sh
jira issue remote-link list PROJ-123 \
  --global-id https://github.com/org/repo/pull/42 \
  --format json
```

### Get current sprint status

```sh
jira sprint boards
jira sprint active --board 123
jira issue list --jql "sprint in openSprints() AND project = PROJ" --limit 50
```

### Build a daily standup summary

```sh
jira issue list --jql "assignee = currentUser() AND status = 'In Progress'" --limit 20
jira issue list --jql "assignee = currentUser() AND updated >= -1d" --limit 20
jira sprint active --board 123
```

---

## Agent Tips

- **Start with verification:** run `jira config --show` if the user reports auth/config problems.
- **Use `--no-color` or `NO_COLOR=1`** when output will be parsed by the agent.
- **Prefer JQL for non-trivial searches:** it is more precise than combining simple filters.
- **Limit search output:** use `--limit <n>` for every broad query.
- **Quote values with spaces:** statuses like `In Progress` and JQL strings must be quoted.
- **Use Markdown files for long content:** prefer `--description-file` and comment `--file` to avoid broken shell quoting.
- **Never print API tokens:** do not echo `JIRA_API_TOKEN`; use environment variables or secure config.
- **Inspect before mutation:** read the issue/comment/link before editing or deleting.
- **Treat destructive commands as explicit-only:** `issue delete`, `comment delete`, and `remote-link delete` require `--force`; only use them after clear user intent.
- **Remote-link deduplication:** use `--global-id` when adding links to stable external resources.
- **Board-first sprint workflow:** if no board ID is given, run `jira sprint boards` before sprint queries.
- **No workflow-transition command is documented in this CLI:** do not promise status transitions unless a newer CLI version adds a transition command.
- **Assignee identifiers vary by Jira instance:** use the username/account value accepted by that Jira instance; if assignment fails, ask the user for the exact Jira user identifier.
- **Use `JIRA_API_VERSION=auto` by default:** only pin v2 or v3 when troubleshooting compatibility.

## Safety Rules for Agents

- Read operations are safe: `issue view`, `issue list`, `comment list`, `remote-link list`, `project list/view`, `sprint boards/list/active`.
- Write operations require clear user intent: `issue create`, `issue edit`, `comment add`, `comment edit`, `remote-link add`, `remote-link update`.
- Destructive operations require explicit user intent and `--force`: `issue delete`, `comment delete`, `remote-link delete`.
- Do not infer deletion from vague wording like “clean up” or “remove noise” without confirming the exact issue/comment/link target.
- When creating or editing, include the exact issue key, project key, summary, and changed fields in your response.

## Error Patterns

| Error / Symptom | Likely Cause | Fix |
|---|---|---|
| `No configuration found` or auth-related startup failure | No config file or missing env vars | Set `JIRA_HOST` and `JIRA_API_TOKEN`, or run `jira config --server ... --token ...` |
| Authentication failure | Token, username, or host is wrong | Run `jira config --show`; verify token and host; add `JIRA_USERNAME` for Basic auth if required |
| Network error | Server URL, VPN, proxy, or company network issue | Check `JIRA_HOST`/server URL and network access |
| Permission error | Account lacks project/issue permission | Ask Jira admin or use an account with permission |
| Invalid issue key | Wrong key format or issue does not exist | Verify format like `PROJ-123`; search with `issue list` |
| Missing required create options | `issue create` lacks project/type/summary | Add `--project`, `--type`, and `--summary` |
| `Cannot use both --description and --description-file` | Both description inputs were provided | Use exactly one description source |
| `At least one field must be specified for update` | `issue edit` or `remote-link update` called with no change flags | Provide at least one supported field |
| `Description file not found` / `Path is not a file` / empty file | Bad `--description-file` or `--file` path | Check file path and content before running |
| Comment text is required | `comment add/edit` called with neither text nor `--file` | Provide direct text or `--file <path>` |
| Deletion requires `--force` | Delete command was called without force flag | Add `--force` only after explicit user intent |
| No issues found | Filters/JQL too narrow or wrong project/status | Broaden query, verify project key/status spelling |
| Multiple boards or missing board context | Sprint command lacks board ID | Run `jira sprint boards`, then rerun with `--board <id>` |
| ANSI escape codes in output | Colored terminal output | Add `--no-color` or set `NO_COLOR=1` |
