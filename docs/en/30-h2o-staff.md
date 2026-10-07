# H2O Staff: own account, own models, own rights

*[Tiếng Việt](../30-nhan-vien-h2o.md) · **English***

Joyce lets every H2O employee have a personal account on the same Joyce server: sign in with a **phone number + PIN**, see their own name on the toolbar, use only **the models an admin granted**, and work in **their own chat channel**, isolated from admin and colleagues.

The goal: one Joyce machine running 24/7 as the hub; employees only need a browser - no admin password, no access to system configuration.

## Where to open it

Left sidebar, **System** group, **Staff** item (right above Account). Only admins see the full management table.

## Admin: managing staff

The Staff page has a list plus add/edit forms. Each staff member has:

| Field | Meaning |
| --- | --- |
| Name | Shows on the screen chip and as the Today viewer |
| Phone | Login username - unique |
| PIN | 4-8 digits; the server stores only the hash, never the raw PIN |
| Role | CEO / Director / Manager / Specialist / Staff / Intern - currently a display LABEL, it does not drive permissions yet |
| Granted models | Tick individual models or "all models of a provider". Fully empty = can use everything |
| Workspace | Private working folder, created automatically on add |
| On/off | Off = account dies immediately, old cookies included |

Wrong PIN entered repeatedly locks the IP temporarily - it shares the brute-force guard with the admin login.

## Staff: sign in and work

1. The login screen has a **"H2O staff (phone + PIN)"** link - click to switch the fields to phone + PIN.
2. Once inside, a **name chip** sits on the model bar. Click it -> confirm -> sign out.
3. The model picker **only lists granted models** - unlisted models are neither visible nor callable (the server enforces it, not just hidden UI).
4. Staff chat sessions are bound to channel `staff:<id>` - admins see them in the session filter; staff A cannot read/rename/delete staff B's or admin's sessions (404 both ways).
5. Opening Settings shows only **their own info card** (name, role, phone, granted models).
6. A first-time staff sign-in lands straight on the **Today** page instead of the cockpit.

## What staff CANNOT do

Enforced at the server layer (`_staff_blocked` in main.py), not just hidden buttons:

- **Writes blocked** to: settings, tokens, plugins, MCP, packs, channels, models, brains, reminders, kanban, workflows, agents, skills, loops, projects, inbox, Telegram, Zalo, h2o-staff (no managing colleagues).
- **Reads blocked too**: `/files`, `/vault`, `/ingest` - vault files are the admin's ledger.
- Reading lists is still allowed (kanban, agents...) because the team needs to see shared work.
- WebSocket `/ws` requires a valid staff cookie; a `chat`-scoped API key cannot reach admin paths.
- The same machine (localhost) remains a legacy trust zone - agent-local endpoints skip the cookie; the staff fence applies to network/tunnel access.

## For developers: where to upgrade

| To change | Touch |
| --- | --- |
| Add a role | `ROLES` in `server/h2o_staff.py` + the `<select>` in `renderStaffPage` (console.js) + i18n `staff.role_*` |
| Change which APIs staff are denied | `_STAFF_DENY` / `_STAFF_DENY_ALL` in `server/main.py` (~line 16218) |
| Staff login / sessions | `server/h2o_staff.py` (`create`, `login`, `staff_by_token`, `revoke`); cookie `h2o_staff` |
| PIN brute-force guard | `h2o_staff.login` reuses admin `_login_fail`/`_login_ok` in main.py |
| Model ACL | enforced in the `/chat` flow (main.py) + `dashboard/model-picker.js` reading `window.__h2oStaff` |
| Name chip + logout | `initAuthGate` in `dashboard/app.js` (~line 4125) |
| Staff admin page | `renderStaffPage` + `_staffSelfCard` in `dashboard/console.js`; i18n `page.staff.*`, `staff.*` |
| Private workspace | `staff_workspaces/` under the state dir (already gitignored); created in `h2o_staff.create` |

APIs: `GET/POST /h2o-staff`, `POST /h2o-staff/{id}/update|pin|toggle|delete` (admin), `POST /staff/login`, `GET /staff/me`, `POST /staff/logout` (last three are public). Data lives in `h2o_staff.json` in the state dir - PINs stored hash+salt, and the file is already in `.gitignore`.

Remember when upgrading: roles are currently labels only - to make a role drive permissions (e.g. Intern read-only) wire it into `_staff_blocked`/`_staff_req`, not the UI. The permission test matrix lives in `tests/` (see the `staff`/`sessions_kenh` tests).
