---
name: agentmail
description: Give AI agents their own email inboxes using the AgentMail API. Use when building email agents, sending/receiving emails programmatically, managing inboxes, handling attachments, organizing with labels, creating drafts for human approval, or setting up real-time notifications via webhooks/websockets. Supports multi-tenant isolation with pods.
license: MIT
metadata:
  author: agentmail-to
  version: "1.0"
---

# AgentMail SDK

AgentMail is an API-first email platform for AI agents. Install the SDK and initialize the client.

## Installation

```bash
# TypeScript/Node
npm install agentmail

# Python
pip install agentmail
```

## Setup

```typescript
import { AgentMailClient } from "agentmail";
const client = new AgentMailClient({ apiKey: "YOUR_API_KEY" });
```

```python
from agentmail import AgentMail
client = AgentMail(api_key="YOUR_API_KEY")
```

## Inboxes

Create scalable inboxes on-demand. Each inbox has a unique email address.

```typescript
// Create inbox (auto-generated address)
const autoInbox = await client.inboxes.create();

// Create with custom username and domain
const customInbox = await client.inboxes.create({
  username: "support",
  domain: "yourdomain.com",
});

// List, get, delete
const inboxes = await client.inboxes.list();
const fetchedInbox = await client.inboxes.get("inbox@agentmail.to");
await client.inboxes.delete("inbox@agentmail.to");
```

```python
# Create inbox (auto-generated address)
inbox = client.inboxes.create()

# Create with custom username and domain
from agentmail.inboxes.types import CreateInboxRequest
inbox = client.inboxes.create(
  request=CreateInboxRequest(username="support", domain="yourdomain.com"),
)

# List, get, delete
inboxes = client.inboxes.list()
inbox = client.inboxes.get(inbox_id="inbox@agentmail.to")
client.inboxes.delete(inbox_id="inbox@agentmail.to")
```

## Messages

Always send both `text` and `html` for best deliverability.

```typescript
// Send message
await client.inboxes.messages.send("agent@agentmail.to", {
  to: "recipient@example.com",
  subject: "Hello",
  text: "Plain text version",
  html: "<p>HTML version</p>",
  labels: ["outreach"],
});

// Reply to message
await client.inboxes.messages.reply("agent@agentmail.to", "msg_123", {
  text: "Thanks for your email!",
});

// List and get messages
const messages = await client.inboxes.messages.list("agent@agentmail.to");
const message = await client.inboxes.messages.get("agent@agentmail.to", "msg_123");

// Update labels
await client.inboxes.messages.update("agent@agentmail.to", "msg_123", {
  addLabels: ["replied"],
  removeLabels: ["unreplied"],
});
```

```python
# Send message
client.inboxes.messages.send(
  inbox_id="agent@agentmail.to",
  to="recipient@example.com",
  subject="Hello",
  text="Plain text version",
  html="<p>HTML version</p>",
  labels=["outreach"]
)

# Reply to message
client.inboxes.messages.reply(
  inbox_id="agent@agentmail.to",
  message_id="msg_123",
  text="Thanks for your email!"
)

# List and get messages
messages = client.inboxes.messages.list(inbox_id="agent@agentmail.to")
message = client.inboxes.messages.get(inbox_id="agent@agentmail.to", message_id="msg_123")

# Update labels
client.inboxes.messages.update(
  inbox_id="agent@agentmail.to",
  message_id="msg_123",
  add_labels=["replied"],
  remove_labels=["unreplied"]
)
```

## Threads

Threads group related messages in a conversation.

```typescript
// List threads (with optional label filter)
const threads = await client.inboxes.threads.list("agent@agentmail.to", {
  labels: ["unreplied"],
});

// Get thread details
const thread = await client.inboxes.threads.get("agent@agentmail.to", "thd_123");

// Org-wide thread listing
const allThreads = await client.threads.list();
```

```python
# List threads (with optional label filter)
threads = client.inboxes.threads.list(inbox_id="agent@agentmail.to", labels=["unreplied"])

# Get thread details
thread = client.inboxes.threads.get(inbox_id="agent@agentmail.to", thread_id="thd_123")

# Org-wide thread listing
all_threads = client.threads.list()
```

## Attachments

Send attachments with Base64 encoding. Retrieve from messages or threads.

```typescript
// Send with attachment
const content = Buffer.from(fileBytes).toString("base64");
await client.inboxes.messages.send("agent@agentmail.to", {
  to: "recipient@example.com",
  subject: "Report",
  text: "See attached.",
  attachments: [
    { content, filename: "report.pdf", contentType: "application/pdf" },
  ],
});

// Get attachment
const fileData = await client.inboxes.messages.getAttachment(
  "agent@agentmail.to",
  "msg_123",
  "att_456",
);
```

```python
import base64

# Send with attachment
content = base64.b64encode(file_bytes).decode()
client.inboxes.messages.send(
  inbox_id="agent@agentmail.to",
  to="recipient@example.com",
  subject="Report",
  text="See attached.",
  attachments=[{"content": content, "filename": "report.pdf", "content_type": "application/pdf"}]
)

# Get attachment
file_data = client.inboxes.messages.get_attachment(
  inbox_id="agent@agentmail.to",
  message_id="msg_123",
  attachment_id="att_456"
)
```

## Drafts

Create drafts for human-in-the-loop approval before sending.

```typescript
// Create draft
const draft = await client.inboxes.drafts.create("agent@agentmail.to", {
  to: "recipient@example.com",
  subject: "Pending approval",
  text: "Draft content",
});

// Send draft (converts to message)
await client.inboxes.drafts.send("agent@agentmail.to", draft.draftId, {});
```

```python
# Create draft
draft = client.inboxes.drafts.create(
  inbox_id="agent@agentmail.to",
  to="recipient@example.com",
  subject="Pending approval",
  text="Draft content"
)

# Send draft (converts to message)
client.inboxes.drafts.send(inbox_id="agent@agentmail.to", draft_id=draft.draft_id)
```

## Pods

Multi-tenant isolation for SaaS platforms. Each customer gets isolated inboxes.

```typescript
// Create pod for a customer
const pod = await client.pods.create({ clientId: "customer_123" });

// Create inbox within pod
const inbox = await client.pods.inboxes.create(pod.podId, { displayName: "Pod Inbox" });

// List threads in a pod
const threads = await client.pods.threads.list(pod.podId);
```

```python
# Create pod for a customer
pod = client.pods.create(client_id="customer_123")

# Create inbox within pod
inbox = client.pods.inboxes.create(pod_id=pod.pod_id, display_name="Pod Inbox")

# List threads in a pod
threads = client.pods.threads.list(pod_id=pod.pod_id)
```

## WebSockets (Real-time)

Real-time email notifications via WebSocket. Best for agents — no public URL needed.

```typescript
import { AgentMailClient, Subscribe, MessageReceivedEvent } from "agentmail";

const client = new AgentMailClient({ apiKey: "YOUR_API_KEY" });

async function main() {
  const socket = await client.websockets.connect();
  await socket.sendSubscribe(Subscribe(inboxIds=["agent@agentmail.to"]));

  for await (const event of socket) {
    if (event instanceof MessageReceivedEvent) {
      processEmail(event.message);
    }
  }
}
```

```python
from agentmail import AgentMail, Subscribe, MessageReceivedEvent

client = AgentMail(api_key="YOUR_API_KEY")

async def main():
  async with client.websockets.connect() as socket:
    await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))
    async for event in socket:
      if isinstance(event, MessageReceivedEvent):
        process_email(event.message)
```

## Webhooks

For servers with public endpoints. AgentMail retries with exponential backoff.

```typescript
const webhook = await client.webhooks.create({
  url: "https://your-server.com/agent/email",
  eventTypes: ["message.received"],
});
```

```python
webhook = client.webhooks.create(
  url="https://your-server.com/agent/email",
  event_types=["message.received"]
)
```

## Error Handling

```typescript
import { AgentMailClient, AgentMailError } from "agentmail";

try {
  const socket = await client.websockets.connect();
  // ...
} catch (err) {
  if (err instanceof AgentMailError) {
    console.error(`API error: ${err.statusCode} - ${err.message}`);
  } else {
    console.error("Connection error:", err);
  }
}
```

```python
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent
from agentmail.core.api_error import ApiError

client = AsyncAgentMail(api_key="YOUR_API_KEY")

async def main():
  try:
    async with client.websockets.connect() as socket:
      await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))
      async for event in socket:
        if isinstance(event, MessageReceivedEvent):
          await process_email(event.message)
  except ApiError as e:
    print(f"API error: {e.status_code} - {e.body}")
  except Exception as e:
    print(f"Connection error: {e}")
```