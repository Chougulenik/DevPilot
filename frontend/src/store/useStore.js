/**
 * DevPilot Global State Store (Zustand)
 *
 * Manages:
 * - Session state (id, query, status)
 * - SSE event stream (all events received)
 * - Agent states (per-agent status, thoughts, findings)
 * - Pending approvals
 * - Final answer
 */
import { create } from 'zustand'

const API_BASE = 'http://localhost:8000'

// Agent names matching the backend AgentName enum
export const AGENT_NAMES = {
  ORCHESTRATOR: 'orchestrator',
  LOG_AGENT: 'log_agent',
  CODE_AGENT: 'code_agent',
  DOCS_AGENT: 'docs_agent',
}

const AGENT_DISPLAY = {
  orchestrator: { label: 'Orchestrator', icon: '🧠', color: '#6378ff' },
  log_agent:    { label: 'Log Agent',    icon: '📋', color: '#f59e0b' },
  code_agent:   { label: 'Code Agent',   icon: '💻', color: '#00d4aa' },
  docs_agent:   { label: 'Docs Agent',   icon: '📚', color: '#a855f7' },
}

const initialAgentState = (name) => ({
  name,
  display: AGENT_DISPLAY[name],
  status: 'idle',
  task: null,
  thoughts: [],
  toolCalls: [],
  findings: [],
  summary: null,
  startedAt: null,
  completedAt: null,
  error: null,
})

const useStore = create((set, get) => ({
  // ---- Session State ----
  sessionId: null,
  query: '',
  sessionStatus: 'idle', // idle | started | complete | error
  startedAt: null,

  // ---- SSE Events (raw) ----
  events: [],

  // ---- Agent States ----
  agents: {
    orchestrator: initialAgentState('orchestrator'),
    log_agent:    initialAgentState('log_agent'),
    code_agent:   initialAgentState('code_agent'),
    docs_agent:   initialAgentState('docs_agent'),
  },

  // ---- Pending Approvals ----
  pendingApprovals: [], // [{ approval_id, agent_name, action_description, action_data, timeout }]

  // ---- Final Answer ----
  finalAnswer: null,

  // ---- Connection State ----
  isConnected: false,
  eventSource: null,

  // ---- UI State ----
  selectedEvent: null,
  logFilter: 'all', // all | error | tool | thought

  // ================================================================
  // Actions
  // ================================================================

  setQuery: (query) => set({ query }),

  /**
   * Submit a new investigation query to the backend.
   * Creates session, then starts SSE stream.
   */
  submitQuery: async (query) => {
    const { connectSSE } = get()

    set({
      query,
      sessionStatus: 'started',
      startedAt: new Date().toISOString(),
      events: [],
      finalAnswer: null,
      pendingApprovals: [],
      agents: {
        orchestrator: initialAgentState('orchestrator'),
        log_agent:    initialAgentState('log_agent'),
        code_agent:   initialAgentState('code_agent'),
        docs_agent:   initialAgentState('docs_agent'),
      },
    })

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`)
      }

      const data = await response.json()
      set({ sessionId: data.session_id })

      // Connect SSE stream
      connectSSE(data.session_id)

    } catch (err) {
      set({ sessionStatus: 'error' })
      console.error('Failed to submit query:', err)
    }
  },

  /**
   * Open SSE connection for a session and handle all event types.
   */
  connectSSE: (sessionId) => {
    const { eventSource: existing } = get()
    if (existing) existing.close()

    const es = new EventSource(`${API_BASE}/stream/${sessionId}`)

    es.onopen = () => {
      set({ isConnected: true })
    }

    es.onerror = (err) => {
      console.error('SSE error:', err)
      set({ isConnected: false })
      // Auto-reconnect is handled natively by EventSource
    }

    // Handle typed events
    const eventTypes = [
      'session_created', 'session_complete', 'session_error',
      'orchestrator_start', 'orchestrator_thought', 'orchestrator_complete',
      'agent_start', 'agent_thought', 'agent_complete', 'agent_error',
      'tool_call', 'tool_result',
      'approval_required', 'approval_received',
      'final_answer', 'heartbeat',
    ]

    eventTypes.forEach((type) => {
      es.addEventListener(type, (e) => {
        const payload = JSON.parse(e.data)
        get().handleEvent(type, payload)
      })
    })

    set({ eventSource: es, isConnected: true })
  },

  /**
   * Central event dispatcher — updates state based on event type.
   */
  handleEvent: (type, payload) => {
    set((state) => {
      // Always append to raw events list
      const newEvents = [...state.events, { type, payload, receivedAt: new Date().toISOString() }]

      // Clone agents for mutation
      const agents = { ...state.agents }

      const agentKey = payload.agent_name
      if (agentKey && agents[agentKey]) {
        agents[agentKey] = { ...agents[agentKey] }
      }

      let sessionStatus = state.sessionStatus
      let finalAnswer = state.finalAnswer
      let pendingApprovals = state.pendingApprovals

      switch (type) {
        // ---- Session ----
        case 'session_created':
          sessionStatus = 'started'
          break

        case 'session_complete':
          sessionStatus = 'complete'
          break

        case 'session_error':
          sessionStatus = 'error'
          break

        // ---- Orchestrator ----
        case 'orchestrator_start':
          agents.orchestrator = {
            ...agents.orchestrator,
            status: 'thinking',
            startedAt: payload.timestamp,
          }
          break

        case 'orchestrator_thought':
          agents.orchestrator = {
            ...agents.orchestrator,
            status: 'thinking',
            thoughts: [...agents.orchestrator.thoughts, payload.thought],
          }
          break

        case 'orchestrator_complete':
          agents.orchestrator = {
            ...agents.orchestrator,
            status: 'complete',
            completedAt: payload.timestamp,
          }
          break

        // ---- Sub-Agents ----
        case 'agent_start':
          if (agentKey) {
            agents[agentKey] = {
              ...agents[agentKey],
              status: 'running',
              task: payload.task,
              startedAt: payload.timestamp,
            }
          }
          break

        case 'agent_thought':
          if (agentKey) {
            agents[agentKey] = {
              ...agents[agentKey],
              status: 'thinking',
              thoughts: [...(agents[agentKey].thoughts || []), payload.thought],
            }
          }
          break

        case 'agent_complete':
          if (agentKey) {
            agents[agentKey] = {
              ...agents[agentKey],
              status: 'complete',
              summary: payload.summary,
              findings: payload.findings || [],
              completedAt: payload.timestamp,
            }
          }
          break

        case 'agent_error':
          if (agentKey) {
            agents[agentKey] = {
              ...agents[agentKey],
              status: 'error',
              error: payload.error,
              completedAt: payload.timestamp,
            }
          }
          break

        // ---- Tools ----
        case 'tool_call':
          if (agentKey) {
            agents[agentKey] = {
              ...agents[agentKey],
              toolCalls: [
                ...(agents[agentKey].toolCalls || []),
                {
                  call_id: payload.call_id,
                  tool_name: payload.tool_name,
                  arguments: payload.arguments,
                  timestamp: payload.timestamp,
                  status: 'pending',
                  result: null,
                },
              ],
            }
          }
          break

        case 'tool_result':
          if (agentKey) {
            const updatedCalls = (agents[agentKey].toolCalls || []).map((tc) =>
              tc.call_id === payload.call_id
                ? { ...tc, status: 'done', result: payload.result, duration_ms: payload.duration_ms }
                : tc
            )
            agents[agentKey] = { ...agents[agentKey], toolCalls: updatedCalls }
          }
          break

        // ---- Approvals ----
        case 'approval_required':
          pendingApprovals = [
            ...pendingApprovals,
            {
              approval_id: payload.approval_id,
              agent_name: payload.agent_name,
              action_description: payload.action_description,
              action_data: payload.action_data,
              timeout_seconds: payload.timeout_seconds,
              received_at: payload.timestamp,
            },
          ]
          if (agentKey) {
            agents[agentKey] = { ...agents[agentKey], status: 'waiting_approval' }
          }
          break

        case 'approval_received':
          pendingApprovals = pendingApprovals.filter(
            (a) => a.approval_id !== payload.approval_id
          )
          break

        // ---- Final Answer ----
        case 'final_answer':
          finalAnswer = {
            answer: payload.answer,
            confidence: payload.confidence,
            sources: payload.sources,
            next_steps: payload.next_steps,
            timestamp: payload.timestamp,
          }
          break

        default:
          break
      }

      return { events: newEvents, agents, sessionStatus, finalAnswer, pendingApprovals }
    })
  },

  /**
   * Submit approval/rejection for a pending action.
   */
  submitApproval: async (approvalId, approved, reason = null) => {
    const { sessionId } = get()
    if (!sessionId) return

    try {
      await fetch(`${API_BASE}/approve/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, approved, reason }),
      })
    } catch (err) {
      console.error('Failed to submit approval:', err)
    }
  },

  /**
   * Reset all state for a new query.
   */
  reset: () => {
    const { eventSource } = get()
    if (eventSource) eventSource.close()
    set({
      sessionId: null,
      query: '',
      sessionStatus: 'idle',
      events: [],
      finalAnswer: null,
      pendingApprovals: [],
      isConnected: false,
      eventSource: null,
      agents: {
        orchestrator: initialAgentState('orchestrator'),
        log_agent:    initialAgentState('log_agent'),
        code_agent:   initialAgentState('code_agent'),
        docs_agent:   initialAgentState('docs_agent'),
      },
    })
  },

  setSelectedEvent: (event) => set({ selectedEvent: event }),
  setLogFilter: (filter) => set({ logFilter: filter }),
}))

export default useStore
