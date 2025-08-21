# Notion MCP Server Setup Guide

## Installation Complete ✅

The Notion MCP server has been installed for the Endemic Grant Agent project.

## Next Steps

1. **Restart Claude Code** or start a new conversation to activate the MCP server

2. **Authorize Notion Access**:
   - When you first use a Notion command, you'll be prompted to authorize
   - Login with your Notion account: zacharyschlosser@gmail.com
   - Grant permissions to the pages/databases you want the agent to access

3. **Test the Integration**:
   Try commands like:
   - "Search Notion for grant templates"
   - "Create a new page in Notion for Templeton Foundation research"
   - "Get the list of funders from my Notion database"

## Common Notion Commands for Grant Writing

### Research & Templates
- "Find all pages in Notion related to [funder name]"
- "Get the grant proposal template from Notion"
- "Search for past successful proposals in Notion"

### Creating Content
- "Create a new Notion page for [funder] grant application"
- "Add this research to the [funder] page in Notion"
- "Save this proposal draft to Notion"

### Database Operations
- "Get all entries from the funders database"
- "Add a new funder to the grants tracking database"
- "Update the status of [grant] in the applications database"

## Troubleshooting

If Notion commands aren't working:
1. Check that you've restarted Claude Code
2. Ensure you've authorized the integration
3. Verify the pages/databases are shared with the integration
4. Try `claude mcp list` to confirm installation

## Configuration File

The MCP server configuration is stored in:
`/Users/home/Desktop/Endemic Grant Agent/.mcp.json`