# Claude Code Configuration Files

This folder contains all Claude Code configurations for the Endemic Grant Agent project.

## Files in this Directory

### mcp-config.json
Contains the MCP (Model Context Protocol) server configurations, including:
- Notion MCP server configuration
- Any other MCP servers added to the project

### How Claude Code Uses These Files

Claude Code looks for configuration files in specific locations:
1. **Project-level**: `.mcp.json` in the project root (hidden file)
2. **Global-level**: `~/.claude.json` in your home directory (hidden file)

To ensure Claude Code recognizes our visible configurations, we maintain symbolic links:
- `.mcp.json` → `claude-config/mcp-config.json`

## Current MCP Servers

### Notion Server
- **Type**: HTTP/stdio hybrid
- **Account**: zacharyschlosser@gmail.com
- **Purpose**: Integrates with Notion workspace for grant management
- **Commands**: Access via `npx @notionhq/notion-mcp-server`

## Managing Configurations

### To Add New MCP Servers
```bash
claude mcp add <server-name> "<command>"
```

### To List MCP Servers
```bash
claude mcp list
```

### To Remove MCP Servers
```bash
claude mcp remove <server-name>
```

## Important Notes

- Always restart Claude Code after modifying MCP configurations
- First-time use of Notion commands will prompt for authorization
- Configurations in this visible folder are linked to Claude's expected hidden locations