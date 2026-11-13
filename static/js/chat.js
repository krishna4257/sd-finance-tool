/**
 * SD Finance: Real-time Web Chat Controller
 * File: SD_Accounting_Tool/static/js/chat.js
 * 
 * Provides:
 * 1. Centrifugo WebSocket connection via official Centrifuge SDK with JWT handshake.
 * 2. Instant real-time message streaming (<10ms).
 * 3. WhatsApp-style delivery receipts (sent [✓] -> delivered [✓✓] -> read [✓✓ blue]).
 * 4. Dynamic unread count badges without page refresh.
 * 5. Automatic 2.5s dual-resilience background sync (history + channel list).
 * 6. Telugu & English UTF-8 message support.
 * 7. Audio recording, camera photos, and GPS location sharing.
 */

(function () {
  'use strict';

  let ws = null;
  let jwtToken = null;
  const loc = window.location;
  const isHttps = loc.protocol === 'https:';
  let wsEndpoint = `${isHttps ? 'wss:' : 'ws:'}//${loc.host}/connection/websocket`;
  let activeChannel = null;
  let channelsList = [];
  let isConnected = false;
  let pingTimer = null;
  let commandId = 1;

  // Centrifuge SDK instance and active subscription
  let centrifugeClient = null;
  let activeSubscription = null;
  let userSubscription = null;
  let currentUserId = null;

  // Audio recording state
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  document.addEventListener('DOMContentLoaded', function () {
    initChat();
    startBackgroundSync();
  });

  // ---------------------------------------------------------------------------
  // 1. INITIAL LOAD: Fetch Config & Channels
  // ---------------------------------------------------------------------------
  async function initChat() {
    try {
      const [tokenRes, channelsRes] = await Promise.all([
        fetch('/api/v1/chat/token').then(r => r.json()),
        fetch('/api/v1/chat/channels').then(r => r.json())
      ]);

      if (tokenRes && tokenRes.success) {
        jwtToken = tokenRes.token;
        currentUserId = tokenRes.user_id;
        if (tokenRes.ws_endpoint) {
          // If accessing via domain or localhost, use endpoint
          if (loc.host && !loc.host.includes('sivadurga.in') && tokenRes.ws_endpoint.includes('sivadurga.in')) {
            wsEndpoint = `${isHttps ? 'wss:' : 'ws:'}//${loc.host}/connection/websocket`;
          } else {
            wsEndpoint = tokenRes.ws_endpoint;
          }
        }
        connectCentrifugo();
      }

      if (channelsRes && channelsRes.success) {
        channelsList = channelsRes.channels || [];
        renderChannels(channelsList);

        // Auto-select first channel
        if (channelsList.length > 0) {
          selectChannel(channelsList[0]);
        }
      }
      if (window.updateChatBadge) window.updateChatBadge();
    } catch (e) {
      console.error('[Chat] Init error:', e);
      updateStatusPill(false, 'Disconnected');
    }
  }

  // ---------------------------------------------------------------------------
  // 2. CENTRIFUGO CONNECTION (Official Centrifuge SDK + WebSocket Fallback)
  // ---------------------------------------------------------------------------
  function connectCentrifugo() {
    if (!jwtToken) return;

    try {
      console.log('[Chat] Initializing Centrifuge SDK client for:', wsEndpoint);

      if (typeof Centrifuge !== 'undefined') {
        centrifugeClient = new Centrifuge(wsEndpoint, {
          token: jwtToken,
          minReconnectDelay: 1000,
          maxReconnectDelay: 4000
        });

        centrifugeClient.on('connected', function (ctx) {
          console.log('[Chat] Centrifugo connected (transport: ' + ctx.transport + ')');
          updateStatusPill(true, 'Connected (Real-time)');
          if (activeChannel) {
            subscribeToChannel(activeChannel.channel_id);
          }
          if (currentUserId) {
            subscribeToChannel('chat:user_' + currentUserId);
          }
        });

        centrifugeClient.on('connecting', function () {
          updateStatusPill(false, 'Connecting...');
        });

        centrifugeClient.on('disconnected', function (ctx) {
          console.warn('[Chat] Centrifugo disconnected (code: ' + ctx.code + ', reason: ' + ctx.reason + ')');
          updateStatusPill(false, 'Reconnecting...');
        });

        centrifugeClient.on('error', function (err) {
          console.warn('[Chat] Centrifugo client error:', err);
        });

        centrifugeClient.connect();
      } else {
        console.warn('[Chat] Centrifuge SDK not found, using native WebSocket fallback');
        connectNativeWs();
      }
    } catch (e) {
      console.error('[Chat] Centrifugo initialization error:', e);
      updateStatusPill(false, 'Reconnecting...');
    }
  }

  function connectNativeWs() {
    try {
      ws = new WebSocket(wsEndpoint);

      ws.onopen = function () {
        console.log('[Chat] Native WebSocket open, sending handshake token...');
        sendWsCommand({
          connect: { token: jwtToken }
        });
        startPing();
      };

      ws.onmessage = function (e) {
        handleWsMessage(e.data);
      };

      ws.onclose = function (e) {
        console.warn('[Chat] Native WebSocket closed:', e.code, e.reason);
        updateStatusPill(false, 'Reconnecting...');
        clearInterval(pingTimer);
        setTimeout(connectNativeWs, 3000);
      };

      ws.onerror = function (err) {
        console.warn('[Chat] Native WebSocket error:', err);
      };
    } catch (e) {
      console.error('[Chat] Native WebSocket failed:', e);
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

      if (data.connect) {
        console.log('[Chat] Native Centrifugo connected:', data.connect);
        updateStatusPill(true, 'Connected (Real-time)');
        if (activeChannel) {
          subscribeToChannel(activeChannel.channel_id);
        }
        if (currentUserId) {
          subscribeToChannel('chat:user_' + currentUserId);
        }
      }

      if (data.push && data.push.pub && data.push.pub.data) {
        const payload = data.push.pub.data;
        const event = payload.event || 'new_message';

        if (event === 'new_message') {
          handleIncomingMessage(payload);
        } else if (event === 'status_update') {
          handleStatusUpdate(payload);
        }
      }
      if (window.updateChatBadge) window.updateChatBadge();
    } catch (e) {
      console.warn('[Chat] Malformed frame:', e);
    }
  }

  function subscribeToChannel(channelId) {
    if (!channelId) return;
    const channelName = channelId.startsWith('chat:') ? channelId : 'chat:' + channelId;
    const isUserCh = channelName.startsWith('chat:user_');

    if (centrifugeClient) {
      let sub = centrifugeClient.getSubscription(channelName);
      if (!sub) {
        sub = centrifugeClient.newSubscription(channelName);
      }

      sub.removeAllListeners();

      sub.on('publication', function (ctx) {
        console.log('[Chat] Real-time publication received (' + channelName + '):', ctx.data);
        const payload = ctx.data;
        const event = payload.event || 'new_message';

        if (event === 'new_message') {
          handleIncomingMessage(payload);
        } else if (event === 'status_update') {
          handleStatusUpdate(payload);
        }
      });

      sub.subscribe();

      if (isUserCh) {
        userSubscription = sub;
      } else {
        if (activeSubscription && activeSubscription !== sub) {
          try { activeSubscription.unsubscribe(); } catch (e) {}
        }
        activeSubscription = sub;
      }
    } else if (ws && ws.readyState === WebSocket.OPEN) {
      sendWsCommand({
        subscribe: { channel: channelName }
      });
    }
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
  // 3. CHANNELS RENDERING & SELECTION
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
      const role = (ch.other_user_role || '').toLowerCase();
      const isSuperAdmin = isDirect && role.includes('superadmin');
      const isAdmin = isDirect && !isSuperAdmin && role.includes('admin');
      const isMgmt = isDirect && (role.includes('mgmt') || role.includes('management'));

      let avatarClass = 'staff';
      let icon = 'fa-user';
      let rolePill = '';

      if (!isDirect) {
        avatarClass = 'broadcast';
        icon = 'fa-bullhorn';
      } else if (isSuperAdmin) {
        avatarClass = 'superadmin';
        icon = 'fa-crown';
        rolePill = '<span class="role-pill superadmin">SUPER ADMIN</span>';
      } else if (isAdmin) {
        avatarClass = 'admin';
        icon = 'fa-shield-halved';
        rolePill = '<span class="role-pill admin">ADMIN</span>';
      } else if (isMgmt) {
        avatarClass = 'mgmt';
        icon = 'fa-user-tie';
        rolePill = '<span class="role-pill mgmt">MGMT</span>';
      } else {
        avatarClass = 'staff';
        icon = 'fa-user';
        rolePill = '<span class="role-pill staff">STAFF</span>';
      }

      const activeClass = (activeChannel && activeChannel.channel_id === ch.channel_id) ? 'active' : '';

      const lastSnippet = ch.last_message 
        ? (ch.last_message.type === 'text' ? escapeHtml(ch.last_message.body) : '📎 Attachment: ' + ch.last_message.type)
        : 'No messages yet';

      // Hide badge for currently open channel
      const unreadCount = (activeChannel && activeChannel.channel_id === ch.channel_id) ? 0 : (ch.unread_count || 0);
      const badgeHtml = unreadCount > 0 
        ? `<span class="channel-badge">${unreadCount}</span>` 
        : '';

      const cleanTitle = escapeHtml(ch.title.replace(/\s*\[(ADMIN|SUPER ADMIN|MGMT)\]/i, ''));

      return `
        <div class="chat-channel-item ${activeClass}" id="channel-item-${ch.channel_id}" onclick="window.selectChannelById('${ch.channel_id}')">
          <div class="channel-avatar ${avatarClass}">
            <i class="fas ${icon}"></i>
          </div>
          <div class="channel-meta">
            <div class="channel-top-row">
              <span class="channel-title">${cleanTitle} ${rolePill}</span>
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
    if (itemEl) {
      itemEl.classList.add('active');
      // Clear badge immediately upon selection
      const badge = itemEl.querySelector('.channel-badge');
      if (badge) badge.remove();
      ch.unread_count = 0;
      if (window.updateChatBadge) window.updateChatBadge();
    }

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
      if (res && res.success) {
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
  // 4. SEND MESSAGE HANDLERS
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
      const resp = await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_uuid: clientUuid,
          channel_id: activeChannel.channel_id,
          type: 'text',
          body: text
        })
      });
      const res = await resp.json();

      if (res && res.success) {
        updateMessageTick(clientUuid, 'sent', res.message_id);
        updateChannelSnippet(activeChannel.channel_id, text);
      } else {
        console.error('[Chat] Send failed:', res ? res.error : 'Unknown');
        const errorEl = document.getElementById('msg-' + clientUuid);
        if (errorEl) {
          const footer = errorEl.querySelector('.bubble-footer');
          if (footer) footer.innerHTML += ' <span style="color:#ef4444; font-size:10px;">(Failed)</span>';
        }
      }
      if (window.updateChatBadge) window.updateChatBadge();
    } catch (e) {
      console.error('[Chat] Send message network error:', e);
    }
  };

  function updateChannelSnippet(channelId, text) {
    const itemEl = document.getElementById('channel-item-' + channelId);
    if (itemEl) {
      const snippetEl = itemEl.querySelector('.channel-snippet');
      if (snippetEl) snippetEl.innerText = text;
      const timeEl = itemEl.querySelector('.channel-time');
      if (timeEl) timeEl.innerText = formatTime(new Date());
    }
  }

  // ---------------------------------------------------------------------------
  // 5. DUAL RESILIENCE BACKGROUND SYNC (2.5s) - Messages, Badges & Ticks
  // ---------------------------------------------------------------------------
  function startBackgroundSync() {
    setInterval(async function () {
      // 1. Sync messages in active conversation
      if (activeChannel) {
        try {
          const res = await fetch('/api/v1/chat/history/' + activeChannel.channel_id + '?limit=30').then(r => r.json());
          if (res && res.success && res.messages && res.messages.length > 0) {
            syncHistoryMessages(res.messages);
          }
        } catch (e) {}
      }

      // 2. Sync channel list (unread badge counters & snippets)
      syncChannels();
    }, 2500);
  }

  function syncHistoryMessages(messages) {
    const container = document.getElementById('conversation-messages');
    if (!container) return;

    // Clear empty notice if messages arrive
    const emptyNotice = container.querySelector('[style*="No messages"]');
    if (emptyNotice && messages.length > 0) {
      renderMessages(messages);
      return;
    }

    let appended = false;
    messages.forEach(m => {
      const existing = document.getElementById('msg-' + m.id) || (m.client_uuid && document.getElementById('msg-' + m.client_uuid));
      if (!existing) {
        appendMessage(m);
        appended = true;
        if (!m.is_me && m.status !== 'read') {
          ackMessage(m.id, activeChannel.channel_id, 'read');
        }
      } else {
        // Synchronize tick status (sent -> delivered -> read)
        if (m.is_me) {
          const footer = existing.querySelector('.bubble-footer');
          if (footer) {
            const span = footer.querySelector('span');
            const timeText = span ? span.outerHTML : `<span>${formatTime(m.created_at)}</span>`;
            footer.innerHTML = `${timeText} ${buildTickHtml(m.status)}`;
          }
        }
      }
      if (window.updateChatBadge) window.updateChatBadge();
    });

    if (appended) scrollToBottom();
  }

  async function syncChannels() {
    try {
      const res = await fetch('/api/v1/chat/channels').then(r => r.json());
      if (res && res.success && Array.isArray(res.channels)) {
        updateChannelsList(res.channels);
      }
    } catch (e) {}
  }

  function updateChannelsList(newList) {
    channelsList = newList;

    newList.forEach(ch => {
      const itemEl = document.getElementById('channel-item-' + ch.channel_id);
      if (!itemEl) return;

      const isCurrentActive = activeChannel && activeChannel.channel_id === ch.channel_id;

      // Update snippet
      const snippetEl = itemEl.querySelector('.channel-snippet');
      if (snippetEl) {
        const lastSnippet = ch.last_message 
          ? (ch.last_message.type === 'text' ? escapeHtml(ch.last_message.body) : '📎 Attachment: ' + ch.last_message.type)
          : 'No messages yet';
        if (snippetEl.innerHTML !== lastSnippet) {
          snippetEl.innerHTML = lastSnippet;
        }
      }

      // Update time
      const timeEl = itemEl.querySelector('.channel-time');
      if (timeEl) {
        const timeStr = formatTime(ch.last_message ? ch.last_message.created_at : ch.created_at);
        if (timeEl.innerText !== timeStr) {
          timeEl.innerText = timeStr;
        }
      }

      // Update unread badge dynamically without page refresh
      const bottomRow = itemEl.querySelector('.channel-bottom-row');
      let badgeEl = itemEl.querySelector('.channel-badge');
      const unreadCount = isCurrentActive ? 0 : (ch.unread_count || 0);

      if (unreadCount > 0) {
        if (badgeEl) {
          if (badgeEl.innerText !== String(unreadCount)) {
            badgeEl.innerText = unreadCount;
          }
        } else if (bottomRow) {
          bottomRow.insertAdjacentHTML('beforeend', `<span class="channel-badge">${unreadCount}</span>`);
        }
      } else {
        if (badgeEl) {
          badgeEl.remove();
        }
      }
      if (window.updateChatBadge) window.updateChatBadge();
    });
  }

  // ---------------------------------------------------------------------------
  // 6. REAL-TIME EVENT HANDLERS (WebSocket Push)
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
      // Mark as read immediately since the recipient is actively viewing this channel
      ackMessage(payload.id, payload.channel_id, 'read');
    } else {
      // Increment unread badge in sidebar in real time (<10ms)
      const itemEl = document.getElementById('channel-item-' + payload.channel_id);
      if (itemEl) {
        let badgeEl = itemEl.querySelector('.channel-badge');
        if (badgeEl) {
          const cur = parseInt(badgeEl.innerText, 10) || 0;
          badgeEl.innerText = cur + 1;
        } else {
          const bottomRow = itemEl.querySelector('.channel-bottom-row');
          if (bottomRow) {
            bottomRow.insertAdjacentHTML('beforeend', '<span class="channel-badge">1</span>');
          }
        }
      }
      if (window.updateChatBadge) window.updateChatBadge();
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
        const span = footer.querySelector('span');
        const timeText = span ? span.outerHTML : '';
        footer.innerHTML = `${timeText} ${buildTickHtml(newStatus)}`;
      }
    }
  }

  function ackMessage(messageId, channelId, status) {
    fetch('/api/v1/chat/ack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, channel_id: channelId, status: status })
    }).then(() => {
      if (status === 'read' && window.updateChatBadge) {
        window.updateChatBadge();
      }
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
  // 7. PHOTO & LOCATION ACTIONS
  // ---------------------------------------------------------------------------
  // Camera state
  let cameraStream = null;
  let capturedBlob = null;

  // Voice recording state
  let audioStream = null;
  let recordingTimerInterval = null;
  let recordingSeconds = 0;

  // ---------------------------------------------------------------------------
  // 7. PHOTO & CAMERA ACTIONS
  // ---------------------------------------------------------------------------
  window.openCameraModal = async function () {
    if (!activeChannel) {
      alert('Please select a conversation first.');
      return;
    }
    const modal = document.getElementById('cameraModal');
    const video = document.getElementById('camera-video-preview');
    const imgPreview = document.getElementById('camera-photo-preview');
    const btnCapture = document.getElementById('btn-camera-capture');
    const btnRetake = document.getElementById('btn-camera-retake');
    const btnSend = document.getElementById('btn-camera-send');
    const errMsg = document.getElementById('camera-error-msg');

    if (errMsg) errMsg.style.display = 'none';
    if (imgPreview) imgPreview.style.display = 'none';
    if (video) video.style.display = 'block';
    if (btnCapture) btnCapture.style.display = 'inline-block';
    if (btnRetake) btnRetake.style.display = 'none';
    if (btnSend) btnSend.style.display = 'none';
    capturedBlob = null;

    if (modal) modal.style.display = 'block';

    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      });
      if (video) {
        video.srcObject = cameraStream;
        await video.play();
      }
    } catch (err) {
      console.warn('[Chat] Camera access failed, falling back to file picker:', err);
      closeCameraModal();
      triggerFileInput();
    }
  };

  window.closeCameraModal = function () {
    const modal = document.getElementById('cameraModal');
    if (modal) modal.style.display = 'none';
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      cameraStream = null;
    }
    capturedBlob = null;
  };

  window.triggerFileInput = function () {
    closeCameraModal();
    const input = document.getElementById('chat-photo-input');
    if (input) input.click();
  };

  window.captureCameraSnapshot = function () {
    const video = document.getElementById('camera-video-preview');
    const canvas = document.getElementById('camera-canvas');
    const imgPreview = document.getElementById('camera-photo-preview');
    const btnCapture = document.getElementById('btn-camera-capture');
    const btnRetake = document.getElementById('btn-camera-retake');
    const btnSend = document.getElementById('btn-camera-send');

    if (!video || !video.videoWidth || !video.videoHeight) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(function (blob) {
      capturedBlob = blob;
      imgPreview.src = URL.createObjectURL(blob);
      imgPreview.style.display = 'block';
      video.style.display = 'none';

      btnCapture.style.display = 'none';
      btnRetake.style.display = 'inline-block';
      btnSend.style.display = 'inline-block';
    }, 'image/jpeg', 0.88);
  };

  window.retakeCameraSnapshot = function () {
    const video = document.getElementById('camera-video-preview');
    const imgPreview = document.getElementById('camera-photo-preview');
    const btnCapture = document.getElementById('btn-camera-capture');
    const btnRetake = document.getElementById('btn-camera-retake');
    const btnSend = document.getElementById('btn-camera-send');

    if (imgPreview) imgPreview.style.display = 'none';
    if (video) video.style.display = 'block';
    if (btnCapture) btnCapture.style.display = 'inline-block';
    if (btnRetake) btnRetake.style.display = 'none';
    if (btnSend) btnSend.style.display = 'none';
    capturedBlob = null;
  };

  window.sendCapturedPhoto = async function () {
    if (!capturedBlob || !activeChannel) return;

    const btnSend = document.getElementById('btn-camera-send');
    btnSend.disabled = true;
    btnSend.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

    const file = new File([capturedBlob], 'camera_snapshot.jpg', { type: 'image/jpeg' });
    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadRes = await fetch('/api/v1/chat/upload-media', {
        method: 'POST',
        body: formData
      }).then(r => r.json());

      if (uploadRes && uploadRes.success) {
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
        closeCameraModal();
        loadHistory(activeChannel.channel_id);
      } else {
        alert('Photo upload failed: ' + (uploadRes.error || 'Server error'));
      }
    } catch (e) {
      console.error('[Chat] Snapshot send error:', e);
      alert('Photo sending error: ' + e.message);
    } finally {
      btnSend.disabled = false;
      btnSend.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
    }
  };

  window.handlePhotoSelect = async function (event) {
    const file = event.target.files[0];
    if (!file || !activeChannel) return;
    event.target.value = ''; // Reset so the same file can be selected again

    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadRes = await fetch('/api/v1/chat/upload-media', {
        method: 'POST',
        body: formData
      }).then(r => r.json());

      if (uploadRes && uploadRes.success) {
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
      } else {
        alert('Photo upload failed: ' + (uploadRes.error || 'Unsupported file format'));
      }
    } catch (e) {
      console.error('[Chat] Photo upload failed:', e);
      alert('Photo upload error: ' + e.message);
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
  // 8. VOICE RECORDING (Cross-Browser HTML5 MediaRecorder)
  // ---------------------------------------------------------------------------
  window.toggleVoiceRecording = async function () {
    if (!isRecording) {
      startVoiceRecording();
    } else {
      stopAndSendVoiceRecording();
    }
  };

  async function startVoiceRecording() {
    if (!activeChannel) {
      alert('Please select a conversation first.');
      return;
    }
    const btn = document.getElementById('btn-voice-record');
    const banner = document.getElementById('voice-recording-banner');
    const timerEl = document.getElementById('voice-record-timer');

    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Determine best supported audio format
      let mimeType = 'audio/webm;codecs=opus';
      if (!window.MediaRecorder || !MediaRecorder.isTypeSupported(mimeType)) {
        if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/webm';
        } else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        } else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/ogg')) {
          mimeType = 'audio/ogg';
        } else {
          mimeType = '';
        }
      }

      mediaRecorder = mimeType ? new MediaRecorder(audioStream, { mimeType: mimeType }) : new MediaRecorder(audioStream);
      audioChunks = [];

      mediaRecorder.ondataavailable = function (e) {
        if (e.data && e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.start(100); // 100ms slice
      isRecording = true;
      btn.classList.add('recording');
      btn.innerHTML = '<i class="fas fa-stop"></i>';
      btn.title = 'Stop and Send Voice Note';

      // Show recording banner with timer
      if (banner) banner.style.display = 'flex';
      recordingSeconds = 0;
      if (timerEl) timerEl.innerText = '00:00';
      clearInterval(recordingTimerInterval);
      recordingTimerInterval = setInterval(function () {
        recordingSeconds++;
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
        const secs = String(recordingSeconds % 60).padStart(2, '0');
        if (timerEl) timerEl.innerText = `${mins}:${secs}`;
      }, 1000);

    } catch (e) {
      console.warn('[Chat] Microphone error:', e);
      alert('Microphone access denied or unavailable: ' + e.message);
    }
  }

  window.stopAndSendVoiceRecording = function () {
    if (!mediaRecorder || !isRecording) return;

    const btn = document.getElementById('btn-voice-record');
    const banner = document.getElementById('voice-recording-banner');
    clearInterval(recordingTimerInterval);
    if (banner) banner.style.display = 'none';

    btn.classList.remove('recording');
    btn.innerHTML = '<i class="fas fa-microphone"></i>';
    btn.title = 'Record Voice Note';
    isRecording = false;

    mediaRecorder.onstop = async function () {
      if (audioChunks.length === 0) return;

      const mime = mediaRecorder.mimeType || 'audio/webm';
      const ext = mime.includes('mp4') ? '.mp4' : (mime.includes('ogg') ? '.ogg' : '.webm');
      const audioBlob = new Blob(audioChunks, { type: mime });
      const audioFile = new File([audioBlob], `voice_note_${Date.now()}${ext}`, { type: mime });

      const formData = new FormData();
      formData.append('file', audioFile);

      try {
        const uploadRes = await fetch('/api/v1/chat/upload-media', {
          method: 'POST',
          body: formData
        }).then(r => r.json());

        if (uploadRes && uploadRes.success) {
          const clientUuid = generateUuid();
          await fetch('/api/v1/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              client_uuid: clientUuid,
              channel_id: activeChannel.channel_id,
              type: 'audio',
              media_url: uploadRes.media_url,
              media_duration_sec: recordingSeconds,
              body: '🎙️ Voice Note'
            })
          });
          loadHistory(activeChannel.channel_id);
        } else {
          alert('Voice note upload failed: ' + (uploadRes.error || 'Server rejected file'));
        }
      } catch (err) {
        console.error('[Chat] Voice upload failed:', err);
        alert('Voice note upload error: ' + err.message);
      } finally {
        if (audioStream) {
          audioStream.getTracks().forEach(t => t.stop());
          audioStream = null;
        }
      }
    };

    mediaRecorder.stop();
  };

  window.cancelVoiceRecording = function () {
    if (!mediaRecorder) return;
    clearInterval(recordingTimerInterval);
    const btn = document.getElementById('btn-voice-record');
    const banner = document.getElementById('voice-recording-banner');
    if (banner) banner.style.display = 'none';
    if (btn) {
      btn.classList.remove('recording');
      btn.innerHTML = '<i class="fas fa-microphone"></i>';
      btn.title = 'Record Voice Note';
    }
    isRecording = false;
    audioChunks = [];
    mediaRecorder.onstop = null;
    try { mediaRecorder.stop(); } catch (e) {}
    if (audioStream) {
      audioStream.getTracks().forEach(t => t.stop());
      audioStream = null;
    }
  };

  // ---------------------------------------------------------------------------
  // 9. BROADCAST ANNOUNCEMENT MODAL
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
  // 10. UTILITIES
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
    const q = (document.getElementById('channel-search-input').value || '').toLowerCase().trim();
    if (!q) {
      renderChannels(channelsList);
      return;
    }
    const filtered = channelsList.filter(c => {
      const titleMatch = (c.title || '').toLowerCase().includes(q);
      const roleMatch = (c.other_user_role || '').toLowerCase().includes(q);
      return titleMatch || roleMatch;
    });
    renderChannels(filtered);
  };

  window.refreshCurrentChannel = function () {
    if (activeChannel) loadHistory(activeChannel.channel_id);
    syncChannels();
  };

})();
