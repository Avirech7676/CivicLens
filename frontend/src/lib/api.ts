const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('civiclens_token');
}

export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('civiclens_token', token);
}

export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('civiclens_token');
  localStorage.removeItem('civiclens_user');
}

export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = getAuthToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export function getMediaUrl(path?: string | null): string {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const baseOrigin = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  return `${baseOrigin}${cleanPath}`;
}

export async function loginUser(email: string, password: string) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Invalid email or password');
  }
  return res.json();
}

export async function getAuthMe() {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to authenticate user');
  }
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`, { cache: 'no-store' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to connect to backend health check');
  }
  return res.json();
}

export async function submitReport(formData: FormData) {
  const res = await fetch(`${API_BASE_URL}/reports`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to submit citizen report');
  }
  return res.json();
}

export async function getIncidents() {
  const res = await fetch(`${API_BASE_URL}/incidents`, { 
    headers: { ...getAuthHeaders() },
    cache: 'no-store' 
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch incidents');
  }
  return res.json();
}

export async function getIncident(id: string) {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}`, { 
    headers: { ...getAuthHeaders() },
    cache: 'no-store' 
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch incident details');
  }
  return res.json();
}

export async function updateIncidentStatus(id: string, status: string, notes?: string, changed_by: string = 'DISPATCHER') {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ status, notes, changed_by }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to update incident status');
  }
  return res.json();
}

export async function overrideIncidentClassification(id: string, category?: string, assigned_department?: string, priority_level?: string, reason: string = "Dispatcher manual override") {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/override`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ category, assigned_department, priority_level, reason }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to override incident classification');
  }
  return res.json();
}

export async function getWorkOrders() {
  const res = await fetch(`${API_BASE_URL}/work-orders`, { 
    headers: { ...getAuthHeaders() },
    cache: 'no-store' 
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch work orders');
  }
  return res.json();
}

export async function getMyWorkOrders() {
  const res = await fetch(`${API_BASE_URL}/work-orders/my`, { 
    headers: { ...getAuthHeaders() },
    cache: 'no-store' 
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch my assigned work orders');
  }
  return res.json();
}

export async function updateWorkOrderStatus(id: string, formData: FormData) {
  const res = await fetch(`${API_BASE_URL}/work-orders/${id}/status`, {
    method: 'PATCH',
    headers: { ...getAuthHeaders() },
    body: formData,
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to update work order status');
  }
  return res.json();
}

export async function assignWorkOrderCrew(id: string, assigned_team?: string, assigned_worker?: string, assigned_worker_id?: string) {
  const res = await fetch(`${API_BASE_URL}/work-orders/${id}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ assigned_team, assigned_worker, assigned_worker_id }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to assign crew to work order');
  }
  return res.json();
}

export async function getEligibleCrews(workOrderId: string) {
  const res = await fetch(`${API_BASE_URL}/work-orders/${workOrderId}/eligible-crews`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch eligible crews');
  }
  return res.json();
}

export async function verifyIncidentResolution(id: string, verifiedFixed: boolean, citizenNotes?: string) {
  const formData = new FormData();
  formData.append('verified_fixed', verifiedFixed ? 'true' : 'false');
  if (citizenNotes) {
    formData.append('citizen_notes', citizenNotes);
  }

  const res = await fetch(`${API_BASE_URL}/incidents/${id}/verify`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to submit verification');
  }
  return res.json();
}

export async function getStats() {
  const res = await fetch(`${API_BASE_URL}/stats`, { cache: 'no-store' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch dashboard stats');
  }
  return res.json();
}

export async function getNotifications(recipientType?: string) {
  const url = recipientType 
    ? `${API_BASE_URL}/notifications?recipient_type=${encodeURIComponent(recipientType)}`
    : `${API_BASE_URL}/notifications`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch notifications');
  }
  return res.json();
}

export async function getUnreadNotificationCount(recipientType?: string) {
  const url = recipientType 
    ? `${API_BASE_URL}/notifications/unread?recipient_type=${encodeURIComponent(recipientType)}`
    : `${API_BASE_URL}/notifications/unread`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch unread notification count');
  }
  return res.json();
}

export async function markNotificationRead(id: string) {
  const res = await fetch(`${API_BASE_URL}/notifications/${id}/read`, {
    method: 'PATCH',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to mark notification as read');
  }
  return res.json();
}

export async function markAllNotificationsRead(recipientType?: string) {
  const url = recipientType 
    ? `${API_BASE_URL}/notifications/read-all?recipient_type=${encodeURIComponent(recipientType)}`
    : `${API_BASE_URL}/notifications/read-all`;
  const res = await fetch(url, {
    method: 'PATCH',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to mark all notifications as read');
  }
  return res.json();
}

export async function getHotspots(status?: string, minScore?: number) {
  let url = `${API_BASE_URL}/hotspots`;
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (minScore) params.append('min_score', minScore.toString());
  if (params.toString()) url += `?${params.toString()}`;

  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch civic hotspots');
  }
  return res.json();
}

export async function getIncidentHotspot(id: string) {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/hotspot`, { cache: 'no-store' });
  if (res.status === 404) return null;
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch incident hotspot association');
  }
  return res.json();
}

export async function queryAssistant(question: string) {
  const res = await fetch(`${API_BASE_URL}/assistant/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to query Command Assistant');
  }
  return res.json();
}

export async function getMLEvaluationSummary(mode: string = 'baseline') {
  const res = await fetch(`${API_BASE_URL}/ml/evaluation/summary?mode=${mode}`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch ML evaluation summary');
  }
  return res.json();
}

export async function getDataQualityStats() {
  const res = await fetch(`${API_BASE_URL}/ml/data-quality`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch data quality stats');
  }
  return res.json();
}

export async function getOperationsAnalytics() {
  const res = await fetch(`${API_BASE_URL}/ml/analytics`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch operations analytics');
  }
  return res.json();
}

export async function getAIReviewQueue() {
  const res = await fetch(`${API_BASE_URL}/incidents/review-queue`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch AI review queue');
  }
  return res.json();
}

export async function getAIFeedbackSummary() {
  const res = await fetch(`${API_BASE_URL}/ml/feedback/summary`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store'
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to fetch AI feedback summary');
  }
  return res.json();
}
