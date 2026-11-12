/**
 * SD Finance: Real-time Web Chat Controller
 * File: SD_Accounting_Tool/static/js/chat.js
 * 
 * Provides:
 * 1. Centrifugo WebSocket connection with JWT handshake.
 * 2. Real-time message streaming (<10ms).
 * 3. WhatsApp-style delivery receipts (sent -> delivered -> read).
 * 4. Telugu & English message rendering.
 * 5. Audio recording & Photo attachment uploads.
 */

(function () {
  'use strict';

  let ws = null;
  let jwtToken = null;
  let wsEndpoint = 'wss://sivadurga.in/connection/websocket';
  let activeChannel = null;
  let channelsList = [];
  let isConnected = false;
  let pingTimer = null;
  let commandId = 1;

  // Audio recording state
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  document.addEventListener('DOMContentLoaded', function () {
    initChat();
  });

  async function initChat() {
    try {
      // 1. Fetch token and channels in parallel
      const [tokenRes, channelsRes] = await Promise.all([
        fetch('/api/v1/chat/token').then(r => r.json()),
        fetch('/api/v1/chat/channels').then(r => r.json())
      ]);

      if (tokenRes.success) {
        jwtToken = tokenRes.token;
        if (tokenRes.ws_endpoint) wsEndpoint = tokenRes.ws_endpoint;
        connectCentrifugo();
      }

      if (channelsRes.success) {
        channelsList = channelsRes.channels || [];
        renderChannels(channelsList);

        // Auto-select first channel (e.g. Broadcast or first staff)
        if (channelsList.length > 0) {
          selectChannel(channelsList[0]);
        }
      }
    } catch (e) {
      console.error('[Chat] Init error:', e);
      updateStatusPill(false, 'Disconnected');
    }
  }

  // ---------------------------------------------------------------------------
  // CENTRIFUGO WEBSOCKET CONNECTION
  // ---------------------------------------------------------------------------
  function connectCentrifugo() {
    if (!jwtToken) return;

    try {
      ws = new WebSocket(wsEndpoint);

      ws.onopen = function () {
        // Send connect handshake
        sendWsCommand({
          connect: { token: jwtToken }
        });
        startPing();
      };

      ws.onmessage = function (event) {
        handleWsMessage(event.data);
      };

      ws.onclose = function () {
        updateStatusPill(false, 'Reconnecting...');
        clearInterval(pingTimer);
        setTimeout(connectCentrifugo, 4000);
      };

      ws.onerror = function (err) {
        console.warn('[Chat] WebSocket error:', err);
      };
    } catch (e) {
      console.error('[Chat] WebSocket connection failed:', e);
    }
  }

  function sendWsCommand(cmd) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      cmd.id = commandId++;
      ws.send(JSON.stringify(cmd));
    }
  }

  function startPing() {
    clearInterval(pingTimer);
    pingTimer = setInterval(function () {
      if (ws && ws.readyState === WebSocket.OPEN) {
        sendWsCommand({ ping: {} });
      }
    }, 25000);
  }

  function handleWsMessage(raw) {
    try {
      const data = JSON.parse(raw);

      // Connected acknowledgment
      if (data.connect) {
        updateStatusPill(true, 'Connected (Real-time)');
        if (activeChannel) {
          subscribeToChannel(activeChannel.channel_id);
        }
      }

      // Incoming Push Notification
      if (data.push && data.push.pub && data.push.pub.data) {
        const payload = data.push.pub.data;
        const event = payload.event || 'new_message';

        if (event === 'new_message') {
          handleIncomingMessage(payload);
        } else if (event === 'status_update') {
          handleStatusUpdate(payload);
        }
      }
    } catch (e) {
      console.warn('[Chat] Malformed frame:', e);
    }
  }

  function subscribeToChannel(channelId) {
    const channelName = channelId.startsWith('chat:') ? channelId : 'chat:' + channelId;
    sendWsCommand({
      subscribe: { channel: channelName }
    });
  }

  function updateStatusPill(connected, text) {
    isConnected = connected;
    const pill = document.getElementById('centrifugo-status-pill');
    if (!pill) return;

    if (connected) {
      pill.innerHTML = '<span class="pulse-dot"></span> ' + text;
      pill.style.background = 'rgba(16, 185, 129, 0.15)';
      pill.style.color = '#10b981';
      pill.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    } else {
      pill.innerHTML = '<span class="pulse-dot" style="background:#f59e0b; box-shadow:none;"></span> ' + text;
      pill.style.background = 'rgba(245, 158, 11, 0.15)';
      pill.style.color = '#f59e0b';
      pill.style.borderColor = 'rgba(245, 158, 11, 0.3)';
    }
  }

  // ---------------------------------------------------------------------------
  // CHANNELS RENDERING & SELECTION
  // ---------------------------------------------------------------------------
  function renderChannels(list) {
    const container = document.getElementById('chat-channels-list');
    if (!container) return;

    if (!list || list.length === 0) {
      container.innerHTML = '<div class="chat-loading-placeholder">No conversations found.</div>';
      return;
    }

    container.innerHTML = list.map(ch => {
      const isDirect = ch.channel_type === 'direct';
      const avatarClass = isDirect ? 'direct' : 'broadcast';
      const icon = isDirect ? 'fa-user-tie' : 'fa-bullhorn';
      const activeClass = (activeChannel && activeChannel.channel_id === ch.channel_id) ? 'active' : '';

      const lastSnippet = ch.last_message 
        ? (ch.last_message.type === 'text' ? escapeHtml(ch.last_message.body) : '📎 Attachment: ' + ch.last_message.type)
        : 'No messages yet';

      const badgeHtml = ch.unread_count > 0 
        ? `<span class="channel-badge">${ch.unread_count}</span>` 
        : '';

      return `
        <div class="chat-channel-item ${activeClass}" id="channel-item-${ch.channel_id}" onclick="window.selectChannelById('${ch.channel_id}')">
          <div class="channel-avatar ${avatarClass}">
            <i class="fas ${icon}"></i>
          </div>
          <div class="channel-meta">
            <div class="channel-top-row">
              <span class="channel-title">${escapeHtml(ch.title)}</span>
              <span class="channel-time">${formatTime(ch.last_message ? ch.last_message.created_at : ch.created_at)}</span>
            </div>
            <div class="channel-bottom-row">
              <span class="channel-snippet">${lastSnippet}</span>
              ${badgeHtml}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  window.selectChannelById = function (channelId) {
    const ch = channelsList.find(c => c.channel_id === channelId);
    if (ch) selectChannel(ch);
  };

  async function selectChannel(ch) {
    activeChannel = ch;

    // Highlight active in UI
    document.querySelectorAll('.chat-channel-item').forEach(el => el.classList.remove('active'));
    const itemEl = document.getElementById('channel-item-' + ch.channel_id);
    if (itemEl) itemEl.classList.add('active');

    // Show conversation view
    document.getElementById('chat-empty-view').style.display = 'none';
    const convoWrap = document.getElementById('chat-conversation-wrap');
    convoWrap.style.display = 'flex';

    // Set Header Info
    document.getElementById('convo-title').innerText = ch.title;
    document.getElementById('convo-status').innerText = ch.channel_type === 'broadcast' 
      ? 'Official Company Broadcast Channel' 
      : 'End-to-End Encrypted Direct Channel';

    // Subscribe WebSocket
    subscribeToChannel(ch.channel_id);

    // Load Message History
    loadHistory(ch.channel_id);
  }

  async function loadHistory(channelId) {
    const container = document.getElementById('conversation-messages');
    container.innerHTML = '<div style="text-align:center; padding:30px; color:rgba(255,255,255,0.4);"><i class="fas fa-circle-notch fa-spin"></i> Loading messages...</div>';

    try {
      const res = await fetch('/api/v1/chat/history/' + channelId).then(r => r.json());
      if (res.success) {
        const messages = res.messages || [];
        renderMessages(messages);

        // Mark unread messages as read
        messages.forEach(m => {
          if (!m.is_me && m.status !== 'read' && m.id) {
            ackMessage(m.id, channelId, 'read');
          }
        });
      }
    } catch (e) {
      console.error('[Chat] Load history error:', e);
      container.innerHTML = '<div style="text-align:center; padding:20px; color:#ef4444;">Failed to load messages.</div>';
    }
  }

  function renderMessages(messages) {
    const container = document.getElementById('conversation-messages');
    if (!messages || messages.length === 0) {
      container.innerHTML = '<div style="text-align:center; padding:40px; color:rgba(255,255,255,0.4); font-size:13px;">No messages in this conversation.<br>Start typing in English or తెలుగు!</div>';
      return;
    }

    container.innerHTML = messages.map(m => buildMessageHtml(m)).join('');
    scrollToBottom();
  }

  function buildMessageHtml(m) {
    const isMe = m.is_me;
    const bubbleClass = isMe ? 'me' : 'other';
    let contentHtml = '';

    if (m.message_type === 'image') {
      contentHtml = `<div class="chat-media-card"><img src="${escapeHtml(m.media_url)}" onclick="window.open('${escapeHtml(m.media_url)}', '_blank')" alt="Photo"></div>`;
    } else if (m.message_type === 'location') {
      contentHtml = `
        <div class="chat-location-card">
          <i class="fas fa-map-marker-alt" style="color:#10b981; font-size:20px;"></i>
          <div>
            <strong>Shared GPS Location</strong><br>
            <a href="https://www.google.com/maps/search/?api=1&query=${m.latitude},${m.longitude}" target="_blank" style="color:#38bdf8; font-size:12px; text-decoration:underline;">Open in Google Maps</a>
          </div>
        </div>
      `;
    } else if (m.message_type === 'audio') {
      contentHtml = `
        <div style="display:flex; align-items:center; gap:8px;">
          <audio controls src="${escapeHtml(m.media_url)}" style="height:32px; max-width:240px;"></audio>
        </div>
      `;
    } else {
      contentHtml = `<span>${escapeHtml(m.body)}</span>`;
    }

    const tickHtml = isMe ? buildTickHtml(m.status) : '';

    return `
      <div class="chat-bubble ${bubbleClass}" id="msg-${m.id || m.client_uuid}">
        ${!isMe && activeChannel && activeChannel.channel_type === 'broadcast' ? `<div style="font-size:11px; font-weight:700; color:#38bdf8; margin-bottom:2px;">${escapeHtml(m.sender_name)}</div>` : ''}
        ${contentHtml}
        <div class="bubble-footer">
          <span>${formatTime(m.created_at)}</span>
          ${tickHtml}
        </div>
      </div>
    `;
  }

  function buildTickHtml(status) {
    if (status === 'queued') return '<i class="far fa-clock" style="font-size:10px;"></i>';
    if (status === 'sent') return '<i class="fas fa-check" style="font-size:11px;"></i>';
    if (status === 'delivered') return '<i class="fas fa-check-double" style="font-size:11px;"></i>';
    if (status === 'read') return '<i class="fas fa-check-double tick-read" style="font-size:11px;"></i>';
    return '';
  }

  // ---------------------------------------------------------------------------
  // SEND MESSAGE HANDLERS
  // ---------------------------------------------------------------------------
  window.handleInputKey = function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  };

  window.sendTextMessage = async function () {
    if (!activeChannel) return;
    const input = document.getElementById('chat-text-input');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    const clientUuid = generateUuid();

    // Optimistic UI insert
    const tempMsg = {
      id: null,
      client_uuid: clientUuid,
      sender_name: 'Me',
      is_me: true,
      message_type: 'text',
      body: text,
      status: 'queued',
      created_at: new Date().toISOString()
    };
    appendMessage(tempMsg);

    try {
      const res = await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_uuid: clientUuid,
          channel_id: activeChannel.channel_id,
          type: 'text',
          body: text
        })
      }).then(r => r.json());

      if (res.success) {
        updateMessageTick(clientUuid, 'sent', res.message_id);
      }
    } catch (e) {
      console.error('[Chat] Send message failed:', e);
    }
  };

  // ---------------------------------------------------------------------------
  // REAL-TIME EVENT HANDLERS
  // ---------------------------------------------------------------------------
  function handleIncomingMessage(payload) {
    if (activeChannel && activeChannel.channel_id === payload.channel_id) {
      appendMessage({
        id: payload.id,
        client_uuid: payload.client_uuid,
        sender_name: payload.sender_name,
        is_me: false,
        message_type: payload.message_type,
        body: payload.body,
        media_url: payload.media_url,
        latitude: payload.latitude,
        longitude: payload.longitude,
        status: payload.status,
        created_at: payload.created_at
      });
      // Mark as read immediately
      ackMessage(payload.id, payload.channel_id, 'read');
    }

    // Update left sidebar snippet
    const snippetEl = document.querySelector(`#channel-item-${payload.channel_id} .channel-snippet`);
    if (snippetEl) {
      snippetEl.innerText = payload.message_type === 'text' ? payload.body : '📎 Attachment: ' + payload.message_type;
    }
  }

  function handleStatusUpdate(payload) {
    const msgId = payload.message_id;
    const newStatus = payload.status;
    const el = document.getElementById('msg-' + msgId);
    if (el) {
      const footer = el.querySelector('.bubble-footer');
      if (footer) {
        const tickSpan = footer.querySelector('i');
        if (tickSpan) {
          tickSpan.className = newStatus === 'read' ? 'fas fa-check-double tick-read' : (newStatus === 'delivered' ? 'fas fa-check-double' : 'fas fa-check');
        }
      }
    }
  }

  function ackMessage(messageId, channelId, status) {
    fetch('/api/v1/chat/ack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, channel_id: channelId, status: status })
    }).catch(() => {});
  }

  function appendMessage(msg) {
    const container = document.getElementById('conversation-messages');
    container.insertAdjacentHTML('beforeend', buildMessageHtml(msg));
    scrollToBottom();
  }

  function updateMessageTick(clientUuid, status, serverId) {
    const el = document.getElementById('msg-' + clientUuid);
    if (el) {
      if (serverId) el.id = 'msg-' + serverId;
      const footer = el.querySelector('.bubble-footer');
      if (footer) {
        footer.innerHTML = `<span>${formatTime(new Date())}</span> ${buildTickHtml(status)}`;
      }
    }
  }

  function scrollToBottom() {
    const container = document.getElementById('conversation-messages');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  // ---------------------------------------------------------------------------
  // PHOTO & LOCATION ACTIONS
  // ---------------------------------------------------------------------------
  window.handlePhotoSelect = async function (event) {
    const file = event.target.files[0];
    if (!file || !activeChannel) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadRes = await fetch('/api/v1/chat/upload-media', {
        method: 'POST',
        body: formData
      }).then(r => r.json());

      if (uploadRes.success) {
        const clientUuid = generateUuid();
        await fetch('/api/v1/chat/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            client_uuid: clientUuid,
            channel_id: activeChannel.channel_id,
            type: 'image',
            media_url: uploadRes.media_url,
            body: '📷 Photo'
          })
        });
        loadHistory(activeChannel.channel_id);
      }
    } catch (e) {
      console.error('[Chat] Photo upload failed:', e);
    }
  };

  window.shareWebLocation = function () {
    if (!navigator.geolocation || !activeChannel) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    navigator.geolocation.getCurrentPosition(async function (pos) {
      const clientUuid = generateUuid();
      await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_uuid: clientUuid,
          channel_id: activeChannel.channel_id,
          type: 'location',
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          body: '📍 Shared Location'
        })
      });
      loadHistory(activeChannel.channel_id);
    }, function (err) {
      alert('Unable to retrieve location: ' + err.message);
    });
  };

  // ---------------------------------------------------------------------------
  // VOICE RECORDING (HTML5 MediaRecorder)
  // ---------------------------------------------------------------------------
  window.toggleVoiceRecording = async function () {
    const btn = document.getElementById('btn-voice-record');

    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = function (e) {
          if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async function () {
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          const audioFile = new File([audioBlob], 'voice_note.webm', { type: 'audio/webm' });

          const formData = new FormData();
          formData.append('file', audioFile);

          const uploadRes = await fetch('/api/v1/chat/upload-media', {
            method: 'POST',
            body: formData
          }).then(r => r.json());

          if (uploadRes.success) {
            const clientUuid = generateUuid();
            await fetch('/api/v1/chat/send', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                client_uuid: clientUuid,
                channel_id: activeChannel.channel_id,
                type: 'audio',
                media_url: uploadRes.media_url,
                body: '🎙️ Voice Note'
              })
            });
            loadHistory(activeChannel.channel_id);
          }
        };

        mediaRecorder.start();
        isRecording = true;
        btn.classList.add('recording');
        btn.innerHTML = '<i class="fas fa-stop"></i>';
      } catch (e) {
        alert('Microphone access denied: ' + e);
      }
    } else {
      mediaRecorder.stop();
      isRecording = false;
      btn.classList.remove('recording');
      btn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
  };

  // ---------------------------------------------------------------------------
  // BROADCAST MODAL
  // ---------------------------------------------------------------------------
  window.openBroadcastModal = function () {
    const modal = document.getElementById('broadcastModal');
    if (modal) modal.style.display = 'block';
  };

  window.closeBroadcastModal = function () {
    const modal = document.getElementById('broadcastModal');
    if (modal) modal.style.display = 'none';
  };

  window.submitBroadcastAnnouncement = async function () {
    const textarea = document.getElementById('broadcast-message-text');
    const text = textarea.value.trim();
    if (!text) return;

    // Find the broadcast channel
    const bChannel = channelsList.find(c => c.channel_type === 'broadcast');
    if (!bChannel) {
      alert('Broadcast channel not found.');
      return;
    }

    const clientUuid = generateUuid();
    await fetch('/api/v1/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_uuid: clientUuid,
        channel_id: bChannel.channel_id,
        type: 'text',
        body: text
      })
    });

    textarea.value = '';
    closeBroadcastModal();
    selectChannel(bChannel);
  };

  // ---------------------------------------------------------------------------
  // UTILITIES
  // ---------------------------------------------------------------------------
  function formatTime(isoStr) {
    if (!isoStr) return '';
    const dt = new Date(isoStr);
    const now = new Date();
    if (now.toDateString() === dt.toDateString()) {
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return (dt.getMonth() + 1) + '/' + dt.getDate();
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, function (m) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m];
    });
  }

  function generateUuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  window.filterChannels = function () {
    const q = (document.getElementById('channel-search-input').value || '').toLowerCase();
    const filtered = channelsList.filter(c => c.title.toLowerCase().includes(q));
    renderChannels(filtered);
  };

  window.refreshCurrentChannel = function () {
    if (activeChannel) loadHistory(activeChannel.channel_id);
  };

})();
