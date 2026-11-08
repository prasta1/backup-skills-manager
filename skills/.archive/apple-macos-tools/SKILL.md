---
name: apple-macos-tools
description: "Comprehensive management of Apple macOS tools and services"
version: 0.1.0
author: Hermes Agent + Teknium
license: MIT
tags: [apple, macos, notes, reminders, findmy, imessage]
---

# Apple macOS Tools

**Trigger:** Managing various Apple macOS tools including Notes, Reminders, FindMy, iMessage, and desktop automation.

This skill provides comprehensive guidance for working with Apple's ecosystem on macOS systems through command-line interfaces and automation.

## Overview

Hermes provides integration with various Apple macOS tools, allowing users to automate and manage their Apple ecosystem workflows through command-line interfaces.

## Apple Notes Management

### Creating and Editing Notes

Hermes integrates with Apple Notes via the memo CLI:

```bash
# Create a new note
memo create "Meeting Notes - Q3 Planning"

# Search for notes
memo search "Q3"

# Edit a note by ID
memo edit 12345 "Updated meeting notes"
```

### Note Organization

Notes can be organized using:
- Tags for categorization
- Folders for hierarchical organization  
- Smart folders for automatic filtering

## Apple Reminders Management

### Creating and Managing Reminders

Hermes integrates with Apple Reminders via the remindctl:

```bash
# Add a new reminder
remindctl add "Buy groceries" --due "2026-05-25 18:00"

# List all reminders
remindctl list

# Complete a reminder
remindctl complete 12345
```

### Reminder Organization

Reminders can be organized by:
- Lists (e.g., "Personal", "Work")
- Due dates and priorities
- Completion status

## FindMy Device Tracking

### Tracking Apple Devices and AirTags

Hermes integrates with FindMy.app to track Apple devices and AirTags:

```bash
# List tracked devices
findmy list

# Locate a specific device
findmy locate "Mac Studio"

# Get location status
findmy status "iPhone 15"
```

### Device Management

FindMy provides:
- Real-time location tracking
- Distance-based alerts
- Lost device protection features

## iMessage and SMS Automation

### Sending and Receiving Messages

Hermes integrates with iMessage/SMS via the imsg CLI:

```bash
# Send an iMessage
imsg send "+1234567890" "Hello from Hermes!"

# Receive messages (requires setup)
imsg receive
```

### Message Management

iMessage integration supports:
- Text messaging to contacts
- Group messaging capabilities
- Message history management

## macOS Desktop Automation

### Computer Use Integration

Hermes provides desktop automation capabilities:

```bash
# Take screenshot
computer_use screenshot

# Simulate mouse clicks
computer_use click 100 200

# Simulate keyboard input  
computer_use type "Hello World"
```

### Background Operations

Hermes can drive macOS desktop operations in the background:

- Screenshots without stealing focus
- Mouse and keyboard automation 
- Scroll and drag operations
- Window management

## Best Practices

### Privacy Considerations

- Ensure proper permissions are granted for Apple services
- Be mindful of location tracking data collection
- Secure authentication credentials for Apple services

### Performance Optimization

- Use efficient command patterns to minimize system overhead
- Cache frequently accessed data from Apple services
- Implement proper error handling for service interruptions

## Related Skills

- `apple-notes` - Apple Notes management via memo CLI
- `apple-reminders` - Apple Reminders via remindctl  
- `findmy` - Apple device tracking via FindMy.app
- `imessage` - iMessage/SMS automation via imsg CLI
- `macos-computer-use` - macOS desktop automation capabilities

## References

- `references/apple-notes-best-practices.md` - Notes organization and management guidelines
- `references/reminders-automation-patterns.md` - Reminder workflow automation patterns
- `templates/imessage-config.yaml` - iMessage configuration template