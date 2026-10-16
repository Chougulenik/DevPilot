/**
 * Timeline — The visual execution timeline showing orchestration graph.
 * 
 * Shows:
 * - Orchestrator node at top
 * - Connecting lines to sub-agents (Log, Code, Docs)
 * - Real-time status updates on each node
 * - Duration counters
 */
import useStore from '../store/useStore'
import AgentCard from './AgentCard'
import styles from './Timeline.module.css'

const AGENT_ORDER = ['orchestrator', 'log_agent', 'code_agent', 'docs_agent']

function ConnectionLine({ fromStatus, toStatus }) {
  const isActive = ['thinking', 'running', 'waiting_approval', 'complete', 'error']
    .includes(toStatus)

  return (
    <div className={`${styles.connector} ${isActive ? styles.connectorActive : ''}`}>
      <div className={styles.connectorLine} />
      {isActive && <div className={styles.connectorDot} />}
    </div>
  )
}

export default function Timeline() {
  const { agents, sessionStatus } = useStore()

  const isActive = sessionStatus === 'started' || sessionStatus === 'complete'
  if (!isActive) return null

  return (
    <div className={styles.timeline} id="agent-timeline">
      <div className={styles.header}>
        <h2 className={styles.title}>
          <span className={styles.titleIcon}>⚡</span>
          Execution Timeline
        </h2>
        <span className={styles.subtitle}>
          {sessionStatus === 'started' ? 'Investigation in progress…' : 'Investigation complete'}
        </span>
      </div>

      <div className={styles.graph}>
        {/* Orchestrator — top level */}
        <div className={styles.orchestratorRow}>
          <AgentCard agent={agents.orchestrator} />
        </div>

        {/* Connection to sub-agents */}
        <div className={styles.branchRow}>
          <div className={styles.branchLine} />
          <div className={styles.branchForks}>
            <div className={styles.fork} />
            <div className={styles.fork} />
            <div className={styles.fork} />
          </div>
        </div>

        {/* Sub-agents — horizontal then vertical */}
        <div className={styles.subAgentsRow}>
          {['log_agent', 'code_agent', 'docs_agent'].map((name) => (
            <div key={name} className={styles.subAgentColumn}>
              <div className={styles.subAgentConnector}>
                <div className={styles.subAgentLine} />
                <div className={`${styles.subAgentDot} ${styles[`dot--${agents[name].status}`]}`} />
              </div>
              <AgentCard agent={agents[name]} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
