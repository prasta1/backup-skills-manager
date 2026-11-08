# Radio Microphone-to-Display Pattern

## Preferred command taxonomy

- `next`
- `previous`
- `volume up`
- `volume down`
- `stop`
- indexed station tokens
- artist tokens

## Display-routing design

- Map model outputs directly to visible UI updates.
- Use a command taxonomy instead of free-form transcript when latency matters.
- Keep continuous inference lightweight if display actions are latency-sensitive.

## Error Pattern

When API calls fail with 403, troubleshoot in order:

- `/api` -> project listing permission problem
- `/{projectId}` -> project access problem
- `/{projectId}/impulse` -> project read error

If all return access denied, ask for key-to-project mapping.
If only one endpoint fails, target that endpoint for review.
