const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const messages = document.querySelector('#messages');
const history = [];

function addMessage(role, text) {
  const node = document.createElement('div');
  node.className = `msg ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

async function ask(text) {
  addMessage('user', text);
  input.value = '';
  const pending = document.createElement('div');
  pending.className = 'msg assistant';
  pending.textContent = '正在扫描天空…';
  messages.appendChild(pending);
  try {
    const response = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text, history}) });
    const data = await response.json();
    pending.textContent = data.reply || data.detail || '暂时没有拿到天气数据。';
    history.push({role:'user', content:text}, {role:'assistant', content:pending.textContent});
  } catch (error) { pending.textContent = '连接不到天气服务，请确认 API 已启动。'; }
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener('submit', (event) => { event.preventDefault(); if (input.value.trim()) ask(input.value.trim()); });
document.querySelectorAll('[data-text]').forEach((button) => button.addEventListener('click', () => ask(button.dataset.text)));
