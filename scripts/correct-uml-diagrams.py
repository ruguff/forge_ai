"""Repository-audited UML corrections. Reuses only the existing drawing engine."""
from pathlib import Path
import json
import hashlib

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/diagrams/corrected'
OUT.mkdir(parents=True,exist_ok=True)

def load_engine(filename, marker):
    source=(ROOT/'scripts'/filename).read_text(encoding='utf-8-sig')
    head,tail=source.split(marker,1)
    ns={'__file__':str(ROOT/'scripts'/filename),'__name__':'uml_correction_engine'}
    exec(head,ns)
    ns['OUT']=OUT
    return ns,marker+tail

ns,render=load_engine('create-uml-diagram.py','mx = ET.Element')
page,box,edge=ns['page'],ns['box'],ns['edge']
ns['pages'].clear()
p=page('ProjectForge AI UML Class Diagram','Figure 2.3(a)  Project data and specification classes')
box(p,'persist','ProjectPersistence',40,100,['+ path: Path'],['+ save(project_id, state, context,','    spec=None)','+ load_all(): list','+ append_event(project_id, payload)'],190)
box(p,'base','BaseModel',410,100,[],['Pydantic framework superclass'],90)
box(p,'compiler','BuildSpecCompiler',780,100,[],['+ compile_model(context, state,','    llm_client): BuildSpec','+ compile(context=None, state=None,','    override_project_type=None)'],190)
box(p,'state','ProjectState',40,350,['+ project_id: str','+ revision: int','+ status: ProjectStatus','+ raw_idea: str'],[],170)
box(p,'context','ProjectContext',410,350,['+ project_id: str','+ version: int','+ execution_state: str','+ build_spec: Optional[dict]','+ requirements: List'],['+ model_post_init(__context): None'],170)
box(p,'spec','BuildSpec',780,350,['+ project_id: str','+ version: int','+ status: BuildSpecStatus','+ files_to_create: List[TargetFileDef]','+ requirements: List'],[],185)
box(p,'req','ExtractedRequirementItem',40,595,['+ id: str','+ description: str','+ source: RequirementSource'],[],115)
box(p,'buildreq','BuildRequirementItem',410,595,['+ id: str','+ description: str','+ source: RequirementSourceType'],[],115)
box(p,'file','TargetFileDef',780,595,['+ file_path: str','+ dependencies: List[str]'],[],115)
edge(p,'state','base','generalization',[(280,350),(280,315),(460,315),(460,190)])
edge(p,'context','base','generalization',[(560,350),(560,190)])
edge(p,'spec','base','generalization',[(850,350),(850,315),(660,315),(660,190)])
edge(p,'persist','state','dependency',[(110,290),(110,350)])
edge(p,'persist','context','dependency',[(340,230),(375,230),(375,420),(410,420)])
edge(p,'persist','spec','dependency',[(190,100),(190,89),(1095,89),(1095,430),(1080,430)])
edge(p,'compiler','spec','dependency',[(980,290),(980,350)],'«create»')
edge(p,'context','req','association',[(410,480),(365,480),(365,650),(340,650)],mult='0..*')
edge(p,'spec','buildreq','association',[(780,490),(745,490),(745,650),(710,650)],mult='0..*')
edge(p,'spec','file','association',[(930,535),(930,595)],mult='0..*')
p['notes']=['build_spec is an optional serialized dict, not a stored BuildSpec instance. No object association is asserted.',
 'Persistence serializes state/context/spec. Nested lists use associations; exclusive lifecycle ownership is not enforced.']

p=page('ProjectForge AI UML Class Diagram','Figure 2.3(b)  Specialist harnesses and provider selection')
agents=[('product','ProductAgent'),('aiml','AIMLAgent'),('eng','EngineeringAgent'),('ux','UXAgent'),('sec','SecurityAgent'),('qa','QAAgent')]
for i,(key,name) in enumerate(agents):
    box(p,key,name,40,100+i*96,['- _harness: AgentExecutionHarness'],['+ analyze(project_state): HarnessResult'],86)
box(p,'settings','Settings',410,100,['+ LLM_PROVIDER: str'],[],95)
box(p,'harness','AgentExecutionHarness<T>',410,300,['+ target_schema: Type[T]','+ llm_client: Callable','+ lint_rules: List[LintRule]'],['+ execute(context_data,','    max_retries=2): HarnessResult'],190)
box(p,'local','LocalModelClient',780,140,['+ settings: Settings','+ calls: int'],['+ generate(prompt, *,','    output_tokens=None): str','+ generate_sync(prompt, *,','    output_tokens=None): str'],190)
box(p,'gemini','GeminiModelClient',780,465,['+ settings: Settings','+ client: genai.Client'],['+ __new__(cls)','+ generate(prompt: str): str','+ generate_sync(prompt: str): str'],170)
for i,(key,name) in enumerate(agents):edge(p,key,'harness','composition',[(340,143+i*96),(410,325+i*28)],mult='1')
edge(p,'harness','local','dependency',[(710,345),(745,345),(745,235),(780,235)])
edge(p,'harness','gemini','dependency',[(710,445),(745,445),(745,550),(780,550)])
edge(p,'gemini','local','dependency',[(930,465),(930,330)],'«create»')
edge(p,'gemini','settings','dependency',[(1080,565),(1100,565),(1100,89),(560,89),(560,100)])
p['notes']=['__new__(): lmstudio -> LocalModelClient(); gemini -> Gemini instance; other providers raise ModelUnavailableError.',
 'Each agent creates its own harness. Harness callbacks bind the selected provider generate(); there is no provider inheritance.']

p=page('ProjectForge AI UML Class Diagram','Figure 2.3(c)  Build ownership and execution collaborators')
box(p,'graph','TaskGraph',40,100,['+ tasks: Dict','+ adj_list: Dict','+ in_degree: Dict'],['+ build_from_spec(spec): None','+ validate_dag(): List[str]'])
box(p,'orch','CodingOrchestrator',410,100,['+ workspace_root: Path','+ coding_agent: CodingAgent','+ test_runner: TestRunner','+ repo: RepositoryManager'],['+ execute_build(spec):','    ExecutionPipelineReport'],190)
box(p,'coding','CodingAgent',780,100,['+ agent_name: str','+ model_client: object'],['+ execute_task(task, spec, tools,','    focused_context=None):','    TaskImplementationResult'])
box(p,'scheduler','TaskScheduler',40,350,['+ graph: TaskGraph'],['+ get_ready_tasks(): List','+ mark_completed(task_id,','    output_summary=None): List','+ mark_failed(task_id, error_message,','    retryable=True): None'],190)
box(p,'runner','TestRunner',410,350,['+ workspace_root: Path','+ executor: SafeCommandExecutor'],['+ run_backend_tests(test_path)','+ run_frontend_build()','+ run_acceptance(checks)','+ run_browser_checks(journeys)'],190)
box(p,'tools','AgentToolContext',780,350,['+ repo: RepositoryManager','+ allowed_files: List[str]'],['+ read_file(relative_path): str','+ write_file(relative_path, content): str'])
box(p,'task','ImplementationTask',40,600,['+ task_id: str','+ dependencies: List[str]','+ status: TaskStatus'],[],110)
box(p,'executor','SafeCommandExecutor',410,580,['+ image: str'],['+ preflight(): tuple','+ execute(command_str, ...):','    ExecutionResult'],130)
box(p,'repo','RepositoryManager',780,590,['+ workspace_root: Path'],['+ write_task_file(...): Path','+ create_checkpoint(...): bool'],120)
edge(p,'orch','graph','dependency',[(410,185),(340,185)],'«create»')
edge(p,'orch','scheduler','dependency',[(410,245),(370,245),(370,435),(340,435)],'«create»')
edge(p,'orch','coding','composition',[(710,185),(780,185)],mult='1')
edge(p,'orch','runner','composition',[(560,290),(560,350)],mult='1')
edge(p,'scheduler','graph','association',[(190,350),(190,270)],mult='1')
edge(p,'graph','task','association',[(40,220),(22,220),(22,655),(40,655)],mult='0..*')
edge(p,'coding','tools','dependency',[(930,270),(930,350)])
edge(p,'runner','executor','composition',[(560,540),(560,580)],mult='1')
edge(p,'tools','repo','association',[(930,520),(930,590)],mult='1')
p['notes']=['TaskGraph and TaskScheduler are local variables in execute_build(), not permanent CodingOrchestrator attributes.',
 'Associations denote references, not whole-part ownership. Ellipses abbreviate selected method parameters.']
class_pages=ns['pages']
# Generation into a distinct corrected directory preserves the original reviewed PDFs.
exec(render,ns)

def uml_header(title):
    return ['@startuml','skinparam backgroundColor white','skinparam monochrome true',
            'skinparam defaultFontName Times New Roman','skinparam defaultFontSize 14',
            'skinparam shadowing false','title '+title]

for i,p in enumerate(class_pages):
    lines=uml_header(p['subtitle'])+['hide empty members']
    for key,n in p['nodes'].items():
        lines.append(f'class "{n["name"]}" as {key} {{')
        lines.extend('  '+v for v in n['attrs'])
        if n['attrs'] and n['ops']:lines.append('  --')
        joined=[]
        for v in n['ops']:
            if v.startswith('    ') and joined:joined[-1]+=' '+v.strip()
            else:joined.append(v)
        lines.extend('  '+v for v in joined);lines.append('}')
    for e in p['edges']:
        arrow={'composition':'*--','association':'-->','dependency':'..>','generalization':'--|>'}[e['kind']]
        mult=f' "{e["mult"]}"' if e['mult'] else ''
        label=f' : {e["label"]}' if e['label'] else ''
        lines.append(f'{e["a"]} {arrow}{mult} {e["b"]}{label}')
    for j,n in enumerate(p['notes']):lines+=['note "'+n.replace('"',"'")+'" as note'+str(j)]
    lines+=['@enduml']
    (OUT/f'Figure_2_3_{chr(97+i)}.puml').write_text('\n'.join(lines)+'\n',encoding='utf-8')

ns,render=load_engine('create-sequence-diagrams.py','mx=ET.Element')
page,msg,frame,active=ns['page'],ns['msg'],ns['frame'],ns['active']
ns['pages'].clear()
p=page('Figure 2.4(a)  Creation understanding and clarification',
 [('User','actor'),('Frontend','boundary'),('Projects API','control'),('Understanding','control'),('Local model','control'),('RequirementEngine','control'),('Persistence','entity')],
 'Clarify updates the pending-question list; it does not re-run RequirementEngine. emit_event persists before responses.')
for a,b,y,l,k in [
 (0,1,176,'Submit idea','sync'),(1,2,198,'POST /api/projects','sync'),
 (2,6,220,'emit_event: append event + save snapshot','sync'),(2,1,242,'Persisted project_id + version','return'),
 (1,2,264,'POST /{id}/understand','sync'),(2,3,286,'execute_understanding(raw_idea)','sync'),
 (3,4,308,'generate(prompt)','sync'),(4,3,352,'Valid model extraction','return'),
 (4,3,410,'Invalid result / exception','return'),(3,3,434,'generate_heuristic_understanding()','sync'),
 (3,2,478,'Structured output + evidence label','return'),
 (2,5,504,'evaluate_requirements(output)','sync'),(5,2,528,'Questions + readiness','return'),
 (2,6,552,'emit_event: save context and events','sync'),(2,1,576,'Context + next clarification','return'),
 (0,1,620,'Answer question','sync'),(1,2,644,'POST /{id}/clarify','sync'),
 (2,2,668,'Update requirement/version; find next PENDING','sync'),
 (2,6,696,'emit_event: save updated context','sync'),(2,1,720,'Next question or REQUIREMENTS_VALIDATED','return')]:msg(p,a,b,y,l,k)
frame(p,440,316,350,140,'alt [valid extraction]',(378,'[invalid / unavailable]'))
frame(p,25,590,1050,145,'loop [while clarification remains]')
for args in [(1,176,560),(2,198,538),(3,286,198),(5,504,30),(6,220,15),(6,552,15),(6,696,15)]:active(p,*args)

p=page('Figure 2.4(b)  Background planning and failure outcomes',
 [('Frontend','boundary'),('Projects API','control'),('Background','control'),('Specialist','control'),('Harness','control'),('Local model','control'),('Compiler','control'),('Persistence','entity')],
 'API /stream reads events_after() and emits SSE; emit_event appends events, signals waiters and saves snapshots.')
for a,b,y,l,k in [
 (0,1,176,'POST /{id}/analyze','sync'),(1,7,198,'save_project(ANALYZING)','sync'),
 (1,2,222,'create_task(background)','async'),(1,0,246,'status: started','return'),
 (2,3,290,'analyze(state)','sync'),(3,4,314,'execute(context)','sync'),
 (4,5,338,'generate(prompt)','sync'),(5,4,362,'JSON / model error','return'),
 (4,4,386,'Schema + lint + bounded retries','sync'),(4,3,410,'HarnessResult / exception','return'),
 (3,2,434,'Validated output / failure','return'),
 (2,7,458,'[success] save + emit_event','sync'),
 (1,7,482,'events_after(project, sequence)','sync'),(7,1,502,'Stored event rows','return'),
 (1,0,522,'SSE: agent progress','async'),
 (2,2,538,'ConflictResolver; FinalArchitect if no conflicts','sync'),
 (2,6,578,'[no conflicts] compile_model(...)','sync'),
 (6,5,600,'Generate + validate sections','sync'),(5,6,622,'Section JSON / error','return'),
 (6,2,644,'Validated BuildSpec','return'),
 (2,7,666,'Save; BUILD_SPEC_COMPILED + PIPELINE_COMPLETED','sync'),
 (2,7,710,'Persist stop status + failure event','sync'),(1,0,730,'SSE: completion / stop events','async')]:msg(p,a,b,y,l,k)
frame(p,285,250,810,222,'loop [next specialist while preceding output valid]')
frame(p,285,554,810,168,'alt [no exception]',(680,'[failure / conflicts]'))
for args in [(1,176,72),(2,222,506),(3,290,150),(4,314,102),(5,338,30),(6,578,72),(5,600,28),(1,482,44)]:active(p,*args)

p=page('Figure 2.4(c)  Awaited build worker and persisted outcomes',
 [('Frontend','boundary'),('Projects API','control'),('Orchestrator','control'),('Code / repo','control'),('TestRunner','control'),('Safe executor','control'),('Docker','control'),('Persistence','entity')],
 'API awaits shield(worker). Graph/scheduler are local. Orchestrator invokes SelfHealingLoop only after backend test failure.')
for a,b,y,l,k in [
 (0,1,176,'POST /{id}/build','sync'),(1,1,198,'Check current spec + guided approval','sync'),
 (1,7,224,'save_project(BUILDING)','sync'),(1,2,246,'to_thread(execute_build)','async'),
 (2,3,280,'initialize_project(); write memory metadata','sync'),
 (2,3,328,'execute_task(task, spec, tools)','sync'),(3,3,354,'Scoped AgentToolContext -> repository write','sync'),
 (3,2,382,'Task result / source failure','return'),(2,3,430,'create_checkpoint(code_complete)','sync'),
 (2,5,450,'preflight()','sync'),(5,2,470,'Runtime available / reason','return'),
 (2,4,510,'Run backend, frontend, API and browser checks','sync'),(4,5,530,'execute(command_str)','sync'),
 (5,6,550,'docker run: read-only, network none','sync'),(6,5,570,'Exit code + stdout/stderr','return'),
 (5,4,590,'ExecutionResult','return'),(4,2,610,'All declared check results','return'),
 (2,1,644,'VERIFIED report','return'),(2,1,684,'BLOCKED / FAILED / REQUIRES_HUMAN','return'),
 (1,7,710,'save_project(final state + report)','sync'),(1,0,732,'HTTP response with build report','return')]:msg(p,a,b,y,l,k)
frame(p,285,288,325,102,'loop [ready tasks; bounded file generation]')
frame(p,285,392,680,225,'opt [all source tasks complete]')
frame(p,300,474,665,143,'opt [runtime available]')
frame(p,25,624,410,74,'alt [all required checks pass]',(658,'[else]'))
for args in [(1,176,560),(2,246,460),(3,280,7),(3,328,60),(5,450,20),(4,510,106),(5,530,66),(6,550,26),(7,224,15),(7,710,15)]:active(p,*args)
seq_pages=ns['pages']
# Eight-lifeline pages use a narrower but uniform pitch. Participant identity is retained.
ns['xpos']=lambda i: (85+i*136) if len(ns['p']['parts'])==8 else (65+i*155)
render=render.replace('x-66,100,132,59', "x-(58 if len(p['parts'])==8 else 66),100,(116 if len(p['parts'])==8 else 132),59")
render=render.replace("and 165<m['y']<734", "and 165<m['y']<734").replace("0<=m['a']<7 and 0<=m['b']<7", "0<=m['a']<len(p['parts']) and 0<=m['b']<len(p['parts'])")
render=render.replace("fontSize=16;labelBackgroundColor", "fontSize=14;labelBackgroundColor")
render=render.replace("text(x,m['y']-19,m['label'],16)","text(x,m['y']-17,m['label'],14)")
exec(render,ns)

for i,p in enumerate(seq_pages):
    lines=uml_header(p['title'])+['hide footbox']
    for j,(name,role) in enumerate(p['parts']):
        # participant stereotypes are descriptive; no unimplemented class is introduced.
        keyword='actor' if role=='actor' else 'participant'
        lines.append(f'{keyword} "{name}" as P{j}')
    events=[]
    for j,(x,y,w,h,label,divider) in enumerate(p['frames']):
        op,guard=label.split(' ',1)
        events.append((y,0,f'{op} {guard}'))
        if divider:events.append((divider[0],0,'else '+divider[1]))
        events.append((y+h,9,'end'))
    for m in p['messages']:
        arrow='->' if m['kind']=='sync' else '->>' if m['kind']=='async' else '-->>'
        events.append((m['y'],5,f'P{m["a"]} {arrow} P{m["b"]} : {m["label"]}'))
    # Activations in source mirror the selected activation ranges in the PDF.
    for part,y,h in p['activations']:
        events.append((y,1,f'activate P{part}'));events.append((y+h,8,f'deactivate P{part}'))
    lines.extend(v for _,_,v in sorted(events))
    lines+=['note over P0,P'+str(len(p['parts'])-1),p['note'],'end note','@enduml']
    (OUT/f'Figure_2_4_{chr(97+i)}.puml').write_text('\n'.join(lines)+'\n',encoding='utf-8')

files=[ROOT/'backend/app/api/endpoints.py',ROOT/'backend/app/api/persistence.py',ROOT/'backend/app/agents/model_client.py',
 ROOT/'backend/app/agents/pipeline.py',ROOT/'backend/app/models/schemas.py',ROOT/'backend/app/execution/orchestrator/coding_orchestrator.py']
(OUT/'source-audit.json').write_text(json.dumps({str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2),encoding='utf-8')
(OUT/'diagram-model.json').write_text(json.dumps({'class_views':class_pages,'sequence_views':seq_pages},indent=2),encoding='utf-8')
print('Corrected six diagrams and generated six PlantUML sources. Source audit hashes recorded.')
