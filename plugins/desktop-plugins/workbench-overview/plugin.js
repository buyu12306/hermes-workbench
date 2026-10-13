/**
 * 工作台总览 (Workbench Overview) — a desktop pane for the multi-agent workbench.
 *
 * Shows, live: the Bot roster (profiles) with working/idle state, session and
 * routine counts, and one-click jumps to the board / bots / cron / command
 * center. Pure SDK consumer; no backend of its own.
 *
 * v2 「夜航」design pass — presentation-layer refinement only: three-tier
 * BotRow hierarchy, unified 8pt rhythm, scoped hover / keyboard-focus feedback,
 * a quieter empty state. Colors, queries, poll config, event wiring, i18n
 * strings and registration are kept verbatim from the baseline. Single file,
 * zero new dependencies, hot-reload safe.
 *
 * Plain ESM, loaded uncompiled — jsx() calls only. Only these imports resolve:
 * @hermes/plugin-sdk, react, react/jsx-runtime.
 */
import { host, usePluginI18n, useQuery, useQueryClient, useValue } from '@hermes/plugin-sdk'
import { useEffect } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'workbench-overview'

const C = {
  text: 'var(--ui-text-secondary, #c9cdd8)',
  strong: 'var(--ui-text-primary, var(--foreground, #ececec))',
  dim: 'var(--ui-text-quaternary, #8f94a8)',
  accent: 'var(--ui-accent, #f2c14e)',
  border: 'var(--ui-stroke-secondary, rgba(255,255,255,0.12))',
  hover: 'var(--chrome-action-hover, rgba(255,255,255,0.06))'
}

// Scoped interaction feedback for this pane only (wbov- prefix). One mechanic
// per state: hover = a quiet background fill; keyboard focus = a single gold
// edge line. No shadows, no offsets, no stacked effects.
const cssText = [
  '.wbov-quick{background:transparent}',
  '.wbov-row,.wbov-quick{transition:background-color 120ms ease}',
  `.wbov-row:hover,.wbov-quick:hover{background:${C.hover}}`,
  `.wbov-row:focus-visible{outline:1px solid ${C.accent};outline-offset:-1px}`,
  `.wbov-quick:focus-visible{outline:1px solid ${C.accent};outline-offset:1px}`,
  '@media (prefers-reduced-motion: reduce){.wbov-row,.wbov-quick{transition:none}}'
].join('')

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

function Dot({ working }) {
  return jsx('span', {
    style: {
      display: 'inline-block',
      width: '8px',
      height: '8px',
      borderRadius: '9999px',
      background: working ? 'var(--ui-ok, #63c88b)' : 'var(--ui-stroke-secondary, rgba(255,255,255,0.22))',
      flex: 'none'
    }
  })
}

function Stat({ value, label }) {
  return jsxs('div', {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      padding: '8px 12px',
      border: `1px solid ${C.border}`,
      borderRadius: '8px',
      minWidth: '0'
    },
    children: [
      jsx('div', { style: { fontSize: '19px', fontWeight: '600', color: C.strong, lineHeight: '1.2' }, children: value }),
      jsx('div', { style: { fontSize: '12px', color: C.dim }, children: label })
    ]
  })
}

function Quick({ label, path }) {
  return jsx('button', {
    type: 'button',
    className: 'wbov-quick',
    onClick: () => host.navigate(path),
    style: {
      padding: '8px',
      fontSize: '13px',
      color: C.text,
      border: `1px solid ${C.border}`,
      borderRadius: '8px',
      cursor: 'pointer',
      textAlign: 'center',
      whiteSpace: 'nowrap'
    },
    children: label
  })
}

function BotRow({ p, t }) {
  const now = Date.now() / 1000
  const worker = p.worker_session
  const last = p.last_session
  const recent = last && last.last_active && now - (last.last_active > 1e12 ? last.last_active / 1000 : last.last_active) < 120
  const working = Boolean(worker) || Boolean(recent)
  const meta = p.ui_meta && p.ui_meta['hermes-bots']
  const name = (meta && meta.title) || p.display_name || p.name
  const model = String(p.model || '').split('/').pop()
  // Execution engine (真引擎) shown before the orchestration model — e.g.
  // `qoderclicn -p`. Gold = fully automatic, dim = GUI / hand-off. Set per
  // profile in ui_meta['hermes-bots'].engine (+ engine_auto).
  const engine = meta && meta.engine ? String(meta.engine) : ''
  const engineAuto = engine ? meta.engine_auto !== false : false
  const tail = [model, last && last.last_active ? ago(last.last_active, t) : null].filter(Boolean).join(' · ')

  const open = () => host.navigate('/agents')

  // Three signal tiers: name (strongest) > engine (mid, gold/dim semantics) >
  // model · last-active tail (weakest). The row is keyboard-reachable.
  return jsxs('div', {
    className: 'wbov-row',
    role: 'button',
    tabIndex: 0,
    onClick: open,
    onKeyDown: e => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault()
        open()
      }
    },
    title: last && last.title ? last.title : name,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      minHeight: '40px',
      padding: '8px',
      borderRadius: '8px',
      cursor: 'pointer'
    },
    children: [
      Dot({ working }),
      jsxs('div', {
        style: { minWidth: '0', flex: '1' },
        children: [
          jsxs('div', {
            style: { display: 'flex', alignItems: 'baseline', gap: '4px', minWidth: '0' },
            children: [
              jsx('span', {
                style: { fontSize: '15px', fontWeight: '600', color: C.strong, minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
                children: name
              }),
              p.is_default
                ? jsx('span', { style: { fontSize: '11px', color: C.accent, flex: 'none' }, children: t('primary') })
                : null
            ]
          }),
          engine || tail
            ? jsxs('div', {
                style: { display: 'flex', alignItems: 'baseline', gap: '4px', minWidth: '0' },
                children: [
                  engine
                    ? jsx('span', {
                        style: { fontSize: '12px', fontWeight: '500', color: engineAuto ? C.accent : C.dim, flex: 'none', whiteSpace: 'nowrap' },
                        children: engine
                      })
                    : null,
                  engine && tail ? jsx('span', { style: { fontSize: '12px', color: C.dim, flex: 'none' }, children: '·' }) : null,
                  tail
                    ? jsx('span', {
                        style: { fontSize: '11.5px', color: C.dim, minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
                        children: tail
                      })
                    : null
                ]
              })
            : null
        ]
      })
    ]
  })
}

function WorkbenchPane() {
  const t = usePluginI18n(ID)
  const gateway = useValue(host.state.gateway)
  const profile = useValue(host.state.profile)
  const busyBySession = useValue(host.state.busyBySession)
  const qc = useQueryClient()

  // Hidden windows throttle interval timers — stay live via gateway events.
  useEffect(() => {
    let last = 0
    const dispose = host.onEvent('*', () => {
      const now = Date.now()
      if (now - last < 2500) return
      last = now
      qc.invalidateQueries({ queryKey: ['workbench-overview'] })
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
  const { data: roster } = useQuery({
    queryKey: ['workbench-overview', 'profiles'],
    queryFn: () => host.request('profiles.list', { include_sessions: true }),
    refetchInterval: 5000,
    ...poll
  })
  const { data: sessions } = useQuery({
    queryKey: ['workbench-overview', 'sessions'],
    queryFn: () => host.request('session.list', { limit: 200 }),
    refetchInterval: 15000,
    ...poll
  })
  const { data: cron } = useQuery({
    queryKey: ['workbench-overview', 'cron'],
    queryFn: () => host.request('cron.manage', { action: 'list', include_disabled: true }),
    refetchInterval: 30000,
    ...poll
  })

  const profiles = (roster && roster.profiles) || []
  const selfRow = profiles.find(p => p.name === 'default')
  const selfMeta = selfRow && selfRow.ui_meta && selfRow.ui_meta['hermes-bots']
  const selfName = (selfMeta && selfMeta.title) || (selfRow && selfRow.display_name) || t('selfName')
  const sessionCount = sessions && sessions.sessions ? sessions.sessions.length : '–'
  const cronCount = cron && typeof cron.count === 'number' ? cron.count : '–'
  const busyCount = Object.keys(busyBySession || {}).length
  const connOk = gateway === 'connected' || gateway === 'open'

  // One rhythm for the whole pane: 16px between sections, 8px inside grids,
  // 4px half-steps between rows and inline elements.
  return jsxs('div', {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
      height: '100%',
      padding: '16px',
      fontSize: '13px',
      overflow: 'hidden'
    },
    children: [
      jsx('style', { children: cssText }),

      jsxs('div', {
        style: { display: 'flex', alignItems: 'center', gap: '8px' },
        children: [
          jsx('div', { style: { fontSize: '15px', fontWeight: '600', color: C.strong }, children: t('paneTitle') }),
          jsx('div', { style: { flex: '1' } }),
          jsx('span', {
            title: `${t('connLabel')} · ${profile || ''}`,
            style: {
              fontSize: '11.5px',
              color: connOk ? 'var(--ui-ok, #63c88b)' : C.dim,
              border: `1px solid ${C.border}`,
              borderRadius: '9999px',
              padding: '4px 8px'
            },
            children: `${selfName} · ${connOk ? t('connOn') : t('connOff')}`
          })
        ]
      }),

      jsxs('div', {
        style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' },
        children: [
          jsx(Stat, { value: String(sessionCount), label: t('statSessions') }),
          jsx(Stat, { value: String(busyCount), label: t('statBusy') }),
          jsx(Stat, { value: String(cronCount), label: t('statCron') }),
          jsx(Stat, { value: String(profiles.length), label: t('statBots') })
        ]
      }),

      jsx('div', { style: { fontSize: '12px', color: C.dim, letterSpacing: '0.04em', flex: 'none' }, children: t('botsHeader') }),
      jsx('div', {
        style: { display: 'flex', flexDirection: 'column', gap: '4px', flex: '1', minHeight: '40px', overflowY: 'auto' },
        children: profiles.length
          ? profiles.map(p => jsx(BotRow, { p, t }, p.name))
          : jsx('div', {
              style: {
                color: C.dim,
                fontSize: '12px',
                lineHeight: '1.6',
                textAlign: 'center',
                border: `1px dashed ${C.border}`,
                borderRadius: '8px',
                padding: '24px 16px',
                flex: 'none'
              },
              children: t('noBots')
            })
      }),

      jsxs('div', {
        style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', flex: 'none' },
        children: [
          jsx(Quick, { label: t('openGraph'), path: '/workflow' }),
          jsx(Quick, { label: t('openKanban'), path: '/kanban' }),
          jsx(Quick, { label: t('openBots'), path: '/agents' }),
          jsx(Quick, { label: t('openCron'), path: '/cron' }),
          jsx(Quick, { label: t('openCenter'), path: '/command-center' })
        ]
      })
    ]
  })
}

export default {
  id: ID,
  name: '工作台总览',
  description: '工作台总览 — 机器人、会话、例行任务与快捷跳转',
  defaultEnabled: true,
  register(ctx) {
    ctx.i18n.register({
      en: {
        paneTitle: 'Workbench',
        selfName: 'manager',
        statSessions: 'sessions',
        statBusy: 'working',
        statCron: 'routines',
        statBots: 'bots',
        botsHeader: 'BOTS · CLICK TO OPEN',
        noBots: 'No bots yet — create one in the Bots tab.',
        openKanban: 'Board',
        openGraph: 'Workflow',
        openBots: 'Bots',
        openCron: 'Routines',
        openCenter: 'Command Center',
        primary: 'primary',
        justNow: 'just now',
        mAgo: n => `${n}m ago`,
        hAgo: n => `${n}h ago`,
        dAgo: n => `${n}d ago`,
        connLabel: 'connection',
        connOn: 'online',
        connOff: 'offline'
      },
      zh: {
        paneTitle: '工作台总览',
        selfName: '总管',
        statSessions: '会话',
        statBusy: '进行中',
        statCron: '例行',
        statBots: '机器人',
        botsHeader: '机器人 · 点击进入',
        noBots: '还没有机器人——到「机器人」页签里创建。',
        openKanban: '看板',
        openGraph: '工作流图',
        openBots: '机器人',
        openCron: '例行任务',
        openCenter: '指挥中心',
        primary: '主',
        justNow: '刚刚',
        mAgo: n => `${n} 分钟前`,
        hAgo: n => `${n} 小时前`,
        dAgo: n => `${n} 天前`,
        connLabel: '连接',
        connOn: '在线',
        connOff: '离线'
      }
    })

    ctx.register({
      id: 'pane',
      area: 'panes',
      title: ctx.i18n.t('paneTitle'),
      data: { placement: 'right', dock: { pane: 'workspace', pos: 'right' }, width: '280px' },
      render: () => jsx(WorkbenchPane, {})
    })
  }
}
