const promptInput = document.getElementById('promptInput');
const submitBtn = document.getElementById('submitBtn');
const outputContainer = document.getElementById('outputContainer');
const agentStream = document.getElementById('agentStream');
const finalReport = document.getElementById('finalReport');
const pills = document.querySelectorAll('.pill');

// Toggle button active state based on input
promptInput.addEventListener('input', () => {
  if (promptInput.value.trim().length > 0) {
    submitBtn.classList.add('enabled');
    submitBtn.removeAttribute('disabled');
  } else {
    submitBtn.classList.remove('enabled');
    submitBtn.setAttribute('disabled', 'true');
  }
});

// Click pills to auto fill and submit
pills.forEach(pill => {
  pill.addEventListener('click', () => {
    // extract inner text heavily, removing the gradient div
    const text = pill.innerText;
    promptInput.value = text.replace(/"/g, '').trim();
    submitBtn.classList.add('enabled');
    submitBtn.removeAttribute('disabled');
    submitBtn.click();
  });
});

submitBtn.addEventListener('click', async () => {
  const topic = promptInput.value.trim();
  if (!topic) return;

  // UI Setup
  outputContainer.style.display = 'block';
  agentStream.innerHTML = '';
  finalReport.innerHTML = '';
  document.querySelector('.suggestions-section').style.display = 'none';
  
  // Submit Plan
  const streamItem = document.createElement('div');
  streamItem.className = 'stream-item';
  streamItem.innerText = `🧠 Planning research for: "${topic}"...`;
  agentStream.appendChild(streamItem);

  try {
    const planRes = await fetch('http://127.0.0.1:8000/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic })
    });
    const planData = await planRes.json();
    
    streamItem.innerText = `✅ Plan generated with ${planData.subquestions.length} sub-questions. Starting execution...`;

    // Execute with SSE
    const execution = await fetch('http://127.0.0.1:8000/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, custom_subquestions: planData.subquestions })
    });

    const reader = execution.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let complete = false;
    while (!complete) {
      const { value, done } = await reader.read();
      if (done) break;
      const dec = decoder.decode(value);
      const parts = dec.split('\\n\\n');

      parts.forEach(part => {
        if (part.startsWith('data: ')) {
          try {
            const dataStr = part.replace('data: ', '').trim();
            const payload = JSON.parse(dataStr);
            
            if (payload && payload.agent) {
               const elem = document.createElement('div');
               elem.className = 'stream-item';
               elem.innerText = `[${payload.agent}] ${payload.status || payload.decision || payload.result || ''}`;
               agentStream.appendChild(elem);
            }

            if (payload && payload.report) {
               finalReport.innerHTML = marked.parse(payload.report);
            }
          } catch (err) {}
        }
      });
    }

  } catch (err) {
    console.error(err);
    const errElem = document.createElement('div');
    errElem.className = 'stream-item';
    errElem.style.borderLeftColor = 'red';
    errElem.innerText = `❌ Error: ${err.message}`;
    agentStream.appendChild(errElem);
  }
});
