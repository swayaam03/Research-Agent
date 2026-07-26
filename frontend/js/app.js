// ============================================
// AI Research Agent — Frontend Application
// SSE Client, DOM Manipulation, State Visualization
// ============================================

/**
 * HOW THIS FILE WORKS:
 * 
 * 1. User types a query and clicks submit (or Ctrl+Enter)
 * 2. We switch from Landing View to Research View
 * 3. We create an SSE connection to POST /api/research
 * 4. As events arrive, we update the pipeline visualization and progress log
 * 5. When the report arrives, we render it as Markdown
 * 6. The user can copy the report or start a new research
 * 
 * SSE (Server-Sent Events) EXPLAINED:
 * Unlike fetch() which waits for the entire response, SSE gives us
 * real-time updates as the server processes the request. Each event
 * contains a JSON payload with type, node, message, and data.
 */

// ---- DOM References ----
const elements = {
    // Landing view
    landingView: document.getElementById('landing-view'),
    queryInput: document.getElementById('query-input'),
    submitBtn: document.getElementById('submit-btn'),
    
    // Research view
    researchView: document.getElementById('research-view'),
    backBtn: document.getElementById('back-btn'),
    queryDisplay: document.getElementById('research-query-display'),
    progressLog: document.getElementById('progress-log'),
    reportContainer: document.getElementById('report-container'),
    reportContent: document.getElementById('report-content'),
    copyReportBtn: document.getElementById('copy-report-btn'),
    
    // Pipeline steps
    steps: {
        planner: document.getElementById('step-planner'),
        searcher: document.getElementById('step-searcher'),
        extractor: document.getElementById('step-extractor'),
        analyzer: document.getElementById('step-analyzer'),
        reporter: document.getElementById('step-reporter'),
    },
};

// ---- State ----
let currentReport = '';
let isResearching = false;

// ---- Event Listeners ----

// Submit button click
elements.submitBtn.addEventListener('click', () => startResearch());

// Ctrl+Enter to submit
elements.queryInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        startResearch();
    }
});

// Back button — return to landing
elements.backBtn.addEventListener('click', () => {
    switchView('landing');
    resetResearchView();
});

// Chip buttons — fill query input
document.querySelectorAll('.chip-btn').forEach(chip => {
    chip.addEventListener('click', () => {
        elements.queryInput.value = chip.dataset.query;
        elements.queryInput.focus();
    });
});

// Copy report button
elements.copyReportBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(currentReport).then(() => {
        elements.copyReportBtn.classList.add('copied');
        elements.copyReportBtn.querySelector('svg + span, svg ~ *') || 
            (elements.copyReportBtn.lastChild.textContent = ' Copied!');
        // Find the text node and update it
        const textNodes = [...elements.copyReportBtn.childNodes].filter(n => n.nodeType === 3);
        if (textNodes.length) textNodes[textNodes.length - 1].textContent = ' Copied!';
        
        setTimeout(() => {
            elements.copyReportBtn.classList.remove('copied');
            const tn = [...elements.copyReportBtn.childNodes].filter(n => n.nodeType === 3);
            if (tn.length) tn[tn.length - 1].textContent = '\n                        Copy\n                    ';
        }, 2000);
    });
});

// Auto-resize textarea
elements.queryInput.addEventListener('input', () => {
    elements.queryInput.style.height = 'auto';
    elements.queryInput.style.height = Math.min(elements.queryInput.scrollHeight, 160) + 'px';
});


// ============================================
// CORE FUNCTIONS
// ============================================

/**
 * Start the research process.
 * Validates input, switches view, and initiates SSE connection.
 */
function startResearch() {
    const query = elements.queryInput.value.trim();
    
    if (!query || query.length < 3) {
        elements.queryInput.focus();
        elements.queryInput.style.borderColor = '#f43f5e';
        setTimeout(() => elements.queryInput.style.borderColor = '', 1500);
        return;
    }
    
    if (isResearching) return;
    isResearching = true;
    
    // Switch to research view
    switchView('research');
    elements.queryDisplay.textContent = query;
    
    // Start SSE connection
    connectSSE(query);
}

/**
 * Switch between landing and research views.
 */
function switchView(view) {
    if (view === 'research') {
        elements.landingView.classList.remove('active');
        elements.researchView.classList.add('active');
    } else {
        elements.researchView.classList.remove('active');
        elements.landingView.classList.add('active');
    }
}

/**
 * Reset the research view for a new query.
 */
function resetResearchView() {
    isResearching = false;
    currentReport = '';
    
    // Reset pipeline steps
    Object.values(elements.steps).forEach(step => {
        step.classList.remove('active', 'completed');
    });
    
    // Reset connectors
    document.querySelectorAll('.pipeline-connector').forEach(conn => {
        conn.style.background = '';
    });
    
    // Clear progress log
    elements.progressLog.innerHTML = `
        <div class="log-entry initial">
            <span class="log-dot"></span>
            <span class="log-text">Initializing research agent...</span>
        </div>
    `;
    
    // Hide report
    elements.reportContainer.classList.add('hidden');
    elements.reportContent.innerHTML = '';
}

/**
 * Connect to the SSE endpoint and process events.
 * 
 * WHY NOT EventSource?
 * The native EventSource API only supports GET requests.
 * We need POST (to send the query body), so we use fetch()
 * with a ReadableStream reader to manually parse SSE events.
 */
async function connectSSE(query) {
    try {
        const response = await fetch('/api/research', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // Process complete SSE events (separated by double newlines)
            const events = buffer.split('\n\n');
            buffer = events.pop(); // Keep incomplete event in buffer
            
            for (const event of events) {
                const dataLine = event.trim();
                if (!dataLine) continue;
                
                // Extract data from "data: {...}" format
                if (dataLine.startsWith('data: ')) {
                    const data = dataLine.substring(6);
                    
                    if (data === '[DONE]') {
                        isResearching = false;
                        continue;
                    }
                    
                    try {
                        const parsed = JSON.parse(data);
                        handleSSEEvent(parsed);
                    } catch (e) {
                        console.warn('Failed to parse SSE event:', data);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('SSE connection error:', error);
        addLogEntry(`❌ Connection error: ${error.message}`, 'error');
        isResearching = false;
    }
}

/**
 * Handle a single SSE event and update the UI.
 */
function handleSSEEvent(event) {
    const { type, node, message, data } = event;
    
    switch (type) {
        case 'status':
            // Update pipeline visualization
            updatePipeline(node);
            // Add to progress log
            const detail = data?.detail ? ` — ${data.detail}` : '';
            addLogEntry(`${message}${detail}`);
            break;
            
        case 'report':
            // Render the research report
            currentReport = data?.report || '';
            renderReport(currentReport);
            addLogEntry(message, 'success');
            break;
            
        case 'error':
            addLogEntry(`❌ ${message}`, 'error');
            break;
            
        case 'done':
            addLogEntry(message, 'success');
            // Mark all steps as completed
            Object.values(elements.steps).forEach(step => {
                if (!step.classList.contains('completed')) {
                    step.classList.remove('active');
                }
            });
            break;
    }
}

/**
 * Update the pipeline visualization.
 * Marks the current node as active and previous nodes as completed.
 */
function updatePipeline(nodeName) {
    const nodeOrder = ['planner', 'searcher', 'extractor', 'analyzer', 'reporter'];
    const currentIndex = nodeOrder.indexOf(nodeName);
    
    if (currentIndex === -1) return;
    
    nodeOrder.forEach((name, index) => {
        const step = elements.steps[name];
        if (!step) return;
        
        if (index < currentIndex) {
            // Previous steps are completed
            step.classList.remove('active');
            step.classList.add('completed');
        } else if (index === currentIndex) {
            // Current step is active
            step.classList.remove('completed');
            step.classList.add('active');
        } else {
            // Future steps are unchanged
            step.classList.remove('active', 'completed');
        }
    });
    
    // Update connectors between completed steps
    const connectors = document.querySelectorAll('.pipeline-connector');
    connectors.forEach((conn, index) => {
        if (index < currentIndex) {
            conn.style.background = 'var(--accent-emerald)';
        } else {
            conn.style.background = '';
        }
    });
}

/**
 * Add a log entry to the progress log.
 */
function addLogEntry(text, type = '') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `
        <span class="log-dot"></span>
        <span class="log-text">${escapeHtml(text)}</span>
    `;
    elements.progressLog.appendChild(entry);
    
    // Auto-scroll to bottom
    entry.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

/**
 * Render Markdown report into the report container.
 */
function renderReport(markdown) {
    if (!markdown) return;
    
    // Configure marked for safe rendering
    marked.setOptions({
        breaks: true,
        gfm: true,
    });
    
    elements.reportContent.innerHTML = marked.parse(markdown);
    elements.reportContainer.classList.remove('hidden');
    
    // Smooth scroll to report
    setTimeout(() => {
        elements.reportContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 300);
}

/**
 * Escape HTML to prevent XSS in log entries.
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
