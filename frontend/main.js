const promptInput = document.getElementById('promptInput');
const submitBtn = document.getElementById('submitBtn');
const hitlContainer = document.getElementById('hitlContainer');
const planList = document.getElementById('planList');
const executeBtn = document.getElementById('executeBtn');
const outputContainer = document.getElementById('outputContainer');
const agentStream = document.getElementById('agentStream');
const reportContainer = document.getElementById('reportContainer');
const finalReport = document.getElementById('finalReport');
const metricsDashboard = document.getElementById('metricsDashboard');
const suggestionsSection = document.getElementById('suggestionsSection');
const historySection = document.getElementById('historySection');
const dlPdfBtn = document.getElementById('dlPdfBtn');
let globalTopic = '';
let globalFinalMarkdown = '';

promptInput.addEventListener('input', () => {
  if (promptInput.value.trim().length > 0) {
    submitBtn.classList.add('enabled'); submitBtn.removeAttribute('disabled');
  } else {
    submitBtn.classList.remove('enabled'); submitBtn.setAttribute('disabled', 'true');
  }
});

document.querySelectorAll('.pill').forEach(pill => {
  pill.addEventListener('click', () => {
    promptInput.value = pill.innerText.replace(/"/g, '').trim();
    submitBtn.classList.add('enabled'); submitBtn.removeAttribute('disabled');
    submitBtn.click();
  });
});

// Phase 1: Planning (HITL)
submitBtn.addEventListener('click', async () => {
  const topic = promptInput.value.trim();
  if (!topic) return;
  globalTopic = topic;

  suggestionsSection.style.display = 'none';
  historySection.style.display = 'none';
  reportContainer.style.display = 'none';
  hitlContainer.style.display = 'none';
  
  // Show intermediate log
  outputContainer.style.display = 'block';
  agentStream.innerHTML = '';
  const initCard = document.createElement('div');
  initCard.className = 'agent-card agent-system';
  initCard.innerHTML = `<b>[0.0s]</b> 📡 <b>SYSTEM</b>: Contacting Planner Agent for "${topic}"...`;
  agentStream.appendChild(initCard);

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
    initCard.innerHTML = `<b>[SYSTEM]</b> ✅ Plan generated with ${planData.subquestions.length} sub-questions. Waiting for user review.`;
    
    // Setup HITL Modal
    planList.innerHTML = '';
    planData.subquestions.forEach(q => {
        const input = document.createElement('input');
        input.className = 'plan-input';
        input.value = q;
        planList.appendChild(input);
    });
    const extra = document.createElement('input');
    extra.className = 'plan-input';
    extra.placeholder = "Add a custom research question...";
    planList.appendChild(extra);
    
    hitlContainer.style.display = 'block';

  } catch (err) {
    const errCard = document.createElement('div');
    errCard.className = 'agent-card agent-critic-reject';
    errCard.innerText = `❌ Error: ${err.message}`;
    agentStream.appendChild(errCard);
  }
});

// Phase 2: Execution
executeBtn.addEventListener('click', async () => {
    hitlContainer.style.display = 'none';
    const subs = Array.from(document.querySelectorAll('.plan-input')).map(el => el.value.trim()).filter(v => v);
    
    outputContainer.style.display = 'block';
    
    try {
        const execution = await fetch('http://127.0.0.1:8000/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: globalTopic, custom_subquestions: subs })
        });
        
        const reader = execution.body.getReader();
        const decoder = new TextDecoder("utf-8");
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunks = decoder.decode(value).split('\\n\\n');

            chunks.forEach(part => {
                if (part.startsWith('data: ')) {
                    try {
                        const payload = JSON.parse(part.replace('data: ', '').trim());
                        
                        // Parse Agent Log
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
                            card.scrollIntoView({behavior: 'smooth'});
                        }

                        // Parse Done State
                        if (payload.report) {
                            reportContainer.style.display = 'block';
                            finalReport.innerHTML = marked.parse(payload.report);
                            globalFinalMarkdown = payload.report;
                            dlPdfBtn.style.display = 'inline-block';
                            
                            // Render Metrics
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
                        }
                        if (payload.error) {
                            const errCard = document.createElement('div'); errCard.className = 'agent-card agent-critic-reject'; errCard.innerText = `Error: ${payload.error}`; agentStream.appendChild(errCard);
                        }
                    } catch(e) {}
                }
            });
        }
    } catch(err) {
        console.error(err);
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
    dlPdfBtn.innerText = '📄 Download PDF';
});

// Load History
async function loadHistory() {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/history');
    const data = await res.json();
    if (data.history && data.history.length > 0) {
      historySection.style.display = 'block';
      data.history.forEach(item => {
         const card = document.createElement('div');
         card.className = 'history-card';
         card.innerHTML = `<h4>${item.topic}</h4><p class="history-date">${new Date(item.created_at).toLocaleDateString()}</p>`;
         card.onclick = () => {
            promptInput.value = item.topic;
            submitBtn.classList.add('enabled'); submitBtn.removeAttribute('disabled');
            window.scrollTo({ top: 0, behavior: 'smooth' });
         };
         document.getElementById('historyGrid').appendChild(card);
      });
    }
  } catch(e) {}
}
loadHistory();
