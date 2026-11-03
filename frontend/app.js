/**
 * TaskMind AI — Frontend Application Logic
 * Workshop Task Management Agent with ChromaDB, Date Parser, and Priority Classifier
 */

// Application State
const state = {
  currentTab: 'tab-agent',
  currentView: 'kanban', // 'kanban' or 'table'
  tasks: [],
  notes: [],
  activeProposal: null,
  activeFilter: {
    search: '',
    priority: 'all',
    category: 'all'
  }
};

// DOM References
const elements = {
  // Tabs
  navTabs: document.querySelectorAll('.nav-tab'),
  tabContents: document.querySelectorAll('.tab-content'),
  
  // Header badges & metrics
  headerNotesCount: document.getElementById('header-notes-count'),
  tabTaskCount: document.getElementById('tab-task-count'),
  tabNotesCount: document.getElementById('tab-notes-count'),
  metricTotalTasks: document.getElementById('metric-total-tasks'),
  metricUrgentTasks: document.getElementById('metric-urgent-tasks'),
  metricCompletionRate: document.getElementById('metric-completion-rate'),
  
  // Chat & Agent
  chatForm: document.getElementById('chat-form'),
  chatInput: document.getElementById('chat-input-text'),
  chatMessages: document.getElementById('chat-messages-container'),
  agentStepsFeed: document.getElementById('agent-steps-feed'),
  sidecarNotes: document.getElementById('sidecar-retrieved-notes'),
  presetChips: document.querySelectorAll('.preset-chip'),
  
  // Task Board
  kanbanContainer: document.getElementById('kanban-container'),
  tableContainer: document.getElementById('table-container'),
  viewBtnKanban: document.getElementById('view-btn-kanban'),
  viewBtnTable: document.getElementById('view-btn-table'),
  taskSearch: document.getElementById('task-filter-search'),
  taskFilterPriority: document.getElementById('task-filter-priority'),
  taskFilterCategory: document.getElementById('task-filter-category'),
  cardsPending: document.getElementById('cards-pending'),
  cardsInProgress: document.getElementById('cards-in_progress'),
  cardsCompleted: document.getElementById('cards-completed'),
  countPending: document.getElementById('count-pending'),
  countInProgress: document.getElementById('count-in_progress'),
  countCompleted: document.getElementById('count-completed'),
  tableBody: document.getElementById('tasks-table-body'),
  
  // Modals
  modalTaskForm: document.getElementById('modal-task-form'),
  modalEditTask: document.getElementById('modal-edit-task'),
  btnOpenNewTaskModal: document.getElementById('btn-open-new-task-modal'),
  btnCloseTaskModal: document.getElementById('btn-close-task-modal'),
  btnCancelTaskModal: document.getElementById('btn-cancel-task-modal'),
  formCreateTask: document.getElementById('form-create-task'),
  formEditTask: document.getElementById('form-edit-task'),
  btnCloseEditModal: document.getElementById('btn-close-edit-modal'),
  btnDeleteTaskModal: document.getElementById('btn-delete-task-modal'),
  btnClearTasks: document.getElementById('btn-clear-tasks'),
  
  // ChromaDB Notes
  notesGrid: document.getElementById('notes-cards-grid'),
  notesSearchForm: document.getElementById('notes-search-form'),
  notesSearchInput: document.getElementById('notes-search-input'),
  vectorSearchResultsBox: document.getElementById('vector-search-results-box'),
  vectorSearchResultsList: document.getElementById('vector-search-results-list'),
  btnClearVectorSearch: document.getElementById('btn-clear-vector-search'),
  addNoteForm: document.getElementById('add-note-form'),
  
  // Sandbox
  sandboxDateForm: document.getElementById('sandbox-date-form'),
  sandboxDateInput: document.getElementById('sandbox-date-input'),
  sandboxDateResult: document.getElementById('sandbox-date-result'),
  sandboxPriorityForm: document.getElementById('sandbox-priority-form'),
  sandboxPriorityTitle: document.getElementById('sandbox-priority-title'),
  sandboxPriorityCategory: document.getElementById('sandbox-priority-category'),
  sandboxPriorityResult: document.getElementById('sandbox-priority-result'),
  
  // Toast
  toastContainer: document.getElementById('toast-container')
};

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await refreshSystemHealth();
  await loadTasks();
  await loadNotes();

  // Hash-based deep linking for direct tab views and demo state
  const hash = window.location.hash;
  if (hash === '#tasks') {
    switchTab('tab-tasks');
  } else if (hash === '#notes') {
    switchTab('tab-notes');
    if (elements.notesSearchInput) {
      elements.notesSearchInput.value = 'vegan food allergy specs';
      setTimeout(() => handleVectorSearch(new Event('submit')), 300);
    }
  } else if (hash === '#sandbox') {
    switchTab('tab-sandbox');
    setTimeout(() => {
      handleTestDateParser(new Event('submit'));
      handleTestPriorityClassifier(new Event('submit'));
    }, 300);
  } else if (hash === '#demo') {
    setTimeout(() => {
      elements.chatInput.value = "Create tasks for preparing the upcoming workshop: book the catering for our attendees with the vegan and allergy specs, test the AV equipment in room 302, get the speaker slides, and print the attendee badges by next Wednesday.";
      handleChatSubmit();
    }, 400);
  }
});

function setupEventListeners() {
  // Navigation Tabs
  elements.navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });

  // View Switcher (Kanban vs Table)
  elements.viewBtnKanban.addEventListener('click', () => setTaskView('kanban'));
  elements.viewBtnTable.addEventListener('click', () => setTaskView('table'));

  // Preset Prompts
  elements.presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const promptText = chip.getAttribute('data-prompt');
      elements.chatInput.value = promptText;
      switchTab('tab-agent');
      elements.chatInput.focus();
      // Auto-submit prompt
      handleChatSubmit();
    });
  });

  // Chat Form Submit
  elements.chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleChatSubmit();
  });

  // Enter key in chat textarea (Shift+Enter for newline)
  elements.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit();
    }
  });

  // Task Filters & Search
  elements.taskSearch.addEventListener('input', (e) => {
    state.activeFilter.search = e.target.value.toLowerCase();
    renderTasks();
  });
  elements.taskFilterPriority.addEventListener('change', (e) => {
    state.activeFilter.priority = e.target.value;
    renderTasks();
  });
  elements.taskFilterCategory.addEventListener('change', (e) => {
    state.activeFilter.category = e.target.value;
    renderTasks();
  });

  // Manual Task Modal
  elements.btnOpenNewTaskModal.addEventListener('click', () => {
    elements.modalTaskForm.classList.remove('hidden');
  });
  elements.btnCloseTaskModal.addEventListener('click', () => {
    elements.modalTaskForm.classList.add('hidden');
  });
  elements.btnCancelTaskModal.addEventListener('click', () => {
    elements.modalTaskForm.classList.add('hidden');
  });
  elements.formCreateTask.addEventListener('submit', handleCreateManualTask);

  // Edit Task Modal
  elements.btnCloseEditModal.addEventListener('click', () => {
    elements.modalEditTask.classList.add('hidden');
  });
  elements.formEditTask.addEventListener('submit', handleUpdateTask);
  elements.btnDeleteTaskModal.addEventListener('click', handleDeleteCurrentTask);

  // Clear Tasks
  elements.btnClearTasks.addEventListener('click', handleClearAllTasks);

  // Notes Search Form
  elements.notesSearchForm.addEventListener('submit', handleVectorSearch);
  elements.btnClearVectorSearch.addEventListener('click', () => {
    elements.vectorSearchResultsBox.classList.add('hidden');
    elements.notesSearchInput.value = '';
  });

  // Add Note Form
  elements.addNoteForm.addEventListener('submit', handleAddNote);

  // Sandbox forms
  elements.sandboxDateForm.addEventListener('submit', handleTestDateParser);
  elements.sandboxPriorityForm.addEventListener('submit', handleTestPriorityClassifier);

  // Sandbox Quick Pills
  document.querySelectorAll('.ex-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      elements.sandboxDateInput.value = btn.innerText;
      handleTestDateParser(new Event('submit'));
    });
  });

  document.querySelectorAll('.ex-pill-p').forEach(btn => {
    btn.addEventListener('click', () => {
      elements.sandboxPriorityTitle.value = btn.getAttribute('data-title');
      elements.sandboxPriorityCategory.value = btn.getAttribute('data-cat');
      handleTestPriorityClassifier(new Event('submit'));
    });
  });
}

// ==================== Navigation Tabs Logic ====================
function switchTab(tabId) {
  state.currentTab = tabId;
  elements.navTabs.forEach(tab => {
    tab.classList.toggle('active', tab.getAttribute('data-tab') === tabId);
  });
  elements.tabContents.forEach(content => {
    content.classList.toggle('active', content.id === tabId);
  });
  if (tabId === 'tab-tasks') {
    loadTasks();
  } else if (tabId === 'tab-notes') {
    loadNotes();
  }
}

function setTaskView(view) {
  state.currentView = view;
  elements.viewBtnKanban.classList.toggle('active', view === 'kanban');
  elements.viewBtnTable.classList.toggle('active', view === 'table');
  elements.kanbanContainer.classList.toggle('hidden', view !== 'kanban');
  elements.tableContainer.classList.toggle('hidden', view !== 'table');
  renderTasks();
}

// ==================== System Health & Stats ====================
async function refreshSystemHealth() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) return;
    const data = await res.json();
    if (elements.headerNotesCount) elements.headerNotesCount.textContent = `${data.notes_count} Notes`;
    if (elements.tabNotesCount) elements.tabNotesCount.textContent = data.notes_count;
  } catch (err) {
    console.error('Failed to load system health:', err);
  }
}

// ==================== Agent Chat & Confirmation Flow ====================
async function handleChatSubmit() {
  const message = elements.chatInput.value.trim();
  if (!message) return;

  // 1. Render User Message
  renderUserMessage(message);
  elements.chatInput.value = '';
  elements.chatInput.focus();

  // 2. Set Sidecar to Loading State
  updateSidecarStepsLoading();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    if (!res.ok) throw new Error('Agent failed to process request');
    const data = await res.json();

    // 3. Update Sidecar Trace Steps
    updateSidecarSteps(data.steps);

    // 4. Update Retrieved ChromaDB Notes in Sidecar
    if (data.proposal && data.proposal.retrieved_notes) {
      renderSidecarRetrievedNotes(data.proposal.retrieved_notes);
    }

    // 5. Render Agent Response & Proposal
    renderAgentMessage(data);

    // If direct tasks were created
    if (data.created_tasks && data.created_tasks.length > 0) {
      await loadTasks();
      showToast(`🎉 ${data.created_tasks.length} tasks committed to database!`, 'success');
    }

  } catch (err) {
    console.error('Chat error:', err);
    renderErrorMessage(`Error processing request: ${err.message}`);
    showToast('Failed to process agent request', 'error');
  }
}

function renderUserMessage(text) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const div = document.createElement('div');
  div.className = 'chat-bubble user-bubble';
  div.innerHTML = `
    <div class="bubble-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </svg>
    </div>
    <div class="bubble-body">
      <div class="bubble-header">
        <span class="bubble-author">You</span>
        <span class="bubble-time">${time}</span>
      </div>
      <div class="bubble-text">
        <p>${escapeHtml(text)}</p>
      </div>
    </div>
  `;
  elements.chatMessages.appendChild(div);
  scrollChatToBottom();
}

function renderAgentMessage(data) {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const div = document.createElement('div');
  div.className = 'chat-bubble agent-bubble';

  let proposalHtml = '';
  if (data.proposal && data.proposal.proposed_tasks && data.proposal.proposed_tasks.length > 0) {
    state.activeProposal = data.proposal;
    proposalHtml = renderProposalCardHtml(data.proposal);
  }

  div.innerHTML = `
    <div class="bubble-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
    </div>
    <div class="bubble-body" style="width: 100%;">
      <div class="bubble-header">
        <span class="bubble-author">TaskMind Agent</span>
        <span class="bubble-time">${time}</span>
      </div>
      <div class="bubble-text">
        <div>${formatMarkdownToHtml(data.reply)}</div>
        ${proposalHtml}
      </div>
    </div>
  `;

  elements.chatMessages.appendChild(div);
  scrollChatToBottom();

  // Attach event listener to proposal confirm button if present
  if (data.proposal) {
    const confirmBtn = div.querySelector('.btn-confirm-proposal');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => handleConfirmProposal(data.proposal, div));
    }
  }
}

function renderProposalCardHtml(proposal) {
  const itemsHtml = proposal.proposed_tasks.map((t, idx) => {
    const pClass = `badge-${t.priority.toLowerCase()}`;
    return `
      <div class="proposal-item" data-id="${t.temp_id}">
        <input type="checkbox" class="proposal-checkbox" checked id="chk-${t.temp_id}" />
        <div class="prop-content">
          <div class="prop-top-row">
            <span class="prop-title">${escapeHtml(t.title)}</span>
            <div class="prop-badges">
              <span class="badge ${pClass}" title="${escapeHtml(t.priority_reason)}">${t.priority}</span>
              <span class="badge badge-cat">${escapeHtml(t.category)}</span>
            </div>
          </div>
          <div class="prop-desc">${escapeHtml(t.description)}</div>
          <div class="prop-footer">
            <span class="prop-due">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              ${escapeHtml(t.due_date)}
            </span>
            ${t.source_notes.length ? `<span class="prop-notes-tag" title="Context retrieved from ChromaDB">🧠 ${escapeHtml(t.source_notes.join(', '))}</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="proposal-box" id="box-${proposal.proposal_id}">
      <div class="proposal-header">
        <div class="proposal-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span>Structured Task Proposal (${proposal.proposed_tasks.length} items)</span>
        </div>
        <span class="proposal-meta">Awaiting Your Confirmation</span>
      </div>
      <div class="proposal-list">
        ${itemsHtml}
      </div>
      <div class="proposal-actions">
        <span style="font-size:0.78rem; color:var(--text-muted);">Confirm to commit approved tasks into SQLite Task Store</span>
        <button class="btn confirm-btn-primary btn-confirm-proposal" data-proposal-id="${proposal.proposal_id}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>Confirm & Create Tasks</span>
        </button>
      </div>
    </div>
  `;
}

async function handleConfirmProposal(proposal, bubbleDiv) {
  const proposalBox = bubbleDiv.querySelector(`#box-${proposal.proposal_id}`);
  const checkboxes = proposalBox.querySelectorAll('.proposal-checkbox');

  // Filter tasks based on checked state
  const approvedTasks = [];
  checkboxes.forEach((cb, idx) => {
    if (cb.checked) {
      approvedTasks.push(proposal.proposed_tasks[idx]);
    }
  });

  if (approvedTasks.length === 0) {
    showToast('Please select at least one task to create.', 'error');
    return;
  }

  const confirmBtn = proposalBox.querySelector('.btn-confirm-proposal');
  confirmBtn.disabled = true;
  confirmBtn.innerHTML = `<span>Committing to DB...</span>`;

  try {
    const res = await fetch('/api/agent/confirm-tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proposal_id: proposal.proposal_id,
        tasks_to_create: approvedTasks
      })
    });

    if (!res.ok) throw new Error('Confirmation commit failed');
    const data = await res.json();

    // Replace proposal box with confirmed success view
    proposalBox.innerHTML = `
      <div style="padding: 16px; background: rgba(16, 185, 129, 0.1); border-top: 1px solid rgba(16, 185, 129, 0.3); display: flex; align-items: center; justify-content: space-between;">
        <div style="display:flex; align-items:center; gap:8px; color:#10B981; font-weight:700; font-size:0.9rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <span>Successfully Created ${approvedTasks.length} Tasks in Database!</span>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="switchTab('tab-tasks')">View Task Board</button>
      </div>
    `;

    // Refresh database tasks & metrics
    await loadTasks();
    showToast(`🎉 Created ${approvedTasks.length} workshop tasks!`, 'success');

  } catch (err) {
    console.error('Error confirming proposal:', err);
    confirmBtn.disabled = false;
    confirmBtn.innerHTML = `<span>Try Again</span>`;
    showToast('Failed to commit tasks', 'error');
  }
}

function updateSidecarStepsLoading() {
  elements.agentStepsFeed.innerHTML = `
    <div class="step-card step-active">
      <div class="step-bullet">⚡</div>
      <div class="step-content">
        <div class="step-title">Querying ChromaDB & Embedding Notes</div>
        <div class="step-desc">Generating dense 384-d vector embeddings with all-MiniLM-L6-v2...</div>
      </div>
    </div>
  `;
}

function updateSidecarSteps(steps) {
  if (!steps || steps.length === 0) return;
  elements.agentStepsFeed.innerHTML = steps.map((s, idx) => `
    <div class="step-card step-success">
      <div class="step-bullet">${idx + 1}</div>
      <div class="step-content">
        <div class="step-title">${escapeHtml(s.name)}</div>
        <div class="step-desc">${escapeHtml(s.details)}</div>
      </div>
    </div>
  `).join('');
}

function renderSidecarRetrievedNotes(notes) {
  if (!notes || notes.length === 0) {
    elements.sidecarNotes.innerHTML = `<div class="empty-sidecar-text">No matching notes found.</div>`;
    return;
  }
  elements.sidecarNotes.innerHTML = notes.map(n => {
    const simPct = n.similarity ? Math.round(n.similarity * 100) : 95;
    return `
      <div class="retrieved-note-chip">
        <div class="r-title">${escapeHtml(n.title)}</div>
        <div class="r-sim">Category: <b>${escapeHtml(n.category)}</b> | Match: <span style="color:#2DD4BF;">${simPct}%</span></div>
      </div>
    `;
  }).join('');
}

function renderErrorMessage(msg) {
  const div = document.createElement('div');
  div.className = 'chat-bubble agent-bubble';
  div.innerHTML = `
    <div class="bubble-avatar" style="color:var(--urgent);">⚠️</div>
    <div class="bubble-body">
      <div class="bubble-text" style="border-color:var(--urgent); color:#FCA5A5;">
        ${escapeHtml(msg)}
      </div>
    </div>
  `;
  elements.chatMessages.appendChild(div);
  scrollChatToBottom();
}

function scrollChatToBottom() {
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// ==================== Task Board (CRUD) Operations ====================
async function loadTasks() {
  try {
    const res = await fetch('/api/tasks');
    if (!res.ok) throw new Error('Failed to fetch tasks');
    state.tasks = await res.json();
    await updateTaskStats();
    renderTasks();
  } catch (err) {
    console.error('Error loading tasks:', err);
  }
}

async function updateTaskStats() {
  try {
    const res = await fetch('/api/tasks/stats');
    if (!res.ok) return;
    const stats = await res.json();
    elements.tabTaskCount.textContent = stats.total;
    elements.metricTotalTasks.textContent = stats.total;
    elements.metricUrgentTasks.textContent = stats.urgent;
    elements.metricCompletionRate.textContent = `${stats.completion_pct}%`;
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

function renderTasks() {
  const filtered = state.tasks.filter(t => {
    // Search filter
    if (state.activeFilter.search) {
      const q = state.activeFilter.search;
      const match = t.title.toLowerCase().includes(q) ||
                    t.description.toLowerCase().includes(q) ||
                    (t.tags && t.tags.some(tag => tag.toLowerCase().includes(q)));
      if (!match) return false;
    }
    // Priority filter
    if (state.activeFilter.priority !== 'all' && t.priority !== state.activeFilter.priority) {
      return false;
    }
    // Category filter
    if (state.activeFilter.category !== 'all' && t.category !== state.activeFilter.category) {
      return false;
    }
    return true;
  });

  if (state.currentView === 'kanban') {
    renderKanbanColumns(filtered);
  } else {
    renderTasksTable(filtered);
  }
}

function renderKanbanColumns(tasks) {
  const pending = tasks.filter(t => t.status === 'pending');
  const inProgress = tasks.filter(t => t.status === 'in_progress');
  const completed = tasks.filter(t => t.status === 'completed');

  elements.countPending.textContent = pending.length;
  elements.countInProgress.textContent = inProgress.length;
  elements.countCompleted.textContent = completed.length;

  elements.cardsPending.innerHTML = pending.length ? pending.map(renderTaskCardHtml).join('') : `<div class="empty-col-message">No pending tasks</div>`;
  elements.cardsInProgress.innerHTML = inProgress.length ? inProgress.map(renderTaskCardHtml).join('') : `<div class="empty-col-message">No tasks in progress</div>`;
  elements.cardsCompleted.innerHTML = completed.length ? completed.map(renderTaskCardHtml).join('') : `<div class="empty-col-message">No completed tasks</div>`;

  // Attach card event listeners
  document.querySelectorAll('.task-card').forEach(card => {
    const taskId = card.getAttribute('data-id');
    card.addEventListener('click', (e) => {
      if (e.target.closest('.btn-card-toggle')) return; // Ignore toggle button click
      openEditTaskModal(taskId);
    });
  });

  document.querySelectorAll('.btn-card-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const taskId = btn.getAttribute('data-id');
      handleToggleTaskStatus(taskId);
    });
  });
}

function renderTaskCardHtml(task) {
  const pClass = `badge-${task.priority.toLowerCase()}`;
  const nextStatusLabel = {
    'pending': 'Start ➔',
    'in_progress': 'Complete ✓',
    'completed': 'Reopen ↺'
  }[task.status] || 'Toggle';

  return `
    <div class="task-card" data-id="${task.id}">
      <div class="card-top-row">
        <span class="card-task-title">${escapeHtml(task.title)}</span>
        <div class="card-badges">
          <span class="badge ${pClass}" title="${escapeHtml(task.priority_reason || '')}">${task.priority}</span>
        </div>
      </div>
      <div class="card-task-desc">${escapeHtml(task.description)}</div>
      <div class="card-meta-row">
        <span class="badge badge-cat">${escapeHtml(task.category)}</span>
        <span class="card-due">🗓️ ${escapeHtml(task.due_date || 'No date')}</span>
      </div>
      <div class="card-actions-row">
        ${task.source_notes.length ? `<span class="prop-notes-tag" title="ChromaDB Context">🧠 ${escapeHtml(task.source_notes[0])}</span>` : '<span></span>'}
        <button class="btn-card-toggle" data-id="${task.id}">${nextStatusLabel}</button>
      </div>
    </div>
  `;
}

function renderTasksTable(tasks) {
  if (tasks.length === 0) {
    elements.tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-muted">No matching tasks found.</td></tr>`;
    return;
  }

  elements.tableBody.innerHTML = tasks.map(t => {
    const pClass = `badge-${t.priority.toLowerCase()}`;
    const statusBadge = {
      'pending': '<span class="badge" style="background:#F59E0B20; color:#F59E0B; border:1px solid #F59E0B40;">Pending</span>',
      'in_progress': '<span class="badge" style="background:#3B82F620; color:#3B82F6; border:1px solid #3B82F640;">In Progress</span>',
      'completed': '<span class="badge" style="background:#10B98120; color:#10B981; border:1px solid #10B98140;">Completed</span>'
    }[t.status];

    return `
      <tr style="cursor:pointer;" onclick="openEditTaskModal('${t.id}')">
        <td>${statusBadge}</td>
        <td><strong style="color:#F9FAFB;">${escapeHtml(t.title)}</strong></td>
        <td><span class="badge ${pClass}">${t.priority}</span></td>
        <td><span class="badge badge-cat">${escapeHtml(t.category)}</span></td>
        <td style="color:#FBBF24;">${escapeHtml(t.due_date)}</td>
        <td><span class="prop-notes-tag">${escapeHtml(t.source_notes.join(', ') || '-')}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); handleToggleTaskStatus('${t.id}')">
            Status
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

async function handleToggleTaskStatus(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/toggle`, { method: 'POST' });
    if (!res.ok) throw new Error('Toggle status failed');
    await loadTasks();
  } catch (err) {
    showToast('Failed to advance task status', 'error');
  }
}

async function handleCreateManualTask(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById('modal-input-title').value.trim(),
    category: document.getElementById('modal-input-category').value,
    priority: document.getElementById('modal-input-priority').value,
    due_date: document.getElementById('modal-input-due').value.trim(),
    description: document.getElementById('modal-input-desc').value.trim()
  };

  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Task creation failed');
    elements.modalTaskForm.classList.add('hidden');
    elements.formCreateTask.reset();
    await loadTasks();
    showToast('Task created successfully!', 'success');
  } catch (err) {
    showToast('Failed to create task', 'error');
  }
}

function openEditTaskModal(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  document.getElementById('edit-task-id').value = task.id;
  document.getElementById('edit-task-title').value = task.title;
  document.getElementById('edit-task-status').value = task.status;
  document.getElementById('edit-task-priority').value = task.priority;
  document.getElementById('edit-task-category').value = task.category;
  document.getElementById('edit-task-due').value = task.due_date;
  document.getElementById('edit-task-desc').value = task.description;

  elements.modalEditTask.classList.remove('hidden');
}

async function handleUpdateTask(e) {
  e.preventDefault();
  const taskId = document.getElementById('edit-task-id').value;
  const updates = {
    title: document.getElementById('edit-task-title').value.trim(),
    status: document.getElementById('edit-task-status').value,
    priority: document.getElementById('edit-task-priority').value,
    category: document.getElementById('edit-task-category').value,
    due_date: document.getElementById('edit-task-due').value.trim(),
    description: document.getElementById('edit-task-desc').value.trim()
  };

  try {
    const res = await fetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    if (!res.ok) throw new Error('Update failed');
    elements.modalEditTask.classList.add('hidden');
    await loadTasks();
    showToast('Task updated successfully', 'success');
  } catch (err) {
    showToast('Failed to update task', 'error');
  }
}

async function handleDeleteCurrentTask() {
  const taskId = document.getElementById('edit-task-id').value;
  if (!confirm('Are you sure you want to delete this task?')) return;

  try {
    const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Delete failed');
    elements.modalEditTask.classList.add('hidden');
    await loadTasks();
    showToast('Task deleted', 'success');
  } catch (err) {
    showToast('Failed to delete task', 'error');
  }
}

async function handleClearAllTasks() {
  if (!confirm('Are you sure you want to clear all tasks from the SQLite database?')) return;
  try {
    const res = await fetch('/api/tasks/actions/clear-all', { method: 'DELETE' });
    if (!res.ok) throw new Error('Clear failed');
    await loadTasks();
    showToast('All tasks cleared', 'success');
  } catch (err) {
    showToast('Failed to clear tasks', 'error');
  }
}

// ==================== ChromaDB Notes Management ====================
async function loadNotes() {
  try {
    const res = await fetch('/api/notes');
    if (!res.ok) throw new Error('Failed to load notes');
    state.notes = await res.json();
    renderNotesGrid(state.notes);
    document.getElementById('notes-total-badge').textContent = `${state.notes.length} Total Notes`;
  } catch (err) {
    console.error('Error loading notes:', err);
  }
}

function renderNotesGrid(notes) {
  if (notes.length === 0) {
    elements.notesGrid.innerHTML = `<div class="empty-col-message">No project notes stored in ChromaDB.</div>`;
    return;
  }
  elements.notesGrid.innerHTML = notes.map(n => `
    <div class="note-card">
      <div class="note-card-header">
        <h4 class="note-card-title">${escapeHtml(n.title)}</h4>
        <span class="badge badge-cat">${escapeHtml(n.category)}</span>
      </div>
      <div class="note-card-content">${escapeHtml(n.content)}</div>
      <div class="note-card-tags">
        ${n.tags.map(t => `<span class="note-tag">#${escapeHtml(t)}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

async function handleVectorSearch(e) {
  e.preventDefault();
  const query = elements.notesSearchInput.value.trim();
  if (!query) return;

  const btn = document.getElementById('btn-run-vector-search');
  btn.disabled = true;
  btn.innerHTML = `<span>Searching ChromaDB...</span>`;

  try {
    const res = await fetch('/api/notes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, n_results: 4 })
    });
    if (!res.ok) throw new Error('Vector search failed');
    const matches = await res.json();

    elements.vectorSearchResultsBox.classList.remove('hidden');
    elements.vectorSearchResultsList.innerHTML = matches.map(m => {
      const pct = Math.round(m.similarity * 100);
      return `
        <div class="vector-res-card">
          <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:600; color:#38BDF8;">
            <span>${escapeHtml(m.title)}</span>
            <span style="color:#2DD4BF;">${pct}% Cosine Sim</span>
          </div>
          <div class="sim-score-bar-bg">
            <div class="sim-score-bar-fill" style="width: ${pct}%;"></div>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">${escapeHtml(m.content.slice(0, 110))}...</div>
        </div>
      `;
    }).join('');

  } catch (err) {
    showToast('Vector search failed', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Search Vector DB</span>`;
  }
}

async function handleAddNote(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById('new-note-title').value.trim(),
    category: document.getElementById('new-note-category').value,
    content: document.getElementById('new-note-content').value.trim(),
    tags: ["workshop", "custom"]
  };

  try {
    const res = await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Add note failed');
    elements.addNoteForm.reset();
    await loadNotes();
    await refreshSystemHealth();
    showToast('New note embedded and saved to ChromaDB!', 'success');
  } catch (err) {
    showToast('Failed to add note', 'error');
  }
}

// ==================== Tools Sandbox Handlers ====================
async function handleTestDateParser(e) {
  if (e && e.preventDefault) e.preventDefault();
  const text = elements.sandboxDateInput.value.trim();
  if (!text) return;

  try {
    const res = await fetch('/api/tools/parse-date', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();

    elements.sandboxDateResult.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:8px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.8rem; color:var(--text-muted);">Formatted Result:</span>
          <span class="badge" style="background:#2DD4BF20; color:#2DD4BF; border:1px solid #2DD4BF40;">${data.source}</span>
        </div>
        <div style="font-size:1.1rem; font-weight:700; color:#FBBF24;">${escapeHtml(data.formatted)}</div>
        <div style="font-size:0.8rem; color:var(--text-main);">Relative: <b>${escapeHtml(data.relative)}</b></div>
        <div style="font-size:0.75rem; color:var(--text-dim); font-family:monospace;">ISO: ${data.iso}</div>
        ${data.reason ? `<div style="font-size:0.75rem; color:#A5B4FC;">Reason: ${escapeHtml(data.reason)}</div>` : ''}
      </div>
    `;
  } catch (err) {
    elements.sandboxDateResult.innerHTML = `<div style="color:var(--urgent);">Failed to parse date</div>`;
  }
}

async function handleTestPriorityClassifier(e) {
  if (e && e.preventDefault) e.preventDefault();
  const title = elements.sandboxPriorityTitle.value.trim();
  const category = elements.sandboxPriorityCategory.value;
  if (!title) return;

  try {
    const res = await fetch('/api/tools/classify-priority', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, category })
    });
    const data = await res.json();
    const pClass = `badge-${data.priority.toLowerCase()}`;

    elements.sandboxPriorityResult.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:0.8rem; color:var(--text-muted);">Calculated Priority:</span>
          <span class="badge ${pClass}">${data.priority}</span>
        </div>
        <div>
          <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:4px;">
            <span>Urgency Score</span>
            <span style="font-weight:700; color:#2DD4BF;">${data.score} / 100</span>
          </div>
          <div class="sim-score-bar-bg">
            <div class="sim-score-bar-fill" style="width:${data.score}%;"></div>
          </div>
        </div>
        <div style="font-size:0.8rem; color:var(--text-muted); line-height:1.45;">
          <b>Reasoning:</b> ${escapeHtml(data.reason)}
        </div>
      </div>
    `;
  } catch (err) {
    elements.sandboxPriorityResult.innerHTML = `<div style="color:var(--urgent);">Failed to classify priority</div>`;
  }
}

// ==================== Utilities ====================
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : 'ℹ️'}</span>
    <span>${escapeHtml(message)}</span>
  `;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
}

function formatMarkdownToHtml(markdown) {
  if (!markdown) return '';
  let html = escapeHtml(markdown);
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Inline Code
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');
  // Line breaks
  html = html.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
  return html;
}
