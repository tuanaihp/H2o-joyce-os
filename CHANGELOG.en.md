# Changelog - H2O Joyce OS

*[Tiếng Việt](CHANGELOG.md) · **English***

## [1.3.52] - 2026-10-31
### Added
- **Token-free web page watch** (ported from Javis 0.239.0). The Recurring work page gains a **Page watch** tab: Joyce fetches a page on a schedule and compares text, **without calling AI**, and only reports when something actually happened - the page changed, a phrase you are waiting for appeared, or a price dropped below a threshold (reads 1,250,000 VND, 1.5 million, 250k, $20). Relative times like "3 minutes ago" never count as a change; failures back off, and after 5 in a row the watch pauses and says so once. Turning on AI summaries makes the background model add a one-paragraph take on each change. Also usable from chat via the `joyce_watch` tool.
- **Cookies - the login vault** (ported from Javis 0.251.0). A new page in the Connections group: sign in on your own browser, export the cookies with Cookie-Editor and paste them (or upload a JSON/cookies.txt file). Joyce reuses that session to read pages behind a sign-in (seller portals, affiliate dashboards, admin panels) through the `joyce_login` tool, and page watches can watch sign-in-protected pages. Cookies are **encrypted on the server**, the AI only ever sees page text and the sign-in's name; when a session expires Joyce says so plainly instead of retrying blindly.
- **Anthropic Compatible** (ported from Javis 0.254.0). The Models page gains a new card: paste a Base URL + API key (and model names when the gateway lists none) to use Claude resellers and the "anthropic" endpoints of DeepSeek, Kimi, MiniMax. Joyce sends one tiny probe before saving, so a wrong key or URL is reported immediately. Full toolkit like every other brain: MCP, vault files, skills, background work.
- **ElevenLabs now speaks Vietnamese properly** (ported from Javis 0.255.0). The default model moves to **Flash v2.5** (the old Multilingual v2 has no Vietnamese); a saved v2 model is swapped automatically when the text is Vietnamese. The voice picker lists **the voices in your ElevenLabs account by name** (cloned ones included) instead of a raw Voice ID. Voice notes sent to Telegram/Zalo also use ElevenLabs when chosen, falling back to Edge if it fails.

### Fixed
- The route table snapshot was re-taken (8 new routes from the four features above).

## [1.3.51] - 2026-10-30
### Added
- **Skill library, step 1: a read-only audit.** Joyce scans every brain, groups the copies back into one skill each, shows which copies differ in content, which is newest, which work group each skill should belong to, and which departments could not be placed. Read-only, it never touches brains.

## [1.3.50] - 2026-10-30
### Fixed
- **Open Skills page in Skill Learn now opens the item that was just installed:** Joyce goes to the right page, scrolls to the exact skill or plugin, and highlights its card so it is immediately visible.

## [1.3.49] - 2026-10-29
### Added
- **Skill Learn now splits "Installed" and "Skipped" into separate tabs** (a Restore button puts a skipped item back in the queue). Each card shows what kind it is and where it goes: **skills go to the Skills page, plugins go to the Tools page (switched off)**; MCP is not part of this tab.
- **Real evidence after installing:** Joyce checks the files are in place, the content matches the repo, Joyce lists the skill/plugin, and plugin code has no syntax error. A failed check is **not counted as installed** and the copied files are cleaned up. A **Check again** button is always there.
- **A Try it button for skills:** the AI reads the skill and follows it for a sample request in a sandbox (no tools); the real answer is saved on the card. For plugins, switch them on from the Tools page and call them, since they are real running code.

## [1.3.48] - 2026-10-29
### Added
- **A waiting store in Skill Learn Update:** for any item you approve but do not want to install yet, press **Save for later**, pick **High / Medium priority or Reference**, and add a short note. The Waiting store tab sorts by priority; when you need one press **Install now**, or tick several to install in one go.
- If the repo changes the content of a saved item, it stays in the waiting store with a **Repo has a new version** badge (it no longer gets lost).

## [1.3.47] - 2026-10-29
### Added
- **Skill Learn Update tab redesigned:** paste a repo link and Joyce downloads it, finds **skills and plugins**, has an AI read and classify them as **Worth taking / Think about it / Not worth it**, with notes in Vietnamese: what it does, what Joyce gains, why, and whether it overlaps something already installed.
- **Approve one by one, or tick several and approve at once.** Each card keeps the original text for cross-checking. Nothing is installed until you approve; an item the static scan flags as high risk is never labelled "Worth taking".
- Plugins installed from a repo always start **switched off** until you turn them on from the Tools page. The daily scan also has the AI read new items (up to 30 per run).
- **You can now pick the brain for the repo-reading step right inside the tab** (Claude, ChatGPT, Gemini, Z.ai...), sharing its source with the Task routing page. If none is picked it uses free Z.ai as before.
- **Fixed scans that found 0 items:** if downloading a repo was cut off midway (for example a server restart), Joyce now deletes the broken copy and downloads again instead of trusting it.

## [1.3.46] - 2026-10-29
### Added
- **Permission blocking per command, not just per tool name.** For example a read-only assistant can still view the Shop ledger figures but cannot write income or expense into the money ledger; multi-action tools from outside connections are also re-classified at call time.
- **The Reconciliation pilot is ready to run:** a trial assistant "Reconciliation Agent (pilot G3)" (the original assistant is not touched), a set of test cases and 20 jobs with a grading sheet for you to run and grade on the Map page.

## [1.3.45] - 2026-10-29
### Added
- **Every hub tool asks for permission before running.** An assistant that declared its permissions (say, read-only) and calls a tool that sends a message, writes the ledger or deletes is blocked, and the block is logged for you. An assistant that declared nothing runs as before.
- **Your chat window, Telegram and the CLI now enter the run log.** Chat with an assistant is recorded under that assistant; tokens and run counts are measured, and the token cap applies to chat too.

## [1.3.44] - 2026-10-29
### Added
- **A completion gate for jobs that act outside:** an outward job (send, post, pay) that has not been independently checked no longer jumps to "done"; it waits in the review column for you to confirm. Change or turn off with `tasks.rao_hoan_thanh`.
- **Real token measurement per run,** shown on the Map; a run whose engine reports nothing is recorded as "not measured", never as 0. Set a cap with `tasks.tran_token_luot` (at most 1,000,000): over the cap the run stops.
### Fixed
- **28 old red tests fixed:** the pinned working folder in normal chats, the ">" in the folder picker, the "call" flag of reminders, and provider errors returned during OAuth connect are reconnected. The UI no longer uses emoji (icons instead). The Reconciliation pilot dossier is written and waits for your approval.

## [1.3.43] - 2026-10-28
### Added
- **Joyce now records every real assistant run** (bot replies to customers, tasks given to an assistant, workflow steps) with the exact configuration used. A retry counts once; if the machine stops mid-run it is recorded as interrupted, never as a pass.
- **A canary only spreads after 20 runs you graded as passing.** Finished is not passed. The Map page has a "Runs waiting for your grade" panel with Pass and Fail buttons; a single fail rolls it back at once.
- **An assistant that declared its permissions is blocked from writing files if it lacks write permission, and each file self-improves at most 2 times a week** (the third waits for you).
- **The Map gets 5 more lights:** Gate (7 days), File writer, Real runs, Running version, Write-path certification. Plainly: no write path is certified yet, and direct chat with Joyce itself is not in the run log yet.

## [1.3.42] - 2026-10-28
### Fixed
- **Self-improvement only auto-applies display changes.** A change to instructions, role or permissions waits for you, with the reason shown. There is a pause switch for auto-deploy on the Map page.
- **A department's own edit is never overwritten.** A department with its own variant stays put until you decide. Every write keeps the old copy so each department can be restored, even if the machine stops mid-write.
- **The Map has a deployment panel:** see the diff, restore per department, mark as read. A broken eval set blocks; no eval set does not block.
- **Plainly:** the canary is still not certified because runs are not tied to agents, so files shared by several departments do not auto-apply yet. Startup is slightly lighter, but the startup test is still close to its limit on this machine.

## [1.3.41] - 2026-10-28
### Fixed
- **Self-improvement now sees every permission change**, including nested config keys and tools swapped between steps. A config it cannot read with confidence waits for you instead of auto-applying. 30 skills whose header was already malformed wait for you for that reason.
- **A broken eval set no longer opens the gate.** A bad eval file blocks the automatic fix instead of being treated as having no eval at all.
- **No overwriting source documents by a side route.** The `sources/` guard now sits right at the file-write command, covering oddly written paths, linked folders and files swapped at the last moment.
- **Safer canary.** It spreads one department at a time and never overwrites a department's own edit; it needs 20 real runs before spreading; any failure stops it. Note: runs are not yet tied to agents, so a canary will wait and expire instead of spreading; tying them is a later package.

## [1.3.40] - 2026-10-28
### Added
- **A Messenger inbox right inside the Fanpage tab.** Turn it on per Page, read customer conversations, press "Suggest a reply" so Joyce drafts and you edit and press Send. By default messages are only saved to the inbox; nothing is sent by itself.
- **Automatic replies are a separate switch, off by default.** It needs a confirmation because messages go straight to the customer. Meta only allows replies within 24 hours of the customer's last message; the screen says so and reports a plain error past that.
- **Add a customer to the CRM with one button** so Joyce proposes profile updates for you to approve.
- One-time setup: paste the webhook address into your Facebook app and add the messaging permission. Real customers need Meta to approve `pages_messaging`; until then you can only test with people who hold a role in the app.

## [1.3.39] - 2026-10-28
### Added
- **Joyce Harness on the Diagram page.** Three tiers (runtime core, department surface, improvement loop), 14 components, each with a light driven by live numbers; anything not built yet shows grey and says so.
- **joyce-guard on by default.** No overwriting source documents in sources/, outsiders cannot get Joyce to send Zalo messages in bulk, an expense of 5 million or more must name its contract or category.
### Changed
- **The 9 shared assistants now live as one source.** Five reviewers, the improvement engineer, two overhaul assistants and the Onboarding assistant change everywhere when edited once; the 549 copies inside brains were removed (backed up). A department that needs its own saves an override.
- **Fewer tokens.** The fixed part of Joyce's instructions is really cached now instead of missing every turn because of the clock; turns that read many pages of data trim old results, Shop ledger numbers stay whole.
### Fixed
- A job declared with "no tools" used to run with full access on the Claude engine; a self-improvement that changes an assistant's permissions now waits for the owner; an eval case that cannot be checked counts as a fail.

## [1.3.38] - 2026-10-27
### Added
- **New tab "Price list & commission".** A price list of 46 service packages with the first deposit, second deposit and final payment schedule, plus the job list per department (Makeup, Photo, Photoshop, Dress consulting...) with a fixed commission per job. Both are preloaded from the H2O sheet and editable on screen.
- **Type a package code and the price fills in.** When creating a contract or quote, just type the package code or name and the price fills itself; the sales order shows which deposit the customer still owes. Ask Joyce "price of package PRW-STCB" for a quick lookup.
- **Split jobs per contract.** Each contract hands every job to a person; the commission in payroll is computed from the amount of each job, not only from a percentage.

- **Two new tabs: Item Catalog and Rental History.** Manage dresses, suits and ao dai for rent: which items are ready, rented out or overdue. Renting links to a contract and can book the payment at once, double-booking is blocked, including the washing days after each return (3 by default, set per item), and late returns are flagged. A button loads 5 sample items to try and clears them cleanly.

## [1.3.37] - 2026-10-27
### Added
- **Say one sentence in chat and Joyce writes the ledger and hands each part to the right department.** For example "contract Tuan Thuy 0899252392, studio photo package 15 million, income 15m, expense 4m setup": Sales records the customer, deal and quote in the CRM, the Income department books the income, the Expense department books the expense. A customer with the same phone number is never created twice, and repeating the sentence does not book it twice.
- **The Shop Manager ledger is real.** Cash book, sales orders (contracts), quotes, staff and payroll, and tasks all read from one shared ledger; the "Tiem banh May" sample numbers are gone; Stock, Customer chat, Care, Marketing and AI Images say "not connected to real data yet". Payroll includes percentage commission computed automatically from the gross profit of signed contracts.
- **The virtual office shows which agent is working.** The department that just handled something lights up, with a log of "which agent, which skill, what".
### Changed
- **Large expenses reported by staff wait for the owner's approval** (limit is configurable, default 2 million); the owner's own reports are booked immediately. A completed contract has the Reconciliation department write a profit and loss report.

## [1.3.36] - 2026-10-27
### Added
- **"Load sample data" button in the Operations CRM** (owner and managers, while the department has no customers): creates 4 sample customers with deals and tasks so you can see the page with data. Sample customers carry the source "Sample data"; "Clear sample data" removes them and never touches real customers.

## [1.3.35] - 2026-10-27
### Added
- **Shop management is now shared across devices**: the data of its 12 modules (orders, stock, cash book, staff, quotes, internal team chat...) used to live only in each browser; it is now stored on the Joyce server, so phone and computer see the same copy. Only the owner and managers (CEO, director, department head, lead) see this page because it holds cash flow and staff data. If two devices edit at once, the last save wins.
### Changed
- Shop management sits under **Business operations** with Research, Career path, Partners, Teams, Chatbot and Operations CRM.
- Operations CRM picks the department with the most customers by default (it could land on an empty department, so every number read 0 and the profile column was empty). Small card headings are 14px as in the mockup.

## [1.3.34] - 2026-10-27
### Added
- **Shop management page** under Capabilities, following the `JOYCE_QUAN_LY_SHOP_PROTOTYPE_V2.html` design: 14 module tabs (Overview, CRM, Sales, Orders, Stock, Cash flow, Staff, Executive assistant, Quotes, Customer inbox, Care, Marketing, AI images, Tasks), department map, department cards and the internal chat room. Its Customer CRM tab runs the real Joyce CRM; the other modules keep data in the browser like the design.
### Changed
- The Operations CRM uses the latest `crm.js` from the handoff bundle (sync notice, guide, money format).

## [1.3.33] - 2026-10-27
### Changed
- **The Operations CRM matches the HTML design more closely**: the left column holds Quick add with AI, search and the contact list (with phone and closed revenue), the right column holds the profile. Tabs have icons and counts, a collapsible "How to use the CRM" line, and Back up and Import customer (.json or .csv) buttons on the right of the tab bar. Pipeline column names are uppercase like the design.
### Fixed
- CRM buttons and inputs are no longer oversized compared with the design.

## [1.3.32] - 2026-10-27
### Changed
- **The Operations CRM uses the new interface**: quick add with AI, a six-field profile Joyce collects (each field can be locked), customers assigned to several departments, pick each proposed field before approving, manage pipeline stages, and filtered to-dos.
- Read-only users no longer see edit buttons; clear messages when you lack permission or the server has not loaded CRM yet.

## [1.3.31] - 2026-10-27
### Changed
- **The Operations CRM now follows the HTML design closely**: stat cards with icons and a caption (bought, deals, win rate, overdue), a pill tab bar with counts, a left column with the always-open Quick add with AI box (plus Add manually), search and a contact list showing closed revenue, and a right column with the profile that opens the first customer. Colors still follow Joyce's light or dark theme.
### Fixed
- With "All departments" selected, the open-deals and won cards no longer show 0; they add up the departments you can see.
- Side menu: the Capabilities group is no longer cut off on phones; Research, Career path, Partners, Teams, Chatbot and CRM now sit under Business operations.

## [1.3.30] - 2026-10-27
### Fixed
- **The Operations CRM now says so when the server has not loaded it** (before it showed a blank page with "Not Found"): restart Joyce after updating. The "Quick add with AI" box is open by default and a one-minute guide sits above Contacts, as designed.

## [1.3.29] - 2026-10-26
### Added
- **Operations CRM**: a separate tab for departments to manage customers (Contacts, Pipeline, Tasks, Proposals, Segments). One customer can belong to several departments, and each department only sees its own deals and tasks. The pipeline has + and - buttons to add or remove stages.
- **Per-account and per-department access**: the CRM tab is hidden by default. On the Staff page pick "View only" or "Full access" per account; the owner also switches CRM on or off per department, and only switched-on departments are visible. Only the owner, CEO, directors and department heads can delete customers or import them from the inbox.
- **Joyce collects customer profiles on its own**: it reads conversations and proposes needs, budget and deadlines; staff approve each item before it enters the profile. The owner picks Off, Review or Auto. Also "Quick add with AI" (paste a chat) and "Remember how to handle this customer" into the department wiki.
- Fixed hard-to-read primary button text in the Daily jobs tray.

## [1.3.28] - 2026-10-26
### Added
- **Z.ai (GLM) as the 12th brain**: free flash models included (`glm-4.7-flash`, `glm-4.5-flash`, `glm-4.6v-flash`). The Models page has a "Free brains" section and the picker puts a FREE chip on `:free` ids (OpenRouter, TokenHarbor, 9router). A dead key turns the card red with the reason and Joyce skips that provider in fallbacks.
- **Voice cloning**: say "clone my voice" and Joyce records a sample from the mic, saves a profile and keeps reading in that voice (runs locally, non-commercial licence). Say "old voice" to go back to the default.
- **Music ducks while Joyce speaks**: the player moved to a Howler.js core with faster streaming and smooth volume fades. Added a local-files source and voice commands ("play lofi", "next", "stop music").
- **Change the avatar backdrop by voice** and a knowledge-index chip row inside the empty chat.
- **Joyce factory and catch-up sweep**: after a job finishes Joyce runs its check command and opens a fix job if it fails; every hour it scans all brains for work that should have run but did not and drops one digest in the inbox. Numbers show on the System map page.
- **Meaning-based tool matching**: Joyce translates the question to English with a cheap model and matches it against tool names, so "close the order for the customer" finds `create_invoice`. The permission filter still applies.
- **H2O Book students on the 3D screen**, **Apple Notes sync** into `sources/apple-notes/`, **incident Q&A (Sevbot)**, and a guide to using Joyce in the car.
- Claude-based agents now get a fallback chain too: if the provider dies midway, the work moves to another one only if nothing outside was done yet.

### Fixed
- Cleaned translation strings that still had stray em dashes or HTML tags.

## [1.3.27] - 2026-10-26
### Added
- **Daily jobs right inside Chat**: open the chat and you see your team's job templates (advising, follow-up, reports...). Tap one, fill a few fields and Joyce does it. Each group has a **+** to add your own job; tap a job to edit or delete it.
- **Done? Tap "Done"**: Joyce asks when the job finishes, and tapping moves it to the Done column of your team's Work board. "Remember how this was done" writes the real way of working into the wiki; after 3 runs of the same job it does so by itself.
- Ready-made jobs for Sales, Customer care and the two personal brains (Thuy, Tuan). With "All divisions" selected, staff only see their main team's jobs.

## [1.3.26] - 2026-10-23
### Added
- **System map page**: one page that shows the whole Joyce system - per-department performance from the real kanban boards, running loops, the dispatcher and items that need attention, with "All" and "Needs attention" filters.

## [1.3.25] - 2026-10-21
### Added
- **Harness²-style self-improvement layer (PPC)**: Joyce learns to optimise its own harness (prompts, skills, agents) from real outcome evidence instead of guesswork. Three new capabilities in Brain Default - the `cham-diem-tuong-phan` skill (anonymous A/B scoring, anti-flattery and injection-resistant evidence), the `tu-cai-tien-agent` workflow (Improvement Engineer proposes -> Contrast Judge scores anonymously -> a proposal waits for owner approval, never self-applies), and the `dinh-duong-bai-hoc` loop (daily distillation of evidence-backed lessons from completed work, auto-opens a proposal when an agent repeats a mistake). Workflow and loop are created OFF - enable them on the Work page when wanted.
- **"Self-improvement (PPC)" card in the Overview tab**: counts pending proposals in `Joyce/proposals/`, lessons and journal days in `Joyce/learn-log/`, plus the most recent learning runs - read straight from vault files so no extra database is needed.

## [1.3.24] - 2026-10-20
### Added
- **Constellation-style Nebula view**: the Nebula tab now shows the open brain's sphere in the centre (Earth for Brain Default, the department's own planet, a star for brand brains) inside a gold ring, surrounded by branches: cyan = knowledge, amber = operations, grey = MCP connections (dashed when off).
- **Branches light up on real work**: when Joyce reads a file in `wiki` the WIKI branch lights, calling Zalo lights the Zalo node, with particles flowing from the core; thinking or speaking speeds the whole web up.
- **Click a branch** for an overview card: note count, vault share, latest notes (click to open). The **Note network** button top-right switches back to the per-note graph (with timelapse).

## [1.3.23] - 2026-10-19
### Added
- **3D Joyce now appears in quantum particles**: when you open 3D Joyce, particles shoot out of a point of light, swirl into a comet stream and assemble into a human figure; the familiar avatar then appears in exactly that spot. Everything after the intro stays as before.
- **3D Joyce extracts data while it works**: when you give it a task (for example "send me the sales guide"), the avatar sends light pulses from its chest, a scan line runs down its body, and it leans and nods each time it pulls data. Names of the brain documents being read and real numbers from the results fly out to both sides of the screen, while a "DATA SCANNED" counter runs up the total. While answering, the counter settles on the final total and the light pulses with the voice. No data means no made-up numbers.

### Fixed
- Fixed failing automated checks (long dashes in translations, mismatched page lists, stale camera checks).

## [1.3.22] - 2026-10-21
### Added
- **Hand-gesture TRAINER panel** (`gesture-trainer.mjs`, opened from the "🎓 TEACH" button next to HAND CAM in 3D Joyce or the "Hand gestures" card in Settings): teaches Joyce YOUR hand instead of shared thresholds. Each gesture is **scanned 3 times at different tempos** - the mean and deviation become the personal tolerance band; reps that disagree too much are rejected with a rescan hint instead of being saved. Unlike the headless control mode, this panel shows a camera preview on purpose - you must see your hand to train it.
- **Trained gestures bind to actions**: hold up 2/3/4/5 fingers or any pose (✌️🤟🖐✊👌 + presets) → pick one of 7 actions: energy pulse, hush Joyce, album open/next/prev/close, fullscreen. Recognition matches a 5-finger `fingerVector` (palm-scale normalised) against the locked template; the pose must hold still for 450ms so a moving/swiping hand never fires it.
- **Built-in gesture calibration**: retrain pinch, open palm and swipe to retune the engine to your real hand (pinchOn/Off, palmExtMin, swipe distance+speed). A ↺ button restores defaults.
- **A trained 5-finger pose replaces the default palm**: when the profile contains a ≥4-finger-extended gesture it supersedes the stock hush command (palmSuppressed) so detection fits the owner's actual hand.
- **Profile persisted server-side**: `GET/PUT /hands/profile` → `STATE_DIR/hand_gestures.json` with strict validation (≤16 gestures, action whitelist, 5-float vec/tol, bounded calib keys). Saving fires `joyce-hands:profile` so a running control camera picks up new thresholds instantly without a restart.
- **Opening the trainer pauses the control camera** (two workers don't race the CPU); closing it resumes hand control if it was on.

## [1.3.21] - 2026-10-21
### Added
- **Fullscreen brain chamber button** (⤢ next to the eye icon in stage-tools): requestFullscreen on `.hud-center` - in the 3D Joyce view the whole screen is just the virtual figure + voice + camera; ESC or press again to exit.
- **Hand swipe opens the PHOTO ALBUM slideshow** (new gesture in GestureEngine): a fast finger sweep ≥0.28 of the frame in <450ms fires a swipe - swipe right/left opens the album then flips photos, swipe down closes it. The album pulls images from the **"Ban Hang - Sales Hinh Anh"** brain (new `GET /album` endpoint scans `attachments/` + `sources/`, images served through the existing `/files/raw`); when empty it explains where to drop photos.
- **Figure shrinks while the album is open**: `.hum-layer` scales to 26% at the bottom-right corner with a smooth transition while the slideshow takes center stage.
- **Two-fingertip continuous album zoom**: the thumb-index distance (pinchRatio already in tracking results) maps directly to 1x..4.5x - spread fingers to zoom in, close to zoom out. Only counts with exactly one hand and not in palm pose (palm remains the quiet gesture).

## [1.3.20] - 2026-10-21
### Added
- **Camera hand control for the avatar - full Worker edition** (`dashboard/joyce-hands/`): integrates JOYCE_HAND_GESTURE_KIT into the 3D Joyce view in HEADLESS mode - pressing "✋ HAND CAM" requests camera permission and starts tracking immediately; the video lives outside the DOM so the interface shows only Joyce (state is shown via the CAM ON button + the avatar's notice line); pressing again or leaving the view stops everything. The camera never requests a microphone and everything is processed on-device - no frames or landmarks leave the browser.
- **Detection runs in a dedicated Worker**, `detectForVideo` is gone from the main thread: ~15 inferences/sec, one pending frame, results older than 500ms discarded, 4s worker watchdog, 30s model-load timeout, camera stops on hidden tab/pagehide/view exit/avatar dispose/dead stream. A crashed worker reports a clear error instead of silently re-running on the main thread. Previously detection ran inside the render loop, dropping frames, with no watchdog.
- **Gestures follow the kit's GestureEngine** (dwell + hysteresis + cooldown), replacing raw distance thresholds: a pinch held ≥160ms fires exactly ONE pulse until released plus a 650ms cooldown; an open palm held still ≥650ms sends a quiet request (hand wobble resets the dwell, a ≥200ms release is required before retriggering, 1800ms cooldown); two hands in frame are ignored rather than stealing control; losing the hand recenters attention.
- **Attention steers the figure's head** via a new `setAttention(x,y)` hook (head yaw + particle parallax, same channel as the mouse); pinch calls `pulse()` at the finger position; the avatar emits `joyce-avatar:exit`/`dispose` so the bridge stops the camera automatically.
- **Open palm = ask Joyce to stop speaking** through `VoiceQuietGate`: it only interrupts when the avatar is really in "speaking" state (read from `#orbState`) and calls the real `stopCurrent()` (= the Stop button in app.js - cuts playing TTS + cancels the current session's turn, mic/call untouched). When not speaking it just pulses lightly as acknowledgment.
- **Reuses the existing MediaPipe model + runtime** under `/static/humanoid/` - no ~28MB duplication, no CDN. Panel supports light/dark themes, Escape closes and returns focus, mobile responsive.
- New `tests/js/test_joyce_hands.js`: 47 checks - full gesture semantics (dwell/hysteresis/cooldown/release), lost hand, small hand, mirroring, and every static wiring point.

## [1.3.19] - 2026-10-20
### Added
- **Per-task-type usage ledger** (`STATE_DIR/task_usage.json`): every background engine now runs through one counting layer inside `swap()`/`_FallbackChain` - each call records the job type (reminder, loop, Kanban, self-improvement...), the provider/model that ACTUALLY ran that turn (a fallback link is credited, not the chain head), in/out tokens, and real cost when the provider reports it. Rolled up daily, kept ~2 months, empty 0-token events are not written. Separate from `usage.json` (which groups by provider|model for the Usage page) - no double counting.
- **Task routing table shows real 30-day usage**: every job type gets a usage column - call count, total tokens, which brains carried the load, and an ESTIMATED $ figure from `usage_pricing.json` (':free' and unpriced models show $0, nothing is made up). Provider-reported cost (Claude Code CLI) stays separate and is never overwritten by the estimate.
- **Recommendations from observed usage**: each job type gets a suggestion chip - "on suggestion" when the current provider is already in the curated list; "switch to X" when a suggested provider is connected but unused; "costing ~$X/30d" when real money is being spent while a free link exists; "no suggested provider connected" otherwise. Recommendations only point at providers actually connected - never push new setup.
- **Ledger survives strip_tools**: the tool-stripping layer for untrusted turns (group reply judge) now keeps the job-type tag when rebuilding the engine chain.
- **i18n**: the whole Task routing page is now translated to German (the rt.* block was missing entirely).
- **Vertical per-provider key frames** (Key rotation card): replaces the multi-line paste box with one row per key - numbered tail, burn status, individual × remove; an input + "Add key" button (or Enter) appends keys with no limit, duplicates rejected. New `/key-rings/add` + `/key-rings/remove` endpoints act on single keys without resending the whole ring; removing the last key also clears the primary key field (a ghost key used to survive).
- **Background fallback chain - provider hops** (new card on Task routing page, `settings.model.aux_fallbacks`): the owner orders providers for background work - when a job type's main link dies on quota/runs out of keys it jumps to the next provider, each still rotating its whole key ring first. The chain sits AFTER the primary link and BEFORE the machine-guessed ones (Claude → main brain → OpenRouter free). Unlike the chat chain it also accepts plan-login providers (OpenAI OAuth/Codex-gmail, Grok CLI, Antigravity) because background rotation is engine-level. Example: Gemini (many keys) → Groq → OpenAI OAuth.
- **"Reset all to defaults" requires typing RESET**: one stray click used to wipe the whole routing table - now a type-to-confirm dialog (same as brain deletion), wrong text or Cancel does nothing. The prompt states the real scope: only task_models are cleared, key rings and the chat fallback chain are untouched.

### Fixed
- **Model box gave no suggestions after switching provider** (both chat fallback rows and the background table): the datalist was painted once at render for the old provider, so a new provider kept stale or empty suggestions. Switching provider now repaints suggestions, and dynamic-catalog providers (OpenAI Compatible, Ollama Local/Cloud, Codex) query `/provider/models` for the LIVE list - rows saved earlier load theirs on page open too.

## [1.3.18] - 2026-10-20
### Added
- **Fallback chain for direct chat** (new "Direct chat" card on the Task routing page): the dashboard chat box, Telegram and other direct channels previously only retried transient errors on the same provider - running out of quota killed the turn and made Telegram commands impossible. The owner now configures an ordered chain of fallback brains; when the main brain returns a quota/dead-key error, Joyce walks each link through its own key ring before jumping to the next, inside the same turn, keeping the conversation context and MCP tools.
- **Safe brain switching**: the chain only changes provider before any content has been emitted - once text, a tool_call or usage has gone out, rotation stops immediately because replaying on another provider would duplicate real actions (sending twice, writing twice). Non-quota errors (500, timeouts, unknown models) are not rotated either.
- **User-ordered chain precedes the machine-guessed one on Telegram**: the existing `_fallback_chain` (installed CLIs → Ollama local → Groq → other API) now tries the owner's `chat_fallbacks` first; heuristics run only after. Dashboard chat with a plan-login CLI main keeps previous behavior (a binary cannot be rotated by config).
- **"Direct chat" card on the Task routing page**: shows the active main brain (changed on the Models page), an add/remove/reorder list of API-provider fallbacks; the background table is now titled "BACKGROUND jobs" so it cannot be confused with the chat box.

## [1.3.17] - 2026-10-20
### Added
- **New "Task routing" page** (Connections group, next to Models): lists every kind of background job that actually calls an LLM - reminders/cron, loops, Kanban dispatch, source ingestion, daily brief, group reply policy, agent judge, self-improvement - and assigns each type its own provider/model instead of one shared background model. Each type shows what it does plus a free/sensible provider suggestion; leaving it empty keeps the shared background model from the Models page as before. If the assigned provider dies at runtime, work still falls through the fallback chain.
- **Multi-key rotation per provider**: each API provider (Gemini, Groq, OpenRouter, DeepSeek, OpenAI, Anthropic, Ollama cloud) now accepts several keys from legitimately registered accounts - paste one per line on the Task routing page. A key rejected for quota/429/auth errors is "burned" for a while (inferred from the error: per-minute waits ~1 minute, per-day waits until UTC midnight) and Joyce jumps to the next key within the same turn, before the fallback chain moves to another engine. Burn state persists in `key_burns.json` so a restart does not retry freshly burned keys; the page shows key tails, per-key call counts and a manual unblock button - full keys are never displayed.
- **Per-key attribution**: turns and tokens are credited to the exact key slot in use (identified by fingerprint + last 4 characters), so it is visible which account carries the load without storing raw keys in the ledger.

## [1.3.16] - 2026-10-19
### Fixed
- **Tunnel and link delivery mistook another app's cloudflared**: `tunnel_notify` and the watchdog previously matched any `cloudflared.exe` process, so while H2O Video Studio's own tunnel (port 5170) ran they believed the Joyce tunnel (:7777) was alive - a freshly booted server would open no tunnel and send no Telegram link, and refresh would even kill the other app's tunnel. Detection and kill now match the command line pointing at :7777, keeping both apps' tunnels fully independent.
- **Joyce did not auto-start after boot**: the autostart registration (Run key `JoyceOS` plus two scheduled tasks) had vanished between 18/10 and the 19/10 morning boot, so the server never started and no link was sent - re-registered. If it recurs, suspect a cleanup tool or AV removed the startup entries; check the AV allowlist or flip "auto-start" off/on again in Settings.

## [1.3.15] - 2026-10-19
### Added
- **Head now turns left/right like the reference**: the shader compresses the plate horizontally with yaw (foreshortening) and lets the inner face region slide further than the silhouette edge, reading as roughly a 20-degree head turn instead of a mild tilt. The head follows the pointer or fingertip (with HAND CAM on) and sways gently at rest; the dust-particle layer rotates by the same angle so it never betrays the illusion.
- **Rhythmic speaking response**: the mouth core pulses on a sine beat scaled by loudness, the particle field shimmers harder while speaking, and each voice burst past threshold emits a ripple from the mouth - the frequency reaction reads as a heartbeat instead of a flat line.

## [1.3.14] - 2026-10-19
### Added
- **Real hand tracking via camera in 3D Joyce**: the "HAND CAM" button enables the camera (opt-in only); an on-device MediaPipe HandLandmarker drives the figure - the index fingertip steers its attention, a thumb-index pinch emits an energy ripple, and an open palm calms it. The camera releases on view exit/tab switch, restarts on return, shows a small corner preview, and clearly states nothing leaves the device.
- **Stronger 3D feel**: the figure tilts subtly with pointer/hand movement (parallax shear in the shader) on top of the existing face-attention offset.

### Fixed
- The Joyce hologram card (water-drop avatar + SCANNING) no longer covers the figure's face during calls in the 3D Joyce view - the figure itself is the call face. Switching back to Water Core mid-call brings the card back as before.

## [1.3.13] - 2026-10-19
### Added
- **3D Joyce upgraded to the APEX reference renderer**: the view now runs the apex-humanoid-inspired renderer prepared by Astra (WebP plates + a 2.5D particle field) - a hollow contour figure with a golden brain, braided spine and energy terrain matching the reference, replacing the earlier parameterized figure. Assembly intro, an EXIT button (back to Water Core), touch ripples and pointer attention come built in.
- Joyce's real state and audio still drive the figure: LISTENING/THINKING/SPEAKING switch the correct plate, mic/speaker level agitates the core and mouth band; no second mic pipeline is created.
- **Automatic fallback**: if the APEX renderer, its assets, or its initialization fails, the parameterized particle figure (1.3.12) takes over so the view is never blank. The APEX plates live in `dashboard/humanoid/` and stay local for now (artwork license unverified, not pushed to git).

## [1.3.12] - 2026-10-19
### Added
- **"3D Joyce" view replaces "3D View"**: the brain chamber's first tab now shows a particle humanoid bust built from over 13,000 glowing points (pure WebGL2, no external library) instead of the old high-definition planet mode. The figure reacts to Joyce's real state: drifting gently when ready, leaning in while listening, particles orbiting while thinking, agitating with audio level while speaking, dimming when interrupted, and a red tint on error. The mouth band and the golden brain core pulse with speech.
- Opening the view replays a particle assembly intro; the planet beneath dims into a starry backdrop while its satellites and knowledge stars stay clickable. The choice persists across sessions.
- It inherits the planet's full safety ladder: four quality profiles (high/balanced/safe/reduced), automatic downgrade on low FPS, WebGL context-loss recovery, and prefers-reduced-motion support.

## [1.3.11] - 2026-10-18
### Added
- **Recurring-job scheduling no longer needs mental minute math**: the loop form replaces the raw "interval (minutes)" box with friendly presets (every 15 min, hourly, daily, weekly...) plus custom day-hour-minute fields.
- **Pin a fixed daily run time**: a loop with an interval of one day or more can now run at a fixed clock time (e.g. "daily at 21:00") instead of drifting on the previous run. A new loop waits for the first pinned time after it is enabled; it does not catch up on missed occurrences.
- Job cards, the Overview page, the Handbook and the capability index sent to engines now show intervals in plain words ("daily at 21:00") instead of "every 1445 minutes".

## [1.3.10] - 2026-10-15
### Added
- **Edit a Telegram chat ID after onboarding is live**: in the trainee detail screen of the Roadmap tab, a department head can add, change or remove the chat ID so Joyce messages the daily lesson to the right person. A test-send button shows whether the trainee has pressed Start on the bot.
- **Telegram bot backup**: the Channels page gets a Backup card next to the Telegram card, keeping the token (last 4 characters only) and the chat ID. Joyce saves it whenever the bot runs; if the config is lost, press "Use this backup".

### Fixed
- Telegram, Zalo and API tokens are no longer wiped when Joyce temporarily cannot decrypt them.

## [1.3.9] - 2026-10-15
### Added
- **Roadmap tab**: a department head presses "Activate roadmap" for a new hire, picks a mentor and a start date. Each day's lesson unlocks for the trainee, and with a Telegram chat ID Joyce messages the lesson title at 7am.
- **Auto-graded quizzes at zero quota cost**: trainees take a multiple-choice quiz right in the tab, submit up to twice, with the choices shuffled per person so position guessing does not work.
- **Mentor grades, department head concludes**: Gate 1, weekly survey, the 100-point rubric and must-pass items are entered in the tab. Joyce proposes Pass, Needs more work or Head review with reasons; a person makes the final call.
- The Makeup roadmap ships with 15 lessons (day 0 to 14) drafted from the real Makeup department process. Approved days off shift the schedule automatically.

## [1.3.8] - 2026-10-15
### Added
- **Telegram `/link` command**: message `/link` to the bot to get back the sign-in link to the running Joyce, no need to open the machine.
- **Telegram `/openclaw mo` and `/openclaw tat` commands**: turn the OpenClaw gateway on or off remotely from Telegram.
- On Windows, Joyce now detects Grok Build installed via the x.ai installer (`~/.grok/bin`).

### Fixed
- When the main brain fails and all fallback brains also fail, Joyce reports the real root error (for example an expired login) instead of an error from a brain you did not pick.

## [1.3.7] - 2026-10-11
### Added
- **Research page**: one place to see which stage each concept idea is at, the concept library, related SOPs, trend bulletins and the decision log of the image-concept research department.
- **Idea classification**: ideas sent to a department are labelled as concept, new process or fixing an existing process, so results do not mix.
- **The default mascot is the orange star**, matching the Joyce logo. Anyone who picked their own image keeps it.

## [1.3.6] - 2026-10-10
### Fixed
- The "Today" AI summarizer no longer silently loses items to a swallowed error.
- Windows-style file paths (`E:\...`) in answers only render as links when the file really lives in the brain - no more dead links.
- The Changelog page now loads paged and cached, opens faster and does not reload the whole store each time.
- On Windows: Vietnam time is correct even without timezone data, and background commands no longer pop a black console window.

## [1.3.5] - 2026-10-10
### Added
- **Department heads see their own department**: the Departments and Distilled Documents tabs now appear for heads, limited to their own department. Admins still see everything; regular staff see neither tab.

### Fixed
- Work counts on diagram arrows no longer double-count: an item both stuck and pending review used to add two.
- The "often opened" list in Department Knowledge no longer shows 01/01 dates, and deleted files no longer appear there.
- Department Knowledge now states when documents are still loading instead of silently truncating. The count on top matches all documents.
- Pressing "seen" rapidly or by several people at once no longer loses each other's marks.

## [1.3.4] - 2026-10-09
### Added
- **Pick a whole block in the brain selector**: besides each department there is now `★ Whole Sales block` pinned at the top of each group, with the total note count. From there, asking "block-wide sales" reads data from every department in the block, while writes still go to each department's own brain.
- **Trash with restore**: deleting a file, folder, assistant, skill or workflow now moves it to a trash kept for 30 days instead of gone forever. Open it with the **Trash** button on the Files page; every item has a Restore button.
- **Live Departments tab**: the customer-flow diagram now shows the stuck-work count on each arrow and paints the bottleneck red, so the pinch point is visible at a glance. Support and Accounting run as a strip along the bottom because they touch every stage.
- **Open a process straight from a department**: click a department, view full screen, and the three Before - During - After columns now list the real process files. Clicking one jumps to chat with that department's brain loaded and a pre-filled prompt asking Joyce to review and standardize it.

### Fixed
- Requesting the access link again no longer freezes the server for almost a minute, and the refresh command can actually reopen the tunnel when the old link dies.
- The watchdog no longer turns the tunnel back on when you turned it off on purpose (create `tools/tunnel-off.flag` to keep it off).
- Staff accounts can no longer read plugin source code, where API keys usually live.

## [1.3.3] - 2026-10-08
### Added
- **Drag knowledge crystals**: after a Big Bang, drag any crystal with the mouse or a finger on mobile to a new spot. The dragged crystal lights up, the rest dim, and dropping plays a landing effect. A click without a drag still opens details.
- **3 result view modes** (3 round buttons at the bottom of the screen during a Big Bang):
  - **✦ Sky** (default): keeps positions on the dome.
  - **◎ Orbit**: sorts crystals into 3 concentric rings by size (large/medium/small); dragging an inner-ring crystal moves all 3 rings.
  - **△ Constellation**: sorts them into 3 triangles by size.
- Switching modes plays a 0.6s animation; orbits and triangles draw as dashed outlines.
- **Galaxy panning**: at the galaxy layer (zoomed out), dragging now pans the view instead of rotating the globe, so department spheres at the screen edge can be reached. Double-tap or fly-to resets the pan.
- **Drag spheres and department blocks**: at the galaxy layer, drag a single sphere to a new spot, or drag a block label (e.g. "Accounting") to move the whole cluster. A plain click still flies to the sphere. The cursor becomes a hand over a sphere.
- **Drag triangle groups**: in Constellation mode, dragging any crystal moves its whole triangle group.
- **3D View**: a new button on the view switcher (3D View | Water Core | Star Trail). Turn it on for an HD look: the shader recompiles with 6 fbm octaves, denser background stars in varied sizes with diffraction spikes, random shooting stars in the shader, a black hole with two-turbulence-frequency accretion disk and a richer orange-white gradient, thicker atmosphere, 3-layer specular (120/30/8), wide fresnel with night cyan, improved tone mapping. The 2D canvas also improves: twinkling dust around the planet, random shooting stars, a 512px moon with a softer halo, knowledge crystals with glow, and a sun with 6 rotating corona rays. Good for team presentations. Click "Water Core" to go back to the light mode.
- **Bottom peek zone**: with the eye hidden (Observe mode), hover or touch the area below READY to reveal the 3 view-mode buttons.

### Improved
- Knowledge-crystal click radius grew from 9px to 15px, easier to hit.
- The "Listen" voice-test button now speaks text via TTS instead of a pre-recorded MP3, correctly saying "Joyce".
- The sample line changed from "HoaiMy/NamMinh" to "Joyce".

## [1.3.2] - 2026-10-08
### Improved
- **Handbook → Fanpage**: each Page now has an ↗ button opening the matching Facebook page in a new tab, no more copying the ID into the browser. Clicking the Page name still selects it for reports.

## [1.3.1] - 2026-10-08
### Added
- **Business tab** in the Capabilities group, opening **AI Content Factory**: H2O's content production hub with 8 standard output types (landing page, ad image, carousel, slide, reel cover, ebook, banner, identity kit), a status board, an approval queue, an output library and a Brand Kit for both H2O Studio and ThuyH2O Academy. On-screen numbers are samples; wiring real sources follows the design.
- Saying "open business" or "open the content factory" to Joyce also lands on this page.

## [1.3.0] - 2026-10-08
### Added
- **Department galaxy**: zoom out (or press **Galaxy**) to see 44 department spheres grouped into 11 clusters by block, spiraling around Earth. Each block has its own look: ringed gold Accounting, green HR, stormy orange Marketing, lava Production, crystalline purple Research, ocean Support, icy Cleaning, pink-glitter ThuyH2O...
- Sphere size tracks document count, brightness tracks weekly activity, a red ring marks stuck work, a small black hole marks raw documents, and moons are the department's assistants. Hover for stats.
- **Clicking a department sphere flies to it and switches the open brain** (chat frame and VAULT follow); the sphere carries its block color, and the black hole, Big Bang and light threads behave like Earth's. **← Earth** returns. Picking a department brain in the selector also flies into that sphere.
- Searching VAULT while viewing the galaxy: departments with matching documents light up with a count; clicking one triggers its Big Bang.

## [1.2.2] - 2026-10-08
### Improved
- Removed the curved grey-white streak above the black hole; only fine dust grains now flow into the hole.

## [1.2.1] - 2026-10-08
### Improved
- **The milky band lies flat, slightly tilted, passing behind the sphere** toward the black hole, in blue-violet tones with pink clouds, calm so it does not crowd the sphere.
- **A star-dust ring around the sphere** like a ring: the back half hides behind the sphere, the front half sweeps across its face, rotating very slowly.

## [1.2.0] - 2026-10-08
### Improved
- **The black hole became a swirling accretion disk like the reference photo**: tilted spiral, yellow-white at the core, pink-orange then blue-violet outward, dark rimmed hole, arms that curl as they spin. Looks the same zoomed out or clicked open.
- **Meteor shower when ingestion finishes**: each ingested document is a meteor flying from the black hole toward H2O, flaring orange on atmosphere entry then flashing at the H2O pin. Many documents make a shower. Asking Joyce still draws the light thread as before.

## [1.1.2] - 2026-10-08
### Improved
- **The black hole lies flat like a funnel**: clicking it now shows a funnel viewed from above at an angle, with rock and crystal debris of many sizes spiralling down the throat at the bottom and raw data crystals on the funnel walls - gone is the upright black disc.
- Around the hole in the normal sky, pale rock-colored dust and debris are pulled in, no more neon-blue streaks.

## [1.1.1] - 2026-10-08
### Fixed
- **Knowledge rays now fire with the Codex brain**: before, only the radar sweep appeared without the light threads, because Codex reads files via shell commands and says an opening line first. It now detects the file inside the command, and documents Joyce cites on the "Source" line also become light threads to H2O and "Knowledge source" chips.

## [1.1.0] - 2026-10-08
### Added
- **Knowledge rays when asking Joyce**: sending a question fires a radar sweep across the sky from the H2O pin. Each document Joyce actually reads flashes its star (or rock) and sends a light thread back to H2O. When Joyce starts answering, the threads retract and the H2O pin flashes.
- Data pulled from an H2O app draws the thread from that app's satellite / Sun; from Facebook, Zalo or the Internet it comes from the labelled gate at the left edge. When nothing is read there is only a soft pulse at the globe core - no fake rays.
- **A "Knowledge sources" chip row** under each answer: the documents Joyce read, click to open the file.

## [1.0.9] - 2026-10-08
### Improved
- **Clicking a celestial body now opens in two steps**: first a small summary card (headings, owning department), then the **Open** button on the card opens the full file viewer. Works for files in another department's brain too.

## [1.0.8] - 2026-10-08
### Fixed
- **Raw-document count no longer doubled**: every Word file ships an extracted-text copy, which used to count as a second rock. Now 47 brains report exactly 261 raw documents (previously 477), and Quick-read on a Word file returns real headings.
### Added
- **KNOWLEDGE BANK block in the RECENT SIGNALS frame** (top right): total documents split like the sky - distilled stars (how many processes), skills, Joyce processes, business memory, raw-document rocks, with counts per brand.

## [1.0.7] - 2026-10-08
### Fixed
- **Clicking a star, dot or knowledge sphere opens that file directly** for reading, including files in another department's brain while viewing the merged sky at Brain Default. The Quick-read card is still behind it when the file closes.

## [1.0.6] - 2026-10-08
### Improved
- **Big Bang rebuilt per feedback**: the knowledge sphere keeps its place in the sky and expands in place, its rocky surface now cratered with a milky-band halo. Nearby bodies rush in, explode yellow then distill blue with two light beams; the Sun fades in and the best-matching document shines brightest.
- **The black hole always rotates slowly**, with a dust stream being pulled in and raw documents waiting around; it spins faster while ingesting.
- **Click inside the black hole to look deep**: the accretion disk, the jet, and raw data crystals bearing real file names collide, burst and distill. Click anywhere or press Esc to leave.
- **When ingestion completes**, a light beam hits the H2O Studio pin in Hai Phong, and each freshly distilled document is born as a new star rising from there.

## [1.0.5] - 2026-10-08
### Added
- **Big Bang on search**: type a keyword in the VAULT box and press Enter (or pause typing); the sky dims, related bodies fly to one point, collide into an explosion, then bloom into a **constellation of small spheres** around the globe to pick from.
- An admin at Brain Default searches knowledge from **every department**, not just the open brain. The best match is biggest and centered; linked documents show a light trail between them.
- Hovering a result row lights up its sphere, and vice versa. Click a sphere to Quick-read; clearing the search sends the constellation home.

## [1.0.4] - 2026-10-08
### Added
- **Knowledge sky around the planet**: every document in the brain is a celestial body. Wiki pages are **stars** (processes are four-pointed stars), skills and memories are **dots on the orbit rings**, and raw undistilled documents are **rocks** around the black hole. Colors follow the brand: H2O Studio blue, ThuyH2O pink.
- Hovering a body shows its name and department; clicking shows a **Quick-read** card with the document's headings plus Open and Ask Joyce buttons.
- An admin at Brain Default sees the **merged sky of every department**; opening one department's brain shows only that sky; staff see their own brain's sky. Toggle under Settings → Joyce Interface → Other card.

## [1.0.3] - 2026-10-08
### Improved
- **Back button on top of every page**: after jumping to another page, a button labelled "Back to Command Board" (or the page you left) returns you to the exact spot, including the scrolled position.
- Browser Back, the mouse back button and the edge swipe on phones also go back a page instead of kicking you out of Joyce.
- **Orbit-ring size slider** in Settings → Joyce Interface → Planet (Other tab): drag to enlarge or shrink the three data orbit rings, plus an **orbit-dot size** slider for the asteroids running on the rings.
- **Remove and add Fanpages right inside Handbook → Fanpage**: each Page has a Remove button (only Joyce and AI stop touching that Page; the Facebook Page stays), a removed Page can be re-added with one button, and "Add Page from Facebook" opens the sign-in to tick new Pages.

## [1.0.2] - 2026-10-07
### Improved
- **The lava river flows slowly and spreads like a real river**: the front creeps forward (about 1.5 minutes per run), widening behind it, with dark scorched banks and slow-drifting cooled crust plates on the lava surface.
- **It burns as it goes**: flames flicker at the front, black smoke billows and drifts downwind along the fresh path, with smoldering embers left behind.
- **Lava-flow speed slider** in Settings → Joyce Interface → Planet (Planet Core tab), from 0.2x to 3x.

## [1.0.1] - 2026-10-07
### Added
- **Overview group** at the top of the sidebar with 5 pages: **Command Board**, Today, **Departments**, **Calendar & Plans**, **Reports**. Today is unchanged, just moved into this group.
- **Command Board**: morning brief, 6 work metrics, priority queue, operations pulse by field, department health, today's schedule, system health and recent activity. All real numbers - where no source is connected it says so, no invented figures.
- **Departments**: every department of every brand, stuck-work departments first; clicking opens that brain or asks Joyce. **Calendar** gathers reminders across every brain for 7 days. **Reports** leads to where the numbers live or asks Joyce to write one.
- Saying "open overview" or "open reports" by voice also reaches the right page.

## [1.0.0] - 2026-10-07

### First internal H2O release
- Independent fork from Joyce OS (MIT), keeping LICENSE and original-author credits.
- Removed all outside infrastructure dependencies: no new-version checks, no outside package store, no telemetry; internal docs read via /static/docs/view.html.
- Department-based control panel (46 brains), Handbook page with sub-tabs: Overview, Departments, Fanpage, Zalo.
- First business skills: lead classification, content planning, performance review, comment-to-lead, post-service care.
