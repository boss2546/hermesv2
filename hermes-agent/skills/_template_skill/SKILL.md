---
name: template-skill-name
description: "Perform concise action and generate verified outputs."
version: 1.0.0
author: Boss (ratchanon2003), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: software-development
    tags: [template, workflow, automation, guide]
    related_skills: [hermes-agent-skill-authoring]
    config:
      api_key_name: "skills.config.template_api_key"
---

# Template Skill Name

## Overview

A brief 2–3 sentence overview of the skill. Clearly explain what capability this skill provides, the high-level workflow it establishes, and what it deliberately does NOT do (scope boundaries).

## When to Use

- When the user asks to perform [Target Workflow A].
- When you need to automate or standardize [Specific Task B].
- When handling multi-step processes involving [Components / APIs C].
- **Don't use for:** 
  - Simple one-off questions that require no workflow.
  - Tasks covered more directly by sibling skills (e.g., use `hermes-agent-skill-authoring` for authoring in-repo Hermes skills).

## Prerequisites

- **Required Environment Variables:**
  - `MY_API_KEY`: API authentication key (configured via `~/.hermes/.env` or runtime environment).
- **Required Tools / Dependencies:**
  - Native Hermes tools: `terminal`, `read_file`, `write_file`, `patch`, `search_files`, `web_search`, `web_extract`.
  - External CLIs (if any): `curl`, `jq`, `git` (ensure they are available in PATH).
- **MCP Servers (if applicable):**
  - If using an MCP server, specify the server name and setup command.

## How to Run

Reference native Hermes tools or helper scripts using clean invocations:

```bash
# Example 1: Running the bundled Python helper script
terminal(command="python skills/<category>/<skill-name>/scripts/helper_script.py --input data.json")

# Example 2: Inspecting output files
read_file(path="output/result.json")
```

## Quick Reference

| Action / Goal | Command / Tool Call | Notes |
|---|---|---|
| Step 1: Initialize | `terminal(command="...")` | Checks environment and readiness |
| Step 2: Process | `read_file(path="...")` | Reads input payload |
| Step 3: Transform | `write_file(path="...", ...)` | Writes structured output |
| Step 4: Validate | `terminal(command="pytest ...")` | Verifies execution correctness |

## Procedure

Follow these sequential steps with checkable completion criteria:

### Step 1: Pre-flight & Discovery
1. Verify required environment variables and dependencies.
2. Read project context or input files using `read_file` or `search_files`.
3. *Completion criterion:* Environment confirmed; all required input files located.

### Step 2: Execution & Transformation
1. If helper scripts exist under `scripts/`, invoke them via `terminal` rather than hallucinating large boilerplate logic.
2. If working with templates, load the base from `templates/` and customize parameters.
3. *Completion criterion:* Target operation executed with exit code 0 or successful tool response.

### Step 3: Verification & Output Generation
1. Validate outputs against schema or expected assertions.
2. Present a clear, structured summary to the user.
3. *Completion criterion:* All changes saved and verified without regressions.

## Supporting Files

When building complex skills, split large domain knowledge and scripts into subdirectories:

- `references/`: Deep documentation, cheat sheets, and API specifications (e.g. `references/api-cheatsheet.md`).
- `templates/`: Boilerplate configuration files, code skeletons, or starter templates (e.g. `templates/sample-config.yaml`).
- `scripts/`: Deterministic Python or shell helper scripts (e.g. `scripts/helper_script.py`).

## Pitfalls

1. **POSIX-only primitives:** Avoid hardcoding `/tmp`, `fcntl`, `os.killpg`, or bash-only pipelines unless `platforms:` is gated to `[linux, macos]`.
2. **Long description in frontmatter:** Keep `description` $\le 60$ characters, 1 sentence ending with a period.
3. **Machine-local paths:** Never hardcode absolute paths like `/Users/meuu/...` in committed skills. Always use relative or environment-derived paths.
4. **Tool names in prose:** Reference native tools in backticks (`terminal`, `read_file`, `write_file`, `patch`, `search_files`), never raw CLI commands like `cat`, `grep`, or `sed`.

## Verification Checklist

- [ ] Frontmatter starts at line 1 with `---` and ends with `---`.
- [ ] Description is $\le 60$ characters, single sentence, ends with `.`.
- [ ] All required sections present (`When to Use`, `Prerequisites`, `How to Run`, `Procedure`, `Pitfalls`, `Verification`).
- [ ] Helper scripts in `scripts/` tested with cross-platform Python.
- [ ] Tested via Hermes agent invocation.
