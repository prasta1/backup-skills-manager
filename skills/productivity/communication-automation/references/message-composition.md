# Message Composition (MML)

Himalaya uses a simple message markup language for composing emails with templates.

## Piping stdin for non-interactive sending

```bash
himalaya -a gmail template send --to user@domain --subject "Hello" < body.txt
```

## Template syntax

Templates use Go template syntax. Variables are passed with `--template-vars`.

## Full reference

See the Himalaya documentation for MML (Message Markup Language) syntax.