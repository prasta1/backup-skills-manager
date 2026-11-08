---
name: tool-evaluation
description: Use when Patrick asks how a tool compares to what we have.
---

# Tool & Adoption Evaluation

Patrick regularly asks "how does X compare to what we have today?" and "what does X get us?" (browser-automation SDKs, monitoring stacks, model providers, dashboards). The answer is a stack-gap evaluation against his actual setup, not a product review.

## Procedure (in order)

1. **Name the need first.** The question only has an answer against a concrete outcome: alerting he'll actually notice, unattended automation, structured output, embedding in a product (e.g. one of his iOS apps). If there is no use case yet, say so — that is often the whole verdict.
2. **Inventory current coverage.** Map the request onto what the stack already does. The baseline lives in `references/current-stack.md`; verify live at eval time rather than trusting it blindly (installed tools and loadouts drift).
3. **Find the gap.** The delta must be a capability, not convenience. "Nicer charts" is not a gap; "runs unattended on cron with validated output" is.
4. **Cost it.** Always-on daemons are RAM + maintenance against a machine whose job is inference. Maintained deps (browser binaries, SDK churn, experimental integrations), API keys, token burn. At single-machine scale, check first whether a cron script logging to a rolling file covers ~60% of the value at ~5% of the complexity — the ponytail ladder applied to adoption, and usually the once-and-for-all answer.
5. **Verdict + reopen condition.** Decision in the first line, then one concrete condition that flips it ("worth it only when X exists; re-open with a real workflow"). When the verdict is don't-build, close the exploration ticket.

## Ground truth first

Every model/experiment comparison must be grounded in real ground truth, never observer-inferred labels. If the labels are your guess (sender domain, subject heuristics), say so explicitly and treat the verdict as provisional. Collect the user's actual decisions (approve/discard/send logs, a labeled batch) or a verified dataset before drawing conclusions. A bakeoff against guessed labels is a hypothesis, not a verdict.

## Pitfalls

- **Review the gap, not the tool.** Feature rundowns of the new tool are padding; the first paragraph must answer what the current stack misses.
- **Count the daemons.** Every new always-on service (prometheus, grafana, agent frameworks) eats RAM and maintenance; curl + cron covers the API-accessible case with no daemon at all.
- **Exploration tickets close as Canceled, not Done.** A setup/evaluation ticket that ends in don't-build is canceled work, not completed work. Append the evaluation notes and reopen conditions to the body so a re-open does not re-derive the analysis, and keep the "no immediate use case" flag visible — it is the reason for the state.
- **Don't leave dead decisions on the board.** A tool eval that needs Patrick's choices (language, vendor, integration) stays open only while the verdict is "maybe." Once it is "don't build," the open questions are moot — close it.
- **Flag phantom references.** When a ticket or doc references a skill or config that does not exist in this profile, name the gap instead of assuming the tooling exists here — it may live on another machine's profile or in a repo. A future session should not hunt for a file that is not there.

## Close-out shape

The close-out note appended to a canceled eval ticket follows the same bones as the verdict: what already covers the case (with the zero-setup tools named), what the tool actually adds, the costs, and the exact condition that would make it worth re-opening. That body text is the artifact a future session reads first.
