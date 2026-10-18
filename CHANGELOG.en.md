# Changelog - H2O Joyce OS

*[Tiếng Việt](CHANGELOG.md) · **English***

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
