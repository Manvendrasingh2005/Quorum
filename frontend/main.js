const promptInput = document.getElementById('promptInput');
const submitBtn = document.getElementById('submitBtn');
const planningStatus = document.getElementById('planningStatus');
const planningStatusText = document.getElementById('planningStatusText');
const hitlContainer = document.getElementById('hitlContainer');
const planList = document.getElementById('planList');
const executeBtn = document.getElementById('executeBtn');
const executionStatus = document.getElementById('executionStatus');
const executionStatusText = document.getElementById('executionStatusText');
const agentStream = document.getElementById('agentStream');
const reportContainer = document.getElementById('reportContainer');
const finalReport = document.getElementById('finalReport');
const metricsDashboard = document.getElementById('metricsDashboard');
const historyList = document.getElementById('historyList');
const dlPdfBtn = document.getElementById('dlPdfBtn');

let globalTopic = '';
let globalFinalMarkdown = '';

promptInput.addEventListener('input', () => {
    submitBtn.disabled = promptInput.value.trim().length === 0;
});

// Phase 1: Planning
submitBtn.addEventListener('click', async () => {
    const topic = promptInput.value.trim();
    if (!topic) return;
    
    globalTopic = topic;
    hitlContainer.style.display = 'none';
    executionStatus.style.display = 'none';
    reportContainer.style.display = 'none';
    
    planningStatus.style.display = 'flex';
    planningStatusText.innerText = '🧠 Planner Agent is breaking down the topic...';
    
    try {
        const planRes = await fetch('http://127.0.0.1:8000/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });
        
        if (!planRes.ok) {
            const errorData = await planRes.json();
            throw new Error(errorData.detail || 'Plan generation failed');
        }
        
        const planData = await planRes.json();
        planningStatusText.innerText = `✅ Planning complete! Generated ${planData.subquestions.length} questions.`;
        
        planList.innerHTML = '';
        planData.subquestions.forEach((q, i) => {
            const label = document.createElement('label');
            label.className = 'input-label';
            label.innerText = `Sub-question ${i+1}`;
            
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'text-input plan-input';
            input.value = q;
            
            planList.appendChild(label);
            planList.appendChild(input);
        });
        
        // Add one extra
        const labelExtra = document.createElement('label'); labelExtra.className = 'input-label'; labelExtra.innerText = `Add custom question (optional)`;
        const inputExtra = document.createElement('input'); inputExtra.type = 'text'; inputExtra.className = 'text-input plan-input'; inputExtra.placeholder = 'Type custom question...';
        planList.appendChild(labelExtra);
        planList.appendChild(inputExtra);
        
        hitlContainer.style.display = 'block';
    } catch (err) {
        planningStatusText.innerText = `❌ Error: ${err.message}`;
    }
});

// Phase 2: Execution
executeBtn.addEventListener('click', async () => {
    hitlContainer.style.display = 'none';
    const subs = Array.from(document.querySelectorAll('.plan-input')).map(el => el.value.trim()).filter(v => v);
    
    executionStatus.style.display = 'block';
    executionStatusText.innerText = '🔍 Researchers are gathering data...';
    
    // Clear old logs
    agentStream.innerHTML = '<h3>📋 Agent Activity Log</h3>';
    
    try {
        const execution = await fetch('http://127.0.0.1:8000/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: globalTopic, custom_subquestions: subs })
        });
        
        const reader = execution.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const chunks = buffer.split(/\r?\n\r?\n/);
            buffer = chunks.pop(); 

            chunks.forEach(part => {
                const dataMatch = part.match(/data:\s*(.*)/);
                if (dataMatch) {
                    try {
                        const payload = JSON.parse(dataMatch[1].trim());
                        
                        if (payload.agent || payload.status) {
                            const sender = payload.agent ? payload.agent.toLowerCase() : 'system';
                            const msg = payload.status || payload.summary || payload.decision || '';
                            let css = 'agent-card'; let icon = '📡';
                            
                            if (sender.includes('planner')) { css += ' agent-planner'; icon = '🧠'; }
                            else if (sender.includes('researcher')) { css += ' agent-researcher'; icon = '🔍'; }
                            else if (sender.includes('writer')) { css += ' agent-writer'; icon = '✍️'; }
                            else if (sender.includes('critic')) { 
                                if (payload.type === 'approval') { css += ' agent-critic-approve'; icon = '✅'; }
                                else { css += ' agent-critic-reject'; icon = '❌'; }
                            } else { css += ' agent-system'; }

                            const card = document.createElement('div');
                            card.className = css;
                            card.innerHTML = `<b>${icon} ${sender.toUpperCase()}</b>: ${msg}`;
                            agentStream.appendChild(card);
                        }

                        if (payload.report) {
                            executionStatusText.innerText = '✅ Research complete!';
                            reportContainer.style.display = 'block';
                            finalReport.innerHTML = marked.parse(payload.report);
                            globalFinalMarkdown = payload.report;
                            
                            if (payload.metrics) {
                                metricsDashboard.innerHTML = '';
                                const metricsList = [
                                    {l: 'Time', v: payload.metrics.total_time + 's'},
                                    {l: 'Calls', v: payload.metrics.model_calls},
                                    {l: 'Searches', v: payload.metrics.search_calls},
                                    {l: 'Mem Hits', v: payload.metrics.memory_hits},
                                    {l: 'Approvals', v: payload.metrics.critic_approvals},
                                    {l: 'Rejections', v: payload.metrics.critic_rejections},
                                ];
                                metricsList.forEach(m => {
                                    metricsDashboard.innerHTML += `<div class="metric-card"><div class="metric-val">${m.v}</div><div class="metric-lbl">${m.l}</div></div>`;
                                });
                            }
                            // Refresh history
                            loadHistory();
                        }
                        
                        if (payload.error) {
                            executionStatusText.innerText = `❌ Error: ${payload.error}`;
                            const errCard = document.createElement('div'); errCard.className = 'agent-card agent-critic-reject'; errCard.innerText = `Error: ${payload.error}`; agentStream.appendChild(errCard);
                        }
                    } catch(e) {
                         const errCard = document.createElement('div');
                         errCard.className = 'agent-card agent-critic-reject';
                         errCard.innerText = `JS Parsing Error: ${e.message} on payload: ${dataMatch[1].substring(0, 100)}`;
                         agentStream.appendChild(errCard);
                    }
                }
            });
        }
    } catch(err) {
        console.error(err);
        executionStatusText.innerText = `❌ Fatal Error: ${err.message}`;
    }
});

// PDF Export
dlPdfBtn.addEventListener('click', async () => {
    dlPdfBtn.innerText = 'Generating PDF...';
    try {
        const res = await fetch('http://127.0.0.1:8000/api/export_pdf', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({topic: globalTopic, markdown_report: globalFinalMarkdown})
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Quorum_Report.pdf`;
        a.click();
    } catch(e) { console.error(e); }
    dlPdfBtn.innerText = '📄 Download as PDF';
});

// Load History
async function loadHistory() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/history');
    const data = await res.json();
    historyList.innerHTML = '';
    
    if (data.history && data.history.length > 0) {
      data.history.forEach(item => {
         const card = document.createElement('div');
         card.className = 'history-card';
         card.innerHTML = `<strong>${item.topic}</strong><small>${new Date(item.created_at).toLocaleDateString()}</small>`;
         card.onclick = () => {
            promptInput.value = item.topic;
            submitBtn.disabled = false;
         };
         historyList.appendChild(card);
      });
    }
  } catch(e) {}
}
loadHistory();
