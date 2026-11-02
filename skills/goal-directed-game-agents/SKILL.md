---
name: goal-directed-game-agents
description: "Use when building game bots. Plan, gate and verify."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    category: autonomous-ai-agents
    tags: [game-automation, agents, planning, approvals]
---

# Goal-directed game agents

Use for bots that pursue a player-defined end state, rather than replaying fixed clicks. Discuss and deliver in Portuguese unless the user asks otherwise.

## When to Use

Load this for browser or native game automation driven by player objectives, including supervised planning and autonomous execution. For input mechanics, also load `computer-use`; for implementation, also load `test-driven-development`.

## Workflow

1. **Inspect existing automation and locate the agent project before designing an interface.** Inventory the relevant workspace for an existing game-agent project; inspect its README, source, tests and working-tree status, then make that project the integration target. Do not create a parallel toolkit in the source userscript clone unless the user asks for a separate artifact. Inventory the userscript's features, data sources and mutating operations as references. UI selectors, session-bound requests and presentation logic are usually too coupled to reuse directly; separate reusable domain rules from page adapters and action execution.
2. **Choose toolkit or MCP based on actual consumers.** Prefer a direct toolkit/library for one tightly coupled subagent; add MCP when standardized access across multiple agents or clients is a real requirement. Keep the domain layer transport-independent so an MCP adapter can be added later without rewriting game logic.
3. **Turn the goal into an observable predicate.** Define the target state, current state fields and completion check. Do not equate a queued action with completed progress.
4. **Separate observer, deterministic planner, executor and supervisor.** The observer reads actual account state; the planner expands prerequisites one level/action at a time; the executor performs only an authorized action; the supervisor reads the target again and records the result. Use an LLM to interpret goals or ambiguity, not as the sole authority for every click.
5. **Offer planning and autonomous modes on the same planner.** Planning mode presents proposals and alternatives for approval. Autonomous mode executes only within a previously defined scope; out-of-scope actions pause for approval. Specify allowed buildings/actions and forbidden spending, military or market actions. A goal is not blanket permission for unrelated side effects.
6. **Research mechanics and resolve prerequisites from observed data.** Inspect official help for per-level costs, static unlock requirements, worker demand, production and storage capacity; these are distinct constraints. Before proposing each next level, verify costs, requirements, resources, free workers, capacity and queue. Expand missing requirements recursively, act on only the next level, then re-observe. Block on unknown costs or requirements rather than assuming zero or none; avoid pre-filling queues when it could change costs or the plan. For KingsAge, use `references/kingsage-buildings.md` to interpret public help, but treat the player's world and live UI as authoritative.
7. **Build and test the planner before live execution.** Test hypothetical states as fixtures (affordable, missing resources, storage bottleneck, queued work, unknown cost, out-of-scope prerequisite and completed goal). Keep the first useful slice read-only and test domain calculations independently of browser adapters. Probe the actual world read-only; verify redirect destination as well as HTTP status, because public help or an anonymous lobby is not account state. Connect an observer to an authenticated session only after confirming the user can interact with that browser or has explicitly supplied a session for a read-only probe. If no shared session exists, offer a reviewed manual console snapshot that exports only same-origin paths and visible state hints—not query strings, hashes, field values, cookies or tokens—and treat it as reconnaissance, not a verified observer. For user-supplied authenticated `curl`, use the minimal application cookie in memory; verify status, redirects, final host, page identity and account markers. Do not log raw HTML or session-bearing values. A successful authenticated read enables observation, not mutation; require separate authorization and before/after verification. Report offline tests, anonymous probes and live verification separately.
8. **Verify every mutation.** Re-read after submission and completion; prevent duplicate submissions when the result is uncertain. Persist objective, scope, last observed state, pending action and audit trail so restart does not repeat work. Declare success only when the observed end-state predicate holds.

## Authentication and session handling

Treat a browser session cookie or exported `curl -b` header as a credential even when the user pastes it voluntarily: never persist it in a repo, test fixture, skill, or command output; use only the minimal cookie for a transient, scoped request and advise session rotation after exposure. Preserve supplied cookie names and values byte-for-byte; do not hand-correct or partially retype long tokens, because a one-character change invalidates the probe. If the minimal cookie fails, an explicitly supplied full header may be tested transiently against the intended first-party host, without forwarding it across redirects. Treat logout redirects and authenticated-API 403 responses as unauthenticated, even when the lobby serves HTTP 200; stop actions and arrange fresh login rather than inferring access from cookies alone. When a game uses federated authentication (Google, Apple, Steam, Facebook, etc.), treat the authenticated browser session—not a password pasted into chat—as the credential. Prefer a dedicated persistent browser profile scoped to that game. On a terminal-only host, arrange an interactive handoff into **that same browser instance** before asking the user to log in: sending the ordinary game URL for them to open in their own browser does not transfer its cookies to the agent. Keep browser debugging on loopback, protect any remote viewer with authentication and TLS, and test its screen/control path before handing it off. The user completes OAuth/2FA manually; verify the resulting game session read-only in the same profile, then again after a fresh launch, and stop unattended runs when the provider asks for fresh authentication. Do not default to copying the user's everyday browser profile. See `references/federated-oauth-login.md` for the terminal workflow and security boundaries.

## User-specific gates

- The user accepts the risk of game-rule restrictions and explicitly prefers not to make support consultation a prerequisite. Do not repeatedly halt the build to request that consultation; a concise risk note is enough when relevant. This does not expand the authorization for spending, attacks, account access, or unrelated actions.
- If live access is requested but the world URL or authenticated session is unavailable, continue with a testable read-only connection probe or offline planner and ask only for the missing non-secret detail. Never request a password in chat. Verify that any proposed browser-login flow is actually interactive for the user before asking them to log in there; otherwise use a reviewed, read-only snapshot from their own browser or another explicitly agreed secure session-sharing route.
- Prioritize a working artifact and actual test output over a speculative architecture sketch when the user says to proceed.
