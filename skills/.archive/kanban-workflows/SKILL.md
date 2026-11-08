---
name: kanban-workflows
description: "Complete Kanban workflow management including orchestrator and worker patterns"
version: 0.1.0
author: Hermes Agent + Teknium
license: MIT
tags: [kanban, workflow, project-management, devops]
---

# Kanban Workflow Management

**Trigger:** Managing complete Kanban workflows including orchestrator roles, worker patterns, and project management.

This skill provides comprehensive guidance for implementing Kanban methodologies within the Hermes ecosystem with both orchestrator and worker roles.

## Overview

Hermes provides full support for Kanban workflow management through dedicated orchestrator and worker roles, enabling efficient project tracking and task execution.

## Kanban Orchestrator Patterns

### Decomposition Playbook

The orchestrator role focuses on decomposition and anti-temptation rules:

1. **Don't do the work yourself**: Delegate specific tasks to workers
2. **Process decomposition**: Break large tasks into manageable components  
3. **Anti-temptation rules**: Prevent scope creep and task diversion

### Orchestrator Responsibilities

Orchestrator profiles in Hermes include:

- **Task routing**: Directing work to appropriate workers based on expertise
- **Process enforcement**: Ensuring Kanban lifecycle is maintained  
- **Workflow optimization**: Identifying bottlenecks and inefficiencies
- **Resource allocation**: Managing team capacity and availability

## Kanban Worker Patterns

### Edge Cases and Pitfalls

Worker roles focus on specific task execution with attention to edge cases:

1. **Lifecycle awareness**: Understanding when tasks enter and exit workflows
2. **Error handling**: Gracefully managing task failures and rework
3. **State synchronization**: Keeping workflow state consistent

### Worker Best Practices

Kanban workers in Hermes follow these principles:

- **Task-specific focus**: Concentrate on individual task completion
- **Quality standards**: Maintain consistent quality across all work
- **Feedback loops**: Provide timely status updates and issue reports

## Workflow Implementation

### Basic Kanban Lifecycle

Hermes automates the standard Kanban workflow:

1. **Backlog**: Task collection and prioritization
2. **Ready**: Tasks prepared for work  
3. **In Progress**: Active task execution
4. **Review**: Quality checks and feedback
5. **Done**: Final task completion and handoff

### Integration Patterns

Hermes integrates with various tools:

- **GitHub Issues**: Direct task creation and tracking
- **Jira**: Enterprise-level project management integration  
- **Slack**: Real-time status updates and notifications

## Advanced Kanban Patterns

### Orchestrator Deep Dive

The orchestrator skill includes:

- **Decomposition playbook**: Detailed guidelines for breaking down complex problems
- **Anti-temptation rules**: Preventing common workflow distractions
- **Role-specific system prompts**: Auto-injected into every worker's system prompt

### Worker Deep Dive

Worker patterns focus on:

- **Lifecycle detail**: Specific examples and edge cases for each workflow stage
- **Task-specific guidance**: Detailed instructions for different task types
- **Performance metrics**: Tracking worker efficiency and output quality

## Configuration and Setup

### Orchestrator Profile Setup

```yaml
# Example orchestrator configuration
kanban:
  role: orchestrator
  workflow: "decomposition-first"
  anti_temptation_rules:
    - "Don't implement solutions yourself"
    - "Always delegate to specialists when appropriate"
```

### Worker Profile Setup

```yaml
# Example worker configuration  
kanban:
  role: worker
  workflow: "standard"
  lifecycle: "auto-injected"
```

## Best Practices

### For Orchestrators

1. **Maintain focus**: Stay focused on the bigger workflow picture
2. **Delegate effectively**: Match tasks to appropriate specialists  
3. **Monitor capacity**: Ensure team workload remains balanced

### For Workers

1. **Follow lifecycle**: Maintain proper task progression
2. **Communicate status**: Provide regular updates on progress
3. **Handle errors**: Report and resolve issues promptly

## Related Skills

- `kanban-orchestrator` - Deep playbook for orchestrator roles
- `kanban-worker` - Detailed guidance for worker patterns and edge cases

## References

- `references/kanban-decomposition-patterns.md` - Decomposition strategies for complex problems
- `templates/kanban-workflow-config.yaml` - Starter configuration templates