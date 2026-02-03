# Faraday Operations

Manage Faraday vulnerability management - import results, check status, list workspaces.

## Arguments

- `status` - Check Faraday connection status
- `import` - Import pending results from results/ directory
- `import --dry-run` - Show what would be imported without importing
- `workspaces` - List all Faraday workspaces
- `list` - List result files and their import status

## Instructions

Based on the argument provided:

### For `status`:
```bash
cd /opt/bojemoi/samsonov/pentest_orchestrator && python3 -c "
from plugins.plugin_faraday import get_status
import json
print(json.dumps(get_status(), indent=2))
"
```

### For `import`:
```bash
cd /opt/bojemoi/samsonov/pentest_orchestrator && python3 import_results.py
```

### For `import --dry-run`:
```bash
cd /opt/bojemoi/samsonov/pentest_orchestrator && python3 import_results.py --dry-run
```

### For `workspaces`:
```bash
cd /opt/bojemoi/samsonov/pentest_orchestrator && python3 -c "
from plugins.plugin_faraday import list_workspaces
import json
print(json.dumps(list_workspaces(), indent=2))
"
```

### For `list`:
```bash
cd /opt/bojemoi/samsonov/pentest_orchestrator && python3 import_results.py --list-all
```

### If no argument or `help`:
Show available commands:
- `/faraday status` - Check connection to Faraday
- `/faraday import` - Import pending scan results
- `/faraday import --dry-run` - Preview import without executing
- `/faraday workspaces` - List all workspaces
- `/faraday list` - List result files

## Output Format

Present results clearly with:
- Connection status (connected/disconnected)
- Number of workspaces or results
- Any errors encountered
