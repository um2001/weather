const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const messages = document.querySelector('#messages');
const conversations = document.querySelector('#conversation-list');
const title = document.querySelector('#session-title');
let conversationId = Number(localStorage.getItem('weather-conversation-id')) || null;

function addMessage(role, text, weather) {
  const node = document.createElement('article');
  node.className = `message ${role}`;
  node.innerHTML = `<div class="bubble"></div>`;
  node.querySelector('.bubble').textContent = text;
  if (weather) {
    const card = document.createElement('div');
    card.className = 'weather-card';
    const day = weather.days ? weather.days[0] : weather;
    card.innerHTML = `<strong>${weather.location || ''}</strong><span>${day.date || ''}</span><b>${day.weather_description || ''}</b><span>${day.temperature_min_c ?? ''}${day.temperature_min_c != null ? '～' : ''}${day.temperature_max_c ?? day.temperature_c ?? ''}°C</span><span>降雨概率 ${day.precipitation_probability_percent ?? '—'}%</span>`;
    node.appendChild(card);
  }
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function renderConversationList(items) {
  conversations.innerHTML = '';
  items.forEach((item) => {
    const button = document.createElement('button');
    button.className = item.id === conversationId ? 'conversation active' : 'conversation';
    button.textContent = item.title;
    button.onclick = () => loadConversation(item.id);
    conversations.appendChild(button);
  });
}

async function refreshConversations() {
  const response = await fetch('/api/conversations');
  renderConversationList(await response.json());
}

async function loadConversation(id) {
  const response = await fetch(`/api/conversations/${id}`);
  const data = await response.json();
  conversationId = id;
  localStorage.setItem('weather-conversation-id', id);
  title.textContent = data.title;
  messages.innerHTML = '';
  data.messages.forEach((item) => addMessage(item.role, item.content, item.weather));
  await refreshConversations();
}

async function ask(text) {
  addMessage('user', text);
  input.value = '';
  const pending = addMessage('assistant', '正在查询真实天气…');
  try {
    const response = await fetch('/api/chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: text, conversation_id: conversationId}) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '请求失败');
    pending.querySelector('.bubble').textContent = data.reply || '暂时没有拿到建议。';
    if (data.weather) {
      pending.remove();
      addMessage('assistant', data.reply, data.weather);
    }
    if (!conversationId) {
      const list = await (await fetch('/api/conversations')).json();
      conversationId = list[0]?.id;
      if (conversationId) localStorage.setItem('weather-conversation-id', conversationId);
    }
    await refreshConversations();
  } catch (error) { pending.querySelector('.bubble').textContent = error.message || '连接不到天气服务。'; }
}

document.querySelector('#new-chat').onclick = async () => {
  const response = await fetch('/api/conversations', {method: 'POST'});
  const data = await response.json();
  conversationId = data.id;
  localStorage.setItem('weather-conversation-id', conversationId);
  title.textContent = data.title;
  messages.innerHTML = '';
  document.querySelector('#message').focus();
  await refreshConversations();
};
form.addEventListener('submit', (event) => { event.preventDefault(); if (input.value.trim()) ask(input.value.trim()); });
document.querySelectorAll('[data-text]').forEach((button) => button.addEventListener('click', () => ask(button.dataset.text)));
refreshConversations();
if (conversationId) loadConversation(conversationId);
