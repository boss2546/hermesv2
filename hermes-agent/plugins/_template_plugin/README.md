# 🧩 Template Plugin for Hermes Agent

This directory is the **official master template for creating custom plugins** in Hermes Agent.

---

## 📂 Directory Structure

```text
plugins/_template_plugin/
├── plugin.yaml       # 📋 Plugin manifest (Name, description, hooks, tools, commands)
├── __init__.py       # 🔌 Registration entry point (register(ctx))
├── plugin_logic.py   # 🧠 Core logic, schemas, and execution handlers
└── README.md         # 📖 Documentation & usage guide
```

---

## ⚡ How to Create a New Plugin

1. **Copy this folder** to a new name under `plugins/` or `~/.hermes/plugins/`:
   ```bash
   cp -r plugins/_template_plugin plugins/my-awesome-plugin
   ```
2. **Update `plugin.yaml`**:
   - Change `name`, `version`, `description`, `author`.
   - List the hooks, commands, or tools your plugin provides.
3. **Implement your logic in `plugin_logic.py` and `__init__.py`**:
   - Add tool schemas and functions.
   - Register commands via `ctx.register_command`.
   - Intercept events via `ctx.register_hook`.
4. **Test immediately**:
   - The plugin is automatically discovered and loaded by Hermes.
   - Test your slash command: `/my-awesome-plugin status`
   - Test your tool: `hermes -z "Use template_plugin_action with message 'hello world'"`

---

## 🌐 Publishing to GitHub / Marketplace

1. Create a GitHub repo (e.g. `github.com/your-user/hermes-plugin-mytool`).
2. Anyone can install it via:
   ```bash
   hermes plugins install your-user/hermes-plugin-mytool
   ```
