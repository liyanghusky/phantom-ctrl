(() => {
  // ── 状态 ──────────────────────────────────────────────────────────────
  let token = sessionStorage.getItem('token') || '';
  let ws = null;
  let wsRetryDelay = 1000;
  let wsRetryTimer = null;

  // ── DOM ───────────────────────────────────────────────────────────────
  const connectPanel = document.getElementById('connect-panel');
  const mainPanel    = document.getElementById('main-panel');
  const tokenInput   = document.getElementById('token-input');
  const connectBtn   = document.getElementById('connect-btn');
  const connectError = document.getElementById('connect-error');
  const canvas       = document.getElementById('game-canvas');
  const ctx          = canvas.getContext('2d');
  const launchBtn    = document.getElementById('launch-btn');
  const textInput    = document.getElementById('text-input');
  const sendBtn      = document.getElementById('send-btn');
  const statusDot    = document.getElementById('status-dot');
  const statusLabel  = document.getElementById('status-label');

  // ── 初始化：已有 token 时直接进主界面 ─────────────────────────────────
  if (token) {
    showMain();
  }

  // ── 连接按钮 ──────────────────────────────────────────────────────────
  connectBtn.addEventListener('click', () => {
    const t = tokenInput.value.trim();
    if (!t) { connectError.textContent = '请输入 Token'; return; }
    token = t;
    sessionStorage.setItem('token', token);
    showMain();
  });

  // ── 切换到主界面并启动 WS ─────────────────────────────────────────────
  function showMain() {
    connectPanel.classList.add('hidden');
    mainPanel.classList.remove('hidden');
    resizeCanvas();
    connectWS();
  }

  // ── API 请求封装 ───────────────────────────────────────────────────────
  async function api(path, body) {
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Token': token },
        body: JSON.stringify(body),
      });
      if (res.status === 401) { sessionStorage.removeItem('token'); location.reload(); }
    } catch (e) {
      console.warn('api error', path, e);
    }
  }

  // ── WebSocket 连接与自动重连 ───────────────────────────────────────────
  function connectWS() {
    if (ws) { ws.onclose = null; ws.close(); }
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/stream?token=${encodeURIComponent(token)}`);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      setStatus('connected');
      wsRetryDelay = 1000; // 成功后重置退避时间
    };

    ws.onmessage = async (e) => {
      // 收到 JPEG 二进制帧 → 解码 → 绘制到 canvas
      const blob = new Blob([e.data], { type: 'image/jpeg' });
      const bmp  = await createImageBitmap(blob);
      ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height);
      bmp.close();
    };

    ws.onerror = () => setStatus('disconnected');

    ws.onclose = () => {
      setStatus('disconnected');
      // 指数退避重连，最长 30s
      wsRetryTimer = setTimeout(() => {
        wsRetryDelay = Math.min(wsRetryDelay * 2, 30000);
        connectWS();
      }, wsRetryDelay);
    };
  }

  function setStatus(state) {
    statusDot.className = `status-dot ${state}`;
    statusLabel.textContent = state === 'connected' ? '已连接' : '未连接';
  }

  // ── canvas 尺寸自适应（16:9） ──────────────────────────────────────────
  function resizeCanvas() {
    const toolbarH = document.getElementById('toolbar').offsetHeight || 130;
    const w = window.innerWidth;
    const h = window.innerHeight - toolbarH;
    // 在可用区域内保持 16:9，以宽度为基准
    const canvasH = Math.min(h, w * 9 / 16);
    const canvasW = canvasH * 16 / 9;
    canvas.width  = Math.round(canvasW);
    canvas.height = Math.round(canvasH);
    canvas.style.width  = canvas.width  + 'px';
    canvas.style.height = canvas.height + 'px';
  }

  window.addEventListener('resize', resizeCanvas);

  // ── canvas 点击 / 触摸 → POST /api/click ──────────────────────────────
  function handlePointer(e, button) {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const src  = e.touches ? e.touches[0] : e;
    // 归一化到 [0, 1]
    const x = (src.clientX - rect.left)  / rect.width;
    const y = (src.clientY - rect.top)   / rect.height;
    api('/api/click', { x, y, button });
  }

  canvas.addEventListener('click',      (e) => handlePointer(e, 'left'));
  canvas.addEventListener('contextmenu',(e) => { e.preventDefault(); handlePointer(e, 'right'); });
  canvas.addEventListener('touchstart', (e) => handlePointer(e, 'left'), { passive: false });

  // ── 文字输入 → POST /api/type ─────────────────────────────────────────
  function sendText() {
    const text = textInput.value;
    if (!text) return;
    api('/api/type', { text });
    textInput.value = '';
  }
  sendBtn.addEventListener('click', sendText);
  textInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendText(); });

  // ── 功能键 → POST /api/key ────────────────────────────────────────────
  document.querySelectorAll('.btn-key').forEach(btn => {
    btn.addEventListener('click', () => {
      api('/api/key', { key: btn.dataset.key });
    });
  });

  // ── 启动游戏 → POST /api/launch ───────────────────────────────────────
  launchBtn.addEventListener('click', async () => {
    launchBtn.disabled = true;
    try {
      await fetch('/api/launch', {
        method: 'POST',
        headers: { 'X-Token': token },
      });
    } finally {
      setTimeout(() => { launchBtn.disabled = false; }, 3000);
    }
  });
})();
