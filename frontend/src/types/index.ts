export type IncidentStatus = 'SUBMITTED' | 'TRIAGED' | 'ASSIGNED' | 'IN_PROGRESS' | 'RESOLVED' | 'VERIFIED';
export type WorkOrderStatus = 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type PriorityLevel = 'P1_CRITICAL' | 'P2_HIGH' | 'P3_MEDIUM' | 'P4_LOW';
export type UserRole = 'CITIZEN' | 'DISPATCHER' | 'FIELD_CREW';

export interface PriorityFactor {
  factor: string;
  score: number;
  contribution: number;
  reason: string;
}

export interface DuplicateMatchInfo {
  is_duplicate: boolean;
  matched_incident_id?: string;
  semantic_similarity: number;
  distance_meters?: number;
  category_match: boolean;
  match_confidence: number;
  reason: string;
}

export interface Report {
  id: string;
  citizen_id?: string;
  description: string;
  image_path?: string;
  latitude?: number;
  longitude?: number;
  address?: string;
  incident_id?: string;
  created_at: string;
  duplicate_info?: DuplicateMatchInfo;
}

export interface WorkOrder {
  id: string;
  incident_id: string;
  assigned_department: string;
  assigned_team?: string;
  assigned_worker?: string;
  assigned_worker_id?: string;
  recommended_action: string;
  required_materials?: string;
  safety_precautions?: string;
  status: WorkOrderStatus;
  sla_deadline?: string;
  sla_status?: 'ON_TRACK' | 'AT_RISK' | 'BREACHED' | 'COMPLETED';
  completion_notes?: string;
  completion_image_path?: string;
  created_at: string;
  assigned_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface StatusLog {
  id: string;
  incident_id: string;
  old_status?: IncidentStatus;
  new_status: IncidentStatus;
  changed_by: string;
  notes?: string;
  timestamp: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  category: string;
  ai_category?: string;
  ai_confidence?: number;
  ai_department?: string;
  confidence_tier?: 'HIGH' | 'MEDIUM' | 'LOW';
  requires_human_review?: boolean;
  review_status?: 'PENDING' | 'ACCEPTED' | 'CORRECTED';
  review_reason?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  severity_level: SeverityLevel;
  severity_reason?: string;
  confidence: number;
  hazards?: string[];
  evidence_observations?: string[];
  recommended_action?: string;
  priority_score: number;
  priority_level?: PriorityLevel;
  priority_reason?: string;
  priority_factors?: PriorityFactor[];
  assigned_department?: string;
  routing_reason?: string;
  verification_notes?: string;
  status: IncidentStatus;
  latitude?: number;
  longitude?: number;
  address?: string;
  created_at: string;
  updated_at: string;
  reports?: Report[];
  work_order?: WorkOrder;
  status_logs?: StatusLog[];
}

export interface DashboardStats {
  total_reports: number;
  total_incidents: number;
  open_incidents: number;
  resolved_incidents: number;
  verified_incidents: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
}

export interface AppNotification {
  id: string;
  recipient_type: string;
  recipient_id?: string;
  incident_id?: string;
  work_order_id?: string;
  channel: string;
  event_type: string;
  title: string;
  message: string;
  status: string;
  provider: string;
  is_read: boolean;
  created_at: string;
  sent_at?: string;
  metadata_json?: string;
}

export interface Hotspot {
  hotspot_id: string;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  incident_count: number;
  report_count: number;
  average_priority_score: number;
  highest_priority_score: number;
  p1_count: number;
  p2_count: number;
  dominant_category: string;
  pattern: string;
  category_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  hotspot_score: number;
  hotspot_level: 'NORMAL' | 'EMERGING' | 'HIGH' | 'CRITICAL';
  explanation: string;
  incident_ids: string[];
}

export interface HotspotRecommendation {
  type: 'HOTSPOT' | 'INCIDENT';
  title: string;
  hotspot_id?: string;
  incident_id?: string;
  incident_count?: number;
  report_count?: number;
  score: number;
  level?: string;
  priority_level?: string;
  department?: string;
  reason: string;
}

export interface HotspotsListResponse {
  total_hotspots: number;
  hotspots: Hotspot[];
  recommendations: HotspotRecommendation[];
}

export interface AssistantSource {
  type: string;
  id: string;
  label: string;
}

export interface AssistantQueryResponse {
  question: string;
  intent: string;
  answer: string;
  sources: AssistantSource[];
}
