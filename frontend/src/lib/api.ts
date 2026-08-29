const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error('Failed to connect to backend health check');
  return res.json();
}

export async function submitReport(formData: FormData) {
  const res = await fetch(`${API_BASE_URL}/reports`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to submit citizen report');
  return res.json();
}

export async function getIncidents() {
  const res = await fetch(`${API_BASE_URL}/incidents`);
  if (!res.ok) throw new Error('Failed to fetch incidents');
  return res.json();
}

export async function getIncident(id: string) {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}`);
  if (!res.ok) throw new Error('Failed to fetch incident details');
  return res.json();
}

export async function updateIncidentStatus(id: string, status: string, notes?: string, changed_by: string = 'DISPATCHER') {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, notes, changed_by }),
  });
  if (!res.ok) throw new Error('Failed to update incident status');
  return res.json();
}

export async function getWorkOrders() {
  const res = await fetch(`${API_BASE_URL}/work-orders`);
  if (!res.ok) throw new Error('Failed to fetch work orders');
  return res.json();
}

export async function updateWorkOrderStatus(id: string, formData: FormData) {
  const res = await fetch(`${API_BASE_URL}/work-orders/${id}/status`, {
    method: 'PATCH',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to update work order status');
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
  const res = await fetch(`${API_BASE_URL}/stats`);
  if (!res.ok) throw new Error('Failed to fetch dashboard stats');
  return res.json();
}

export async function getNotifications(recipientType?: string) {
  const url = recipientType 
    ? `${API_BASE_URL}/notifications?recipient_type=${encodeURIComponent(recipientType)}`
    : `${API_BASE_URL}/notifications`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch notifications');
  return res.json();
}

export async function getUnreadNotificationCount(recipientType?: string) {
  const url = recipientType 
    ? `${API_BASE_URL}/notifications/unread?recipient_type=${encodeURIComponent(recipientType)}`
    : `${API_BASE_URL}/notifications/unread`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch unread notification count');
  return res.json();
}

export async function markNotificationRead(id: string) {
  const res = await fetch(`${API_BASE_URL}/notifications/${id}/read`, {
    method: 'PATCH',
  });
  if (!res.ok) throw new Error('Failed to mark notification as read');
  return res.json();
}

export async function markAllNotificationsRead(recipientType?: string) {
  const url = recipientType 
    ? `${API_BASE_URL}/notifications/read-all?recipient_type=${encodeURIComponent(recipientType)}`
    : `${API_BASE_URL}/notifications/read-all`;
  const res = await fetch(url, {
    method: 'PATCH',
  });
  if (!res.ok) throw new Error('Failed to mark all notifications as read');
  return res.json();
}

export async function getHotspots(status?: string, minScore?: number) {
  let url = `${API_BASE_URL}/hotspots`;
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (minScore) params.append('min_score', minScore.toString());
  if (params.toString()) url += `?${params.toString()}`;

  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch civic hotspots');
  return res.json();
}

export async function getIncidentHotspot(id: string) {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/hotspot`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch incident hotspot association');
  return res.json();
}

export async function queryAssistant(question: string) {
  const res = await fetch(`${API_BASE_URL}/assistant/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error('Failed to query Command Assistant');
  return res.json();
}
