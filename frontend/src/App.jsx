/**
 * DevPilot — Main Application
 * 
 * Layout:
 * ┌─────────────────────────────────────────────┐
 * │  Header (logo + connection status)          │
 * ├─────────────────────────────────────────────┤
 * │                                             │
 * │  QueryInput (hero section)                  │
 * │                                             │
 * │  Timeline (agent execution graph)           │
 * │                                             │
 * │  FinalAnswer (synthesized report)           │
 * │                                             │
 * └─────────────────────────────────────────────┘
 * 
 * Overlay: ApprovalModal (shown when agent needs human approval)
 */
import QueryInput from './components/QueryInput'
import Timeline from './components/Timeline'
import FinalAnswer from './components/FinalAnswer'
import ApprovalModal from './components/ApprovalModal'
import useStore from './store/useStore'
import styles from './App.module.css'

function Header() {
  const { isConnected, sessionId, sessionStatus } = useStore()

  return (
    <header className={styles.header} id="app-header">
      <div className={styles.headerLogo}>
        <div className={styles.logoMark}>✦</div>
        <span className={styles.logoText}>DevPilot</span>
        <span className={styles.logoBadge}>AI Agent</span>
      </div>

      <div className={styles.headerRight}>
        {sessionId && (
          <span className={styles.sessionId}>
            Session: {sessionId.slice(0, 8)}…
          </span>
        )}
        <div className={`${styles.connectionStatus} ${isConnected && sessionId ? styles.connectionStatusActive : ''}`}>
          <span className={styles.connectionDot} />
          {isConnected && sessionId ? 'Connected' : 'Ready'}
        </div>
      </div>
    </header>
  )
}

function StatusBar() {
  const { events, agents, sessionStatus } = useStore()

  const stats = {
    events: events.length,
    toolCalls: Object.values(agents).reduce((sum, a) => sum + a.toolCalls.length, 0),
    thoughts: Object.values(agents).reduce((sum, a) => sum + a.thoughts.length, 0),
    agentsDone: Object.values(agents).filter(a => a.status === 'complete').length,
  }

  if (sessionStatus === 'idle') return null

  return (
    <div className={styles.statusBar}>
      <div className={styles.statItem}>
        <span className={styles.statValue}>{stats.events}</span>
        <span className={styles.statLabel}>Events</span>
      </div>
      <div className={styles.statDivider} />
      <div className={styles.statItem}>
        <span className={styles.statValue}>{stats.toolCalls}</span>
        <span className={styles.statLabel}>Tool Calls</span>
      </div>
      <div className={styles.statDivider} />
      <div className={styles.statItem}>
        <span className={styles.statValue}>{stats.thoughts}</span>
        <span className={styles.statLabel}>Thoughts</span>
      </div>
      <div className={styles.statDivider} />
      <div className={styles.statItem}>
        <span className={styles.statValue}>{stats.agentsDone}/4</span>
        <span className={styles.statLabel}>Agents Done</span>
      </div>
    </div>
  )
}

export default function App() {
  const { finalAnswer, sessionStatus } = useStore()

  return (
    <div className={`${styles.app} bg-animated bg-grid`}>
      <Header />

      <main className={styles.main}>
        {/* Query Input — always visible */}
        <section className={styles.querySection}>
          <QueryInput />
        </section>

        {/* Stats Bar */}
        <StatusBar />

        {/* Execution Timeline */}
        <section className={styles.timelineSection}>
          <Timeline />
        </section>

        {/* Final Answer */}
        {finalAnswer && (
          <section className={styles.finalSection}>
            <FinalAnswer answer={finalAnswer} />
          </section>
        )}

        {/* Empty state */}
        {sessionStatus === 'idle' && (
          <div className={styles.emptyState}>
            <div className={styles.emptyGrid}>
              {[
                { icon: '📋', title: 'Log Analysis', desc: 'Searches production logs for error patterns and anomalies' },
                { icon: '💻', title: 'Code Search', desc: 'Finds bugs and suspicious code patterns in your codebase' },
                { icon: '📚', title: 'Runbook Lookup', desc: 'Surfaces relevant runbooks and mitigation procedures' },
                { icon: '⏸', title: 'Human-in-Loop', desc: 'Requires your approval before executing risky commands' },
              ].map((card, i) => (
                <div key={i} className={styles.featureCard} style={{ animationDelay: `${i * 80}ms` }}>
                  <span className={styles.featureIcon}>{card.icon}</span>
                  <h3 className={styles.featureTitle}>{card.title}</h3>
                  <p className={styles.featureDesc}>{card.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Human-in-Loop Modal Overlay */}
      <ApprovalModal />
    </div>
  )
}
