# Design Spec: Overview Tabs Modernization (Phase 1 + Phase 2)

Date: 2026-10-09
Reference: Wriai.com (AI Market Radar + Plan Calendar pages)
Files: `dashboard/console.css` (`.ov-*` classes), `dashboard/overview.js`, `dashboard/console.js` (`.td-*` inline CSS)

## Design Principles (from Wriai reference)

1. **Colored accent borders** - KPI/metric cards use colored left borders (3px) to differentiate categories
2. **Hover lift** - Interactive cards lift 2-3px on hover with expanding box-shadow
3. **Glass panel headers** - Panels use subtle gradient backgrounds on headers (`wash -> transparent`)
4. **Distinct icon colors** - Report cards, domain rows each have a unique color per category
5. **Transition everything** - All interactive elements have 150-200ms transitions
6. **Decorative blobs** - Brief/hero sections have soft circular gradient decorations (pseudo-elements)
7. **Tabular numbers** - All numeric values use `font-variant-numeric: tabular-nums` for alignment
8. **Uppercase labels** - KPI labels are uppercase with letter-spacing for a dashboard feel

## Color Palette per Component

### KPI Cards (`.ov-kpi`, `.td-metric`)
Each card gets a different `border-left-color`:
- Card 1: `var(--accent)` (cyan/teal)
- Card 2: `var(--ok-ink)` (green)
- Card 3: `var(--warn-ink)` (gold/amber)
- Card 4: `var(--danger-ink)` (red)
- Card 5: `var(--info)` (blue)
- Card 6: `var(--text3)` (gray)

Trend arrows added via `.ov-kpi-trend` (icons: `trending-up`, `trending-down`, `minus`).

### Report Cards (`.ov-rep`)
Each report type gets a unique icon background:
1. Daily (sun): `rgba(251,191,36,.15)` / `#f59e0b` (gold) - light: `#b45309`
2. Weekly (trending-up): `rgba(74,222,128,.15)` / `var(--ok-ink)` (green)
3. Department (layers): `rgba(76,145,255,.15)` / `var(--info)` (blue)
4. Social (share-2): `rgba(168,85,247,.15)` / `#a855f7` (purple) - light: `#7c3aed`
5. Knowledge (brain): `rgba(34,211,238,.15)` / `var(--accent)` (cyan)
6. Usage (chart-column): `rgba(99,102,241,.15)` / `#6366f1` (indigo) - light: `#4f46e5`

### Light Theme Overrides
- Brief shadow: `rgba(8,145,178,.08)` instead of cyan
- Primary button shadow: `rgba(14,116,144,.2/.25)` instead of cyan
- Calendar today shadow: `rgba(8,145,178,.1)`
- Report icon colors adjusted darker for contrast

## Interaction Patterns

### Hover Effects
| Component | Effect |
|-----------|--------|
| `.ov-kpi` | `translateY(-2px)` + `box-shadow: 0 4px 16px rgba(0,0,0,.12)` |
| `.ov-dcard` | `translateY(-3px)` + `box-shadow: 0 6px 20px rgba(0,0,0,.1)` + border accent |
| `.ov-rep` | `translateY(-3px)` + `box-shadow: 0 6px 20px rgba(0,0,0,.1)` |
| `.ov-panel` | `box-shadow: 0 2px 8px rgba(0,0,0,.1)` |
| `.ov-prio` | `background: var(--wash)` |
| `.ov-hrow` | `background: var(--wash)` |
| `.ov-deep` | `translateX(3px)` + shadow |
| `.ov-primary` | `translateY(-1px)` + shadow glow |
| `.td-rt` | `translateY(-1px)` + shadow |
| `.td-metric` | `translateY(-2px)` + shadow |
| `.td-app` | `translateY(-1px)` + shadow |
| table rows | `background: var(--wash)` |

### Transitions
- Cards: `transform .18s, box-shadow .18s`
- Buttons: `all .15s ease`
- Panels: `box-shadow .2s`
- Border colors: `.15s`

## Structure by Tab

### Tab 1: Bang dieu hanh (Command Center)
Layout: Brief hero -> 6 KPI cards -> 2-column grid (main + sidebar)
- Main: Priority queue panel, Domain table panel, Units panel
- Sidebar: Schedule panel, System health panel, Memory panel, Activity panel

### Tab 2: Hom nay (Today)
Layout: Header greeting -> Brief card -> Routine checklist -> 6 Metrics -> 2-column panel grid
- Panels: Priority tasks, Schedule, Pulse (live alerts), Apps health, Token usage

### Tab 3: Phong ban (Departments)
Layout: Filter chips toolbar -> Unit summary cards -> Department grid cards (with drawer on click)

### Tab 4: Lich & ke hoach (Calendar)
Layout: Navigation toolbar (prev/today/next) -> 7-column weekly grid
- Each day column contains event cards with time, title, source

### Tab 5: Bao cao (Reports)
Layout: Brief hero -> 3-column report card grid
- Each card: colored icon, title, description, source meta, action buttons

## Phase 2 Roadmap (not yet implemented)

1. **Sparkline SVGs in KPI cards** - Mini line charts showing 7-day trend. Requires API to send `spark: [n1, n2, ..., n7]` in each KPI object.
2. **Monthly calendar view** - Toggle between weekly/monthly. Monthly uses a 7x5 grid. Requires `/api/joyce/v1/overview/calendar?days=35&start=YYYY-MM-01`.
3. **Calendar sidebar** - Right sidebar showing upcoming events list (next 5 items).
4. **Pipeline steps** - Wriai-style numbered horizontal pipeline (01-05) for workflow visualization in Command Center.
5. **Trend percentages** - KPI cards show `+12%` or `-5%` with colored text. Requires API `change_pct` field.
6. **Filter tabs with counts** - Department filter chips show `(count)` badge next to brand name.

## CSS Token Dependencies

All colors use CSS custom properties from `style.css`:
- Backgrounds: `--card`, `--wash`, `--surface-1`, `--surface-2`
- Borders: `--line`, `--hairline`, `--accent-line`
- Text: `--text`, `--text2`, `--text3`
- Semantic: `--accent`, `--accent-ink`, `--ok-ink`, `--warn-ink`, `--danger-ink`, `--info`
- Composite: `--accent-wash`, `--accent-wash-2`, `--ok-bg`, `--warn-bg`, `--danger-bg`

These tokens auto-switch between dark/light themes. Hardcoded colors (report icons) have explicit `:root[data-theme="light"]` overrides.
