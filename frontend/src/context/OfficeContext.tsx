import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';
import {
  AgentCharacter,
  AgentRole,
  AgentStatus,
  ArtifactItem,
  BackendEvent,
  BuildTestState,
  CameraState,
  ClarificationQuestion,
  ConflictItem,
  DiscussionSession,
  FeedEvent,
  PipelineStage,
  ProjectContextData,
  WorkspaceId,
} from '../types/office';
import { INITIAL_AGENTS, WORKSPACE_COORDINATES, COLLAB_SEATS } from '../services/initialData';
import {
  createProject,
  submitIntakeAnswer,
  startPipelineAnalysis,
  understandProject,
  submitClarification,
  fetchProjectContext,
  startAutonomousBuild,
  resolveProjectConflict,
} from '../services/api';
import { BackendEventSource } from '../services/eventStream';

interface OfficeContextType {
  projectId: string;
  projectIdea: string;
  pipelineStage: PipelineStage;
  isPaused: boolean;
  agents: Record<AgentRole, AgentCharacter>;
  artifacts: ArtifactItem[];
  activityFeed: FeedEvent[];
  activeDiscussion: DiscussionSession | null;
  activeConflict: ConflictItem | null;
  conflictsHistory: ConflictItem[];
  camera: CameraState;
  selectedAgentId: AgentRole | null;
  selectedArtifact: ArtifactItem | null;
  finalBlueprintMarkdown: string | null;
  intakeAnswers: Record<string, string>;
  currentIntakeIndex: number;
  projectContext: ProjectContextData | null;
  activeClarification: ClarificationQuestion | null;
  executionMode: 'AUTONOMOUS' | 'GUIDED';
  buildTestState: BuildTestState;

  // Modal / Drawer visibility controls
  isRequirementsOpen: boolean;
  setIsRequirementsOpen: (open: boolean) => void;
  isBlueprintOpen: boolean;
  setIsBlueprintOpen: (open: boolean) => void;
  isConflictOpen: boolean;
  setIsConflictOpen: (open: boolean) => void;
  isDiscussionOpen: boolean;
  setIsDiscussionOpen: (open: boolean) => void;
  isActivityExpanded: boolean;
  setIsActivityExpanded: (open: boolean) => void;

  // Actions
  setExecutionMode: (mode: 'AUTONOMOUS' | 'GUIDED') => void;
  setProjectIdea: (idea: string) => void;
  startIntake: (idea: string) => Promise<void>;
  startAutonomousProject: (idea: string, mode?: 'AUTONOMOUS' | 'GUIDED') => Promise<void>;
  answerClarification: (questionId: string, answer: string) => Promise<void>;
  answerIntakeQuestion: (questionId: string, answer: string) => Promise<void>;
  launchPipeline: () => Promise<void>;
  pausePipeline: () => void;
  resumePipeline: () => void;
  selectAgent: (role: AgentRole | null) => void;
  selectArtifact: (artifact: ArtifactItem | null) => void;
  focusCameraOnTarget: (targetId: string, zoom?: number) => void;
  resetCameraOverview: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  fitOffice: () => void;
  resolveConflict: (conflictId: string, approvedOption: 'A' | 'B' | 'OVERRIDE', overrideText?: string) => void;
  requestReanalysis: (agentRole: AgentRole) => void;
  resetOffice: () => void;
}

const OfficeContext = createContext<OfficeContextType | undefined>(undefined);

export const OfficeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projectId, setProjectId] = useState<string>('');
  const [projectIdea, setProjectIdea] = useState<string>('');
  const [pipelineStage, setPipelineStage] = useState<PipelineStage>('NOT_STARTED');
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [executionMode, setExecutionMode] = useState<'AUTONOMOUS' | 'GUIDED'>('AUTONOMOUS');
  const [agents, setAgents] = useState<Record<AgentRole, AgentCharacter>>(INITIAL_AGENTS);
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [projectContext, setProjectContext] = useState<ProjectContextData | null>(null);
  const [activeClarification, setActiveClarification] = useState<ClarificationQuestion | null>(null);

  // Modals & Panels visibility
  const [isRequirementsOpen, setIsRequirementsOpen] = useState(false);
  const [isBlueprintOpen, setIsBlueprintOpen] = useState(false);
  const [isConflictOpen, setIsConflictOpen] = useState(false);
  const [isDiscussionOpen, setIsDiscussionOpen] = useState(false);
  const [isActivityExpanded, setIsActivityExpanded] = useState(false);

  // Build & Test loop state
  const [buildTestState, setBuildTestState] = useState<BuildTestState>({
    status: 'IDLE',
    currentFile: undefined,
    filesChanged: [],
    totalTests: 0,
    passedTests: 0,
    failedTests: 0,
    testOutput: undefined,
    terminalLogs: [],
  });

  const [activityFeed, setActivityFeed] = useState<FeedEvent[]>([
    {
      id: 'init-1',
      timestamp: new Date().toLocaleTimeString(),
      eventType: 'SYSTEM',
      message: 'ProjectForge AI Autonomous Engineering Platform initialized.',
      severity: 'info',
    },
  ]);
  const [activeDiscussion, setActiveDiscussion] = useState<DiscussionSession | null>(null);
  const [activeConflict, setActiveConflict] = useState<ConflictItem | null>(null);
  const [conflictsHistory, setConflictsHistory] = useState<ConflictItem[]>([]);
  const [camera, setCamera] = useState<CameraState>({ x: 0, y: 0, zoom: 1, focusedTarget: null });
  const [selectedAgentId, setSelectedAgentId] = useState<AgentRole | null>(null);
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactItem | null>(null);
  const [finalBlueprintMarkdown, setFinalBlueprintMarkdown] = useState<string | null>(null);
  const [intakeAnswers, setIntakeAnswers] = useState<Record<string, string>>({});
  const [currentIntakeIndex, setCurrentIntakeIndex] = useState<number>(0);

  const eventSourceRef = useRef<BackendEventSource | null>(null);

  const addFeedEvent = useCallback(
    (msg: string, eventType = 'SYSTEM', agentRole?: AgentRole, severity: FeedEvent['severity'] = 'info') => {
      const newEvent: FeedEvent = {
        id: `evt-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
        timestamp: new Date().toLocaleTimeString(),
        eventType,
        message: msg,
        agentRole,
        agentName: agentRole ? agents[agentRole]?.name : undefined,
        severity,
      };
      setActivityFeed((prev) => [newEvent, ...prev.slice(0, 49)]);
    },
    [agents]
  );

  const updateAgent = useCallback((role: AgentRole, updates: Partial<AgentCharacter>) => {
    setAgents((prev) => ({
      ...prev,
      [role]: { ...prev[role], ...updates },
    }));
  }, []);

  const moveAgentToWorkspace = useCallback(
    (role: AgentRole, workspaceId: WorkspaceId) => {
      if (workspaceId === 'collaboration_table' && COLLAB_SEATS[role]) {
        const seat = COLLAB_SEATS[role];
        updateAgent(role, {
          workspaceId,
          position: { x: seat.x, y: seat.y },
        });
        return;
      }

      const ws = WORKSPACE_COORDINATES[workspaceId];
      if (!ws) return;
      const targetX = ws.x + ws.width / 2;
      const targetY = ws.y + ws.height / 2;

      updateAgent(role, {
        workspaceId,
        position: { x: targetX, y: targetY },
      });
    },
    [updateAgent]
  );

  const focusCameraOnTarget = useCallback(
    (targetId: string, zoom = 1.2) => {
      const ws = WORKSPACE_COORDINATES[targetId as WorkspaceId];
      if (ws) {
        setCamera({
          x: -(ws.x + ws.width / 2 - 800),
          y: -(ws.y + ws.height / 2 - 370),
          zoom,
          focusedTarget: targetId,
        });
        return;
      }
      const ag = agents[targetId as AgentRole];
      if (ag) {
        setCamera({
          x: -(ag.position.x - 800),
          y: -(ag.position.y - 370),
          zoom,
          focusedTarget: targetId,
        });
      }
    },
    [agents]
  );

  const resetCameraOverview = useCallback(() => {
    setCamera({ x: 0, y: 0, zoom: 1, focusedTarget: null });
  }, []);

  const zoomIn = useCallback(() => {
    setCamera((prev) => ({ ...prev, zoom: Math.min(1.8, prev.zoom + 0.15) }));
  }, []);

  const zoomOut = useCallback(() => {
    setCamera((prev) => ({ ...prev, zoom: Math.max(0.65, prev.zoom - 0.15) }));
  }, []);

  const fitOffice = useCallback(() => {
    setCamera({ x: 0, y: 0, zoom: 0.88, focusedTarget: null });
  }, []);

  const resolveConflict = async (
    conflictId: string,
    approvedOption: 'A' | 'B' | 'OVERRIDE',
    overrideText?: string
  ) => {
    if (!activeConflict) return;
    let resolution = '';
    if (approvedOption === 'A') {
      resolution = `Adopted Option A: ${activeConflict.recommendations['engineering_lead'] || 'REST API over HTTP/2'}`;
    } else if (approvedOption === 'B') {
      resolution = `Adopted Option B: ${activeConflict.recommendations['aiml_architect'] || 'Bi-directional WebSocket streaming'}`;
    } else {
      resolution = overrideText || 'Manual user architectural override applied.';
    }

    const resolved: ConflictItem = {
      ...activeConflict,
      status: approvedOption === 'OVERRIDE' ? 'OVERRIDDEN' : 'RESOLVED',
      arbitratedResolution: resolution,
    };

    try {
      const result = await resolveProjectConflict(projectId, conflictId, resolution);
      setProjectContext(result.context);
    } catch (error) {
      addFeedEvent(String(error), 'PIPELINE_FAILED', undefined, 'error');
      return;
    }
    setConflictsHistory((prev) => [...prev, resolved]);
    setActiveConflict(null);
    addFeedEvent(`Arbitration complete for ${conflictId}: ${resolution}`, 'CONFLICT_RESOLVED', 'conflict_resolver', 'success');

    // Move agents back to their desks
    moveAgentToWorkspace('engineering_lead', 'engineering_workspace');
    moveAgentToWorkspace('aiml_architect', 'aiml_workspace');
    updateAgent('engineering_lead', { status: 'WAITING' });
    updateAgent('aiml_architect', { status: 'WAITING' });
    updateAgent('conflict_resolver', { status: 'WAITING', activityMessage: 'Decision saved; reanalysis required.' });
    await launchPipeline();
  };

  const startAutonomousProject = async (idea: string, mode: 'AUTONOMOUS' | 'GUIDED' = 'AUTONOMOUS') => {
    setProjectIdea(idea);
    setExecutionMode(mode);
    setPipelineStage('UNDERSTANDING');
    addFeedEvent(`Initializing Autonomous Project: "${idea}" [${mode}]`, 'PROJECT_CREATED', undefined, 'info');

    let projId = projectId;
    try {
      const created = await createProject(idea, mode);
      projId = created.project_id;
      setProjectId(projId);
    } catch (err) {
      setPipelineStage('FAILED');
      addFeedEvent(String(err), 'PIPELINE_FAILED', undefined, 'error');
      return;
    }

    // Step 1: Project Understanding Agent (17 Dimensions)
    updateAgent('product_manager', {
      status: 'WORKING',
      currentTask: 'Extracting 17 architectural dimensions from prompt...',
      activityMessage: 'Classifying domain, requirements & non-goals...',
    });
    focusCameraOnTarget('understanding_workspace', 1.25);

    try {
      const understandRes = await understandProject(projId);
      if (understandRes?.context) {
        setProjectContext(understandRes.context);
      }
      if (understandRes?.next_clarification) {
        setActiveClarification(understandRes.next_clarification);
        setPipelineStage('REQUIREMENTS');
        addFeedEvent(
          `Material decision required: ${understandRes.next_clarification.question}`,
          'CLARIFICATION_REQUIRED',
          undefined,
          'warning'
        );
        return;
      }
    } catch (err) {
      setPipelineStage('FAILED');
      addFeedEvent(String(err), 'PIPELINE_FAILED', undefined, 'error');
      return;
    }

    // Continue to specialist pipeline
    await launchPipeline(projId);
  };

  const answerClarification = async (questionId: string, answer: string) => {
    addFeedEvent(`Decision recorded: "${answer}"`, 'CLARIFICATION_ANSWERED', undefined, 'success');
    let res: any = null;
    try {
      res = await submitClarification(projectId, questionId, answer);
      if (res?.context) {
        setProjectContext(res.context);
      }
    } catch (err) {
      setPipelineStage('FAILED');
      addFeedEvent(String(err), 'PIPELINE_FAILED', undefined, 'error');
      return;
    }
    if (res?.next_clarification) {
      setActiveClarification(res.next_clarification);
    } else {
      setActiveClarification(null);
      addFeedEvent('All clarification decisions resolved. Launching architecture pipeline.', 'STAGE_CHANGE', undefined, 'success');
      await launchPipeline();
    }
  };

  const startIntake = async (idea: string) => {
    setProjectIdea(idea);
    setPipelineStage('INTAKE');
    setCurrentIntakeIndex(0);
    try {
      const created = await createProject(idea);
      setProjectId(created.project_id);
    } catch (err) {
      console.warn('Project creation fallback:', err);
    }
    addFeedEvent(`New project initialized: "${idea}"`, 'PROJECT_CREATED', undefined, 'success');
  };

  const answerIntakeQuestion = async (questionId: string, answer: string) => {
    setIntakeAnswers((prev) => ({ ...prev, [questionId]: answer }));
    try {
      await submitIntakeAnswer(projectId, questionId, answer);
    } catch (err) {
      console.warn('Intake answer offline:', err);
    }
    addFeedEvent(`Answered ${questionId}: ${answer.substring(0, 40)}...`, 'INTAKE_ANSWER', 'product_manager', 'info');
    setCurrentIntakeIndex((prev) => prev + 1);
  };

  const launchPipeline = async (selectedProject = projectId) => {
    try {
      eventSourceRef.current?.disconnect();
      const sse = new BackendEventSource();
      eventSourceRef.current = sse;
      sse.subscribe((event: BackendEvent) => {
        const kind: string = event.type;
        if (event.message) addFeedEvent(event.message, event.type, event.agent_id);
        if (kind === 'AGENT_STARTED' && event.agent_id) {
          setPipelineStage('ANALYSIS');
          updateAgent(event.agent_id, { status: 'WORKING', currentTask: event.message || 'Working' });
          moveAgentToWorkspace(event.agent_id, agents[event.agent_id].workspaceId);
        }
        if (kind === 'AGENT_COMPLETED' && event.agent_id) {
          updateAgent(event.agent_id, { status: 'COMPLETED', activityMessage: event.message || 'Validated' });
        }
        if (kind === 'BLUEPRINT_GENERATED' && event.data?.blueprint) {
          setFinalBlueprintMarkdown(event.data.blueprint);
          setPipelineStage('ARCHITECTURE');
        }
        if (kind === 'CONFLICT_DETECTED' && event.data) {
          setActiveConflict({ id: event.data.conflict_id, title: 'Specialist contradiction', issue: event.data.issue,
            participatingAgents: ['engineering_lead', 'aiml_architect'], recommendations: event.data.conflicting_recommendations,
            criteriaScores: event.data.evaluation_criteria_scores || {}, status: 'DETECTED' });
          setPipelineStage('CONFLICT_RESOLUTION');
        }
        if (kind === 'PIPELINE_COMPLETED') {
          void fetchProjectContext(selectedProject).then(async context => {
            setProjectContext(context);
            if (context.execution_state !== 'BUILD_SPEC_READY' || context.mode !== 'AUTONOMOUS') return;
            setPipelineStage('BUILD');
            const report = await startAutonomousBuild(selectedProject);
            if (report.status === 'VERIFIED') {
              setPipelineStage('COMPLETED');
              setBuildTestState(previous => ({ ...previous, status: 'PASSED' }));
            } else {
              setPipelineStage('FAILED');
              const failedChecks = Object.entries(report.verification_checks || {})
                .filter(([, status]) => status !== 'PASSED')
                .map(([name, status]) => `${name.replace(/_/g, ' ')}: ${status}`);
              addFeedEvent(`Build status: ${report.status}. ${failedChecks.join('; ') || 'See the saved build report for details.'}`, 'BUILD_FAILED', 'coding_agent', 'error');
            }
          }).catch(error => {
            setPipelineStage('FAILED');
            addFeedEvent(String(error), 'BUILD_FAILED', 'coding_agent', 'error');
          });
        }
        if (kind === 'TESTS_COMPLETED') {
          setBuildTestState(previous => ({ ...previous, totalTests: (event.data?.passed || 0) + (event.data?.failed || 0),
            passedTests: event.data?.passed || 0, failedTests: event.data?.failed || 0,
            status: event.data?.is_success ? 'TESTING' : 'FAILED' }));
        }
        if (['PIPELINE_FAILED', 'PIPELINE_BLOCKED', 'AGENT_FAILED', 'BUILD_BLOCKED', 'REQUIRES_HUMAN', 'PIPELINE_CANCELLED'].includes(kind)) {
          setPipelineStage('FAILED');
          setAgents(previous => Object.fromEntries(Object.entries(previous).map(([role, agent]) => [role,
            ['WORKING', 'THINKING', 'MOVING', 'DISCUSSING', 'REVIEWING'].includes(agent.status)
              ? { ...agent, status: 'BLOCKED', activityMessage: event.message || 'Execution stopped' }
              : agent])) as Record<AgentRole, AgentCharacter>);
          if (event.agent_id) updateAgent(event.agent_id, { status: 'BLOCKED', activityMessage: event.message || 'Stopped' });
        }
      });
      sse.connect(selectedProject);
      const current = await fetchProjectContext(selectedProject);
      if (!current.requirements?.length) {
        const understanding = await understandProject(selectedProject);
        setProjectContext(understanding.context);
        if (understanding.clarification) {
          setActiveClarification(understanding.clarification);
          setPipelineStage('REQUIREMENTS');
          return;
        }
      }
      await startPipelineAnalysis(selectedProject);
    } catch (error) {
      setPipelineStage('FAILED');
      addFeedEvent(String(error), 'PIPELINE_FAILED', undefined, 'error');
      updateAgent('product_manager', { status: 'BLOCKED', activityMessage: String(error) });
    }
  };

  const pausePipeline = () => addFeedEvent('Live execution cannot be paused by a display toggle. Use the backend cancellation endpoint to stop analysis.', 'SYSTEM', undefined, 'warning');
  const resumePipeline = () => addFeedEvent('Start a new analysis to resume a cancelled run.', 'SYSTEM', undefined, 'info');
  const selectAgent = (role: AgentRole | null) => setSelectedAgentId(role);
  const selectArtifact = (artifact: ArtifactItem | null) => setSelectedArtifact(artifact);

  const requestReanalysis = (agentRole: AgentRole) => {
    addFeedEvent(`User requested re-analysis for ${agents[agentRole]?.name}`, 'REANALYSIS_REQUESTED', agentRole, 'warning');
    void launchPipeline();
  };

  const resetOffice = () => {
    eventSourceRef.current?.disconnect();
    setPipelineStage('NOT_STARTED');
    setAgents(INITIAL_AGENTS);
    setArtifacts([]);
    setActiveDiscussion(null);
    setActiveConflict(null);
    setConflictsHistory([]);
    setFinalBlueprintMarkdown(null);
    setSelectedAgentId(null);
    setSelectedArtifact(null);
    setBuildTestState({
      status: 'IDLE',
      currentFile: undefined,
      filesChanged: [],
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      testOutput: undefined,
      terminalLogs: [],
    });
    resetCameraOverview();
  };

  return (
    <OfficeContext.Provider
      value={{
        projectId,
        projectIdea,
        pipelineStage,
        isPaused,
        executionMode,
        setExecutionMode,
        agents,
        artifacts,
        activityFeed,
        activeDiscussion,
        activeConflict,
        conflictsHistory,
        camera,
        selectedAgentId,
        selectedArtifact,
        finalBlueprintMarkdown,
        intakeAnswers,
        currentIntakeIndex,
        projectContext,
        activeClarification,
        buildTestState,

        // Modal visibility
        isRequirementsOpen,
        setIsRequirementsOpen,
        isBlueprintOpen,
        setIsBlueprintOpen,
        isConflictOpen,
        setIsConflictOpen,
        isDiscussionOpen,
        setIsDiscussionOpen,
        isActivityExpanded,
        setIsActivityExpanded,

        // Actions
        setProjectIdea,
        startIntake,
        startAutonomousProject,
        answerClarification,
        answerIntakeQuestion,
        launchPipeline,
        pausePipeline,
        resumePipeline,
        selectAgent,
        selectArtifact,
        focusCameraOnTarget,
        resetCameraOverview,
        zoomIn,
        zoomOut,
        fitOffice,
        resolveConflict,
        requestReanalysis,
        resetOffice,
      }}
    >
      {children}
    </OfficeContext.Provider>
  );
};

export const useOffice = () => {
  const context = useContext(OfficeContext);
  if (!context) {
    throw new Error('useOffice must be used within an OfficeProvider');
  }
  return context;
};

