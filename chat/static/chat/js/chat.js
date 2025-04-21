document.addEventListener("DOMContentLoaded", () => {
  console.log("JS已加载，当前路径:", window.location.pathname);
  
  // 获取房间名
  // 方法1: 从URL中提取
  let roomName = "";
  if (window.location.pathname.startsWith("/room/")) {
    roomName = window.location.pathname.split("/").filter(Boolean).pop();
  }
  // 方法2: 从页面数据中获取(如果模板提供了这个变量)
  if (window.roomData && window.roomData.name) {
    roomName = window.roomData.name;
  }
  
  if (!roomName) {
    console.error("无法确定房间名称，无法建立WebSocket连接");
    return;
  }
  
  // 更新状态显示
  const statusDiv = document.getElementById("connection-status");
  function updateStatus(message, isError = false) {
    if (statusDiv) {
      statusDiv.innerHTML = isError 
        ? `<i class="bi bi-exclamation-triangle me-1"></i>WebSocket状态: ${message}`
        : `<i class="bi bi-wifi me-1"></i>WebSocket状态: ${message}`;
      
      statusDiv.className = isError 
        ? "chat-status text-danger" 
        : "chat-status";
    }
    console.log("WebSocket状态:", message);
  }
  
  updateStatus("正在连接...");
  
  // 创建WebSocket连接
  const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${wsScheme}://${window.location.host}/ws/chat/${roomName}/`;

  console.log("尝试连接WebSocket:", wsUrl);
  
  const chatSocket = new WebSocket(wsUrl);
  
  const log = document.querySelector("#chat-log");
  const input = document.querySelector("#chat-message-input");
  const sendButton = document.querySelector("#chat-message-submit");
  const historyButton = document.querySelector("#load-history-btn");
  
  // 当前历史记录页码
  let currentHistoryPage = 1;
  // 是否已经加载完所有历史记录
  let historyEnded = false;
  // 是否正在加载
  let isLoading = false;
  // 加载指示器
  const loadingIndicator = document.createElement("div");
  loadingIndicator.className = "chat-message message-system";
  loadingIndicator.innerHTML = `<div><i class="bi bi-arrow-repeat loading-icon"></i> 正在加载历史消息...</div>`;

  // 格式化时间的辅助函数
  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  
  // 格式化时间戳
  function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // 添加消息到聊天记录
  function addMessage(data, prepend = false) {
    const messageDiv = document.createElement("div");
    const time = data.timestamp ? formatTimestamp(data.timestamp) : getCurrentTime();
    
    if (data.system) {
      // 系统消息
      messageDiv.className = "chat-message message-system";
      messageDiv.innerHTML = `
        <div>${data.message}</div>
        <small>${time}</small>
      `;
    } else {
      // 判断是否为当前用户发送的消息
      const isSelf = data.username === document.querySelector(".user-info").textContent.trim();
      
      messageDiv.className = isSelf 
        ? "chat-message message-self" 
        : "chat-message message-other";
      
      messageDiv.innerHTML = `
        <div>
          ${!isSelf ? `<strong>${data.username}</strong><br>` : ''}
          ${data.message}
        </div>
        <small>${time}</small>
      `;
    }
    
    if (prepend) {
      log.insertBefore(messageDiv, log.firstChild);
    } else {
      log.appendChild(messageDiv);
      log.scrollTop = log.scrollHeight;
    }
  }

  // 添加加载历史记录按钮
  function addHistoryButton() {
    if (document.getElementById("history-button-container")) {
      return; // 已经存在，不重复添加
    }
    
    const buttonContainer = document.createElement("div");
    buttonContainer.id = "history-button-container";
    buttonContainer.className = "text-center my-2";
    buttonContainer.innerHTML = `
      <button id="load-history-btn" class="btn btn-sm btn-outline-secondary">
        <i class="bi bi-clock-history me-1"></i>加载历史消息
      </button>
    `;
    
    log.insertBefore(buttonContainer, log.firstChild);
    
    // 添加点击事件
    document.getElementById("load-history-btn").addEventListener("click", loadHistory);
  }
  
  // 加载历史记录
  function loadHistory() {
    if (isLoading || historyEnded) return;
    
    isLoading = true;
    
    // 添加加载指示器
    log.insertBefore(loadingIndicator, log.firstChild);
    
    // 请求历史记录
    chatSocket.send(JSON.stringify({
      load_history: true,
      page: currentHistoryPage
    }));
  }
  
  // 检测滚动到顶部，加载更多历史记录
  log.addEventListener("scroll", () => {
    if (log.scrollTop === 0 && !isLoading && !historyEnded) {
      loadHistory();
    }
  });

  // 连接事件处理程序
  chatSocket.onopen = function(e) {
    updateStatus("已连接");
    // 清空初始连接消息并添加欢迎消息
    log.innerHTML = "";
    addMessage({
      system: true,
      message: `欢迎来到 #${roomName} 聊天室`
    });
    
    // 添加历史记录按钮
    addHistoryButton();
  };

  chatSocket.onerror = function(e) {
    console.error("WebSocket错误:", e);
    updateStatus("连接错误", true);
  };
  
  chatSocket.onmessage = function (e) {
    console.log("收到消息:", e.data);
    try {
      const data = JSON.parse(e.data);
      
      if (data.history) {
        // 移除加载指示器
        if (log.contains(loadingIndicator)) {
          log.removeChild(loadingIndicator);
        }
        
        // 处理历史记录
        const messages = data.messages;
        historyEnded = data.is_end;
        currentHistoryPage++;
        
        if (messages.length === 0) {
          // 没有更多历史记录
          historyEnded = true;
          
          // 显示提示
          const noMoreHistory = document.createElement("div");
          noMoreHistory.className = "chat-message message-system";
          noMoreHistory.innerHTML = `<div>没有更多历史消息了</div>`;
          log.insertBefore(noMoreHistory, log.firstChild);
        } else {
          // 添加历史消息，从旧到新
          for (const msg of messages) {
            addMessage(msg, true);
          }
        }
        
        // 如果已经到达历史记录末尾，移除加载按钮
        if (historyEnded) {
          const buttonContainer = document.getElementById("history-button-container");
          if (buttonContainer) {
            log.removeChild(buttonContainer);
          }
        }
        
        isLoading = false;
      } else if (data.error) {
        addMessage({
          system: true,
          message: `错误: ${data.error}`
        });
      } else {
        addMessage(data);
      }
    } catch (error) {
      console.error("解析消息时出错:", error);
    }
  };

  chatSocket.onclose = function(e) {
    updateStatus(`连接已关闭 (代码: ${e.code})`, true);
    console.error("WebSocket连接关闭. 代码:", e.code, "原因:", e.reason || "未知");
    
    addMessage({
      system: true,
      message: "与服务器的连接已断开，将在5秒后尝试重新连接..."
    });
    
    // 如果连接关闭，尝试每5秒重新连接一次
    setTimeout(() => {
      updateStatus("尝试重新连接...");
      window.location.reload(); // 简单的重新连接方法是刷新页面
    }, 5000);
  };

  // 发送消息函数
  function sendMessage() {
    const message = input.value.trim();
    if (message === "") return;
    
    try {
      console.log("发送消息:", message);
      chatSocket.send(JSON.stringify({ message: message }));
      
      // 只有在消息成功发送时才清空输入框
      input.value = "";
    } catch (error) {
      console.error("发送消息时出错:", error);
      updateStatus("发送消息失败", true);
    }
  }

  // 键盘事件监听
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // 阻止默认的回车换行
      sendMessage();
    }
  });

  // 发送按钮点击事件
  if (sendButton) {
    sendButton.addEventListener("click", sendMessage);
  }
  
  // 聚焦到输入框
  input.focus();
}); 