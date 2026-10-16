/**
 * ApprovalModal — Human-in-the-loop approval dialog.
 * 
 * Shown when the DocsAgent (or any agent) surfaces an action that
 * requires human review before execution.
 * 
 * Features:
 * - Command preview with code block
 * - Risk/rollback info
 * - Accept / Reject with optional reason
 * - Timeout countdown
 */
import { useState, useEffect } from 'react'
import useStore from '../store/useStore'
import styles from './ApprovalModal.module.css'

function CountdownTimer({ receivedAt, timeoutSeconds }) {
  const [remaining, setRemaining] = useState(timeoutSeconds)

  useEffect(() => {
    const started = new Date(receivedAt).getTime()
    const interval = setInterval(() => {
      const elapsed = (Date.now() - started) / 1000
      const rem = Math.max(0, timeoutSeconds - Math.floor(elapsed))
      setRemaining(rem)
    }, 1000)
    return () => clearInterval(interval)
  }, [receivedAt, timeoutSeconds])

  const pct = (remaining / timeoutSeconds) * 100
  const isUrgent = remaining < 60

  return (
    <div className={styles.timer}>
      <div className={styles.timerBar}>
        <div
          className={`${styles.timerFill} ${isUrgent ? styles.timerFillUrgent : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`${styles.timerLabel} ${isUrgent ? styles.timerLabelUrgent : ''}`}>
        {remaining > 0 ? `${remaining}s remaining` : 'Timed out'}
      </span>
    </div>
  )
}

function ApprovalCard({ approval, onDismiss }) {
  const { submitApproval } = useStore()
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [decision, setDecision] = useState(null)

  const handleDecision = async (approved) => {
    if (submitting) return
    setSubmitting(true)
    setDecision(approved ? 'approved' : 'rejected')
    await submitApproval(approval.approval_id, approved, reason || null)
    setTimeout(onDismiss, 1200)
  }

  const agentLabel = {
    docs_agent:   'Docs Agent',
    log_agent:    'Log Agent',
    code_agent:   'Code Agent',
    orchestrator: 'Orchestrator',
  }[approval.agent_name] || approval.agent_name

  if (decision) {
    return (
      <div className={`${styles.decisionResult} ${decision === 'approved' ? styles.decisionApproved : styles.decisionRejected}`}>
        <span className={styles.decisionIcon}>{decision === 'approved' ? '✓' : '✗'}</span>
        <span>{decision === 'approved' ? 'Action approved!' : 'Action rejected.'}</span>
      </div>
    )
  }

  return (
    <div className={styles.card} id={`approval-card-${approval.approval_id.slice(0,8)}`}>
      {/* Header */}
      <div className={styles.cardHeader}>
        <div className={styles.agentTag}>
          <span className={styles.agentIcon}>📚</span>
          {agentLabel}
        </div>
        <span className={styles.approvalLabel}>Action Required</span>
      </div>

      {/* Description */}
      <div className={styles.body}>
        <h3 className={styles.actionTitle}>{approval.action_description}</h3>

        {/* Command */}
        {approval.action_data?.command && (
          <div className={styles.commandBlock}>
            <div className={styles.commandHeader}>
              <span>⚡ Command to execute</span>
              <button
                className={styles.copyBtn}
                onClick={() => navigator.clipboard.writeText(approval.action_data.command)}
              >
                Copy
              </button>
            </div>
            <pre className={styles.command}>{approval.action_data.command}</pre>
          </div>
        )}

        {/* Risk & Impact */}
        {(approval.action_data?.risk || approval.action_data?.estimated_impact) && (
          <div className={styles.infoGrid}>
            {approval.action_data.risk && (
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>⚠ Risk</span>
                <p className={styles.infoValue}>{approval.action_data.risk}</p>
              </div>
            )}
            {approval.action_data.estimated_impact && (
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>📊 Impact</span>
                <p className={styles.infoValue}>{approval.action_data.estimated_impact}</p>
              </div>
            )}
            {approval.action_data.rollback && (
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>↩ Rollback</span>
                <pre className={styles.rollbackCmd}>{approval.action_data.rollback}</pre>
              </div>
            )}
          </div>
        )}

        {/* Reason input */}
        <div className={styles.reasonWrapper}>
          <label className={styles.reasonLabel} htmlFor="approval-reason">
            Reason (optional)
          </label>
          <textarea
            id="approval-reason"
            className={`input ${styles.reasonInput}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Add a note about your decision…"
            rows={2}
          />
        </div>

        {/* Timeout */}
        <CountdownTimer
          receivedAt={approval.received_at}
          timeoutSeconds={approval.timeout_seconds}
        />

        {/* Actions */}
        <div className={styles.actions}>
          <button
            id="reject-action-btn"
            className="btn btn--danger"
            onClick={() => handleDecision(false)}
            disabled={submitting}
          >
            ✗ Reject
          </button>
          <button
            id="approve-action-btn"
            className="btn btn--success btn--lg"
            onClick={() => handleDecision(true)}
            disabled={submitting}
          >
            ✓ Approve & Execute
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ApprovalModal() {
  const { pendingApprovals } = useStore()
  const [dismissed, setDismissed] = useState([])

  const visible = pendingApprovals.filter((a) => !dismissed.includes(a.approval_id))

  if (visible.length === 0) return null

  return (
    <div className="modal-overlay" id="approval-modal-overlay">
      <div className={styles.modalInner}>
        <div className={styles.modalTitle}>
          <span className={styles.modalIcon}>⏸</span>
          <div>
            <h2>Human Approval Required</h2>
            <p className={styles.modalDesc}>
              An agent wants to execute a privileged action. Review and approve or reject below.
            </p>
          </div>
        </div>

        <div className={styles.cards}>
          {visible.map((approval) => (
            <ApprovalCard
              key={approval.approval_id}
              approval={approval}
              onDismiss={() => setDismissed((d) => [...d, approval.approval_id])}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
