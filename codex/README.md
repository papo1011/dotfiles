# Codex

Personal Codex configuration, linked to `~/.codex/config.toml`.

## Configuration

`config.toml` contains the current configuration, including model preferences,
trusted projects, plugins, desktop appearance, and local integrations.
It sets "Approve for me" as the default for eligible approval
requests. Codex works within the workspace sandbox and sends requests for
additional permissions to an automatic reviewer, which can approve or deny them.

## Installation

From the root of this repository, back up any existing configuration and create
the symlink:

```sh
mkdir -p "$HOME/.codex"
if [ -e "$HOME/.codex/config.toml" ] || [ -L "$HOME/.codex/config.toml" ]; then
    mv "$HOME/.codex/config.toml" "$HOME/.codex/config.toml.backup-$(date +%Y%m%d-%H%M%S)"
fi
ln -s "$PWD/codex/config.toml" "$HOME/.codex/config.toml"
```

The configuration includes absolute paths specific to this Mac. Review those
paths before using it on another machine. Changes made through the symlink also
update the file in this repository; review the diff before committing.

Restart Codex and open a new conversation to use the updated defaults.
Managed settings or explicit session overrides may take precedence.

## Scope

Keep credentials, session history, caches, and other runtime state in
`~/.codex/`, outside this repository. Shared skills remain in `../agents/skills/`.

See the [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
for supported settings.
