const promptInput = document.getElementById('promptInput');
const submitBtn = document.getElementById('submitBtn');
const planningStatus = document.getElementById('planningStatus');
const planningStatusText = document.getElementById('planningStatusText');
const hitlContainer = document.getElementById('hitlContainer');
const planList = document.getElementById('planList');
const executeBtn = document.getElementById('executeBtn');
const executionStatus = document.getElementById('executionStatus');
const executionStatusText = document.getElementById('executionStatusText');
const agentStreamDetails = document.getElementById('agentStreamDetails');
const agentStream = document.getElementById('agentStream');
const reportContainer = document.getElementById('reportContainer');
const finalReport = document.getElementById('finalReport');
const metricsDashboard = document.getElementById('metricsDashboard');
const historyList = document.getElementById('historyList');
const dlPdfBtn = document.getElementById('dlPdfBtn');

const imageBtn = document.getElementById('imageBtn');
const imageInput = document.getElementById('imageInput');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const imageThumbnail = document.getElementById('imageThumbnail');
const removeImageBtn = document.getElementById('removeImageBtn');

let globalTopic = '';
let globalFinalMarkdown = '';
let globalBase64Image = null;

// Voice Recognition Setup
const micBtn = document.getElementById('micBtn');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    recognition.onstart = () => { micBtn.classList.add('listening'); };
    recognition.onend = () => { micBtn.classList.remove('listening'); };
    recognition.onerror = () => { micBtn.classList.remove('listening'); alert("Microphone access denied or error occurred."); };
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        promptInput.value = transcript;
        submitBtn.disabled = false;
    };
    
    micBtn.addEventListener('click', () => {
        if (micBtn.classList.contains('listening')) { recognition.stop(); } 
        else { recognition.start(); }
    });
} else {
    micBtn.style.display = 'none'; // Hide if browser doesn't support it
}

// Image Upload Logic
imageBtn.addEventListener('click', () => { imageInput.click(); });
imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            // Strip the standard base64 data prefix 'data:image/jpeg;base64,' automatically added by Firefox/Chrome
            const fullData = event.target.result;
            globalBase64Image = fullData.split(',')[1];
            imageThumbnail.src = fullData;
            imagePreviewContainer.style.display = 'block';
            submitBtn.disabled = false; // Enable submit purely on image upload
        };
        reader.readAsDataURL(file);
    }
});
removeImageBtn.addEventListener('click', () => {
    globalBase64Image = null;
    imageInput.value = "";
    imagePreviewContainer.style.display = 'none';
    submitBtn.disabled = promptInput.value.trim().length === 0;
});

promptInput.addEventListener('input', () => {
    submitBtn.disabled = (promptInput.value.trim().length === 0 && !globalBase64Image);
});

// Phase 1: Planning
submitBtn.addEventListener('click', async () => {
    const topic = promptInput.value.trim();
    if (!topic && !globalBase64Image) return;
    
    globalTopic = topic;
    hitlContainer.style.display = 'none';
    executionStatus.style.display = 'none';
    agentStreamDetails.style.display = 'none';
    reportContainer.style.display = 'none';
    
    planningStatus.style.display = 'flex';
    planningStatusText.innerText = '🧠 Planner Agent is breaking down the topic...';
    
    try {
        const payload = { topic };
        if (globalBase64Image) { payload.base64_image = globalBase64Image; }
        
        const planRes = await fetch('http://127.0.0.1:8000/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
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
    agentStreamDetails.style.display = 'block';
    executionStatusText.innerText = '🔍 Researchers are gathering data (Click below to view live logs)...';
    
    // Clear old logs
    agentStream.innerHTML = '';
    
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
                            let sender = payload.agent ? payload.agent.toLowerCase() : 'system';
                            const msg = payload.status || payload.summary || payload.decision || '';
                            let css = 'agent-card'; let icon = '📡';
                            
                            // Smartly infer sender from message if backend hardcoded System
                            if (sender === 'system' || sender === '') {
                                const lowerMsg = msg.toLowerCase();
                                if (lowerMsg.includes('[critic]') || lowerMsg.includes('critic reviewing')) sender = 'critic';
                                else if (lowerMsg.includes('[researcher]') || lowerMsg.includes('researcher (attempt') || lowerMsg.includes('searching:')) sender = 'researcher';
                                else if (lowerMsg.includes('[supervisor]') && lowerMsg.includes('synthesizing')) sender = 'writer';
                                else if (lowerMsg.includes('[supervisor]')) sender = 'planner';
                            }
                            
                            if (sender.includes('planner')) { css += ' agent-planner'; icon = '🧠'; sender = 'Planner'; }
                            else if (sender.includes('researcher')) { css += ' agent-researcher'; icon = '🔍'; sender = 'Researcher'; }
                            else if (sender.includes('writer')) { css += ' agent-writer'; icon = '✍️'; sender = 'Writer'; }
                            else if (sender.includes('critic')) { 
                                sender = 'Critic';
                                if (payload.type === 'approval' || msg.includes('✅ APPROVED')) { css += ' agent-critic-approve'; icon = '✅'; }
                                else { css += ' agent-critic-reject'; icon = '❌'; }
                            } else { css += ' agent-system'; sender = 'System'; }

                            const card = document.createElement('div');
                            card.className = css;
                            card.innerHTML = `<b>${icon} ${sender}</b>: ${msg}`;
                            agentStream.appendChild(card);
                            
                            // Autoscroll stream buffer block
                            agentStream.scrollTop = agentStream.scrollHeight;
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
            globalTopic = item.topic;
            globalFinalMarkdown = item.report_text;
            submitBtn.disabled = false;
            
            // Immediately render the report from DB
            hitlContainer.style.display = 'none';
            planningStatus.style.display = 'none';
            executionStatus.style.display = 'none';
            agentStreamDetails.style.display = 'none';
            
            reportContainer.style.display = 'block';
            finalReport.innerHTML = marked.parse(item.report_text);
            
            // Render cached metrics if available
            if (item.data && item.data.metrics) {
                metricsDashboard.innerHTML = '';
                const metricsList = [
                    {l: 'Time', v: item.data.metrics.total_time + 's'},
                    {l: 'Calls', v: item.data.metrics.model_calls},
                    {l: 'Searches', v: item.data.metrics.search_calls},
                    {l: 'Mem Hits', v: item.data.metrics.memory_hits},
                    {l: 'Approvals', v: item.data.metrics.critic_approvals},
                    {l: 'Rejections', v: item.data.metrics.critic_rejections},
                ];
                metricsList.forEach(m => {
                    metricsDashboard.innerHTML += `<div class="metric-card"><div class="metric-val">${m.v}</div><div class="metric-lbl">${m.l}</div></div>`;
                });
            }
            
            // Scroll to the report
            window.scrollTo({ top: 0, behavior: 'smooth' });
         };
         historyList.appendChild(card);
      });
    }
  } catch(e) {}
}
loadHistory();
