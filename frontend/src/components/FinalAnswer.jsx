/**
 * FinalAnswer — Displays the orchestrator's synthesized investigation report.
 * 
 * Shows:
 * - Root cause analysis (Gemini generated)
 * - Confidence score
 * - Evidence sources
 * - Prioritized next steps with copy buttons
 */
import { useState } from 'react'
import styles from './FinalAnswer.module.css'

function ConfidenceBar({ confidence }) {
  const pct = Math.round(confidence * 100)
  const color = pct >= 80 ? '#00d4aa' : pct >= 60 ? '#f59e0b' : '#f43f5e'

  return (
    <div className={styles.confidence}>
      <div className={styles.confidenceBar}>
        <div
          className={styles.confidenceFill}
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className={styles.confidenceLabel} style={{ color }}>
        {pct}% confidence
      </span>
    </div>
  )
}

function NextStep({ step, index }) {
  const [copied, setCopied] = useState(false)
  const hasCommand = step.includes(':') && step.includes(' ')

  const copy = () => {
    navigator.clipboard.writeText(step)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={styles.nextStep} id={`next-step-${index}`}>
      <span className={styles.stepNum}>{index + 1}</span>
      <p className={styles.stepText}>{step}</p>
      <button className={styles.copyStepBtn} onClick={copy} title="Copy">
        {copied ? '✓' : '⎘'}
      </button>
    </div>
  )
}

export default function FinalAnswer({ answer }) {
  if (!answer) return null

  return (
    <div className={styles.wrapper} id="final-answer">
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.headerIcon}>🔬</span>
          <div>
            <h2 className={styles.title}>Investigation Complete</h2>
            <p className={styles.timestamp}>
              {new Date(answer.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
        <ConfidenceBar confidence={answer.confidence} />
      </div>

      {/* Root Cause */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <span>🎯</span> Root Cause Analysis
        </h3>
        <div className={styles.analysisText}>
          {answer.answer.split('\n').filter(Boolean).map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      </div>

      {/* Sources */}
      {answer.sources?.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>
            <span>📎</span> Evidence Sources
          </h3>
          <div className={styles.sources}>
            {answer.sources.map((src, i) => (
              <div key={i} className={styles.source}>
                <span className={styles.sourceType}>{src.type}</span>
                <span className={styles.sourceDesc}>
                  {src.description || src.title || src.file || `${src.count?.toLocaleString()} entries`}
                </span>
                {src.line && <span className={styles.sourceLine}>:{src.line}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Steps */}
      {answer.next_steps?.length > 0 && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>
            <span>⚡</span> Recommended Actions
          </h3>
          <div className={styles.nextSteps}>
            {answer.next_steps.map((step, i) => (
              <NextStep key={i} step={step} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
