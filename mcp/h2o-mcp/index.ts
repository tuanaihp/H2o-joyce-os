// H2O MCP GENERIC - Edge Function mau dung cho MOI webapp H2O tren Supabase.
// Copy file nay vao <project>/supabase/functions/h2o-mcp/index.ts roi deploy,
// Joyce doc duoc TOAN BO bang + file R2 cua project do, khong can viet them gi.
//
// Deploy:
//   supabase functions deploy h2o-mcp --no-verify-jwt
//   supabase secrets set H2O_MCP_TOKEN=<chuoi-ngau-nhien>=
//   (tuy chon) H2O_APP_NAME=<ten-app>  H2O_R2_WORKER=<url-worker>  H2O_R2_TOKEN=<jwt>
//   (tuy chon) H2O_MCP_DENY=bang1,bang2  H2O_MCP_ALLOW=bang1,bang2
//
// Cam vao Joyce: trang Ket noi -> Them MCP -> HTTP:
//   URL:    https://<project-ref>.supabase.co/functions/v1/h2o-mcp
//   Header: Authorization: Bearer <H2O_MCP_TOKEN>
//
// Chi doc. Khong co tool ghi/xoa.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.45.4'

// CORS doc lap - khong can _shared/cors.ts, file nay tu chay duoc o moi project.
function corsHeaders(_req: Request, allow = 'content-type, authorization'): HeadersInit {
  return {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'POST, OPTIONS',
    'access-control-allow-headers': allow,
  }
}

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const APP = Deno.env.get('H2O_APP_NAME') || 'h2o-app'
const R2_WORKER = (Deno.env.get('H2O_R2_WORKER') || '').replace(/\/$/, '')
const R2_TOKEN = Deno.env.get('H2O_R2_TOKEN') || ''
const sb = createClient(SUPABASE_URL, SERVICE_KEY)

const SERVER = { name: `h2o-mcp:${APP}`, version: '1.0.0' }
const PROTOCOL = '2025-06-18'

// Bang mac dinh KHONG cho doc (du lieu nhay cam). Ghi de bang H2O_MCP_DENY / H2O_MCP_ALLOW.
const DENY = new Set(
  (Deno.env.get('H2O_MCP_DENY') || 'staff,staff_sessions,profiles,id_counters')
    .split(',').map(s => s.trim()).filter(Boolean),
)
const ALLOW = new Set(
  (Deno.env.get('H2O_MCP_ALLOW') || '').split(',').map(s => s.trim()).filter(Boolean),
)

type Args = Record<string, unknown>
type ToolDef = { name: string; description: string; inputSchema: Record<string, unknown>; run: (a: Args) => Promise<unknown> }

// ---- schema cache: lay danh sach bang + cot tu OpenAPI cua PostgREST ----
let _spec: Record<string, string[]> | null = null
async function spec(): Promise<Record<string, string[]>> {
  if (_spec) return _spec
  const r = await fetch(`${SUPABASE_URL}/rest/v1/`, {
    headers: { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` },
  })
  const j = await r.json()
  const defs = j?.definitions || j?.paths || {}
  const out: Record<string, string[]> = {}
  for (const [name, def] of Object.entries(defs as Record<string, { properties?: Record<string, unknown> }>)) {
    out[name] = Object.keys(def?.properties || {})
  }
  _spec = out
  return out
}
const publicTable = (t: string) => /^[a-zA-Z0-9_]+$/.test(t) && !t.startsWith('_')
const denied = (t: string) => DENY.has(t) || (ALLOW.size > 0 && !ALLOW.has(t))

const lim = (a: Args, def = 50, max = 200) => {
  const n = Number(a.limit)
  return Number.isFinite(n) ? Math.max(1, Math.min(max, Math.floor(n))) : def
}

// filters: [{col, op, val}] - op: eq neq gt gte lt lte like ilike in is cs
const OPS = new Set(['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'ilike', 'in', 'is', 'cs'])
function applyFilters(q: any, filters: unknown, cols: string[]) {
  const arr = Array.isArray(filters) ? filters : []
  let hasDel = false
  for (const f of arr) {
    const col = String((f as Args)?.col || '')
    const op = String((f as Args)?.op || 'eq')
    const val = (f as Args)?.val
    if (!col || !OPS.has(op)) continue
    if (col === 'is_deleted') hasDel = true
    if (op === 'in') q = q.in(col, Array.isArray(val) ? val : String(val).split(','))
    else q = q.filter(col, op, val === undefined ? null : val)
  }
  // Tu dong loc record da xoa mem neu bang co cot is_deleted va caller chua loc
  if (cols.includes('is_deleted') && !hasDel) q = q.eq('is_deleted', false)
  return q
}

const TOOLS: ToolDef[] = [
  {
    name: 'h2o_ping',
    description: 'Kiem tra cong MCP con song: ten app, so bang doc duoc.',
    inputSchema: { type: 'object', properties: {} },
    async run() {
      const s = await spec()
      const ok = Object.keys(s).filter(t => publicTable(t) && !denied(t))
      return { ok: true, app: APP, tables: ok.length, r2: Boolean(R2_WORKER) }
    },
  },
  {
    name: 'h2o_tables',
    description: 'Liet ke moi bang doc duoc kem danh sach cot. Goi dau tien de biet schema.',
    inputSchema: { type: 'object', properties: {} },
    async run() {
      const s = await spec()
      const out: Record<string, string[]> = {}
      for (const [t, cols] of Object.entries(s)) if (publicTable(t) && !denied(t)) out[t] = cols
      return out
    },
  },
  {
    name: 'h2o_count',
    description: 'Dem so dong 1 bang. Args: table, filters (nhu h2o_query).',
    inputSchema: {
      type: 'object',
      properties: { table: { type: 'string' }, filters: { type: 'array' } },
      required: ['table'],
    },
    async run(a) {
      const t = String(a.table || '')
      const s = await spec()
      if (!publicTable(t) || denied(t) || !s[t]) return { error: `Khong doc duoc bang "${t}".` }
      let q = sb.from(t).select('id', { count: 'exact', head: true })
      q = applyFilters(q, a.filters, s[t])
      const { count, error } = await q
      if (error) return { error: error.message }
      return { table: t, count: count ?? 0 }
    },
  },
  {
    name: 'h2o_query',
    description:
      'Doc dong cua bang bat ky. Args: table, select (PostgREST, vd "id,title,created_at"), ' +
      'filters [{col,op,val}] op=eq|neq|gt|gte|lt|lte|like|ilike|in|is|cs, ' +
      'order (vd "created_at.desc"), limit (mac 200), offset. ' +
      'Bang co is_deleted tu dong chi tra record chua xoa.',
    inputSchema: {
      type: 'object',
      properties: {
        table: { type: 'string' },
        select: { type: 'string' },
        filters: { type: 'array' },
        order: { type: 'string' },
        limit: { type: 'number' },
        offset: { type: 'number' },
      },
      required: ['table'],
    },
    async run(a) {
      const t = String(a.table || '')
      const s = await spec()
      if (!publicTable(t) || denied(t) || !s[t]) return { error: `Khong doc duoc bang "${t}".` }
      let q = sb.from(t).select(typeof a.select === 'string' && a.select ? a.select : '*')
      q = applyFilters(q, a.filters, s[t])
      if (typeof a.order === 'string' && a.order) {
        const m = a.order.match(/^([a-zA-Z0-9_]+)\.(asc|desc)$/)
        if (m) q = q.order(m[1], { ascending: m[2] === 'asc' })
      }
      q = q.limit(lim(a))
      if (Number(a.offset) > 0) q = q.range(Math.floor(Number(a.offset)), Math.floor(Number(a.offset)) + lim(a) - 1)
      const { data, error } = await q
      if (error) return { error: error.message }
      return data
    },
  },
  {
    name: 'h2o_r2_ls',
    description: 'Liet ke object tren R2 cua app (can H2O_R2_WORKER + H2O_R2_TOKEN). Args: prefix.',
    inputSchema: { type: 'object', properties: { prefix: { type: 'string' } } },
    async run(a) {
      if (!R2_WORKER || !R2_TOKEN) return { error: 'App chua cau hinh R2 worker.' }
      const u = `${R2_WORKER}/usage?keys=1`
      const r = await fetch(u, { headers: { Authorization: `Bearer ${R2_TOKEN}` } })
      if (!r.ok) return { error: `R2 worker ${r.status}` }
      const j = await r.json()
      const keys: string[] = j.keys || []
      const p = String(a.prefix || '')
      return { totalBytes: j.bytes ?? j.totalBytes ?? null, objects: p ? keys.filter(k => k.startsWith(p)) : keys }
    },
  },
  {
    name: 'h2o_r2_url',
    description: 'Lay link doc 1 file R2 (presigned). Args: key.',
    inputSchema: { type: 'object', properties: { key: { type: 'string' } }, required: ['key'] },
    async run(a) {
      if (!R2_WORKER || !R2_TOKEN) return { error: 'App chua cau hinh R2 worker.' }
      const k = encodeURIComponent(String(a.key || ''))
      const r = await fetch(`${R2_WORKER}/object/${k}`, { headers: { 'X-Sync-Token': R2_TOKEN } })
      if (!r.ok) return { error: `R2 worker ${r.status}` }
      return await r.json().catch(() => ({ raw: true }))
    },
  },
]

const TOOL_INDEX: Record<string, ToolDef> = Object.fromEntries(TOOLS.map(t => [t.name, t]))

Deno.serve(async (req) => {
  const cors = corsHeaders(req, 'content-type, authorization, mcp-session-id')
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { ...cors, 'content-type': 'application/json' } })
  if (req.method === 'OPTIONS') return new Response(null, { headers: cors })
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405)

  const token = Deno.env.get('H2O_MCP_TOKEN') || ''
  if (!token) return json({ error: 'H2O_MCP_TOKEN chua cau hinh.' }, 503)
  if (req.headers.get('authorization') !== `Bearer ${token}`)
    return json({ error: 'Sai hoac thieu Bearer token.' }, 401)

  const msg = await req.json().catch(() => null)
  if (!msg) return json({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'JSON khong hop le.' } })

  const id = msg.id ?? null
  const reply = (result: unknown) => json({ jsonrpc: '2.0', id, result })
  const rpcErr = (code: number, m: string) => json({ jsonrpc: '2.0', id, error: { code, message: m } })

  switch (msg.method) {
    case 'initialize':
      return reply({ protocolVersion: PROTOCOL, capabilities: { tools: {} }, serverInfo: SERVER })
    case 'notifications/initialized':
    case 'initialized':
      return new Response(null, { status: 202, headers: cors })
    case 'ping':
      return reply({})
    case 'tools/list':
      return reply({
        tools: TOOLS.map(t => ({ name: t.name, description: t.description, inputSchema: t.inputSchema })),
      })
    case 'tools/call': {
      const tool = TOOL_INDEX[String(msg.params?.name || '')]
      if (!tool) return rpcErr(-32602, `Khong co tool "${msg.params?.name}".`)
      try {
        const data = await tool.run(msg.params?.arguments || {})
        return reply({ content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] })
      } catch (e) {
        return reply({ content: [{ type: 'text', text: `Loi: ${e instanceof Error ? e.message : String(e)}` }], isError: true })
      }
    }
    default:
      return rpcErr(-32601, `Method "${msg.method}" khong ho tro.`)
  }
})
