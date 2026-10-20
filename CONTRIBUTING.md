# Adding a tool to MyDesk

Every MyDesk tool is a plain Python script plus a small `tool.json`. MyDesk reads the JSON to put the tool in a section and build its form; the script does the work and can always be run on its own.

## 1. Copy the template

```
tools/_template  ->  tools/<your_tool_id>
```

Use lowercase and underscores for the folder name, e.g. `tools/resume_builder`. Folders starting with `_` are ignored.

## 2. Fill in `tool.json`

```json
{
  "id": "resume_builder",
  "name": "Resume Builder",
  "section": "junkyard",
  "script": "resume_builder.py",
  "description": "One sentence shown on the tile and as a tooltip.",
  "run_label": "Build",
  "inputs": [
    {"name": "profile", "label": "LinkedIn profile link", "type": "url", "positional": true, "required": true},
    {"name": "style", "label": "Style", "type": "select", "options": [["modern", "Modern"], ["classic", "Classic"]], "default": "modern"},
    {"name": "pdf", "label": "Also export PDF", "type": "checkbox"}
  ],
  "outputs": {"glob": "resumes/*.md", "label": "Saved resumes", "empty": "No resumes yet."}
}
```

| Key | Meaning |
| --- | --- |
| `section` | One of the ids in `sections.json`: `os_monitor`, `my_finance`, `my_events`, `my_social`, `my_chest`, `junkyard`, `my_mirror`, `my_block` |
| `inputs[].type` | `text`, `url`, `select` or `checkbox` |
| `inputs[].positional` | Passed as a bare argument instead of `--name value` |
| `outputs.glob` | Markdown files (inside the tool's data folder) to list in the tool's library. Front-matter keys `title`, `platform`, `captured`, `cover` and `video` are used for the cards and viewer |

The form above becomes the command `python resume_builder.py <profile> --style modern --pdf --out data/resume_builder --events`.

## 3. Write the script

MyDesk always adds `--out <data folder>` and `--events`. With `--events`, report progress by printing JSON lines that start with `@@`:

```python
print('@@{"event": "progress", "msg": "Reading profile"}', flush=True)
print('@@{"event": "result", "msg": "Saved resume", "open": "resumes/manoj.md"}', flush=True)
print('@@{"event": "error", "msg": "Profile is private"}', flush=True)  # then exit non-zero
```

`open` is a path (relative to the data folder) that MyDesk shows right after the run. The template has `say()`, `finish()` and error handling already wired up.

## 4. Try it

```
run_tool list
run_tool resume_builder "https://linkedin.com/in/..."
```

Restart MyDesk and the tool appears in its section's hover menu. Run `python -m unittest discover tests` before opening a pull request — it checks every tool's `tool.json` points at a real section and script.

## Guidelines

- Put new Python packages in `requirements.txt`, with a comment saying which tool needs them.
- Never commit personal data, cookies or API keys. Read keys from environment variables.
- Save outputs only under the `--out` folder you're given.
