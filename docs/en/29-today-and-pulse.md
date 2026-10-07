# Today & H2O Pulse: the start-of-day workstation

*[Tiếng Việt](../29-hom-nay-va-pulse.md) · **English***

The **Today** page is the working overview: Joyce pre-collects everything that needs a human hand (stuck tasks, pending approvals, a dead H2O app, unread results) into one screen, instead of you sweeping every page yourself.

The page's philosophy: **not a dashboard to admire, but an intervention list**. Numbers that need no action stay small; anything whose silence costs money gets big and red.

## Where to open it

**Today** (sun icon) sits at the top of the sidebar in its own group. For a staff member's first sign-in it is also the default landing page.

The page follows the **currently selected brain**: switching brains switches the work queue, the approval count and the sidebar badges.

## What is on the page

| Block | Content | Clicking |
| --- | --- | --- |
| Greeting + brief | Time-aware greeting, viewer name, one line counting groups needing attention | - |
| 6 metric tiles | Running / Pending review / Done 24h / H2O apps up / Due today / Unread inbox | jumps to the matching page |
| Today's priorities | Stuck and pending-review tasks first, then queued work | opens Work + that task's detail drawer |
| Today's schedule | Pending reminders due today, aggregated across all brains | opens recurring Work |
| **H2O Pulse** | LIVE alert feed ranked by severity | click an item -> straight to the page that fixes it |
| H2O ecosystem | Each Vercel app: green/red dot + response ms | opens the real webapp |

When a data source fails (locked kanban sqlite, dead health check), the page shows a **yellow "missing sources" banner** naming the failed sources, instead of silently pretending the system is clean.

## How to read H2O Pulse

Pulse is **not a log**. It only lists signals with a cost of silence, sorted `severity x age`:

| Level | Examples |
| --- | --- |
| **critical** (red) | AI engine broken/session expired; an H2O app not responding |
| **high** (orange) | Stuck task; broken connector/MCP |
| **medium** (amber) | Review pending over 4 hours; queue filled while orchestration is off; reminder with no notification channel |
| **low** (grey) | Unread background results in Inbox |

Items **disappear on their own** once the source recovers - there is no "mark as read" button, because the feed mirrors current state, not a mailbox.

## The "Pending approval" strip on Work

Every task the AI finished while "Require result approval" was ticked (or a worker pushed to `review`) sits in a yellow-bordered strip pinned to the top of the Work page:

- **Approve**: task moves to done immediately, no drawer needed.
- **Request changes**: task goes back to blocked for fixing/re-triage.
- Clicking the task body still opens the usual detail drawer.

The pending count also shows as a **red badge next to Work** in the sidebar, refreshing every 60 seconds and on every brain switch.

## The Ctrl+K command palette

Press **Ctrl+K** (Cmd+K on Mac) or the **"Quick search"** button at the right of the page header:

- Type a page name (accents optional: `viec` finds "Work") to jump to it.
- Built-in commands: create a new task, refresh the current page.
- Arrow keys to select, Enter to open, Esc to close. Mouse clicks work too.

## Toggling the whole Workstation layer

Settings -> General tab -> **"Today workstation"** card. Turning it off removes Today from the rail immediately and the page falls back to a placeholder; data and APIs are untouched. Useful for comparing with the classic UI or for installs that do not need this layer.

## For developers: where to upgrade

| To change | Touch |
| --- | --- |
| Add a Pulse alert source | `server/joyce_today.py` -> `_pulse()` (each source has its own try/except) |
| Add a metric/today field | `api_today()` in `joyce_today.py`; change deps via `TodayDeps` + `register()` in `server/main.py` (~line 16175) |
| Change the stale-review threshold | `_REVIEW_STALE_SEC` in `joyce_today.py` (default 4h) |
| Change the H2O app ping TTL | `_PING_TTL` (120s) in `joyce_today.py` |
| Today page UI | `renderToday()` in `dashboard/console.js`; CSS `.td-*` inside `_injectExtraCss()` |
| Approval strip | `renderKanban()` -> `#knApproveStrip` + `doTaskAction()`; CSS `.kn-approve` |
| Rail badge | `_pollBadges()` in `dashboard/console.js`; CSS `.rail-badge` |
| Command palette | `_cmdkBuild/_cmdkItems` in `dashboard/console.js` (add a command = add a dict to `items`) |
| Feature flag | `settings.features.workstation_v1`; read in `freshSettings()` (console.js ~line 9323), toggled in `renderSettings()` |
| LLM brief | `_brief_ai_today()` in `main.py` (isolated engine) + `api_brief_ai`/`_brief_cache` in `joyce_today.py`; change the voice = edit the prompt in `api_brief_ai`, TTL = `_BRIEF_TTL` |
| Add a command | the `_v1_cmd_today()` whitelist in `main.py` (hard-coded - each command calls the old endpoint's function) |
| i18n | `today.*`, `page.today.*`, `kanban.approve_*`, `cmdk.*`, `settings.ws*`, `nav.group.hom_nay` |

APIs: `GET /api/joyce/v1/today` (one call for the whole page) and `GET /api/joyce/v1/pulse` (standalone feed returning `approvals`, `partial`, `sources_down`). Both go through the shared auth middleware; no new store is created - everything reads through adapters over the existing kanban/reminders/inbox/h2o_projects/connect_health services.

Phase 4 adds:

- `GET /api/joyce/v1/brief-ai` - greeting written by the **background model** (the aux model picked on Models). The engine runs in an empty dir with no MCP and no tools; the prompt carries only counts + task titles. 10-minute cache keyed on the numbers signature (F5 does not re-bill); aux error/slow/missing → `fallback: true` with the deterministic brief, so the page never blocks. The frontend fetches lazily after first paint.
- `GET /api/joyce/v1/knowledge/search?q=` - wraps `/files/search` (walks the brain root in a threadpool, accent-insensitive); every item tagged `source: "vault"`. **Staff gets 403** (vault read is owner-only).
- `GET/POST /api/joyce/v1/chat/threads` - wraps `/sessions` (staff scope preserved: staff only see their own `staff:<id>` channel). POST creates a `web` (admin) or `staff:<id>` (staff) channel session. Collaboration channels (`agent:/workflow:/coding:`) still go through `/sessions/new`.
- `POST /api/joyce/v1/commands` - **command whitelist, not a shell**: `kanban.nudge` (kick the dispatcher), `pulse.refresh` (drop the H2O ping cache), `orchestration.auto|.manual|.off` (board mode). Unknown command → 404. **Staff 403**.
- `GET /api/joyce/v1/learning-proposals` - the "what Joyce learned" queue = learn commits in the brain git repo (wraps `/learn/review`). `POST .../learning-proposals` queues a note into the learn pipeline (staff 403, text <20 chars → 400). `POST .../learning-proposals/undo` = one-click revert (staff 403).
- `POST /api/joyce/v1/agent-runs` - assigns work to the agent fleet = kanban task enqueue (`tasks_feature.enqueue`), returns `task_id`, supports `needs_approval`/`chat_id`/`idempotency_key` (retries do not double-queue). **Staff 403**, same as `/kanban` writes.
- `GET /api/joyce/v1/integrations` - **Integration Center (machine-readable face)**: merges MCP connectors (redacted, no secrets) + health, engines, H2O apps (cached ping), channel bots; `summary.down` counts what is broken. The Connections UI is unchanged - this is the aggregate contract for other clients, not a route migration.
- `GET /api/joyce/v1/context/{type}/{id}` - generic context drawer. Only `type=task` has an internal adapter; domain types (customer/lead/project...) return 404 with `supported` - those objects live in H2O Legacy.
- `POST /api/joyce/v1/chat/threads/{id}/messages` - appends a user message to the session (staff limited to their own `staff:<id>` channel, unknown session 404). Replies still stream via `/chat` - this endpoint seeds a thread, it does not run the engine.

Related tests: `tests/python/test_joyce_today.py`, `tests/js/test_trang_hom_nay.js`, `tests/js/test_settings_tabs.js` (rail group expectation), `tests/python/test_route_table.py` (route snapshot).
