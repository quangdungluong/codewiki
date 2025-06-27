const getWebSocketUrl = () => {
  const baseUrl = process.env.SERVER_BASE_URL || 'ws://localhost:8001';
  const wsBaseUrl = baseUrl.replace('http', 'ws');
  return `${wsBaseUrl}/ws/chat`;
};

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletionRequest {
  repo_url: string;
  messages: ChatMessage[];
  filePath?: string;
  token?: string;
  type?: string;
  language?: string;
}

export const createChatWebSocket = (
  request: ChatCompletionRequest,
  onMessage: (message: string) => void,
  onError: (error: Event) => void,
  onClose: () => void
): WebSocket => {
  const ws = new WebSocket(getWebSocketUrl());

  ws.onopen = () => {
    ws.send(JSON.stringify(request));
  };

  ws.onmessage = (event) => {
    onMessage(event.data);
  };
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError(error);
  };
  ws.onclose = () => {
    onClose();
  };
  return ws;
};

export const closeWebSocket = (ws: WebSocket | null) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
};
