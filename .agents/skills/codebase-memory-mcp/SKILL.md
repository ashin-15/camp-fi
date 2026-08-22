---
name: codebase-memory-mcp
description: Navigates and explores codebases using codebase-memory-mcp knowledge graph. Use when exploring architecture, finding symbols, tracing call graphs, reading functions/classes, and investigating impact without wasting tokens on broad grep/glob or full-file scans.
---

# Codebase Memory MCP Navigation

## Overview

Traditional code search tools (`grep`, `glob`, reading whole files) waste significant context window tokens by returning line noise, comments, irrelevant matches, and multi-hundred-line files when only a 15-line function is needed. 

`codebase-memory-mcp` maintains a persistent AST knowledge graph (Nodes: Function, Method, Class, Module, File, Variable; Edges: CALLS, IMPORTS, DEFINES, USAGE, TESTS). Navigating through the graph allows surgical exploration with minimal token consumption.

---

## Tool Priority & Selection Matrix

| Goal | MCP Tool | Arguments / Pattern |
| :--- | :--- | :--- |
| **Understand Architecture** | `get_architecture` | `{"project": "<project>"}` |
| **Find Symbol / Function / Class** | `search_graph` | `{"project": "<project>", "query": "..."}` or `name_pattern` |
| **Trace Callers (Who calls this?)** | `trace_path` | `{"project": "<project>", "function_name": "...", "direction": "inbound"}` |
| **Trace Callees (What does this call?)** | `trace_path` | `{"project": "<project>", "function_name": "...", "direction": "outbound"}` |
| **Read Specific Implementation** | `get_code_snippet` | `{"project": "<project>", "qualified_name": "..."}` |
| **Graph-Augmented Regex Search** | `search_code` | `{"project": "<project>", "pattern": "..."}` |
| **Complex Multi-Hop Relations** | `query_graph` | `{"project": "<project>", "query": "MATCH ... RETURN ..."}` |
| **Impact Analysis Before/After Edit** | `detect_changes` | `{"project": "<project>"}` |
| **List Available Projects** | `list_projects` | `{}` |

---

## When to Use Graph vs Fallbacks

```
Task: Locate or Understand Code
├── Is it code structure (function, class, caller, callee, architecture)?
│   └── YES → ALWAYS use codebase-memory-mcp tools (search_graph, trace_path, get_code_snippet)
└── Is it non-code text or specific literals?
    ├── Searching configs (.yaml, .json, .toml, .env) → read / grep
    ├── Searching exact string literals / UI labels / error messages → search_code or grep
    └── Searching documentation (.md) → read / grep
```

---

## Step-by-Step Navigation Playbooks

### Playbook 1: Zero-to-Architecture in a New Repo
1. **Identify Project**: Call `list_projects` to find the exact project slug (e.g. `home-ashin-Projects-wifi-auther`).
2. **Overview**: Call `get_architecture(project="<project>")` to view:
   - Packages and layers (`core`, `leaf`, `entry`).
   - Architectural clusters and hot spots (high fan-in symbols).
   - Key boundaries and file tree.

### Playbook 2: Finding and Inspecting a Symbol
1. **Locate**:
   ```json
   {
     "project": "home-ashin-Projects-wifi-auther",
     "name_pattern": ".*run_daemon.*"
   }
   ```
   *(or use `"query": "daemon loop"` for natural language semantic search)*
2. **Read Exact Snippet**:
   Pass the returned `qualified_name` directly to `get_code_snippet`:
   ```json
   {
     "project": "home-ashin-Projects-wifi-auther",
     "qualified_name": "home-ashin-Projects-wifi-auther.src.camp_fi.daemon.run_daemon"
   }
   ```
   *Benefit: Reads only the target function source, complexity, and signature without loading the whole file.*

### Playbook 3: Tracing Inbound & Outbound Call Chains
1. **Who calls this function? (Inbound)**:
   ```json
   {
     "project": "home-ashin-Projects-wifi-auther",
     "function_name": "run_daemon",
     "direction": "inbound"
   }
   ```
2. **What does this function depend on? (Outbound)**:
   ```json
   {
     "project": "home-ashin-Projects-wifi-auther",
     "function_name": "run_daemon",
     "direction": "outbound"
   }
   ```

### Playbook 4: Cypher Query Recipes (`query_graph`)

Use `query_graph` for fast multi-hop structural queries:

#### Find all entry points and what they call
```cypher
MATCH (f:Function {is_entry_point: true})-[r:CALLS]->(target)
RETURN f.name, target.name, target.file_path
```

#### Find high fan-in functions (hotspots)
```cypher
MATCH (caller)-[:CALLS]->(f:Function)
RETURN f.name, f.file_path, count(caller) AS callers
ORDER BY callers DESC
LIMIT 10
```

#### Find all methods belonging to a specific class
```cypher
MATCH (c:Class {name: "DaemonState"})-[:DEFINES_METHOD]->(m:Method)
RETURN m.name, m.start_line, m.end_line, m.signature
```

#### Find tests covering a specific function
```cypher
MATCH (t:Function)-[:TESTS|CALLS]->(f:Function {name: "run_daemon"})
RETURN t.name, t.file_path
```

---

## Token Efficiency: Anti-Patterns vs Best Practice

| Scenario | Anti-Pattern (Token Heavy ❌) | Graph Memory Best Practice (Token Lean ✅) |
| :--- | :--- | :--- |
| **Locating a function** | Grepping across repo (dumps 50+ lines of matches & false positives) | `search_graph(name_pattern=".*func.*")` $\rightarrow$ 1 concise JSON result |
| **Reading logic** | `read(file.py)` loading 500 lines into context | `get_code_snippet(qualified_name="...")` $\rightarrow$ only the 20 lines needed |
| **Checking callers** | Grepping function name, sorting through comments/imports | `trace_path(function_name="...", direction="inbound")` $\rightarrow$ exact caller list |
| **Change Impact** | Manually inspecting files for references | `detect_changes(project="...")` $\rightarrow$ calculates impacted symbol graph |

---

## Verification Checklist

Before using file-wide search or full reads:
- [ ] Checked if project is indexed via `list_projects`
- [ ] Used `search_graph` for symbol discovery instead of `grep`
- [ ] Used `get_code_snippet` for reading specific functions instead of reading entire source files
- [ ] Used `trace_path` to find callers/callees instead of manual call-site grep
- [ ] Used `detect_changes` to evaluate impact before modifying shared symbols
