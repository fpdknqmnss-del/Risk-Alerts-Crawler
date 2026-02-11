---
name: subagent-coordination
description: Coordinate parallel subagents to prevent race conditions, file conflicts, and state corruption. Use when launching multiple subagents, planning parallel task execution, or orchestrating complex multi-step workflows with the Task tool.
---

# Subagent Coordination

## Before Launching Parallel Subagents

Build a dependency map:

1. For each planned subagent, list:
   - Files it will READ
   - Files it will WRITE
   - System resources it will use (git, npm, build, test runner)
2. Check for conflicts:
   - WRITE-WRITE conflict: Two subagents write the same file -> run sequentially
   - READ-WRITE conflict: One reads what another writes -> run reader after writer
   - RESOURCE conflict: Two use the same system resource with side effects -> run sequentially
3. Only parallelize subagents with zero conflicts

## Safe Parallel Patterns

These are safe to run in parallel:
- Multiple explore subagents reading different parts of the codebase
- One subagent editing frontend files + another editing backend files (no shared files)
- One subagent writing code + another researching documentation (read-only)

## Unsafe Parallel Patterns

Never run these in parallel:
- Two subagents editing the same file
- A subagent reading a file while another writes to it
- Multiple subagents running git commands
- Multiple subagents installing dependencies
- Two subagents running builds that output to the same directory

## Post-Parallel Verification

After all parallel subagents complete:
1. Check that no file was left in a partial or inconsistent state
2. Re-read any files that were modified to confirm expected state
3. Run linting on all modified files
4. If anything looks wrong, fix sequentially before proceeding

## Sequential Fallback

When in doubt, run sequentially. The cost of a race condition bug is much higher than the time saved by parallelization.
