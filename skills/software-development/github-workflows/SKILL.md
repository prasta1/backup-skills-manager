---
name: github-workflows
description: "Complete GitHub workflow management including authentication, code review, issues, PRs, and repository operations"
version: 0.1.0
author: Hermes Agent + Teknium
license: MIT
tags: [github, ci/cd, workflows, automation]
---

# GitHub Workflow Management

**Trigger:** Managing complete GitHub workflows including authentication, code review, issue tracking, pull request lifecycle, and repository operations.

This skill provides comprehensive guidance for managing all aspects of GitHub workflows within the Hermes ecosystem.

## Overview

Hermes integrates with GitHub to provide full automation capabilities for software development workflows. This skill covers the complete spectrum of GitHub operations from authentication to repository management.

## GitHub Authentication

### Setup Process

Hermes supports both HTTPS tokens and SSH keys for secure GitHub authentication:

```bash
# Setup HTTPS token (recommended for automation)
gh auth login --with-token < <token>

# Setup SSH keys for local development
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
ssh-add ~/.ssh/id_rsa
gh auth login --with-ssh
```

### Credentials Management

When using `gh` CLI, credentials are automatically managed through the GitHub CLI configuration system.

## Code Review Workflows

### Pull Request Reviews

Hermes can automate code reviews with:

1. **Automated checks**: Static analysis, security scanning, and quality gates
2. **Inline comments**: Direct feedback on code changes
3. **Status updates**: Continuous integration status reporting

### Review Configuration

```yaml
# Example review configuration in .github/review.yml
rules:
  - name: "Security scan"
    enabled: true
    severity: high
  - name: "Code quality"
    enabled: true
    severity: medium
```

## Issue Management

### Creating and Triaging Issues

Hermes can automatically create, triage, and assign GitHub issues:

```bash
# Create new issue with labels
gh issue create --title "Bug in authentication flow" --body "Users report login failures" --label bug,authentication
```

### Issue Classification

- **Bug reports**: Issues that indicate system malfunctions
- **Feature requests**: New capabilities or enhancements requested
- **Documentation**: Updates to documentation or examples

## Pull Request Management

### PR Lifecycle

Hermes automates the complete PR lifecycle:

1. **Branch creation**: Automated feature branch setup
2. **Commit management**: Ensuring proper commit messages and structure
3. **CI integration**: Running tests on every commit
4. **Merge preparation**: Ensuring all checks pass before merge

### PR Configuration Example

```yaml
# .github/pr.yml
pr:
  required_checks:
    - ci
    - security_scan
    - code_quality
  auto_merge:
    when: all_checks_passed
```

## Repository Operations

### Clone/Create/Fork Repositories

Hermes supports full repository management:

```bash
# Clone a repository
gh repo clone owner/repo

# Create a new repository
gh repo create my-new-repo --public

# Fork an existing repository  
gh repo fork owner/repo
```

### Remote Management

```bash
# Add remote to existing repository
git remote add upstream https://github.com/owner/repo.git

# Manage multiple remotes for collaboration
git remote set-url origin https://github.com/yourname/repo.git
```

## Release Management

### Creating and Managing Releases

Hermes can automate release processes:

```bash
# Create a new release
gh release create v1.0.0 --title "Version 1.0.0" --notes "Release notes here"

# Update existing release
gh release edit v1.0.0 --title "Version 1.0.1" --notes "Bug fixes"
```

## Best Practices

### Security Considerations

- Use personal access tokens with minimal required scopes
- Implement proper secret management for CI/CD pipelines
- Regularly rotate authentication credentials

### Performance Optimization

- Enable GitHub Actions caching for faster builds
- Use branch protection rules to prevent unwanted changes
- Implement automated testing before PR merges

## Related Skills

- `github-auth` - GitHub authentication setup and configuration
- `github-code-review` - Automated code review workflows  
- `github-issues` - Issue creation and management
- `github-pr-workflow` - Pull request lifecycle automation
- `github-repo-management` - Repository operations and management

## References

- `references/github-authentication-best-practices.md` - Authentication security guidelines
- `references/pr-lifecycle-checklist.md` - Complete PR workflow checklist
- `templates/github-workflow-config.yaml` - Starter workflow configuration template