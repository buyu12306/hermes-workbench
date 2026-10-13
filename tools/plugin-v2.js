/**
 * 工作流图 (Workflow Graph) v2 — live architecture diagram for the multi-agent workbench.
 *
 * 你 → 总管(default) → 各 agent（软件智能体，一行最多三张、超出双行） → 看板任务池。
 * 数据：profiles.list（状态/在跑会话）+ /api/plugins/workbench-graph/tasks（任务池）
 *       + model.options RPC（点击 agent 卡片上的模型芯片可直接切换其模型）。
 *
 * Plain ESM, loaded uncompiled — jsx() calls only.
 */
import { host, usePluginI18n, useQuery, useQueryClient, useValue, PALETTE_AREA, ROUTES_AREA, SIDEBAR_NAV_AREA } from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'workbench-graph'
let rest = null

const C = {
  text: 'var(--ui-text-secondary, #c9cdd8)',
  strong: 'var(--ui-text-primary, var(--foreground, #ececec))',
  dim: 'color-mix(in srgb, var(--ui-text-quaternary, #8f94a8) 55%, var(--ui-text-primary, var(--foreground, #ececec)))',
  accent: 'var(--ui-accent, #f2c14e)',
  ok: 'var(--ui-ok, #63c88b)',
  warn: 'var(--ui-warn, #f0b64a)',
  err: 'var(--ui-error, #ef6a7a)',
  border: 'var(--ui-stroke-secondary, rgba(255,255,255,0.12))',
  edge: 'color-mix(in srgb, var(--ui-text-secondary) 62%, transparent)',
  cardFill: 'color-mix(in srgb, var(--ui-text-secondary) 8%, transparent)',
  cardFillActive: 'color-mix(in srgb, var(--ui-accent) 18%, transparent)',
  chipFill: 'color-mix(in srgb, var(--ui-text-secondary) 10%, transparent)'
}

const STATUS = {
  triage: { c: '#b58dd8' },
  todo: { c: '#8f94a8' },
  scheduled: { c: '#c3c9d6' },
  ready: { c: '#f0b64a' },
  running: { c: '#63c88b' },
  review: { c: '#6db3f2' },
  blocked: { c: '#ef6a7a' },
  done: { c: '#2f855a' },
  archived: { c: '#62697b' }
}
const LANES = ['triage', 'todo', 'scheduled', 'ready', 'running', 'review', 'blocked', 'done']

// 模型分层标注（高智能优先方案）与兜底目录。
const MODEL_TIER = {
  'deepseek-flash': 'fast',
  'deepseek-v4-pro': 'smart'
}
const MODEL_FALLBACK = ['deepseek-v4-pro', 'deepseek-flash']

// 驱动类型：auto=全自动（可无头执行），half=半自动（图形界面，人机接力）。
const DRIVE = {
  'claude-code': 'auto',
  'deepseek-harness': 'auto',
  qoder: 'auto',
  trae: 'half',
  'trae-solo': 'half',
  workbuddy: 'auto'
}

// 各软件 agent 的「自有模型」——由软件自己供应与计费，不走 Hermes 的 API。
const OWN_MODEL = {
  'claude-code': 'Qwen3.8-Flash（千问网关）',
  'deepseek-harness': 'DeepSeek（Harness 账户）',
  qoder: 'Qwen3.8-Flash（Qoder 托管）',
  trae: 'Trae 内置模型',
  'trae-solo': 'SOLO 内置模型',
  workbuddy: '本地运行时'
}

// 能力卡兜底文案（roster 未带 description 时显示；与 profile descriptions 同步）。
const CAPS = {
  'claude-code': '复杂代码与重构、严谨推理。通道：claude -p 全自动（Qwen3.8-Flash 网关）。计费：千问AI平台按量计费。',
  'deepseek-harness': '通用任务、文档与表格、中文写作。通道：dsh headless 全自动。计费：软件自有 DeepSeek 账户。',
  qoder: '中文工程与代码场景。通道：Qoder 图形界面（半自动）。供模型：Qwen3.8-Flash（Qoder 托管）。计费：Qoder 账户 Credits。',
  trae: 'IDE 协作、前后端编码。通道：图形界面（半自动）。',
  'trae-solo': '端到端独立交付（SOLO）。通道：图形界面（半自动）。',
  workbuddy: '本地文件与数据处理、自动化。通道：图形界面（本地运行时）。'
}

// 参战名单（拖入图中的 agent）本地持久化键。
const SEL_KEY = 'hermes.desktop.workbenchGraph.selection.v1'

function keyActivate(e, fn) {
  if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
    e.preventDefault()
    e.stopPropagation()
    if (fn) fn(e)
  }
}

function statusMeta(s, t) {
  const m = STATUS[s]
  return { label: t('st_' + s), c: m ? m.c : '#8f94a8' }
}

function botTitle(row) {
  const meta = row.ui_meta && row.ui_meta['hermes-bots']
  return (meta && meta.title) || row.display_name || row.name
}
function botColor(row) {
  const meta = row.ui_meta && row.ui_meta['hermes-bots']
  return (meta && meta.color) || '#8f94a8'
}
function botHidden(row) {
  const meta = row.ui_meta && row.ui_meta['hermes-bots']
  return Boolean(meta && meta.hidden)
}
function modelShort(row) {
  const m = row && row.model ? String(row.model) : ''
  return m.split('/').pop()
}
function lastActive(row) {
  const s = row.last_session || row.worker_session
  return (s && (s.last_active || s.started_at)) || 0
}
function isWorking(row, runningCount) {
  if (runningCount > 0) return true
  if (row.worker_session) {
    const la = lastActive(row)
    return la > 0 && Date.now() / 1000 - (la > 1e12 ? la / 1000 : la) < 90
  }
  return false
}
function ago(ts, t) {
  if (!ts) return ''
  const s = Math.max(0, Math.floor(Date.now() / 1000 - (ts > 1e12 ? ts / 1000 : ts)))
  if (s < 90) return t('justNow')
  const m = Math.floor(s / 60)
  if (m < 60) return t('mAgo', m)
  const h = Math.floor(m / 60)
  if (h < 24) return t('hAgo', h)
  return t('dAgo', Math.floor(h / 24))
}

// 右侧软件智能体池的卡片：可拖入图中、可＋加入、⚙ 打开调整抽屉。
function PoolCard({ a, t, b, mo, onAdd, onOpen }) {
  const col = botColor(a)
  const drive = DRIVE[a.name] === 'auto'
  const ok = Boolean(b && b.status === 'ok')
  const smallBtn = { border: `1px solid ${C.border}`, borderRadius: '8px', background: 'transparent', color: C.text, cursor: 'pointer', fontSize: '15px', lineHeight: '22px', padding: '3px 10px', flex: 'none' }
  return jsxs('div', {
    'data-agent': a.name,
    draggable: true,
    onDragStart: e => { try { e.dataTransfer.setData('text/plain', a.name); e.dataTransfer.effectAllowed = 'copy' } catch (err) {} },
    style: { border: `1px solid ${C.border}`, borderRadius: '12px', padding: '9px 10px', marginBottom: '8px', background: C.cardFill, cursor: 'grab' },
    children: [
      jsxs('div', { style: { display: 'flex', alignItems: 'center', gap: '7px' }, children: [
        jsx('span', { style: { width: '9px', height: '9px', borderRadius: '9999px', background: col, flex: 'none' } }),
        jsx('span', { style: { fontSize: '14.5px', fontWeight: '600', color: C.strong, flex: '1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: botTitle(a) }),
        jsx('span', { style: { fontSize: '13px', color: drive ? C.ok : C.dim, flex: 'none' }, children: drive ? t('driveAuto') : t('driveHalf') }),
        jsx('button', { type: 'button', title: t('addHint'), onClick: onAdd, style: smallBtn, 'aria-label': t('ariaAdd', botTitle(a)), children: '＋' }),
        jsx('button', { type: 'button', title: t('details'), onClick: onOpen, style: smallBtn, 'aria-label': t('ariaGear', botTitle(a)), children: '⚙' })
      ] }),
      jsx('div', { style: { fontSize: '13px', marginTop: '3px', color: C.dim }, children: `${t('ownModel')} ${mo || '—'}` }),
      jsx('div', { style: { fontSize: '13.5px', marginTop: '2px', color: ok ? C.ok : C.dim }, children: `${t('balanceLabel')} ${b ? b.text : '…'}` })
    ]
  })
}

// 调整抽屉：能力卡 / 余额 / 派活 / 复制自配置指令 / 加入移出 / 打开会话。
function Drawer({ a, t, b, bm, instr, inGraph, onClose, onAdd, onRemove, onPick }) {
  const [ttl, setTtl] = useState('')
  const [bd, setBd] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [msgErr, setMsgErr] = useState(false)
  const [bBusy, setBBusy] = useState(false)
  const qc = useQueryClient()
  const col = botColor(a)
  const drive = DRIVE[a.name] === 'auto'
  const ok = Boolean(b && b.status === 'ok')
  const refreshBal = () => {
    if (bBusy) return
    setBBusy(true)
    Promise.resolve(rest('/balances?refresh=1'))
      .then(() => qc.invalidateQueries({ queryKey: ['wg', 'balances'] }))
      .catch(() => {})
      .then(() => setBBusy(false))
  }
  const wakeIt = () => {
    setMsg('')
    Promise.resolve(rest('/wake', { method: 'POST', body: { agent: a.name } }))
      .then(r => {
        const good = Boolean(r && r.ok)
        setMsgErr(!good)
        setMsg(good ? (r.note || t('wakeOk')) : t('wakeFail') + ((r && r.error) || ''))
      })
      .catch(err => { setMsgErr(true); setMsg(t('wakeFail') + String(err).slice(0, 60)) })
  }
  const setBm = m => {
    if (!m || m === (bm && bm.current)) return
    setMsg('')
    Promise.resolve(rest('/builtin-model', { method: 'POST', body: { agent: a.name, model: m } }))
      .then(r => {
        const good = Boolean(r && r.ok)
        setMsgErr(!good)
        setMsg(good ? t('bmOk', m) : t('bmFail') + ((r && r.error) || ''))
        if (good) qc.invalidateQueries({ queryKey: ['wg', 'builtinModels'] })
      })
      .catch(err => { setMsgErr(true); setMsg(t('bmFail') + String(err).slice(0, 60)) })
  }
  const sendTask = () => {
    const title = ttl.trim()
    if (!title || busy) return
    setBusy(true)
    setMsg('')
    Promise.resolve(rest('/task', { method: 'POST', body: { assignee: a.name, title, body: bd.trim() } }))
      .then(r => {
        if (r && r.ok) {
          const m = t('dispatched', r.task_id)
          setMsgErr(false)
          setMsg(m)
          setTtl('')
          setBd('')
          try { host.notify && host.notify({ kind: 'success', message: m }) } catch (err) {}
        } else {
          setMsgErr(true)
          setMsg(t('dispatchFailed') + ((r && r.error) || ''))
        }
      })
      .catch(err => { setMsgErr(true); setMsg(t('dispatchFailed') + String(err).slice(0, 60)) })
      .then(() => setBusy(false))
  }
  const copyInstr = () => {
    const txt = instr || ''
    if (!txt) { setMsgErr(true); setMsg(t('noInstr')); return }
    const done = () => { setMsgErr(false); setMsg(t('copied')) }
    const fb = () => { try { const ta = document.createElement('textarea'); ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); done() } catch (err) {} }
    try { navigator.clipboard.writeText(txt).then(done).catch(fb) } catch (err) { fb() }
  }
  const field = { width: '100%', boxSizing: 'border-box', background: 'transparent', border: `1px solid ${C.border}`, borderRadius: '8px', color: C.text, fontSize: '13px', padding: '6px 9px', outline: 'none' }
  const btnS = { border: `1px solid ${C.border}`, borderRadius: '9px', background: 'transparent', color: C.text, cursor: 'pointer', fontSize: '13px', padding: '6px 11px' }
  return jsxs('div', {
    style: { position: 'absolute', top: '0', right: '0', bottom: '0', width: '330px', background: 'color-mix(in srgb, var(--background, #0e1626) 86%, #ffffff)', borderLeft: `1px solid ${C.border}`, padding: '14px 16px', overflowY: 'auto', zIndex: 30, boxShadow: '0 0 24px rgba(0,0,0,0.45)' },
    children: [
      jsxs('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' }, children: [
        jsx('span', { style: { width: '10px', height: '10px', borderRadius: '9999px', background: col, flex: 'none' } }),
        jsx('span', { style: { fontSize: '17px', fontWeight: '600', color: C.strong, flex: '1' }, children: botTitle(a) }),
        jsx('span', { style: { fontSize: '13px', color: drive ? C.ok : C.dim }, children: drive ? t('driveAuto') : t('driveHalf') }),
        jsx('button', { type: 'button', onClick: onClose, style: { border: `1px solid ${C.border}`, borderRadius: '8px', background: 'transparent', color: C.text, cursor: 'pointer', fontSize: '13px', padding: '2px 9px' }, children: '✕' })
      ] }),
      jsx('div', { style: { fontSize: '13px', color: C.dim, marginTop: '9px' }, children: `${t('ownModel')} ${(bm && bm.current) || OWN_MODEL[a.name] || '—'}` }),
      jsxs('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }, children: [
        jsx('span', { style: { fontSize: '13px', color: C.text }, children: t('builtinModel') }),
        bm && bm.editable
          ? jsx('select', {
              value: bm.current,
              onChange: e => setBm(e.target.value),
              style: { background: '#0f1728', border: `1px solid ${C.border}`, borderRadius: '8px', color: C.text, fontSize: '13px', padding: '3px 7px', outline: 'none' },
              children: (bm.options.includes(bm.current) ? bm.options : [bm.current, ...bm.options]).map(o => jsx('option', { value: o, children: o }))
            })
          : jsx('span', { style: { fontSize: '12.5px', color: C.dim }, children: t('inAppHint') })
      ] }),
      jsxs('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }, children: [
        jsx('span', { style: { fontSize: '13px', color: ok ? C.ok : C.dim }, children: `${t('balanceLabel')} ${b ? b.text : '…'}` }),
        jsx('button', { type: 'button', disabled: bBusy, onClick: refreshBal, style: { border: `1px solid ${C.border}`, borderRadius: '8px', background: 'transparent', color: C.dim, cursor: 'pointer', fontSize: '12.5px', padding: '3px 9px' }, children: bBusy ? '…' : t('refreshBal') })
      ] }),
      jsx('div', { style: { fontSize: '13px', color: C.text, lineHeight: '1.6', marginTop: '10px', borderTop: `1px solid ${C.border}`, paddingTop: '10px' }, children: a.description || CAPS[a.name] || t('noDesc') }),
      jsxs('div', { style: { display: 'flex', gap: '6px', marginTop: '13px' }, children: [
        jsx('input', { value: ttl, placeholder: t('taskTitlePh'), onChange: e => setTtl(e.target.value), style: field }),
        jsx('button', { type: 'button', disabled: busy, onClick: sendTask, style: { border: `1px solid ${C.border}`, borderRadius: '8px', background: 'transparent', color: busy ? C.dim : C.text, cursor: 'pointer', fontSize: '13px', padding: '6px 12px', flex: 'none' }, children: busy ? '…' : t('dispatchBtn') })
      ] }),
      jsx('textarea', { value: bd, placeholder: t('taskBodyPh'), rows: 3, onChange: e => setBd(e.target.value), style: Object.assign({}, field, { marginTop: '6px', resize: 'vertical', fontFamily: 'inherit' }) }),
      jsxs('div', { style: { display: 'flex', gap: '8px', marginTop: '11px', flexWrap: 'wrap' }, children: [
        jsx('button', { type: 'button', onClick: copyInstr, style: btnS, children: t('copyInstr') }),
        jsx('button', { type: 'button', onClick: onPick, style: btnS, title: t('modelTip'), children: t('bridgeModel') }),
        jsx('button', { type: 'button', onClick: wakeIt, style: btnS, children: t('wakeBtn') }),
        jsx('button', { type: 'button', onClick: () => { try { host.navigate('/agents') } catch (err) {} }, style: btnS, children: t('openChat') }),
        jsx('button', { type: 'button', onClick: () => { if (inGraph) onRemove(); else onAdd() }, style: btnS, children: inGraph ? t('dRemove') : t('dAdd') })
      ] }),
      jsx('div', { style: { fontSize: '12.5px', color: C.dim, marginTop: '10px' }, children: t('standbyNote') }),
      msg ? jsx('div', { style: { fontSize: '12.5px', color: msgErr ? C.err : C.ok, marginTop: '9px' }, children: msg }) : null
    ]
  })
}

// --- SVG primitives ----------------------------------------------------------

function Card({ x, y, w, h, active, onClick, title, ariaLabel }) {
  return jsx('rect', Object.assign({
    x, y, width: w, height: h, rx: 14,
    fill: active ? C.cardFillActive : C.cardFill,
    stroke: active ? C.accent : C.border,
    strokeWidth: active ? 1.8 : 1,
    style: Object.assign(
      onClick ? { cursor: 'pointer' } : {},
      active ? { filter: 'drop-shadow(0 0 10px color-mix(in srgb, var(--ui-accent, #f2c14e) 32%, transparent))' } : {}
    ),
    onClick: onClick || undefined,
    children: title ? jsx('title', { children: title }) : null
  }, onClick ? {
    role: 'button',
    tabIndex: 0,
    'aria-label': ariaLabel,
    onKeyDown: e => keyActivate(e, onClick)
  } : {}))
}

function Dot({ cx, cy, color, pulse, r }) {
  return jsx('circle', {
    cx, cy, r: r || 5, fill: color,
    className: pulse ? 'wg-anim-pulse' : undefined
  })
}

function L({ x, y, size, color, anchor, weight, children, title }) {
  return jsx('text', {
    x, y, fontSize: size || 13, fill: color || C.text,
    textAnchor: anchor || 'start', fontWeight: weight || '400',
    style: { letterSpacing: '-0.2px', fontVariantNumeric: 'tabular-nums' },
    children: title ? [children, jsx('title', { children: title })] : children
  })
}

// 测宽辅助：SVG text 无 text-overflow 能力，长名需逐字回退截断（复用 L 的字距/数字样式）。
let _mSvg = null
function measureText(str, size, weight) {
  if (typeof document === 'undefined') return 0
  if (!_mSvg || !_mSvg.isConnected) {
    _mSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    _mSvg.setAttribute('width', '0')
    _mSvg.setAttribute('height', '0')
    _mSvg.style.cssText = 'position:absolute;left:-9999px;top:-9999px'
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    t.style.letterSpacing = '-0.2px'
    t.style.fontVariantNumeric = 'tabular-nums'
    _mSvg.appendChild(t)
    document.body.appendChild(_mSvg)
  }
  const t = _mSvg.firstChild
  t.setAttribute('font-size', size)
  t.setAttribute('font-weight', weight || '400')
  t.textContent = String(str)
  try { return t.getComputedTextLength() } catch (e) { return 0 }
}
function fitText(str, size, weight, max) {
  const s0 = String(str)
  if (max >= 1e9 || measureText(s0, size, weight) <= max + 1) return s0
  let s = s0
  while (s.length > 1) {
    s = s.slice(0, -1)
    if (measureText(s + '…', size, weight) <= max + 1) return s + '…'
  }
  return s0.slice(0, 1) + '…'
}

function Edge({ d, active, dim, gold, arrowGold, solid }) {
  return jsxs('g', { children: [
    jsx('path', {
      d, fill: 'none',
      stroke: gold ? C.accent : C.edge,
      strokeWidth: solid ? 1.5 : 1.3,
      markerEnd: (arrowGold ?? (active || gold)) ? 'url(#wg-arrow-gold)' : 'url(#wg-arrow-dim)'
    }),
    active
      ? jsx('path', {
          d, fill: 'none', stroke: C.accent, strokeWidth: 2.2, strokeDasharray: '6 6',
          className: 'wg-anim-dash'
        })
      : null
  ] })
}

function edgePath(x1, y1, x2, y2) {
  const dy = Math.max(24, (y2 - y1) / 2)
  return `M ${x1} ${y1} C ${x1} ${y1 + dy}, ${x2} ${y2 - dy}, ${x2} ${y2}`
}

// --- 模型选择弹层 --------------------------------------------------------------

function ModelPicker({ agent, t, onClose }) {
  const qc = useQueryClient()
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')

  const { data: opts } = useQuery({
    queryKey: ['wg', 'modelOptions'],
    queryFn: () => host.request('model.options', { include_unconfigured: true, explicit_only: false }),
    staleTime: 120000,
    retry: false
  })

  let models = []
  const providers = (opts && opts.providers) || []
  const cur = modelShort(agent)
  const targetProv = agent.provider || 'custom'
  let provRows = providers.filter(p => p.slug === targetProv)
  if (!provRows.length) {
    provRows = providers.filter(p =>
      (p.models || []).some(m => (typeof m === 'string' ? m : m.id || m.name || '') === cur)
    )
  }
  if (!provRows.length) provRows = providers
  for (const p of provRows) {
    for (const m of (p.models || [])) {
      const id = typeof m === 'string' ? m : (m.id || m.name || '')
      if (id) models.push(id)
    }
  }
  models = [...new Set(models.concat(MODEL_FALLBACK))]
  if (!models.length) models = MODEL_FALLBACK.slice()
  if (cur && !models.includes(cur)) models.unshift(cur)

  const switchTo = async model => {
    if (busy) return
    setBusy(model)
    try {
      const res = await host.request('profiles.configure', {
        name: agent.name,
        model,
        provider: agent.provider || 'custom',
        confirm_expensive_model: true
      })
      const okModel = res && res.applied && res.applied.model === true
      if (!okModel) throw new Error(t('switchFail') + JSON.stringify(res && res.applied ? res.applied : res))
      await qc.invalidateQueries({ queryKey: ['wg', 'profiles'] })
      host.notify({ kind: 'info', message: t('switchDone', botTitle(agent), model) })
      onClose()
    } catch (error) {
      setErr(String(error && error.message ? error.message : error).slice(0, 320))
      host.notify({ kind: 'error', message: String(error && error.message ? error.message : error).slice(0, 160) })
      setBusy('')
    }
  }

  return jsxs('div', {
    onClick: onClose,
    style: {
      position: 'absolute', inset: '0', zIndex: '50',
      background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    },
    children: [
      jsxs('div', {
        onClick: e => e.stopPropagation(),
        style: {
          width: '440px', maxHeight: '76%', overflow: 'auto',
          background: 'var(--background, #0e1626)',
          border: `1px solid ${C.border}`, borderRadius: '16px',
          padding: '18px 18px 14px', boxShadow: '0 18px 50px rgba(0,0,0,0.5)'
        },
        children: [
          jsx('div', { style: { fontSize: '16px', fontWeight: '600', color: C.strong }, children: t('switchTitle', botTitle(agent)) }),
          jsx('div', { style: { fontSize: '13px', color: C.dim, margin: '6px 0 12px' }, children: t('switchHint') }),
          err ? jsx('div', { style: { fontSize: '12.5px', color: C.err, margin: '0 0 10px', wordBreak: 'break-all' }, children: err }) : null,
          ...models.map(m =>
            jsxs('button', {
              type: 'button',
              key: m,
              disabled: Boolean(busy),
              onClick: () => switchTo(m),
              style: {
                display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
                padding: '11px 13px', marginBottom: '8px', textAlign: 'left',
                background: m === cur ? C.cardFillActive : 'transparent',
                border: `1px solid ${m === cur ? C.accent : C.border}`,
                borderRadius: '11px', cursor: 'pointer', color: C.text, fontSize: '14px'
              },
              children: [
                jsx('span', { style: { flex: '1' }, children: m }),
                MODEL_TIER[m]
                  ? jsx('span', {
                      style: {
                        fontSize: '12px', padding: '2px 8px', borderRadius: '9999px',
                        color: MODEL_TIER[m] === 'smart' ? '#1a1405' : C.dim,
                        background: MODEL_TIER[m] === 'smart' ? C.accent : C.chipFill,
                        fontWeight: '600'
                      },
                      children: MODEL_TIER[m] === 'smart' ? t('tierSmart') : t('tierFast')
                    })
                  : null,
                m === cur ? jsx('span', { style: { fontSize: '12.5px', color: C.accent }, children: t('current') }) : null,
                busy === m ? jsx('span', { style: { fontSize: '12.5px', color: C.dim }, children: '…' }) : null
              ]
            }, m)
          ),
          jsx('button', {
            type: 'button',
            onClick: onClose,
            style: {
              width: '100%', padding: '9px', marginTop: '4px',
              background: 'transparent', border: `1px solid ${C.border}`,
              borderRadius: '11px', color: C.dim, fontSize: '13px', cursor: 'pointer'
            },
            children: t('close')
          })
        ]
      })
    ]
  })
}

// --- Page --------------------------------------------------------------------

function GraphPage() {
  const t = usePluginI18n(ID)
  const gateway = useValue(host.state.gateway)
  const busyBySession = useValue(host.state.busyBySession)
  const qc = useQueryClient()
  const [picker, setPicker] = useState(null)

  // A hidden Electron window throttles interval timers — gateway events keep the graph live.
  useEffect(() => {
    let last = 0
    const dispose = host.onEvent('*', () => {
      const now = Date.now()
      if (now - last < 2500) return
      last = now
      // Scope the refresh to the two keys that events actually change; balances/instructions/
      // builtinModels keep their own intervals. (opt-round 2026-10-09)
      qc.invalidateQueries({ queryKey: ['wg', 'summary'] })
      qc.invalidateQueries({ queryKey: ['wg', 'profiles'] })
    })
    return () => dispose()
  }, [qc])

  const poll = {
    refetchIntervalInBackground: true,
    refetchOnMount: 'always',
    staleTime: 1000,
    retry: 10,
    retryDelay: attempt => Math.min(30000, 1000 * 2 ** attempt)
  }
  const { data: roster, isError: rosterErr } = useQuery({
    queryKey: ['wg', 'profiles'],
    queryFn: () => host.request('profiles.list', { include_sessions: true }),
    refetchInterval: 10000,
    ...poll
  })
  const { data: tdata, isError: tasksErr, dataUpdatedAt } = useQuery({
    queryKey: ['wg', 'summary'],
    queryFn: () => rest('/summary'),
    refetchInterval: 3000,
    ...poll
  })

  const rows = (roster && roster.profiles) || []
  const manager = rows.find(r => r.name === 'default') || null
  const agents = rows.filter(r => r.name !== 'default' && !botHidden(r))
  const agentStats = (tdata && tdata.agents) || {}
  const statsOf = name => agentStats[name] || { counts: {}, last_done: 0 }
  const byStatus = (tdata && tdata.by_status) || {}
  const running = byStatus.running || 0
  const queue = (byStatus.ready || 0) + (byStatus.todo || 0) + (byStatus.triage || 0) + (byStatus.scheduled || 0)
  const done = byStatus.done || 0

  const busy = Object.keys(busyBySession || {}).length > 0

  // --- 各软件自有账户的余额/积分（后端探测）+ 参战名单（拖入图中） ---
  const { data: bdata } = useQuery({
    queryKey: ['wg', 'balances'],
    queryFn: () => rest('/balances'),
    refetchInterval: 300000,
    staleTime: 60000,
    retry: 3,
    retryDelay: attempt => Math.min(15000, 1000 * 2 ** attempt)
  })
  const { data: instrData } = useQuery({
    queryKey: ['wg', 'instructions'],
    queryFn: () => rest('/instructions'),
    staleTime: 600000,
    retry: 2
  })
  const { data: bmData } = useQuery({
    queryKey: ['wg', 'builtinModels'],
    queryFn: () => rest('/builtin-models'),
    staleTime: 60000,
    refetchInterval: 300000,
    retry: 2
  })
  const bms = (bmData && bmData.models) || {}
  const balances = (bdata && bdata.balances) || {}
  const [sel, setSel] = useState(() => {
    try {
      const v = JSON.parse(localStorage.getItem(SEL_KEY) || '[]')
      return Array.isArray(v) ? v : []
    } catch (err) { return [] }
  })
  const [over, setOver] = useState(false)
  const [drawer, setDrawer] = useState(null)
  const selLoaded = useRef(false)
  useEffect(() => {
    try { localStorage.setItem(SEL_KEY, JSON.stringify(sel)) } catch (err) {}
    if (!selLoaded.current) return
    const id = setTimeout(() => {
      try { Promise.resolve(rest('/selection', { method: 'POST', body: { agents: sel } })).catch(() => {}) } catch (err) {}
    }, 150)
    return () => clearTimeout(id)
  }, [sel])
  useEffect(() => {
    if (selLoaded.current) return
    try {
      Promise.resolve(rest('/selection')).then(d => {
        const ag = (d && d.agents) || []
        if (Array.isArray(ag) && ag.length) {
          setSel(ag)
        } else {
          try { Promise.resolve(rest('/selection', { method: 'POST', body: { agents: sel } })).catch(() => {}) } catch (err) {}
        }
        selLoaded.current = true
      }).catch(() => { selLoaded.current = true })
    } catch (err) { selLoaded.current = true }
  }, [])
  const addAgent = name => setSel(prev => (prev.includes(name) ? prev : [...prev, name]))
  const removeAgent = name => setSel(prev => prev.filter(x => x !== name))

  const W = 1000
  const cx = 500
  // 参战名单（拖入图中的）画进流程图；其余留在右侧池里。
  const selAgents = sel.map(nm => agents.find(a => a.name === nm)).filter(Boolean)
  const n = selAgents.length
  // 每行最多 3 张（k≥4 时旧算法会重叠）：超出自动加行，行距 132u。
  const grid = []
  for (let i = 0; i < selAgents.length; i += 3) grid.push(selAgents.slice(i, i + 3))
  if (!grid.length) grid.push([])
  const ROWY = grid.map((_, r) => 346 + r * 132)
  const BY = 556 + Math.max(0, grid.length - 2) * 132
  const VH = BY + 92
  const placed = grid.flatMap((row, r) =>
    row.map((a, i) => {
      const k = row.length
      const spread = Math.min(720, Math.max(0, k - 1) * 260)
      const x = k <= 1 ? cx : cx - spread / 2 + (spread / (k - 1)) * i
      return { a, x, y: ROWY[r] }
    })
  )
  const now = Date.now() / 1000
  const workingOf = row => isWorking(row, (statsOf(row.name).counts.running) || 0)

  return jsxs('div', {
    style: { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', position: 'relative' },
    children: [
      jsx('style', {
        children: `
          @media (prefers-reduced-motion: no-preference) {
            @keyframes wg-dash { to { stroke-dashoffset: -24; } }
            @keyframes wg-pulse { 0%,100% { opacity: 1 } 50% { opacity: .3 } }
            .wg-anim-dash { animation: wg-dash 1.1s linear infinite; }
            .wg-anim-pulse { animation: wg-pulse 1.6s ease-in-out infinite; }
          }
        `
      }),
      picker ? jsx(ModelPicker, { agent: picker, t, onClose: () => setPicker(null) }) : null,
      drawer && agents.find(a => a.name === drawer)
        ? jsx(Drawer, { a: agents.find(a => a.name === drawer), t, b: balances[drawer], bm: bms[drawer], instr: (instrData && instrData.text) || '', inGraph: sel.includes(drawer), onClose: () => setDrawer(null), onAdd: () => addAgent(drawer), onRemove: () => removeAgent(drawer), onPick: () => setPicker(agents.find(x => x.name === drawer) || null) })
        : null,
      // Header
      jsxs('div', {
        style: { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 18px', borderBottom: `1px solid ${C.border}`, flex: 'none' },
        children: [
          jsx('div', { style: { fontSize: '17.5px', fontWeight: '600', color: C.strong }, children: t('pageTitle') }),
          jsx('div', { style: { fontSize: '13.5px', color: C.dim }, children: t('pageSub') }),
          jsx('div', { style: { flex: '1' } }),
          jsxs('div', {
            style: {
              display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px',
              color: running > 0 ? C.ok : C.dim, border: `1px solid ${C.border}`,
              borderRadius: '9999px', padding: '3px 11px'
            },
            children: [ `${t('running')} ${running} · ${t('queue')} ${queue}` ]
          }),
          jsx('button', {
            type: 'button',
            onClick: () => host.navigate('/kanban'),
            style: { fontSize: '13px', color: C.text, background: 'transparent', border: `1px solid ${C.border}`, borderRadius: '9px', padding: '5px 13px', cursor: 'pointer' },
            children: t('openBoard')
          })
        ]
      }),
      (rosterErr || tasksErr)
        ? jsx('div', { style: { padding: '8px 18px', fontSize: '12.5px', color: C.err, flex: 'none' }, children: t('dataHint') })
        : null,
      // Canvas + 右侧软件智能体池（拖入图中参战）
      jsxs('div', {
        style: { display: 'flex', flex: '1', minHeight: '0' },
        children: [
        jsx('div', {
          'data-dropzone': '1',
          onDragOver: e => { e.preventDefault(); if (!over) setOver(true) },
          onDragLeave: () => setOver(false),
          onDrop: e => { e.preventDefault(); setOver(false); let nm = ''; try { nm = e.dataTransfer.getData('text/plain') } catch (err) {} if (nm) addAgent(nm) },
          style: { flex: '1', minHeight: '0', overflow: 'auto', padding: '10px 18px 14px', borderRadius: '12px', outline: over ? `2px dashed ${C.accent}` : 'none', outlineOffset: '-10px', background: over ? 'color-mix(in srgb, var(--ui-accent, #f2c14e) 5%, transparent)' : 'transparent' },
          children: jsxs('svg', {
          viewBox: `0 0 ${W} ${VH}`,
          preserveAspectRatio: 'xMidYMid meet',
          // minWidth 940: readability floor — narrow windows scroll horizontally rather than shrink text (user rule; 940 per v7 review).
          style: { width: '100%', minWidth: '940px', height: '100%', display: 'block', maxWidth: '1250px', maxHeight: '100%', margin: '0 auto' },
          children: [
            jsx('defs', { children: jsxs('g', { children: [
              jsx('marker', { id: 'wg-arrow-gold', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto-start-reverse', children: jsx('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: C.accent }) }),
              jsx('marker', { id: 'wg-arrow-dim', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto-start-reverse', children: jsx('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: '#7d8596' }) })
            ] }) }),
            // --- edges ---
            Edge({ d: edgePath(cx, 84, cx, 166), active: busy, solid: true, arrowGold: busy, gold: busy }),
            ...placed.map(p =>
              jsx(Edge, { d: edgePath(cx, 260, p.x, p.y - 58), active: workingOf(p.a), solid: true, arrowGold: workingOf(p.a) ? true : false, gold: workingOf(p.a) }, `e${p.a.name}`)
            ),
            Edge({ d: `M 375 210 C 180 214, 64 260, 64 430 L 64 ${BY - 36} C 64 ${BY - 10}, 140 ${BY - 3}, 178 ${BY + 1}`, active: queue > 0 || running > 0, solid: true, arrowGold: true, gold: true }),

            // --- 你 ---
            Card({ x: cx - 85, y: 26, w: 170, h: 58, active: busy }),
            L({ x: cx, y: 52, size: 16.5, color: C.strong, anchor: 'middle', weight: '600', children: t('you') }),
            L({ x: cx, y: 72, size: 13.5, color: C.dim, anchor: 'middle', children: busy ? t('youBusy') : t('youIdle') }),

            // --- 总管 ---
            Card({ x: cx - 125, y: 166, w: 250, h: 94, active: busy || running > 0 }),
            Dot({ cx: cx - 101, cy: 196, color: busy ? C.ok : C.dim, pulse: busy }),
            L({ x: cx - 86, y: 202, size: 17, color: C.strong, weight: '600', children: manager ? botTitle(manager) : t('manager') }),
            L({ x: cx - 101, y: 226, size: 13.5, color: C.dim, children: modelShort(manager) ? `${modelShort(manager)} · ${t('coordinator')}` : t('coordinator') }),
            L({ x: cx - 101, y: 248, size: 13.5, color: C.dim, children: `${t('queue')} ${queue} · ${t('running')} ${running} · ${t('doneLabel')} ${done}` }),

            // --- agents ---
            n === 0
              ? jsxs('g', { children: [
                  jsx('rect', { x: cx - 260, y: 286, width: 520, height: 120, rx: 14, fill: 'transparent', stroke: C.border, strokeDasharray: '6 5', strokeWidth: 1 }),
                  L({ x: cx, y: 336, size: 15.5, color: C.dim, anchor: 'middle', children: t('emptySel') }),
                  L({ x: cx, y: 362, size: 13.5, color: C.dim, anchor: 'middle', children: t('emptySel2') })
                ] })
              : null,
            ...placed.map(({ a, x, y: ay }) => {
              const st = statsOf(a.name)
              const run = st.counts.running || 0
              const rdy = (st.counts.ready || 0) + (st.counts.todo || 0)
              const okN = st.counts.done || 0
              const lastDone = st.last_done || 0
              const working = workingOf(a)
              const justDone = !working && lastDone > 0 && now - lastDone < 90
              const la = lastActive(a)
              const col = botColor(a)
              const bal = balances[a.name]
              const balTxt = bal ? (String(bal.text).length > 15 ? String(bal.text).slice(0, 15) + '…' : String(bal.text)) : '…'
              const stateText = working
                ? t('working')
                : justDone
                  ? `${t('justDone')} · ${ago(lastDone, t)}`
                  : la ? `${t('dormant')} · ${ago(la, t)}` : t('dormant')
              const stateTip = working ? t('working') : t('dormantTip')
              const driveLabel = DRIVE[a.name] === 'auto' ? t('driveAuto') : t('driveHalf')
              return jsxs('g', { children: [
                Card({ x: x - 118, y: ay - 58, w: 236, h: 116, active: working, onClick: () => host.navigate('/agents'), title: a.name, ariaLabel: t('ariaCard', botTitle(a)) }),
                Dot({ cx: x - 98, cy: ay - 34, color: col }),
                L({ x: x - 83, y: ay - 28, size: 16, color: C.strong, weight: '600', title: botTitle(a), children: fitText(botTitle(a), 16, '600', 159 - measureText(driveLabel, 13.5, '400')) }),
                L({ x: x + 82, y: ay - 28, size: 13.5, color: DRIVE[a.name] === 'auto' ? C.ok : C.dim, anchor: 'end', title: t('driveTip'), children: driveLabel }),
                Dot({ cx: x + 98, cy: ay - 34, color: working || justDone ? C.ok : C.dim, pulse: working }),
                // 余额/积分（软件自有账户）
                L({ x: x - 98, y: ay - 4, size: 14, color: bal && bal.status === 'ok' ? C.ok : C.dim, children: `${t('balanceLabel')} ${balTxt}` }),
                L({ x: x - 98, y: ay + 22, size: 13.5, color: working || justDone ? C.ok : C.dim, title: stateTip, children: stateText }),
                L({ x: x - 98, y: ay + 44, size: 13.5, color: C.dim, children: `${t('readyShort')} ${rdy} · ${t('runShort')} ${run} · ${t('doneShort')} ${okN}` }),
                // 调整（打开详情抽屉）
                jsx('g', { style: { cursor: 'pointer' }, onClick: e => { e.stopPropagation(); setDrawer(a.name) }, role: 'button', tabIndex: 0, 'aria-label': t('ariaGear', botTitle(a)), onKeyDown: e => keyActivate(e, () => setDrawer(a.name)), children: [
                  jsx('rect', { x: x + 80, y: ay - 6, width: 30, height: 28, rx: 8, fill: 'transparent', stroke: C.border, strokeWidth: 1, children: jsx('title', { children: t('details') }) }),
                  L({ x: x + 95, y: ay + 14, size: 14, color: C.dim, anchor: 'middle', children: '⚙' })
                ] }),
                // 移出流程图（回到右侧池）
                jsx('g', { style: { cursor: 'pointer' }, onClick: e => { e.stopPropagation(); removeAgent(a.name) }, role: 'button', tabIndex: 0, 'aria-label': t('ariaRemove', botTitle(a)), onKeyDown: e => keyActivate(e, () => removeAgent(a.name)), children: [
                  jsx('rect', { x: x + 80, y: ay + 24, width: 30, height: 28, rx: 8, fill: 'transparent', stroke: C.border, strokeWidth: 1, children: jsx('title', { children: t('removeHint') }) }),
                  L({ x: x + 95, y: ay + 44, size: 14, color: C.dim, anchor: 'middle', children: '✕' })
                ] })
              ] }, a.name)
            }),

            // --- 看板任务池 ---
            jsxs('g', { style: { cursor: 'pointer' }, onClick: () => host.navigate('/kanban'), role: 'button', tabIndex: 0, 'aria-label': t('ariaPool'), onKeyDown: e => keyActivate(e, () => host.navigate('/kanban')), children: [
              Card({ x: 140, y: BY, w: 720, h: 78, active: running > 0 }),
              L({ x: 160, y: BY + 30, size: 15.5, color: C.strong, weight: '600', children: t('boardTitle') }),
              L({ x: 160, y: BY + 52, size: 13.5, color: C.dim, children: t('boardSub') }),
              ...LANES.map((s, i) => {
                const cnt = byStatus[s] || 0
                const meta = statusMeta(s, t)
                const bx = 330 + i * 66
                return jsxs('g', { children: [
                  jsx('rect', { x: bx, y: BY + 16, width: 64, height: 46, rx: 9, fill: C.cardFill, stroke: cnt > 0 ? meta.c : C.border, strokeWidth: cnt > 0 ? 1.5 : 1 }),
                  L({ x: bx + 32, y: BY + 36, size: 17, color: cnt > 0 ? C.strong : C.dim, anchor: 'middle', weight: '600', children: String(cnt) }),
                  L({ x: bx + 32, y: BY + 51, size: 13.5, color: C.dim, anchor: 'middle', children: (s === 'done' ? '✓ ' : s === 'blocked' ? '! ' : s === 'scheduled' ? '◷ ' : '') + meta.label })
                ] }, s)
              })
            ] })
          ]
        })
        }),
        jsxs('div', { style: { width: '248px', flex: 'none', borderLeft: `1px solid ${C.border}`, overflowY: 'auto', padding: '10px 12px' }, children: [
          jsx('div', { style: { fontSize: '15px', fontWeight: '600', color: C.strong }, children: t('poolTitle') }),
          jsx('div', { style: { fontSize: '13.5px', color: C.dim, margin: '3px 0 10px' }, children: t('poolHint') }),
          ...agents.filter(a => !sel.includes(a.name)).map(a => jsx(PoolCard, { key: a.name, a, t, b: balances[a.name], mo: (bms[a.name] && bms[a.name].current) || OWN_MODEL[a.name] || '—', onAdd: () => addAgent(a.name), onOpen: () => setDrawer(a.name) })),
          sel.length ? jsx('div', { style: { marginTop: '4px', fontSize: '13.5px', color: C.dim }, children: t('inGraphNote') }) : null
        ] })
      ] }),
      // Legend
      jsxs('div', {
        style: { display: 'flex', alignItems: 'center', gap: '16px', padding: '9px 18px', borderTop: `1px solid ${C.border}`, fontSize: '13.5px', color: C.dim, flex: 'none' },
        children: [
          jsxs('span', { style: { display: 'flex', alignItems: 'center', gap: '6px' }, children: [
            jsx('span', { style: { width: '20px', height: '2px', background: C.accent } }),
            t('legendDelegation')
          ] }),
          jsxs('span', { style: { display: 'flex', alignItems: 'center', gap: '6px' }, children: [
            jsx('span', { style: { width: '20px', height: '2px', backgroundImage: 'repeating-linear-gradient(90deg, var(--ui-accent, #f2c14e) 0 5px, transparent 5px 9px)' } }),
            t('legendFlow')
          ] }),
          jsxs('span', { style: { display: 'flex', alignItems: 'center', gap: '6px' }, children: [
            jsx('span', { style: { width: '9px', height: '9px', borderRadius: '9999px', background: C.ok } }),
            t('legendWorking')
          ] }),
          jsxs('span', { style: { display: 'flex', alignItems: 'center', gap: '6px' }, children: [
            jsx('span', { style: { width: '9px', height: '9px', borderRadius: '9999px', background: C.dim } }),
            t('legendIdle')
          ] }),
          jsx('span', { style: { flex: '1' } }),
          jsx('span', { children: dataUpdatedAt ? `${t('updatedAt')} ${new Date(dataUpdatedAt).toLocaleTimeString()}` : t('refreshHint') })
        ]
      })
    ]
  })
}

export default {
  id: ID,
  name: 'Workflow Graph',
  description: '工作流图 — 你 → 总管 → 各 agent 的实时架构与任务流',
  defaultEnabled: true,
  register(ctx) {
    rest = ctx.rest

    ctx.i18n.register({
      en: {
        pageTitle: 'Workflow Graph',
        pageSub: 'You → Manager → Agents · live',
        you: 'You',
        youBusy: 'relayed to manager',
        youIdle: 'waiting',
        manager: 'Manager',
        coordinator: 'coordinator',
        queue: 'queue',
        running: 'running',
        doneLabel: 'done',
        working: 'working…',
        justDone: 'just finished',
        idle: 'idle',
        never: 'no runs yet',
        noAgents: 'No agents yet — create one in the Bots tab',
        readyShort: 'ready',
        runShort: 'run',
        doneShort: 'done',
        boardTitle: 'Kanban task pool',
        boardSub: 'agents claim cards here · click to open board',
        openBoard: 'Open board',
        externalsLabel: 'External agents (desktop)',
        dataHint: 'Task data unavailable — backend plugin may not be mounted yet.',
        justNow: 'just now',
        mAgo: n => `${n}m ago`,
        hAgo: n => `${n}h ago`,
        dAgo: n => `${n}d ago`,
        legendWorking: 'working',
        legendIdle: 'dormant (zero cost)',
        legendDelegation: 'delegation',
        legendFlow: 'live task flow',
        refreshHint: 'auto-refresh 3s',
        updatedAt: 'updated at',
        modelLabel: 'model',
        modelTip: 'Click to switch this agent’s model',
        switchTitle: name => `Choose model · ${name}`,
        switchHint: 'Takes effect for this agent’s next tasks.',
        tierFast: 'fast',
        tierSmart: 'high-intelligence',
        driveAuto: 'auto',
        driveHalf: 'hand-off',
        driveTip: 'auto = runs headless in the background; hand-off = GUI software, finish it in the app',
        poolTitle: 'Software agents',
        poolHint: 'Drag onto the graph (or press ＋) to field it · dormant (zero cost) when idle',
        ownModel: 'own model:',
        balanceLabel: 'balance',
        addHint: 'Field this agent',
        removeHint: 'Return to the pool',
        inGraphNote: 'In the graph — these agents take part in the next task.',
        emptySel: 'No agents fielded yet — drag software agents here from the right',
        emptySel2: 'or press ＋ on a card. Fielded agents join the next task.',
        details: 'details',
        collapse: 'collapse',
        noDesc: 'No capability notes yet.',
        taskTitlePh: 'Task title…',
        taskBodyPh: 'Notes (optional)',
        dispatchBtn: 'Dispatch',
        dispatched: id => `Dispatched ${id} — starts within ~1 min`,
        dispatchFailed: 'Dispatch failed: ',
        openChat: 'Open chats page ›',
        noInstr: 'Instruction pack not available yet — backend restart pending.',
        copyInstr: 'Copy self-config instructions',
        copied: 'Copied ✓',
        dAdd: 'Field into graph',
        dRemove: 'Move out of graph',
        refreshBal: 'refresh',
        wakeBtn: 'Wake app',
        wakeOk: 'App launched.',
        wakeFail: 'Wake failed: ',
        bridgeModel: 'bridge model',
        builtinModel: 'built-in model',
        inAppHint: 'choose inside the app, or ask the assistant to tune it via computer-use',
        bmOk: m => `Built-in model → ${m}`,
        bmFail: 'Switch failed: ',
        dormant: 'dormant',
        dormantTip: 'no task = zero processes, zero compute; wakes on dispatch',
        standbyNote: 'Standby: no task → zero processes & compute; dispatch wakes it. Idle apps can be closed and will be woken again when needed.',
        current: 'current',
        close: 'Close',
        switchDone: (name, model) => `${name} → ${model}`,
        switchFail: 'Switch failed: ',
        st_triage: 'Triage', st_todo: 'Todo', st_scheduled: 'Sched.', st_ready: 'Ready',
        st_running: 'Running', st_review: 'Review', st_blocked: 'Blocked', st_done: 'Done', st_archived: 'Archived',
        nav: 'Workflow',
        openGraph: 'Open workflow graph',
        ariaCard: name => `Open chats page of ${name}`,
        ariaGear: name => `Open details of ${name}`,
        ariaRemove: name => `Remove ${name} from graph`,
        ariaPool: 'Open kanban board',
        ariaAdd: name => `Field ${name} into this task`
      },
      zh: {
        pageTitle: '工作流图',
        pageSub: '你 → 总管 → 各 agent · 实时',
        you: '你',
        youBusy: '指令已传达',
        youIdle: '待命',
        manager: '总管',
        coordinator: '协调者',
        queue: '队列',
        running: '运行中',
        doneLabel: '完成',
        working: '工作中…',
        justDone: '刚刚完成',
        idle: '空闲',
        never: '未启动',
        noAgents: '还没有 agent——到「机器人」页签里创建',
        readyShort: '就绪',
        runShort: '运行',
        doneShort: '完成',
        boardTitle: '看板任务池',
        boardSub: 'agent 领卡 · 点击打开看板',
        openBoard: '打开看板',
        externalsLabel: '外部智能体（桌面）',
        dataHint: '任务数据暂不可用——后端插件可能还没挂载。',
        justNow: '刚刚',
        mAgo: n => `${n} 分钟前`,
        hAgo: n => `${n} 小时前`,
        dAgo: n => `${n} 天前`,
        legendWorking: '工作中',
        legendIdle: '休眠（零占用）',
        legendDelegation: '派发',
        legendFlow: '实时任务流',
        refreshHint: '每 3 秒自动刷新',
        updatedAt: '数据更新于',
        modelLabel: '模型',
        modelTip: '点击切换该 agent 的模型',
        switchTitle: name => `切换模型 · ${name}`,
        switchHint: '立即生效，该 agent 的下一个任务起使用新模型。',
        tierFast: '快速',
        tierSmart: '高智能',
        driveAuto: '全自动',
        driveHalf: '半自动',
        driveTip: '全自动=可后台无头执行；半自动=图形界面软件，最后一步在软件里完成',
        poolTitle: '软件智能体池',
        poolHint: '拖入图内（或点 ＋）参战 · 空闲自动休眠（零占用）',
        ownModel: '自有模型',
        balanceLabel: '余额',
        addHint: '加入本次任务',
        removeHint: '移出图（回到右侧）',
        inGraphNote: '已在图内 — 这些 agent 将参加下一次任务。',
        emptySel: '还没有 agent 参加本次任务 — 从右侧把软件智能体拖到这里',
        emptySel2: '或点卡片上的 ＋。拖入的 agent 将参加下一次任务。',
        details: '详情',
        collapse: '收起',
        noDesc: '（暂无能力描述）',
        taskTitlePh: '任务标题…',
        taskBodyPh: '补充说明（可选）',
        dispatchBtn: '派活',
        dispatched: id => `已派发 ${id} · 约 1 分钟内自动开始`,
        dispatchFailed: '派发失败：',
        openChat: '打开会话页 ›',
        noInstr: '指令文本暂不可用——等后端重启后生效。',
        copyInstr: '复制自配置指令',
        copied: '已复制 ✓',
        dAdd: '加入图中',
        dRemove: '移出图',
        refreshBal: '刷新余额',
        wakeBtn: '唤醒软件',
        wakeOk: '已为你打开软件。',
        wakeFail: '唤醒失败：',
        bridgeModel: '桥接模型',
        builtinModel: '内置模型',
        inAppHint: '在软件内选择；或让助手用「电脑操作」代调（直说即可）',
        bmOk: m => `内置模型已切换为 ${m}`,
        bmFail: '切换失败：',
        dormant: '休眠',
        dormantTip: '无任务=零进程零算力；派发任务时自动唤醒',
        standbyNote: '休眠策略：无任务=零进程零算力；派发时自动唤醒。空闲的软件本体可随时关闭，需要时会再唤醒。',
        current: '当前',
        close: '关闭',
        switchDone: (name, model) => `${name} 的模型已切换为 ${model}`,
        switchFail: '切换失败：',
        st_triage: '分诊', st_todo: '待办', st_scheduled: '已排期', st_ready: '就绪',
        st_running: '运行中', st_review: '审查', st_blocked: '受阻', st_done: '完成', st_archived: '归档',
        nav: '工作流图',
        openGraph: '打开工作流图',
        ariaCard: name => `打开 ${name} 的会话页`,
        ariaGear: name => `打开 ${name} 详情`,
        ariaRemove: name => `将 ${name} 移出图`,
        ariaPool: '打开看板任务池',
        ariaAdd: name => `将 ${name} 加入本次任务`
      }
    })

    ctx.register({
      id: 'page',
      area: ROUTES_AREA,
      data: { path: '/workflow' },
      render: () => jsx(GraphPage, {})
    })

    // Label-bearing contributions re-register on locale change (kanban pattern).
    const registerLabels = () =>
      ctx.registerMany([
        {
          id: 'nav',
          area: SIDEBAR_NAV_AREA,
          order: 51,
          data: { codicon: 'type-hierarchy', label: ctx.i18n.t('nav'), path: '/workflow' }
        },
        {
          id: 'open',
          area: PALETTE_AREA,
          data: {
            id: 'workbench-graph.open',
            label: ctx.i18n.t('openGraph'),
            keywords: ['workflow', 'graph', 'agents', '工作流', '架构'],
            run: () => host.navigate('/workflow')
          }
        }
      ])

    let disposeLabels = registerLabels()
    ctx.i18n.onLocaleChange(() => {
      disposeLabels()
      disposeLabels = registerLabels()
    })
  }
}
