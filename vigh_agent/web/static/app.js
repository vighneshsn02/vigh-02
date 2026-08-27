// VIGH-02 AI AGENT - Client Frontend State & Interactions

let currentFilePath = null;
let isStreaming = false;
let currentMode = 'single';

document.addEventListener('DOMContentLoaded', () => {
  configureMarkedRenderer();
  initTabs();
  initSidebarTabs();
  initModeToggle();
  loadStatus();
  loadModels();
  loadFileTree();
  loadAgents();
  initChat();
  initEditor();
  initQuickActions();
  initWorkspaceModal();
  initTerminalRunner();
  initCopyDelegation();
  enhanceCodeBlocks(document.getElementById('chat-messages'));
});

// Configure Marked.js renderer to generate code blocks with language badge and copy button
function configureMarkedRenderer() {
  if (typeof marked === 'undefined') return;

  const customRenderer = {
    code(tokenOrCode, maybeLang) {
      let code = '';
      let lang = '';
      if (typeof tokenOrCode === 'object' && tokenOrCode !== null) {
        code = tokenOrCode.text !== undefined ? tokenOrCode.text : '';
        lang = tokenOrCode.lang || '';
      } else {
        code = tokenOrCode || '';
        lang = maybeLang || '';
      }

      const cleanLang = (lang || '').trim().split(/\s+/)[0] || '';
      const displayLang = cleanLang ? cleanLang.toLowerCase() : 'code';

      let highlighted = '';
      if (cleanLang && typeof hljs !== 'undefined' && hljs.getLanguage(cleanLang)) {
        try {
          highlighted = hljs.highlight(code, { language: cleanLang, ignoreIllegals: true }).value;
        } catch (e) {
          highlighted = escapeHtml(code);
        }
      } else if (typeof hljs !== 'undefined') {
        try {
          highlighted = hljs.highlightAuto(code).value;
        } catch (e) {
          highlighted = escapeHtml(code);
        }
      } else {
        highlighted = escapeHtml(code);
      }

      return `
<div class="code-block-wrapper">
  <div class="code-block-header">
    <div class="code-lang">
      <span class="code-lang-dot"></span>
      <span class="code-lang-text">${escapeHtml(displayLang)}</span>
    </div>
    <button class="copy-code-btn" type="button" aria-label="Copy code to clipboard" title="Copy code">
      <svg class="copy-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span class="copy-btn-text">Copy</span>
    </button>
  </div>
  <pre><code class="hljs language-${escapeHtml(displayLang)}">${highlighted}</code></pre>
</div>
`;
    }
  };

  try {
    if (marked.use) {
      marked.use({ renderer: customRenderer });
    } else if (marked.Renderer) {
      const r = new marked.Renderer();
      r.code = customRenderer.code;
      marked.setOptions({ renderer: r, breaks: true, gfm: true });
    }
  } catch (err) {
    console.warn('Failed to configure marked renderer:', err);
  }
}

// Enhance any pre/code blocks in a container that might not be wrapped
function enhanceCodeBlocks(container) {
  if (!container) return;

  const preElements = container.querySelectorAll('pre');
  preElements.forEach((pre) => {
    if (pre.closest('.code-block-wrapper')) return;

    const codeEl = pre.querySelector('code') || pre;
    let lang = 'code';
    if (codeEl.className) {
      const match = codeEl.className.match(/language-([a-zA-Z0-9_\-+]+)/);
      if (match) lang = match[1];
    }

    if (typeof hljs !== 'undefined' && codeEl && !codeEl.classList.contains('hljs')) {
      try {
        hljs.highlightElement(codeEl);
      } catch (e) {}
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';

    const header = document.createElement('div');
    header.className = 'code-block-header';
    header.innerHTML = `
      <div class="code-lang">
        <span class="code-lang-dot"></span>
        <span class="code-lang-text">${escapeHtml(lang)}</span>
      </div>
      <button class="copy-code-btn" type="button" aria-label="Copy code to clipboard" title="Copy code">
        <svg class="copy-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span class="copy-btn-text">Copy</span>
      </button>
    `;

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(header);
    wrapper.appendChild(pre);
  });
}

// Render markdown string into container and ensure code block styling and highlighting
function renderMarkdownInto(container, markdownText) {
  if (!container) return;
  if (typeof marked !== 'undefined') {
    container.innerHTML = marked.parse(markdownText || '');
  } else {
    container.innerHTML = `<pre><code>${escapeHtml(markdownText || '')}</code></pre>`;
  }

  container.querySelectorAll('pre code').forEach((el) => {
    if (!el.classList.contains('hljs') && typeof hljs !== 'undefined') {
      try {
        hljs.highlightElement(el);
      } catch (e) {}
    }
  });

  enhanceCodeBlocks(container);
}

// Tab navigation for Main Area
function initTabs() {
  document.querySelectorAll('.view-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view-container').forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const viewId = tab.getAttribute('data-view');
      const target = document.getElementById(viewId);
      if (target) target.classList.add('active');
    });
  });
}

// Sidebar Tab navigation
function initSidebarTabs() {
  document.querySelectorAll('.sidebar-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sidebar-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');

      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      const pane = document.getElementById(tabId);
      if (pane) pane.style.display = 'block';

      if (tabId === 'history-tab') loadUndoHistory();
    });
  });

  document.getElementById('refresh-files-btn').addEventListener('click', loadFileTree);
  document.getElementById('revert-last-btn').addEventListener('click', revertLastEdit);
  document.getElementById('undo-from-diff-btn').addEventListener('click', revertLastEdit);

  const copyDiffBtn = document.getElementById('copy-diff-btn');
  if (copyDiffBtn) {
    copyDiffBtn.addEventListener('click', async () => {
      const diffContent = document.getElementById('diff-content-display');
      const text = diffContent ? (diffContent.innerText || diffContent.textContent) : '';
      if (!text || text.includes('No active diff recorded')) return;
      const success = await copyTextToClipboard(text);
      if (success) {
        showCopiedFeedback(copyDiffBtn);
      }
    });
  }
}

// Mode Toggle (Single vs Multi-Agent)
function initModeToggle() {
  const toggleBtn = document.getElementById('mode-toggle-btn');
  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', async () => {
    const targetMode = (currentMode === 'multi') ? 'single' : 'multi';
    try {
      const res = await fetch('/api/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: targetMode })
      });
      const data = await res.json();
      if (data.success) {
        currentMode = data.mode;
        updateModeUI(currentMode);
      }
    } catch (err) {
      console.error('Failed to toggle mode:', err);
    }
  });
}

function updateModeUI(mode) {
  const toggleBtn = document.getElementById('mode-toggle-btn');
  const modeText = document.getElementById('mode-text');
  const modeIcon = document.getElementById('mode-icon');
  if (!toggleBtn || !modeText) return;

  if (mode === 'multi') {
    toggleBtn.classList.add('multi-mode');
    modeText.textContent = 'Multi-Agent Swarm';
    if (modeIcon) modeIcon.textContent = '👥';
  } else {
    toggleBtn.classList.remove('multi-mode');
    modeText.textContent = 'Single Agent';
    if (modeIcon) modeIcon.textContent = '⚡';
  }
}

// Load Session Status
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('workspace-name-display').textContent = data.workspace_name || data.workspace;
    document.getElementById('workspace-badge').title = `Active Directory: ${data.workspace}`;
    if (data.mode) {
      currentMode = data.mode;
      updateModeUI(currentMode);
    }
  } catch (err) {
    console.error('Failed to load status:', err);
  }
}

// Load Specialized Agents into Swarm Dashboard
async function loadAgents() {
  const container = document.getElementById('agents-cards-container');
  if (!container) return;

  try {
    const res = await fetch('/api/agents');
    const data = await res.json();
    container.innerHTML = '';

    if (data.agents && data.agents.length > 0) {
      data.agents.forEach(agent => {
        const card = document.createElement('div');
        card.className = 'agent-card';
        card.innerHTML = `
          <div class="agent-card-header">
            <div class="agent-card-title">
              <span style="font-size:18px;">${agent.icon}</span>
              <span>${escapeHtml(agent.name)}</span>
            </div>
            <span class="agent-status-pill">Ready</span>
          </div>
          <div class="agent-card-role">${escapeHtml(agent.role)}</div>
          <div class="agent-card-desc">${escapeHtml(agent.description)}</div>
        `;
        container.appendChild(card);
      });
    }
  } catch (err) {
    console.error('Failed to load agents:', err);
  }
}

// Load Swarm Blackboard Context
async function loadSwarmContext() {
  const display = document.getElementById('swarm-blackboard-display');
  if (!display) return;

  try {
    const res = await fetch('/api/multi-agent/context');
    const data = await res.json();
    display.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    display.textContent = 'Error loading shared context: ' + err;
  }
}

// Load Models
async function loadModels() {
  try {
    const res = await fetch('/api/models');
    const data = await res.json();
    const select = document.getElementById('model-select');
    select.innerHTML = '';

    if (data.models && data.models.length > 0) {
      data.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = JSON.stringify({ provider: m.provider, model: m.id });
        opt.textContent = `${m.name} (${m.size || m.provider})`;
        if (m.id === data.current_model) opt.selected = true;
        select.appendChild(opt);
      });
    } else {
      const opt = document.createElement('option');
      opt.textContent = 'No local models found';
      select.appendChild(opt);
    }

    select.addEventListener('change', async () => {
      if (!select.value) return;
      const parsed = JSON.parse(select.value);
      try {
        await fetch('/api/models/select', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        });
        loadStatus();
      } catch (err) {
        alert('Failed to switch model: ' + err);
      }
    });
  } catch (err) {
    console.error('Failed to load models:', err);
  }
}

// Load File Tree
async function loadFileTree() {
  const container = document.getElementById('file-tree-container');
  container.innerHTML = '<div style="color:var(--text-muted); padding:6px;">Refreshing tree...</div>';

  try {
    const res = await fetch('/api/files/tree');
    const data = await res.json();
    container.innerHTML = '';

    function renderNodes(nodes, parentEl) {
      nodes.forEach(node => {
        const nodeEl = document.createElement('div');
        nodeEl.className = 'tree-node';
        nodeEl.innerHTML = `<span>${node.is_dir ? '📁' : '📄'}</span> <span>${node.name}</span>`;

        if (node.is_dir) {
          const childrenContainer = document.createElement('div');
          childrenContainer.className = 'tree-children';
          childrenContainer.style.display = 'none';

          nodeEl.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = childrenContainer.style.display === 'block';
            childrenContainer.style.display = isOpen ? 'none' : 'block';
            nodeEl.querySelector('span').textContent = isOpen ? '📁' : '📂';
          });

          parentEl.appendChild(nodeEl);
          if (node.children) renderNodes(node.children, childrenContainer);
          parentEl.appendChild(childrenContainer);
        } else {
          nodeEl.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('active'));
            nodeEl.classList.add('active');
            openFileInEditor(node.path);
          });
          parentEl.appendChild(nodeEl);
        }
      });
    }

    if (data.tree && data.tree.length > 0) {
      renderNodes(data.tree, container);
    } else {
      container.innerHTML = '<div style="color:var(--text-muted); padding:6px;">Workspace is empty.</div>';
    }
  } catch (err) {
    container.innerHTML = `<div style="color:var(--accent-red); padding:6px;">Error loading files: ${err}</div>`;
  }
}

// Open File in Editor
async function openFileInEditor(relPath) {
  try {
    const res = await fetch(`/api/files/content?path=${encodeURIComponent(relPath)}`);
    const data = await res.json();
    if (data.success) {
      currentFilePath = relPath;
      document.getElementById('editor-file-label').textContent = relPath;
      document.getElementById('code-editor-textarea').value = data.content;

      // Switch to editor tab
      document.querySelector('[data-view="editor-view"]').click();
    } else {
      alert(data.content || 'Cannot open file.');
    }
  } catch (err) {
    alert('Error opening file: ' + err);
  }
}

// Editor Save, Copy & AI Edit
function initEditor() {
  const saveBtn = document.getElementById('editor-save-btn');
  saveBtn.addEventListener('click', async () => {
    if (!currentFilePath) {
      alert('Please open or specify a file first.');
      return;
    }
    const content = document.getElementById('code-editor-textarea').value;
    try {
      const res = await fetch('/api/files/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: currentFilePath,
          content: content,
          description: `Manual save from Web Editor: ${currentFilePath}`
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Saved ${currentFilePath} successfully!`);
        loadFileTree();
      } else {
        alert(`Save failed: ${data.error}`);
      }
    } catch (err) {
      alert('Save error: ' + err);
    }
  });

  const copyBtn = document.getElementById('editor-copy-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const content = document.getElementById('code-editor-textarea').value;
      if (!content) return;
      const success = await copyTextToClipboard(content);
      if (success) {
        showCopiedFeedback(copyBtn);
      }
    });
  }

  document.getElementById('editor-ask-ai-btn').addEventListener('click', () => {
    if (!currentFilePath) {
      alert('Select a file to edit first.');
      return;
    }
    const instruction = prompt(`What changes would you like VIGH-02 to make to '${currentFilePath}'?`);
    if (instruction) {
      document.querySelector('[data-view="chat-view"]').click();
      sendChatMessage(`Please edit file '${currentFilePath}'. Instructions: ${instruction}`);
    }
  });
}

// Chat System with SSE Streaming
function initChat() {
  const textarea = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');

  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const text = textarea.value.trim();
      if (text && !isStreaming) {
        sendChatMessage(text);
        textarea.value = '';
      }
    }
  });

  sendBtn.addEventListener('click', () => {
    const text = textarea.value.trim();
    if (text && !isStreaming) {
      sendChatMessage(text);
      textarea.value = '';
    }
  });
}

async function sendChatMessage(promptText, requestedMode = null) {
  const chatMessages = document.getElementById('chat-messages');
  isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  const modeToUse = requestedMode || currentMode || 'single';

  // Add User Bubble
  const userMsgEl = document.createElement('div');
  userMsgEl.className = 'message user';
  userMsgEl.innerHTML = `
    <div class="avatar">👤</div>
    <div class="bubble">${escapeHtml(promptText)}</div>
  `;
  chatMessages.appendChild(userMsgEl);

  // Add Assistant Bubble
  const assistantMsgEl = document.createElement('div');
  assistantMsgEl.className = 'message assistant';
  assistantMsgEl.innerHTML = `
    <div class="avatar">${modeToUse === 'multi' ? '👥' : '⚡'}</div>
    <div class="bubble"><div class="response-content"></div></div>
  `;
  chatMessages.appendChild(assistantMsgEl);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  const contentBox = assistantMsgEl.querySelector('.response-content');
  let accumulatedMarkdown = '';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: promptText,
        mode: modeToUse
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.substring(6));
            const agentName = (event.data && event.data.agent) ? event.data.agent.toLowerCase() : 'agent';

            if (event.type === 'token' && event.content) {
              const isNearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 140;
              accumulatedMarkdown += event.content;
              renderMarkdownInto(contentBox, accumulatedMarkdown);
              if (isNearBottom) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
              }
            } else if (event.type === 'phase_start' && event.content) {
              const pCard = document.createElement('div');
              pCard.className = 'phase-card';
              pCard.innerHTML = `<span>⚡</span> <span>${escapeHtml(event.content)}</span>`;
              contentBox.appendChild(pCard);
              chatMessages.scrollTop = chatMessages.scrollHeight;
            } else if (event.type === 'agent_start') {
              const aBadge = document.createElement('div');
              aBadge.className = `agent-turn-badge ${agentName}`;
              aBadge.innerHTML = `<span>▶ [${escapeHtml((event.data && event.data.agent) || 'AGENT').toUpperCase()}]</span> Working...`;
              contentBox.appendChild(aBadge);
              chatMessages.scrollTop = chatMessages.scrollHeight;
            } else if (event.type === 'tool_start') {
              const badge = document.createElement('div');
              badge.className = 'tool-badge';
              badge.textContent = `⚡ [${escapeHtml(agentName.toUpperCase())}] Executing ${event.data ? event.data.name : 'tool'}...`;
              contentBox.appendChild(badge);
              chatMessages.scrollTop = chatMessages.scrollHeight;
            } else if (event.type === 'tool_end') {
              const badge = document.createElement('div');
              badge.className = 'tool-badge';
              badge.style.color = '#34d399';
              badge.style.borderColor = 'rgba(52, 211, 153, 0.3)';
              badge.textContent = `✓ [${escapeHtml(agentName.toUpperCase())}] ${event.data ? event.data.name : 'Tool'} complete`;
              contentBox.appendChild(badge);
              loadFileTree(); // Refresh files if tool mutated disk
            } else if (event.type === 'autofix_start') {
              const fixBox = document.createElement('div');
              fixBox.className = 'autofix-box';
              fixBox.innerHTML = `<strong>🔧 Self-Healing Triggered:</strong> ${escapeHtml(event.content || 'Applying automated error repairs...')}`;
              contentBox.appendChild(fixBox);
              chatMessages.scrollTop = chatMessages.scrollHeight;
            } else if (event.type === 'autofix_complete') {
              const fixBox = document.createElement('div');
              fixBox.className = 'tool-badge';
              fixBox.style.color = '#34d399';
              fixBox.textContent = `✓ ${event.content || 'Auto-fix complete.'}`;
              contentBox.appendChild(fixBox);
            } else if (event.type === 'diff' && event.content) {
              renderDiffView(event.content);
            } else if (event.type === 'error') {
              const errEl = document.createElement('div');
              errEl.style.color = 'var(--accent-red)';
              errEl.textContent = `Error: ${event.content}`;
              contentBox.appendChild(errEl);
            }
          } catch (e) {
            console.error('SSE JSON parse error:', e);
          }
        }
      }
    }
  } catch (err) {
    contentBox.innerHTML += `<div style="color:var(--accent-red)">Request failed: ${err}</div>`;
  } finally {
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
    if (accumulatedMarkdown) {
      renderMarkdownInto(contentBox, accumulatedMarkdown);
    }
    loadSwarmContext();
  }
}

// Render Diff in Tab
function renderDiffView(diffText) {
  const container = document.getElementById('diff-content-display');
  container.innerHTML = '';
  const lines = diffText.split('\n');

  lines.forEach(line => {
    const div = document.createElement('div');
    if (line.startsWith('+') && !line.startsWith('+++')) {
      div.className = 'diff-line-add';
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      div.className = 'diff-line-del';
    } else if (line.startsWith('@@')) {
      div.className = 'diff-line-hunk';
    }
    div.textContent = line;
    container.appendChild(div);
  });
}

// Quick Actions
function initQuickActions() {
  const multiAction = document.getElementById('action-multi-agent');
  if (multiAction) {
    multiAction.addEventListener('click', () => {
      currentMode = 'multi';
      updateModeUI('multi');
      document.querySelector('[data-view="chat-view"]').click();
      sendChatMessage('Please organize a full multi-agent workflow: plan the requirements, implement code changes, execute automated tests, audit security, review quality, and self-heal any failures.', 'multi');
    });
  }

  const swarmTaskBtn = document.getElementById('swarm-run-quick-task');
  if (swarmTaskBtn) {
    swarmTaskBtn.addEventListener('click', () => {
      const task = prompt('Describe the engineering goal for the Multi-Agent Swarm (Planner, Coder, Tester, Reviewer, Security):');
      if (task) {
        currentMode = 'multi';
        updateModeUI('multi');
        document.querySelector('[data-view="chat-view"]').click();
        sendChatMessage(task, 'multi');
      }
    });
  }

  const refreshSwarmBtn = document.getElementById('refresh-swarm-btn');
  if (refreshSwarmBtn) {
    refreshSwarmBtn.addEventListener('click', () => {
      loadAgents();
      loadSwarmContext();
    });
  }

  document.getElementById('action-scan').addEventListener('click', () => {
    document.querySelector('[data-view="scanner-view"]').click();
    runFullScan();
  });

  document.getElementById('action-refactor').addEventListener('click', () => {
    document.querySelector('[data-view="chat-view"]').click();
    sendChatMessage('Please scan the codebase, analyze code quality, and suggest specific modular refactoring optimizations.');
  });

  document.getElementById('action-tests').addEventListener('click', () => {
    document.querySelector('[data-view="chat-view"]').click();
    sendChatMessage('Please generate comprehensive unit test suites with edge cases for the files in this workspace.');
  });

  document.getElementById('action-security').addEventListener('click', () => {
    document.querySelector('[data-view="scanner-view"]').click();
    runFullScan();
  });

  document.getElementById('action-explain').addEventListener('click', () => {
    document.querySelector('[data-view="chat-view"]').click();
    sendChatMessage('Please deeply analyze this project, explain its architecture, data flow, key components, and tech stack.');
  });

  document.getElementById('run-full-scan-btn').addEventListener('click', runFullScan);
}

// Run Full Scan & Populate Dashboard
async function runFullScan() {
  const scanBtn = document.getElementById('run-full-scan-btn');
  scanBtn.disabled = true;
  scanBtn.textContent = 'Scanning...';

  try {
    const res = await fetch('/api/scan');
    const data = await res.json();

    if (data.success) {
      document.getElementById('stat-files').textContent = data.total_files;
      document.getElementById('stat-loc').textContent = Number(data.total_lines_of_code).toLocaleString();
      document.getElementById('stat-todos').textContent = data.todos.length;
      document.getElementById('stat-security').textContent = data.security_findings.length;

      // Populate Security Findings
      const secBody = document.getElementById('security-findings-body');
      secBody.innerHTML = '';
      if (data.security_findings.length > 0) {
        data.security_findings.forEach(sec => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td class="severity-${sec.severity.toLowerCase()}">${sec.severity}</td>
            <td style="font-family:var(--font-mono); font-size:12px;">${sec.file}:${sec.line}</td>
            <td>${sec.description}</td>
            <td><code>${escapeHtml(sec.snippet)}</code></td>
          `;
          secBody.appendChild(tr);
        });
      } else {
        secBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--accent-green);">✓ No obvious security vulnerabilities detected.</td></tr>';
      }

      // Populate TODOs
      const todoBody = document.getElementById('todos-body');
      todoBody.innerHTML = '';
      if (data.todos.length > 0) {
        data.todos.forEach(t => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td style="font-family:var(--font-mono); font-size:12px;">${t.file}</td>
            <td>${t.line}</td>
            <td>${escapeHtml(t.comment)}</td>
          `;
          todoBody.appendChild(tr);
        });
      } else {
        todoBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--accent-green);">✓ No pending TODOs found.</td></tr>';
      }
    }
  } catch (err) {
    alert('Scan error: ' + err);
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = '⚡ Run Full Scan';
  }
}

// Undo & Revert
async function revertLastEdit() {
  try {
    const res = await fetch('/api/files/revert', { method: 'POST' });
    const data = await res.json();
    alert(data.message);
    loadFileTree();
    loadUndoHistory();
  } catch (err) {
    alert('Revert failed: ' + err);
  }
}

async function loadUndoHistory() {
  const container = document.getElementById('undo-history-list');
  try {
    const res = await fetch('/api/history/undo');
    const data = await res.json();
    container.innerHTML = '';

    if (data.history && data.history.length > 0) {
      data.history.forEach(item => {
        const d = document.createElement('div');
        d.style.padding = '6px';
        d.style.background = 'var(--bg-tertiary)';
        d.style.borderRadius = 'var(--radius-sm)';
        d.innerHTML = `<strong>[${item.type.toUpperCase()}]</strong> ${escapeHtml(item.description || item.file)}`;
        container.appendChild(d);
      });
    } else {
      container.innerHTML = '<div style="color:var(--text-muted);">No edits recorded yet.</div>';
    }
  } catch (err) {
    container.innerHTML = 'Error loading history.';
  }
}

// Change Workspace Modal
function initWorkspaceModal() {
  const modal = document.getElementById('workspace-modal');
  const badge = document.getElementById('workspace-badge');
  const closeBtn = document.getElementById('close-modal-btn');
  const saveBtn = document.getElementById('save-workspace-btn');
  const input = document.getElementById('workspace-path-input');

  badge.addEventListener('click', () => {
    modal.style.display = 'flex';
    input.focus();
  });

  closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  saveBtn.addEventListener('click', async () => {
    const newPath = input.value.trim();
    if (!newPath) return;

    try {
      const res = await fetch('/api/workspace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newPath })
      });
      const data = await res.json();
      if (data.success) {
        modal.style.display = 'none';
        loadStatus();
        loadFileTree();
      } else {
        alert(data.detail || 'Failed to switch workspace');
      }
    } catch (err) {
      alert('Error switching workspace: ' + err);
    }
  });
}

// Terminal Command Runner
function initTerminalRunner() {
  const runBtn = document.getElementById('terminal-run-btn');
  const input = document.getElementById('terminal-cmd-input');
  const output = document.getElementById('terminal-output');
  const copyBtn = document.getElementById('terminal-copy-btn');

  async function runCmd() {
    const cmd = input.value.trim();
    if (!cmd) return;

    output.textContent = `$ ${cmd}\nExecuting command...\n`;
    try {
      const res = await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json();
      output.textContent = `$ ${cmd}\n(Exit Code: ${data.exit_code})\n\nSTDOUT:\n${data.stdout || '(none)'}\n\nSTDERR:\n${data.stderr || '(none)'}`;
      loadFileTree();
    } catch (err) {
      output.textContent += `\nExecution error: ${err}`;
    }
  }

  runBtn.addEventListener('click', runCmd);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runCmd();
  });

  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const text = output ? (output.innerText || output.textContent) : '';
      if (!text) return;
      const success = await copyTextToClipboard(text);
      if (success) {
        showCopiedFeedback(copyBtn);
      }
    });
  }
}

// Event Delegation for all Copy Code Buttons in chat & dynamic blocks
function initCopyDelegation() {
  document.addEventListener('click', async (e) => {
    const copyBtn = e.target.closest('.copy-code-btn');
    if (!copyBtn) return;

    e.preventDefault();
    e.stopPropagation();

    const wrapper = copyBtn.closest('.code-block-wrapper');
    let codeToCopy = '';

    if (wrapper) {
      const codeEl = wrapper.querySelector('pre code') || wrapper.querySelector('pre');
      if (codeEl) {
        codeToCopy = codeEl.textContent || codeEl.innerText || '';
      }
    } else {
      const preEl = copyBtn.closest('pre') || (copyBtn.parentElement ? copyBtn.parentElement.querySelector('pre') : null);
      if (preEl) {
        codeToCopy = preEl.textContent || preEl.innerText || '';
      }
    }

    if (!codeToCopy) return;

    const success = await copyTextToClipboard(codeToCopy);
    if (success) {
      showCopiedFeedback(copyBtn);
    }
  });
}

// Clipboard Copy Utility with Fallback
async function copyTextToClipboard(text) {
  if (!text) return false;

  // 1. Try modern async Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('navigator.clipboard.writeText failed, using fallback:', err);
    }
  }

  // 2. Reliable textarea + execCommand fallback (works over HTTP / localhost / webview)
  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '-9999px';
    textArea.style.left = '-9999px';
    textArea.style.opacity = '0';
    textArea.setAttribute('readonly', '');
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, 999999);
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    return successful;
  } catch (fallbackErr) {
    console.error('Copy fallback failed:', fallbackErr);
    return false;
  }
}

// Visual Feedback when Code/Text is Copied
function showCopiedFeedback(button) {
  if (!button) return;
  const originalHTML = button.innerHTML;
  button.classList.add('copied');
  button.innerHTML = `
    <svg class="copy-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    <span class="copy-btn-text">Copied!</span>
  `;

  setTimeout(() => {
    button.classList.remove('copied');
    button.innerHTML = originalHTML;
  }, 2000);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
