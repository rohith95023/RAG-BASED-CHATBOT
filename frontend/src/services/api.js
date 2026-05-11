/**
 * API Service for backend communication
 * Handles all HTTP requests to the backend API
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response) {
      const { status, data } = error.response;
      
      let errorMessage = 'Request failed';
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
      } else if (data.message) {
        errorMessage = data.message;
      }

      return Promise.reject({
        status,
        message: errorMessage,
        data: data,
      });
    }

    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  register: async (username, email, password, confirmPassword) => {
    const response = await api.post('/auth/register', {
      username,
      email,
      password,
      confirm_password: confirmPassword,
    });
    return response.data;
  },

  login: async (username, password) => {
    const response = await api.post('/auth/login', new URLSearchParams({
      username,
      password,
    }), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  logout: async () => {
    const token = localStorage.getItem('access_token');
    const response = await api.post('/auth/logout', {}, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  refreshToken: async (refreshToken) => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  getCurrentUser: async () => {
    const token = localStorage.getItem('access_token');
    const response = await api.get('/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  updateProfile: async (profileData) => {
    const token = localStorage.getItem('access_token');
    const response = await api.put('/auth/me', profileData, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  changePassword: async (currentPassword, newPassword, confirmPassword) => {
    const token = localStorage.getItem('access_token');
    const response = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  verifyToken: async () => {
    const token = localStorage.getItem('access_token');
    const response = await api.get('/auth/verify-token', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },
};

// Documents API
export const documentsAPI = {
  uploadDocument: async (file, category, onProgress) => {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        if (onProgress) onProgress(percentCompleted);
      },
    });
    return response.data;
  },

  getDocuments: async (category = null, search = null, page = 1, pageSize = 20) => {
    const token = localStorage.getItem('access_token');
    const params = { page, page_size: pageSize };
    if (category) params.category = category;
    if (search) params.search = search;

    const response = await api.get('/documents/', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      params,
    });
    return response.data;
  },

  getDocument: async (documentId) => {
    const token = localStorage.getItem('access_token');
    const response = await api.get(`/documents/${documentId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  getDocumentsBatch: async (documentIds) => {
    const token = localStorage.getItem('access_token');
    const response = await api.post('/documents/batch', documentIds, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  updateDocument: async (documentId, updateData) => {
    const token = localStorage.getItem('access_token');
    const response = await api.put(`/documents/${documentId}`, updateData, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  deleteDocument: async (documentId) => {
    const token = localStorage.getItem('access_token');
    const response = await api.delete(`/documents/${documentId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  getCategories: async () => {
    const token = localStorage.getItem('access_token');
    const response = await api.get('/documents/categories/list', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  getDocumentStats: async () => {
    const token = localStorage.getItem('access_token');
    const response = await api.get('/documents/stats/overview', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },
};

// Chat API
export const chatAPI = {
  queryDocuments: async (question, documentIds, sessionId = null, topK = 5, similarityThreshold = 0.3, stream = false, mode = 'gemini', image = null, mimeType = null) => {
    const token = localStorage.getItem('access_token');
    const response = await api.post('/chat/query', {
      question,
      session_id: sessionId,
      document_ids: documentIds,
      top_k: topK,
      similarity_threshold: similarityThreshold,
      stream,
      mode,
      image,
      mime_type: mimeType,
    }, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  queryDocumentsStreaming: async (question, documentIds, sessionId = null, topK = 5, similarityThreshold = 0.3, onChunk, abortSignal, mode = 'gemini', image = null, mimeType = null) => {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch(`${API_BASE_URL}/chat/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        session_id: sessionId,
        top_k: topK,
        similarity_threshold: similarityThreshold,
        stream: true,
        mode,
        image,
        mime_type: mimeType,
      }),
      signal: abortSignal
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Streaming request failed' }));
      throw new Error(errorData.detail || 'Streaming request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);
          onChunk(data);
        } catch (e) {
          console.warn('Error parsing stream chunk', e);
        }
      }
    }

    if (buffer.trim()) {
      try {
        onChunk(JSON.parse(buffer));
      } catch (e) {
        console.warn('Error parsing final stream chunk', e);
      }
    }
  },

  createSession: async (title, documentIds = []) => {
    const token = localStorage.getItem('access_token');
    const response = await api.post('/chat/sessions', {
      title,
      document_ids: documentIds,
    }, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  getSessions: async (isActive = null, page = 1, pageSize = 20) => {
    const token = localStorage.getItem('access_token');
    const params = { page, page_size: pageSize };
    if (isActive !== null) params.is_active = isActive;

    const response = await api.get('/chat/sessions', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      params,
    });
    return response.data;
  },

  getSession: async (sessionId) => {
    const token = localStorage.getItem('access_token');
    const response = await api.get(`/chat/sessions/${sessionId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  updateSession: async (sessionId, updateData) => {
    const token = localStorage.getItem('access_token');
    const response = await api.put(`/chat/sessions/${sessionId}`, updateData, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  deleteSession: async (sessionId) => {
    const token = localStorage.getItem('access_token');
    const response = await api.delete(`/chat/sessions/${sessionId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },

  getSessionMessages: async (sessionId, skip = 0, limit = 100) => {
    const token = localStorage.getItem('access_token');
    const response = await api.get(`/chat/sessions/${sessionId}/messages`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      params: { skip, limit },
    });
    return response.data;
  },

  getChatStats: async () => {
    const token = localStorage.getItem('access_token');
    const response = await api.get('/chat/stats/overview', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    return response.data;
  },
};

export default api;
