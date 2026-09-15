import React, { useEffect, useMemo, useState } from 'react'
import { ROLE, TOKEN, api, sessionIdFromToken } from './api.js'
import Curator from './Curator.jsx'

const MAX_FIELDS = 8
const MARK = { full: '●', partial: '◐', none: '○' }

function Err({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="err" role="alert">
      <b>{error.message}</b>
      {error.hint && <div className="small">{error.hint}</div>}
      {onRetry && <button className="btn-link" onClick={onRetry}>Повторить</button>}
    </div>
  )
}

function Loading({ title }) {
  return (
    <div className="app">
      <div className="head"><h1>{title}</h1><p>Загружаем данные…</p></div>
      <div className="skeleton" /><div className="skeleton" /><div className="skeleton" />
    </div>
  )
}

function Picker({ catalog, selected, toggle, query, setQuery, onNext, busy }) {
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    return catalog.groups
      .map((g) => ({
        ...g,
        items: catalog.items.filter(
          (i) => i.group === g.id && (!q || i.name.toLowerCase().includes(q) || i.code.includes(q))
        ),
      }))
      .filter((g) => g.items.length)
  }, [catalog, query])

  return (
    <>
      <h2>Какие направления вам интересны?</h2>
      <p className="muted small">
        Отметьте до {MAX_FIELDS} направлений — сравним по ним профили вашей школы.
        Это укрупнённые группы: внутри каждой десятки конкретных специальностей.
      </p>
      <input
        className="search"
        placeholder="Поиск: медицина, 09.00.00, право…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Поиск направления"
      />
      {groups.length === 0 && <p className="muted">Ничего не нашлось. Измените запрос.</p>}
      {groups.map((g) => (
        <div key={g.id}>
          <h3>{g.name}</h3>
          {g.items.map((i) => {
            const on = selected.includes(i.code)
            const full = !on && selected.length >= MAX_FIELDS
            return (
              <label key={i.code} className={`opt ${on ? 'on' : ''}`}>
                <input type="checkbox" checked={on} disabled={full} onChange={() => toggle(i.code)} />
                <span>
                  {i.name}
                  <div className="code">{i.code}{i.extra_exam ? ` · ${i.extra_exam}` : ''}</div>
                </span>
              </label>
            )
          })}
        </div>
      ))}
      <div className="sticky">
        <div>
          <button className="btn-primary" disabled={!selected.length || busy} onClick={onNext}>
            {busy ? 'Считаем…' : `Сравнить профили (${selected.length})`}
          </button>
        </div>
      </div>
    </>
  )
}

function ProfileCard({ p, subjects, top }) {
  const [open, setOpen] = useState(top)
  const name = (id) => subjects.find((s) => s.id === id)?.name || id
  return (
    <div className={`card ${top ? 'top' : ''}`}>
      <div className="row">
        <div>
          <h2>{p.profile_name}</h2>
          <div className="muted small">Углублённо: {p.advanced.map(name).join(', ') || '—'}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="big">{p.available}/{p.total}</div>
          <div className="muted small">{p.percent}%</div>
        </div>
      </div>
      <div className="bar"><i style={{ width: `${p.percent}%` }} /></div>
      <div className="muted small">
        {p.full > 0 ? `Полностью закрыто направлений: ${p.full}` : 'Полностью закрытых направлений нет'}
      </div>

      <button className="btn-link" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? 'Свернуть разбор' : 'Показать разбор по направлениям'}
      </button>

      {open && (
        <div>
          {p.fields.map((f) => (
            <div className="field" key={f.code}>
              <span className={`dot ${f.status}`}>{MARK[f.status]}</span>
              <span>
                {f.name}
                {f.status === 'partial' && <span className="muted"> — доступна часть вузов</span>}
                {f.status === 'none' && (
                  <span className="muted">
                    {' '}— не хватает:{' '}
                    {[f.gap_required.map(name).join(', '),
                      f.gap_options.length ? `один из: ${f.gap_options.map(name).join(', ')}` : '']
                      .filter(Boolean).join('; ')}
                  </span>
                )}
              </span>
            </div>
          ))}
          {p.advice && (
            <div className="note">
              <b>Что спросить в школе.</b> Если добрать {p.advice.add.map(name).join(' и ')}
              {p.advice.elective_in_school ? ' (школа предлагает это элективом)' : ' (такого электива в школе пока нет)'},
              вернётся направлений: {p.advice.gain}.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const sid = useMemo(() => sessionIdFromToken(TOKEN), [])
  const [screen, setScreen] = useState('loading')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [catalog, setCatalog] = useState(null)
  const [session, setSession] = useState(null)
  const [meta, setMeta] = useState(null)
  const [selected, setSelected] = useState([])
  const [extra, setExtra] = useState([])
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (ROLE === 'curator') { setScreen('curator'); return }
    if (!TOKEN || !sid) {
      setError({ message: 'Нет ссылки на анкету',
        hint: 'Откройте мини-приложение кнопкой в чат-боте «Профиль 10».' })
      setScreen('error')
      return
    }
    Promise.all([api.fields(), api.session(sid), api.meta()])
      .then(([c, s, m]) => {
        setCatalog(c); setSession(s); setMeta(m)
        setSelected(s.selected_fields || []); setExtra(s.extra_subjects || [])
        setScreen('pick')
      })
      .catch((e) => { setError(e); setScreen('error') })
  }, [sid])

  const toggle = (code) =>
    setSelected((cur) => cur.includes(code)
      ? cur.filter((c) => c !== code)
      : cur.length >= MAX_FIELDS ? cur : [...cur, code])

  async function compute(nextExtra = extra) {
    setBusy(true); setError(null)
    try {
      const r = await api.match(sid, { selected_fields: selected, extra_subjects: nextExtra })
      setResult(r); setScreen('result')
      window.scrollTo({ top: 0 })
    } catch (e) { setError(e) } finally { setBusy(false) }
  }

  async function send(profileId) {
    setBusy(true); setError(null)
    try {
      await api.decide(sid, { profile_id: profileId, remind: true })
      setScreen('sent')
    } catch (e) { setError(e) } finally { setBusy(false) }
  }

  if (screen === 'curator') return <Curator />
  if (screen === 'loading') return <Loading title="Профиль 10" />

  if (screen === 'error') {
    return (
      <div className="app">
        <div className="head"><h1>Профиль 10</h1></div>
        <Err error={error} onRetry={() => window.location.reload()} />
      </div>
    )
  }

  if (screen === 'sent') {
    return (
      <div className="app ok-screen">
        <div className="big">✓</div>
        <h2>Разбор отправлен в чат</h2>
        <p className="muted">
          Карточку можно показать родителям и классному руководителю.
          Напоминание о сроке подачи заявления придёт в чат заранее.
        </p>
        <button className="btn-ghost" onClick={() => setScreen('result')}>Вернуться к сравнению</button>
      </div>
    )
  }

  const school = session?.school
  const adm = session?.admission

  return (
    <div className="app">
      <div className="head">
        <h1>Профиль 10</h1>
        <p>{school?.name}, {school?.city} · класс {session?.class_code}</p>
      </div>
      <Err error={error} />

      {screen === 'pick' && (
        <Picker catalog={catalog} selected={selected} toggle={toggle} query={query}
                setQuery={setQuery} onNext={() => compute()} busy={busy} />
      )}

      {screen === 'result' && result && (
        <>
          <button className="btn-link" onClick={() => setScreen('pick')}>← Изменить выбор направлений</button>
          <h2>Сравнение профилей</h2>
          <p className="muted small">
            По {result.selected_fields.length} выбранным направлениям. Чем выше доля — тем больше
            ваших направлений остаётся доступно после 11 класса.
          </p>
          <div className="legend">
            <span><span className="dot full">●</span> доступны все вузы</span>
            <span><span className="dot partial">◐</span> часть вузов</span>
            <span><span className="dot none">○</span> недоступно</span>
          </div>

          <div className="card">
            <b className="small">Готовы добрать предмет самостоятельно или элективом?</b>
            <p className="muted small">Отметьте — пересчитаем все профили с учётом этого.</p>
            <div className="chips">
              {result.subjects.filter((s) => s.id !== 'rus').map((s) => {
                const on = extra.includes(s.id)
                return (
                  <button key={s.id} className={`chip ${on ? 'on' : ''}`} disabled={busy}
                          onClick={() => {
                            const next = on ? extra.filter((x) => x !== s.id) : [...extra, s.id]
                            setExtra(next); compute(next)
                          }}>
                    {on ? '✓ ' : '+ '}{s.name}
                  </button>
                )
              })}
            </div>
            {busy && <p className="muted small">Пересчитываем…</p>}
          </div>

          {result.profiles.map((p, i) => (
            <ProfileCard key={p.profile_id} p={p} subjects={result.subjects} top={i === 0} />
          ))}

          <h3>Отправить разбор в чат</h3>
          <p className="muted small">
            Выберите профиль, который рассматриваете — карточка с разбором придёт в чат,
            вместе с напоминанием о сроке подачи заявления ({adm?.deadline}).
          </p>
          <div className="chips">
            {result.profiles.map((p) => (
              <button key={p.profile_id} className="chip" disabled={busy} onClick={() => send(p.profile_id)}>
                {p.profile_name}
              </button>
            ))}
          </div>

          <div className="footer">
            Расчёт информационный: он показывает, какие вступительные испытания требует направление,
            и не заменяет правила приёма конкретного вуза и решение школы.<br />
            Справочник вступительных испытаний: версия {result.data.fields}, обновлён{' '}
            {result.data.fields_updated_at}. {meta?.data?.demo_data && 'Данные демонстрационные.'}
          </div>
        </>
      )}
    </div>
  )
}
