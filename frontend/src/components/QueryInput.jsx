/**
 * QueryInput — Hero section with the investigation query input.
 * Features animated gradient border, suggestion chips, and character count.
 */
import { useState, useRef } from 'react'
import useStore from '../store/useStore'
import styles from './QueryInput.module.css'

const SUGGESTION_QUERIES = [
  'Production users are getting 500 errors on /api/users',
  'Login endpoint is returning 401 for valid credentials',
  'Database queries are timing out in the payment service',
  'Memory usage spiking on auth-service pods',
]

export default function QueryInput() {
  const { query, setQuery, submitQuery, sessionStatus, reset } = useStore()
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef(null)

  const isRunning = sessionStatus === 'started'
  const isComplete = sessionStatus === 'complete' || sessionStatus === 'error'

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim() || isRunning) return
    submitQuery(query.trim())
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e)
    }
  }

  const useSuggestion = (s) => {
    setQuery(s)
    textareaRef.current?.focus()
  }

  return (
    <div className={styles.wrapper}>
      {/* Hero Header */}
      <div className={styles.hero}>
        <div className={styles.logoMark}>
          <span className={styles.logoIcon}>✦</span>
        </div>
        <h1 className={styles.heroTitle}>
          DevPilot
          <span className={styles.heroTitleAccent}> AI</span>
        </h1>
        <p className={styles.heroSubtitle}>
          Autonomous engineering agent — describe a production issue and watch it investigate in real-time
        </p>
      </div>

      {/* Query Form */}
      <form className={styles.form} onSubmit={handleSubmit} id="query-form">
        <div className={`${styles.inputWrapper} ${isFocused ? styles.inputWrapperFocused : ''} ${isRunning ? styles.inputWrapperRunning : ''}`}>
          <textarea
            ref={textareaRef}
            id="query-input"
            className={styles.textarea}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. Production users are getting 500 errors on /api/users endpoint…"
            rows={3}
            disabled={isRunning}
            maxLength={2000}
          />
          <div className={styles.inputFooter}>
            <span className={styles.charCount}>{query.length}/2000</span>
            <span className={styles.hint}>⌘ + Enter to submit</span>
          </div>
        </div>

        <div className={styles.actions}>
          {isComplete && (
            <button type="button" className="btn btn--ghost" onClick={reset} id="reset-btn">
              ↺ New Query
            </button>
          )}
          <button
            type="submit"
            className="btn btn--primary btn--lg"
            disabled={!query.trim() || isRunning}
            id="submit-query-btn"
          >
            {isRunning ? (
              <>
                <span className={styles.spinner} />
                Investigating…
              </>
            ) : (
              <>
                <span>⚡</span>
                Investigate
              </>
            )}
          </button>
        </div>
      </form>

      {/* Suggestion Chips */}
      {sessionStatus === 'idle' && (
        <div className={styles.suggestions}>
          <span className={styles.suggestionsLabel}>Try an example:</span>
          <div className={styles.chips}>
            {SUGGESTION_QUERIES.map((s, i) => (
              <button
                key={i}
                className={styles.chip}
                onClick={() => useSuggestion(s)}
                id={`suggestion-${i}`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
