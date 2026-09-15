import React, { useState } from 'react'
import { api } from './api.js'

// Экран классного руководителя или завуча: обезличенный агрегат по классу.
// Открывается ссылкой с ?role=curator — отдельный вход по коду куратора.
export default function Curator() {
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [head, setHead] = useState(null)

  async function login(e) {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const auth = await api.curatorAuth(code.trim())
      const stats = await api.analytics(auth.class.code, auth.token)
      setHead(auth); setData(stats)
    } catch (err) { setError(err) } finally { setBusy(false) }
  }

  if (!data) {
    return (
      <div className="app">
        <div className="head">
          <h1>Профиль 10 · класс</h1>
          <p>Обезличенная сводка по классу для классного руководителя</p>
        </div>
        {error && (
          <div className="err" role="alert">
            <b>{error.message}</b>
            {error.hint && <div className="small">{error.hint}</div>}
          </div>
        )}
        <form className="card" onSubmit={login}>
          <label className="small"><b>Код куратора</b></label>
          <input className="search" value={code} onChange={(e) => setCode(e.target.value)}
                 placeholder="KUR-114-9A" aria-label="Код куратора" style={{ marginTop: 8 }} />
          <button className="btn-primary" disabled={busy || code.trim().length < 3}>
            {busy ? 'Проверяем…' : 'Открыть сводку'}
          </button>
        </form>
        <div className="footer">
          Сводка не содержит идентификаторов учеников и открывается только при достаточном
          числе анкет — по ней нельзя узнать ответ конкретного ребёнка.
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="head">
        <h1>{head.class.title} · {data.school.name}</h1>
        <p>{data.filled} заполненных анкет из {data.started} начатых</p>
      </div>

      {data.status === 'insufficient_data' ? (
        <div className="card">
          <h2>Сводка пока закрыта</h2>
          <p className="muted small">{data.message}</p>
        </div>
      ) : (
        <>
          <div className="card">
            <h2>Что выбирают</h2>
            {data.profile_demand.length === 0 && <p className="muted small">Пока никто не зафиксировал выбор.</p>}
            {data.profile_demand.map((p) => (
              <div className="field spread" key={p.profile_id}><span>{p.name}</span><b>{p.students}</b></div>
            ))}
            <p className="muted small" style={{ marginTop: 10 }}>
              Изменили первоначальный выбор после расчёта: {data.changed_mind.count} из {data.changed_mind.of}.
            </p>
          </div>

          <div className="card">
            <h2>Самые востребованные направления</h2>
            {data.top_fields.map((f) => (
              <div className="field spread" key={f.code}><span>{f.name}</span><b>{f.students}</b></div>
            ))}
          </div>

          <div className="card">
            <h2>Запросы, которые школа не закрывает</h2>
            {data.uncovered_fields.length === 0 ? (
              <p className="muted small">Все отмеченные направления закрываются существующими профилями.</p>
            ) : (
              data.uncovered_fields.map((f) => (
                <div className="field spread" key={f.code}><span>{f.name}</span><b>{f.students}</b></div>
              ))
            )}
            {data.best_elective && (
              <div className="note">
                <b>Одно действие с наибольшим эффектом.</b> Добавить {data.best_elective.subject_name} в
                профиль «{data.best_elective.profile_name}»
                {data.best_elective.elective_in_school ? ' (электив уже заявлен)' : ''} — это вернёт
                направлений: {data.best_elective.returns_fields.length}, их отметили{' '}
                {data.best_elective.affected_students} учеников.
              </div>
            )}
          </div>
        </>
      )}

      <div className="footer">{data.privacy_note}</div>
    </div>
  )
}
