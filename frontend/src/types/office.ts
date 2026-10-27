export type AgentRole =
  | 'product_manager'
  | 'aiml_architect'
  | 'engineering_lead'
  | 'ux_designer'
  | 'security_auditor'
  | 'qa_strategist'
  | 'conflict_resolver'
  | 'blueprint_architect'
  | 'coding_agent';

export type AgentStatus =
  | 'IDLE'
  | 'THINKING'
  | 'WORKING'
  | 'WAITING'
  | 'MOVING'
  | 'DISCUSSING'
  | 'REVIEWING'
  | 'CONFLICT'
  | 'BLOCKED'
  | 'COMPLETED'
  | 'FAILED'
  | 'ERROR';

export type WorkspaceId =
  | 'understanding_workspace'
  | 'product_workspace'
  | 'aiml_workspace'
  | 'engineering_workspace'
  | 'ux_workspace'
  | 'security_workspace'
  | 'qa_workspace'
  | 'collaboration_table'
  | 'conflict_room'
  | 'architect_office'
  | 'coding_workshop'
  | 'testing_workspace';

export interface Position {
  x: number;
  y: number;
}

export interface AgentCharacter {
  id: AgentRole;
  name: string;
  roleTitle: string;
  avatarColor: string;
  accentColor: string;
  iconName: string;
  status: AgentStatus;
  currentTask: string;
  activityMessage: string;
  workspaceId: WorkspaceId;
  position: Position;
  confidence: number;
  factCount: number;
  assumptionsCount: number;
  riskPenalty: number;
  currentArtifactId?: string;
  personality: {
    focus: string;
    style: string;
    quote: string;
  };
}

export interface ArtifactItem {
  id: string;
  title: string;
  type: 'product_spec' | 'ai_spec' | 'engineering_spec' | 'ux_spec' | 'security_report' | 'qa_spec' | 'decision_record' | 'blueprint';
  producedBy: AgentRole;
  currentLocation: WorkspaceId;
  createdAt: string;
  content: any; // Raw JSON or Markdown
  version: number;
}

export interface DiscussionMessage {
  id: string;
  senderRole: AgentRole;
  senderName: string;
  text: string;
  timestamp: string;
  artifactId?: string;
  isConflictPoint?: boolean;
}

export interface DiscussionSession {
  id: string;
  topic: string;
  participants: AgentRole[];
  messages: DiscussionMessage[];
  location: WorkspaceId;
  isResolved: boolean;
  resolutionDecision?: string;
}

export interface ConflictItem {
  id: string;
  title: string;
  issue: string;
  participatingAgents: AgentRole[];
  recommendations: Record<string, string>;
  criteriaScores: Record<string, Record<string, number>>;
  arbitratedResolution?: string;
  justification?: string;
  penalties?: string[];
  confidence?: number;
  status: 'DETECTED' | 'RESOLVING' | 'RESOLVED' | 'OVERRIDDEN';
}

export interface FeedEvent {
  id: string;
  timestamp: string;
  agentRole?: AgentRole;
  agentName?: string;
  eventType: string;
  message: string;
  severity?: 'info' | 'success' | 'warning' | 'error';
}

export interface ExtractedRequirementItem {
  id: string;
  dimension: string;
  title: string;
  description: string;
  type: 'EXPLICIT' | 'INFERRED' | 'ASSUMPTION' | 'UNKNOWN';
  source: 'USER' | 'AGENT' | 'INFERENCE';
  confidence: number;
  evidence?: string;
}

export interface ClarificationQuestion {
  question_id: string;
  unknown_item_id?: string;
  question: string;
  reason: string;
  impact_if_unknown: string;
  possible_options: string[];
  status: 'PENDING' | 'ANSWERED' | 'SKIPPED';
  answer?: string;
}

export interface ProjectContextData {
  project_id: string;
  version: number;
  raw_request: string;
  project_name: string;
  problem_statement: string;
  goals: string[];
  target_users: string[];
  user_journeys: string[];
  requirements: ExtractedRequirementItem[];
  assumptions: ExtractedRequirementItem[];
  unknowns: ExtractedRequirementItem[];
  constraints: ExtractedRequirementItem[];
  clarification_questions: ClarificationQuestion[];
  decisions: any[];
  execution_state: string;
  mode: 'AUTONOMOUS' | 'GUIDED';
}

export type PipelineStage =
  | 'NOT_STARTED'
  | 'INTAKE'
  | 'UNDERSTANDING'
  | 'REQUIREMENTS'
  | 'ANALYSIS'
  | 'CORE_ANALYSIS'
  | 'ENGINEERING_ANALYSIS'
  | 'DISCUSSION'
  | 'CONFLICT_RESOLUTION'
  | 'ARBITRATION'
  | 'ARCHITECTURE'
  | 'FINAL_SYNTHESIS'
  | 'BUILD'
  | 'TEST'
  | 'VERIFICATION'
  | 'SHIP'
  | 'COMPLETED'
  | 'FAILED';

export interface CameraState {
  x: number;
  y: number;
  zoom: number;
  focusedTarget: string | null;
}

export interface CodeFileActivity {
  path: string;
  action: 'CREATED' | 'MODIFIED' | 'DELETED';
  timestamp: string;
}

export interface BuildTestState {
  status: 'IDLE' | 'BUILDING' | 'TESTING' | 'FAILED' | 'FIXING' | 'PASSED';
  currentFile?: string;
  filesChanged: CodeFileActivity[];
  totalTests: number;
  passedTests: number;
  failedTests: number;
  testOutput?: string;
  terminalLogs: string[];
}

// Backend SSE Event Types
export type BackendEventType =
  | 'PROJECT_CREATED'
  | 'UNDERSTANDING_STARTED'
  | 'UNDERSTANDING_COMPLETED'
  | 'REQUIREMENT_DISCOVERED'
  | 'AMBIGUITY_DETECTED'
  | 'CLARIFICATION_REQUIRED'
  | 'USER_CLARIFICATION_RECEIVED'
  | 'REQUIREMENTS_VALIDATED'
  | 'AGENT_STARTED'
  | 'AGENT_THINKING'
  | 'AGENT_WORKING'
  | 'AGENT_COMPLETED'
  | 'AGENT_MOVED'
  | 'AGENT_COLLABORATING'
  | 'AGENT_REVIEWING'
  | 'AGENT_DISCUSSION_STARTED'
  | 'AGENT_DISCUSSION_MESSAGE'
  | 'ARTIFACT_CREATED'
  | 'ARTIFACT_TRANSFERRED'
  | 'CONFLICT_DETECTED'
  | 'CONFLICT_RESOLVED'
  | 'DECISION_CREATED'
  | 'ARCHITECT_STARTED'
  | 'BLUEPRINT_GENERATED'
  | 'BUILD_STARTED'
  | 'FILE_CREATED'
  | 'FILE_EDITED'
  | 'FILE_DELETED'
  | 'TEST_STARTED'
  | 'TEST_FAILED'
  | 'TEST_PASSED'
  | 'FIX_STARTED'
  | 'FIX_COMPLETED'
  | 'PROJECT_SHIPPED'
  | 'PIPELINE_COMPLETED'
  | 'PIPELINE_FAILED';

export interface BackendEvent {
  type: BackendEventType;
  agent_id?: AgentRole;
  from?: WorkspaceId;
  to?: WorkspaceId;
  message?: string;
  data?: any;
  timestamp?: string;
}

