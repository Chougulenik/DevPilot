/**
 * AgentCard — Shows a single agent's status, thoughts, tool calls, and findings.
 * Features animated status indicator, collapsible thoughts, tool call timeline.
 */
import { useState } from 'react'
import styles from './AgentCard.module.css'

const STATUS_CONFIG = {
  idle:             { label: 'Idle',     cls: 'idle',     icon: '○' },
  thinking:         { label: 'Thinking', cls: 'thinking', icon: '◐' },
  running:          { label: 'Running',  cls: 'running',  icon: '▶' },
  waiting_approval: { label: 'Approval', cls: 'approval', icon: '⏸' },
  complete:         { label: 'Done',     cls: 'complete', icon: '✓' },
  error:            { label: 'Error',    cls: 'error',    icon: '✗' },
}

const SEVERITY_COLORS = {
  critical:        '#f43f5e',
  high:            '#f59e0b',
  info:            '#6378ff',
  action_required: '#a855f7',
}

function ToolCallItem({ call }) {
  const [expanded, setExpanded] = useState(false)
  const isDone = call.status === 'done'

  return (
    <div className={`${styles.toolCall} ${isDone ? styles.toolCallDone : styles.toolCallPending}`}>
      <button className={styles.toolCallHeader} onClick={() => setExpanded(!expanded)}>
        <span className={styles.toolCallIcon}>{isDone ? '⚡' : '⏳'}</span>
        <span className={styles.toolCallName}>{call.tool_name}</span>
        {isDone && (
          <span className={styles.toolCallDuration}>{call.duration_ms}ms</span>
        )}
        <span className={styles.toolCallChevron}>{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className={styles.toolCallBody}>
          <div className={styles.toolCallSection}>
            <span className={styles.toolCallLabel}>Arguments</span>
            <pre className={styles.toolCallCode}>{JSON.stringify(call.arguments, null, 2)}</pre>
          </div>
          {call.result && (
            <div className={styles.toolCallSection}>
              <span className={styles.toolCallLabel}>Result Preview</span>
              <pre className={styles.toolCallCode}>
                {JSON.stringify(
                  typeof call.result === 'object'
                    ? Object.fromEntries(
                        Object.entries(call.result).slice(0, 4).map(([k, v]) => [
                          k,
                          typeof v === 'object' ? '[...]' : v,
                        ])
                      )
                    : call.result,
                  null,
                  2
                )}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AgentCard({ agent }) {
  const [thoughtsExpanded, setThoughtsExpanded] = useState(true)
  const [findingsExpanded, setFindingsExpanded] = useState(true)

  const statusCfg = STATUS_CONFIG[agent.status] || STATUS_CONFIG.idle
  const hasContent = agent.thoughts.length > 0 || agent.toolCalls.length > 0 || agent.findings.length > 0

  // Calculate duration
  let duration = null
  if (agent.startedAt && agent.completedAt) {
    const ms = new Date(agent.completedAt) - new Date(agent.startedAt)
    duration = ms > 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
  }

  return (
    <div
      className={`${styles.card} ${styles[`card--${statusCfg.cls}`]}`}
      id={`agent-card-${agent.name}`}
    >
      {/* Card Header */}
      <div className={styles.header}>
        <div className={styles.agentInfo}>
          <span className={styles.agentIcon} style={{ background: `${agent.display.color}22`, color: agent.display.color }}>
            {agent.display.icon}
          </span>
          <div>
            <h3 className={styles.agentName}>{agent.display.label}</h3>
            {agent.task && (
              <p className={styles.agentTask}>{agent.task}</p>
            )}
          </div>
        </div>

        <div className={styles.headerRight}>
          {duration && (
            <span className={styles.duration}>{duration}</span>
          )}
          <span className={`${styles.statusBadge} ${styles[`statusBadge--${statusCfg.cls}`]}`}>
            <span className={`${styles.statusDot} ${styles[`statusDot--${statusCfg.cls}`]}`} />
            {statusCfg.label}
          </span>
        </div>
      </div>

      {/* Content */}
      {hasContent && (
        <div className={styles.content}>
          {/* Thoughts */}
          {agent.thoughts.length > 0 && (
            <div className={styles.section}>
              <button
                className={styles.sectionHeader}
                onClick={() => setThoughtsExpanded(!thoughtsExpanded)}
              >
                <span className={styles.sectionIcon}>💭</span>
                <span className={styles.sectionTitle}>Reasoning</span>
                <span className={styles.sectionCount}>{agent.thoughts.length}</span>
                <span className={styles.sectionChevron}>{thoughtsExpanded ? '▲' : '▼'}</span>
              </button>
              {thoughtsExpanded && (
                <div className={styles.thoughts}>
                  {agent.thoughts.map((t, i) => (
                    <div key={i} className={`${styles.thought} fade-in`}>
                      <span className={styles.thoughtIndex}>{i + 1}</span>
                      <p className={styles.thoughtText}>{t}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tool Calls */}
          {agent.toolCalls.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionHeader} style={{ cursor: 'default' }}>
                <span className={styles.sectionIcon}>🔧</span>
                <span className={styles.sectionTitle}>Tool Calls</span>
                <span className={styles.sectionCount}>{agent.toolCalls.length}</span>
              </div>
              <div className={styles.toolCalls}>
                {agent.toolCalls.map((call) => (
                  <ToolCallItem key={call.call_id} call={call} />
                ))}
              </div>
            </div>
          )}

          {/* Findings */}
          {agent.findings.length > 0 && (
            <div className={styles.section}>
              <button
                className={styles.sectionHeader}
                onClick={() => setFindingsExpanded(!findingsExpanded)}
              >
                <span className={styles.sectionIcon}>📌</span>
                <span className={styles.sectionTitle}>Findings</span>
                <span className={styles.sectionCount}>{agent.findings.length}</span>
                <span className={styles.sectionChevron}>{findingsExpanded ? '▲' : '▼'}</span>
              </button>
              {findingsExpanded && (
                <div className={styles.findings}>
                  {agent.findings.map((f, i) => (
                    <div key={i} className={`${styles.finding} fade-in`}>
                      <div
                        className={styles.findingSeverity}
                        style={{ background: SEVERITY_COLORS[f.severity] || '#6378ff' }}
                      />
                      <div className={styles.findingContent}>
                        <span className={styles.findingDesc}>{f.description}</span>
                        {typeof f.value === 'string' && (
                          <p className={styles.findingValue}>{f.value}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Summary */}
          {agent.summary && (
            <div className={styles.summary}>
              <span className={styles.summaryIcon}>✅</span>
              <p className={styles.summaryText}>{agent.summary}</p>
            </div>
          )}

          {/* Error */}
          {agent.error && (
            <div className={styles.errorBox}>
              <span>⚠</span>
              <p>{agent.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
