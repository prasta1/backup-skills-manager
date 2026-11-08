#!/bin/bash
# Calendar wrapper for cron jobs and manual use
# Shows events from "Lynds / Patrick - Busy Things" calendar by default

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3 -W ignore"

# Calendar ID for "Lynds / Patrick - Busy Things"
BUSY_THINGS_CAL="fcnhb05jqcj16pktf3v4s1v1ss@group.calendar.google.com"

# Function to list events
list_events() {
    local max=${1:-10}
    $PYTHON_CMD "$SCRIPT_DIR/simple_calendar.py" list --max $max
}

# Function to list all calendars
list_calendars() {
    $PYTHON_CMD "$SCRIPT_DIR/simple_calendar.py" calendars
}

# Function to list events from specific calendar
list_calendar() {
    local cal_id=$1
    local max=${2:-10}
    $PYTHON_CMD "$SCRIPT_DIR/simple_calendar.py" list --calendar "$cal_id" --max $max
}

# If script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "$1" in
        list)
            list_events "${2:-10}"
            ;;
        calendars)
            list_calendars
            ;;
        *)
            echo "Usage: $0 {list|calendars} [args]"
            echo "  list [max]         - List events from busy things calendar (default: 10)"
            echo "  calendars          - List all available calendars"
            exit 1
            ;;
    esac
fi