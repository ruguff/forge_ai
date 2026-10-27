import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from 'file:///C:/Users/HET/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';

const root='D:/capstone_project';
const work=root+'/docs/projectforge-presentation';
const build=work+'/.build';
const skill='C:/Users/HET/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const runtime='C:/Users/HET/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const C={ink:'#132C43',accent:'#087E8B',body:'#263746',muted:'#5D6B77',line:'#B8C4CC',pale:'#F0F5F7',white:'#FFFFFF'};
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const tableOwners=[];
const sectionMap=[];
function text(slide,value,x,y,w,h,size=26,bold=false,color=C.body,align='left',font='Arial'){
 const s=slide.shapes.add({geometry:'textbox',name:value.slice(0,70),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;s.text.insets=0;s.text.style={typeface:font,fontSize:size,bold,color,alignment:align,verticalAlignment:'top',lineSpacing:1.04};return s;
}
function shape(slide,label,x,y,w,h,{geometry='rect',fill=C.white,color=C.ink,size=24,bold=false,stroke=C.ink}={}){
 const s=slide.shapes.add({geometry,name:label||geometry,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:1.3}});
 if(label){s.text=label;s.text.insets=9;s.text.style={typeface:'Arial',fontSize:size,color,bold,alignment:'center',verticalAlignment:'middle',lineSpacing:1.02};}return s;
}
function poly(slide,pts,{fill='none',color=C.ink,width=1.3,dashed=false,closed=false}={}){
 const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);const x=Math.min(...xs),y=Math.min(...ys),w=Math.max(1,Math.max(...xs)-x),h=Math.max(1,Math.max(...ys)-y);
 const commands=[{moveTo:{x:pts[0][0]-x,y:pts[0][1]-y}},...pts.slice(1).map(p=>({lineTo:{x:p[0]-x,y:p[1]-y}}))];if(closed)commands.push({close:{}});
 return slide.shapes.add({geometry:'custom',name:'Diagram connector',position:{left:x,top:y,width:w,height:h},fill,line:{fill:color,width,style:dashed?'dashed':'solid'},customPaths:[{width:w,height:h,commands}]});
}
function arrow(slide,pts,label='',kind='sync',symbol='end'){
 poly(slide,pts,{dashed:kind==='return'||kind==='dependency'});
 if(kind!=='plain'){
   const a=symbol==='start'?pts[1]:pts[pts.length-2],b=symbol==='start'?pts[0]:pts[pts.length-1];let dx=a[0]-b[0],dy=a[1]-b[1];const len=Math.hypot(dx,dy);dx/=len;dy/=len;
   if(kind==='composition')poly(slide,[b,[b[0]+dx*7-dy*4,b[1]+dy*7+dx*4],[b[0]+dx*14,b[1]+dy*14],[b[0]+dx*7+dy*4,b[1]+dy*7-dx*4]],{fill:C.ink,closed:true});
   else poly(slide,[[b[0]+dx*10-dy*4,b[1]+dy*10+dx*4],b,[b[0]+dx*10+dy*4,b[1]+dy*10-dx*4]],{fill:kind==='sync'?C.ink:kind==='generalization'?C.white:'none',closed:kind==='sync'||kind==='generalization'});
 }
 if(label){const a=pts[0],b=pts[pts.length-1];text(slide,label,(a[0]+b[0])/2-155,(a[1]+b[1])/2-27,310,24,18,false,C.ink,'center');}
}
function slide(title,section,notes=''){
 const s=deck.slides.add();s.background.fill=C.white;
 text(s,section,56,27,1120,25,17,true,C.accent);
 text(s,title,56,66,1170,58,40,true,C.ink);
 text(s,'PROJECTFORGE AI',56,687,400,19,13,true,C.muted);
 text(s,String(deck.slides.items.length).padStart(2,'0'),1170,686,55,20,14,false,C.muted,'right');
 s.speakerNotes.text=notes;sectionMap.push({slide:deck.slides.items.length,section,title});return s;
}
function caption(s,value){text(s,value,56,649,1165,29,17,false,C.muted);}
function table(s,heads,rows,widths,{top=156,height=460,font=23}={}){
 const vals=[heads,...rows];const t=s.tables.add({rows:vals.length,columns:heads.length,left:56,top,width:1168,height,columnWidths:widths,values:vals});
 t.borders.assign({fill:C.line,width:0.6,style:'solid'});
 for(let r=0;r<vals.length;r++)for(let c=0;c<heads.length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.ink:(r%2===0?C.pale:C.white);
  cell.text.style={typeface:'Arial',fontSize:font,bold:r===0,color:r===0?C.white:C.body,verticalAlignment:'middle'};
 }
 tableOwners.push(deck.slides.items.length);return t;
}
const SRS='Source: C:/Users/HET/Downloads/srs_final_year.pdf';
const code='Implementation reference: D:/capstone_project/backend/app/';

// 1: a restrained academic cover.
{
 const s=slide('','B.TECH SEMESTER VII PROJECT REVIEW',SRS+' pp. 1–18; supplied corrected UML PDFs; Section_3_1_Database_Tables.docx. Scope is Sections 1.1 through 3.1.');
 text(s,'PROJECTFORGE AI',56,190,1170,85,66,true,C.ink);
 text(s,'Software engineering with specialist AI agents',60,295,1080,72,36,false,C.body);
 text(s,'Problem definition, requirements and technologies\nSystem design and database tables',60,450,1080,95,28,false,C.muted);
 text(s,'Sections 1.1–3.1',60,589,700,35,22,true,C.accent);
}
{
 const s=slide('Problem definition','1.1 ABOUT THE SYSTEM',SRS+' pp. 1–3. The SRS describes coordination, ambiguity, repeated work and traceability as the motivating problems.');
 const rows=[['Ambiguous ideas','A project prompt often omits requirements, constraints or acceptance criteria.'],['Fragmented development','Planning, coding and testing use separate tools and disconnected decisions.'],['Repeated work','Similar projects repeat architecture selection, file setup and verification.'],['Weak traceability','A generated file alone does not show that a requirement was implemented and tested.']];
 rows.forEach(([a,b],i)=>{text(s,a,60,164+i*110,335,70,28,true,C.ink);text(s,b,425,164+i*110,775,82,27);});
}
{
 const s=slide('Proposed system and current scope','1.1 AIM AND OBJECTIVES',SRS+' pp. 2–3. '+code+'execution/agent/declarative.py and execution/orchestrator/coding_orchestrator.py. Current local generation uses DECLARATIVE_CRUD for a supported unauthenticated single-entity application, not arbitrary unrestricted software synthesis.');
 text(s,'Aim',60,158,190,40,30,true,C.accent);
 text(s,'Convert a software idea into structured requirements, a build specification and a project checked against declared tests.',60,215,1145,100,33,true,C.ink);
 text(s,'The platform coordinates specialist analysis, preserves project history and exposes real progress in a virtual office.',60,365,1145,85,28);
 text(s,'Current offline prototype',60,493,1110,37,27,true,C.accent);
 text(s,'One entity, local SQLite, React and FastAPI CRUD. Unsupported scope and unresolved failures require review.',60,543,1145,80,28);
}
const fr=[
 ['FR-001','Project idea input','Accept a natural-language software idea.'],['FR-002','Project understanding','Extract project dimensions, objectives, users and constraints.'],['FR-003','Requirement classification','Separate explicit user requirements from inferred items.'],['FR-004','Adaptive clarification','Ask about critical unknown information.'],['FR-005','Context management','Update context when the user supplies information.'],['FR-006','Product analysis','Analyze personas, workflows and product scope.'],['FR-007','AI/ML analysis','Assess whether AI is needed and recommend an approach.'],['FR-008','Engineering analysis','Define architecture, APIs, data and technologies.'],
 ['FR-009','UX analysis','Define user journeys, screen states and interactions.'],['FR-010','Security analysis','Identify threats, access needs and mitigations.'],['FR-011','QA analysis','Define scenarios, quality criteria and verification needs.'],['FR-012','Output review','Collect and compare specialist outputs.'],['FR-013','Conflict detection','Identify incompatible agent recommendations.'],['FR-014','Conflict arbitration','Evaluate alternatives and obtain review where required.'],['FR-015','Decision records','Record decisions and their reasoning.'],['FR-016','Master blueprint','Combine requirements, outputs and resolved decisions.'],
 ['FR-017','Build specification','Produce a structured machine-readable contract.'],['FR-018','Task generation','Define file tasks, dependencies and associated tests.'],['FR-019','Source generation','Generate files according to the build specification.'],['FR-020','Repository management','Manage the generated directory and authorized source files.'],['FR-021','Command execution','Execute approved build and test commands.'],['FR-022','Application execution','Run application processes inside the verification environment.'],['FR-023','Automated testing','Execute backend, build, API and browser checks.'],
 ['FR-024','Error detection','Collect execution and testing errors.'],['FR-025','Error diagnosis','Identify probable causes and affected components.'],['FR-026','Code repair','Apply eligible fixes within authorized file scope.'],['FR-027','Retesting','Rerun relevant tests after a repair.'],['FR-028','Verification','Check declared requirements and acceptance criteria.'],['FR-029','Monitoring','Display stages, task activity, errors and results.'],['FR-030','VS Code integration','Open a verified project for further development.']];
[[0,8,'Understanding and specialist inputs'],[8,16,'Review and architectural planning'],[16,23,'Implementation and testing'],[23,30,'Errors, repair and verification']].forEach(([a,b,t])=>{
 const s=slide(t,'1.2 FUNCTIONAL REQUIREMENTS',SRS+' pp. 4–8. All FR-001 through FR-030 are retained across four slides. FR-014 currently requires user review of contradictions. FR-026 is limited to implemented backend repair. FR-022 is controlled test execution; automatic persistent preview hosting is not claimed.');
 table(s,['ID','Requirement','System task'],fr.slice(a,b),[135,310,723],{height:475,font:21});
});
const nfr=[['NFR-001','Performance','Responsive interface and streamed progress for long operations.'],['NFR-002','Reliability','Persist requirements, decisions, tasks and results.'],['NFR-003','Scalability','Allow modular expansion of agents and supported technology stacks.'],['NFR-004','Security','Restrict commands and isolate generated code execution.'],['NFR-005','Maintainability','Use modular components and structured data contracts.'],['NFR-006','Traceability','Connect requirements, decisions, tasks, files and tests.'],['NFR-007','Fault handling','Handle failed tasks with controlled retries and repair.'],['NFR-008','Controlled automation','Bound repair attempts and escalate unresolved problems.'],['NFR-009','Extensibility','Support future languages, frameworks and tools.'],['NFR-010','Usability','Show project stage, activity, errors and verification clearly.']];
for(const [a,b,t] of [[0,5,'Quality requirements'],[5,10,'Traceability and controlled automation']]){
 const s=slide(t,'1.2 NON-FUNCTIONAL REQUIREMENTS',SRS+' pp. 9–10. These are requirement statements, not evidence of measured scalability, performance or security certification.');
 table(s,['ID','Category','Requirement'],nfr.slice(a,b),[150,280,738],{height:440,font:24});caption(s,'Performance, security and extensibility targets require their own evaluation.');
}
{
 const s=slide('Tools and technologies','1.3 IMPLEMENTATION STACK',SRS+' pp. 11–13. '+code+'api/persistence.py, agents/model_client.py, execution/sandbox/Dockerfile and generated NoteKeeper backend/app/main.py. SRS describes SQLAlchemy generically; active platform persistence uses sqlite3. SQLAlchemy is used by generated NoteKeeper.');
 table(s,['Layer','Technology','Purpose'],[
 ['Frontend','React, TypeScript, Vite','Interactive office and project controls'],['Interface','Tailwind CSS, Framer Motion','Styling and motion'],['Backend','Python, FastAPI, Pydantic','API, orchestration and validated contracts'],['Local AI','LM Studio, Nemotron 3 Nano 4B','Local model inference through a loopback API'],['Persistence','SQLite; sqlite3 / SQLAlchemy','Platform state / generated application data'],['Verification','Docker, pytest, HTTPX, Playwright','Isolated backend, API, build and browser checks'],['Communication / IDE','REST, SSE, Visual Studio Code','Requests, progress events and verified project access']],[235,465,468],{height:475,font:21});
}
{
 const s=slide('Six specialist roles','1.3 AGENT ARCHITECTURE',SRS+' pp. 2, 13. '+code+'agents/pipeline.py. Offline execution is sequential: Product, AI/ML, Engineering, UX, Security, QA. Cloud mode may run UX and Security concurrently. Contradictions stop for human review.');
 table(s,['Agent','Primary output'],[['Product','Personas, scope, goals and product risks'],['AI/ML','AI suitability, approaches and limitations'],['Engineering','Architecture, APIs, storage and trade-offs'],['UX','User journeys, screen states and interface requirements'],['Security','Threats, security requirements and mitigations'],['QA','Test cases, testing strategy and acceptance needs']],[285,883],{height:420,font:25});
 caption(s,'Offline order is sequential. Each specialist has its own validation harness.');
}

// DFD and use-case views are native editable technical diagrams.
{
 const s=slide('Level 0 data flow diagram','2.1 SYSTEM CONTEXT',SRS+' p. 14. Redrawn as native slide objects and aligned to current Docker execution rather than unrestricted OS-shell execution.');
 shape(s,'User / developer',60,300,225,95,{size:27});shape(s,'0.0\nProjectForge AI',475,270,325,155,{geometry:'roundRect',fill:C.pale,size:30,bold:true});
 shape(s,'Generated workspace',970,180,250,85,{size:25});shape(s,'Docker runtime',970,440,250,85,{size:25});shape(s,'Visual Studio Code',475,550,325,70,{size:24});
 arrow(s,[[285,320],[475,320]],'Idea / answers');arrow(s,[[475,390],[285,390]],'Blueprint / results');
 arrow(s,[[800,300],[875,300],[875,222],[970,222]],'');text(s,'Source files',823,245,200,27,21);
 arrow(s,[[800,380],[875,380],[875,482],[970,482]],'');text(s,'Commands / results',835,532,350,30,21);
 arrow(s,[[635,425],[635,550]],'Verified project');caption(s,'Context view: user input becomes planning artifacts, generated files and verification results.');
}
{
 const s=slide('Level 1 data flow diagram','2.1 MAIN PROCESSES',SRS+' p. 15. D1 includes requirements/decisions nested in SQLite snapshots; D2 is the build-spec artifact; D3 is the generated repository. No separate ADR database table is invented.');
 const labels=['1.0  Intake and clarification','2.0  Specialist analysis and conflict review','3.0  Blueprint and build specification','4.0  Task graph and source generation','5.0  Isolated testing and bounded repair'];
 labels.forEach((t,i)=>shape(s,t,65,151+i*99,480,65,{geometry:'roundRect',fill:C.pale,size:24}));
 for(let i=0;i<4;i++)arrow(s,[[305,216+i*99],[305,250+i*99]],'', 'sync');
 shape(s,'D1  SQLite project state\nrequirements, history, events',825,185,380,100,{size:24});
 shape(s,'D2  build_spec.json',825,365,380,80,{size:24});shape(s,'D3  Generated repository\nsource and test reports',825,535,380,90,{size:24});
 arrow(s,[[545,182],[690,182],[690,220],[825,220]],'');text(s,'Persist context',575,140,240,30,21);
 arrow(s,[[545,380],[825,405]],'Build contract');arrow(s,[[545,480],[690,480],[690,570],[825,570]],'');
 text(s,'Write source',576,495,210,30,21);arrow(s,[[825,600],[545,600]],'Read / test / report');
}
{
 const s=slide('Level 2 data flow: specialist planning','2.1 PROCESS DECOMPOSITION',SRS+' p. 16. Source says parallel routing; this view follows the actual sequential offline implementation. ConflictResolver detects contradictions and requires review rather than silently choosing alternatives.');
 const roles=['2.1 Product','2.2 AI/ML','2.3 Engineering','2.4 UX','2.5 Security','2.6 QA'];
 roles.forEach((r,i)=>shape(s,r,65+i*194,190,170,85,{geometry:'roundRect',fill:C.pale,size:24}));
 for(let i=0;i<5;i++)arrow(s,[[235+i*194,232],[259+i*194,232]],'');
 shape(s,'2.7 Conflict detection',840,380,325,75,{geometry:'roundRect',size:24});
 shape(s,'3.1 Final Architect',455,380,295,75,{geometry:'roundRect',size:24});
 shape(s,'3.2 BuildSpec compiler',65,380,300,75,{geometry:'roundRect',size:24});
 arrow(s,[[1120,275],[1120,380]],'');arrow(s,[[840,418],[750,418]],'');arrow(s,[[455,418],[365,418]],'');
 shape(s,'Human review if contradictions remain',840,555,325,70,{size:23});arrow(s,[[1002,455],[1002,555]],'');
 text(s,'Inputs: validated requirements and prior outputs\nOutputs: specialist specifications, decisions, blueprint and build contract',65,537,680,88,26);
}
{
 const s=slide('Level 2 data flow: generation and repair','2.1 PROCESS DECOMPOSITION',SRS+' p. 16. '+code+'execution/orchestrator/coding_orchestrator.py and repair/self_healing_loop.py. Source generation is current DECLARATIVE_CRUD. Backend repairs are at most three attempts; frontend/API/browser failures require review.');
 const nodes=[['4.1 Task graph',70,190],['4.2 Coding Agent',455,190],['4.3 Repository',840,190],['5.1 Docker checks',840,405],['5.2 Verification',455,405],['5.3 Review / repair',70,405]];
 nodes.forEach(([t,x,y])=>shape(s,t,x,y,300,90,{geometry:'roundRect',fill:C.pale,size:27}));
 arrow(s,[[370,235],[455,235]],'');arrow(s,[[755,235],[840,235]],'');arrow(s,[[990,280],[990,405]],'');
 arrow(s,[[840,450],[755,450]],'');arrow(s,[[455,450],[370,450]],'');arrow(s,[[220,405],[220,330],[605,330],[605,280]],'');
 text(s,'Eligible backend failure',120,302,370,25,20);text(s,'Checks passed: persist VERIFIED\nUnresolved failure: preserve evidence and request review',455,561,730,78,27);
}
{
 const s=slide('Use case diagram','2.2 USER INTERACTION',SRS+' pp. 17–18. Main actor and API-supported actions retained. Agents are internal implementation components rather than external user actors. Source image and text use different UC numbering; this deck uses the four descriptive IDs from p. 18 and leaves the extra use cases unnumbered.');
 shape(s,'ProjectForge AI',340,150,640,490,{size:1,color:C.white,fill:'none'});text(s,'ProjectForge AI system',355,163,500,30,25,true,C.accent);
 shape(s,'User / developer',65,332,215,90,{size:26});
 const uc=[['Submit project idea',215],['Answer clarifications',282],['Monitor workflow',349],['Review blueprint',416],['Start build and view results',483],['Open verified project in VS Code',550]];
 uc.forEach(([t,y])=>{shape(s,t,420,y,460,53,{geometry:'ellipse',size:23});poly(s,[[280,377],[420,y+26]],{width:1});});
 text(s,'External support:\nLM Studio supplies inference.\nDocker runs verification.',1015,280,210,210,24);
}
{
 const s=slide('Primary use cases','2.2 USE CASE DESCRIPTIONS',SRS+' p. 18. UC-03 and UC-04 follow the written use-case descriptions rather than different numbering in the embedded source figure. VS Code launch is gated by verification.');
 table(s,['Use case','Actor and trigger','Expected result'],[
 ['UC-01 Submit project idea','User enters a software description','Project ID and saved initial context'],['UC-02 Answer clarifications','User answers a critical unknown','Updated requirements and next pending question'],['UC-03 Monitor workflow','User views the live office','Persisted events and current execution status'],['UC-04 Open in VS Code','User opens a verified inactive project','Generated workspace opens in the IDE']],[330,385,453],{height:415,font:24});
 caption(s,'Clarification updates the pending list; the current API does not rerun the full requirement engine after each answer.');
}

const diagrams=JSON.parse(await fs.readFile(root+'/docs/diagrams/corrected/diagram-model.json','utf8'));
function diagramNote(s,value){text(s,value,56,649,1168,29,16,false,C.muted);}
function classDiagram(p,index){
 const s=slide(['Project data and specification classes','Specialists and model-provider selection','Build and verification collaborators'][index],'2.3 CLASS DIAGRAM '+String.fromCharCode(65+index),
 `Source: C:/Users/HET/Downloads/ProjectForge_UML_Class_Diagram_A4.pdf, page ${index+1}. Rebuilt as editable native shapes from the corrected diagram model. `+
 ['Explain ProjectState, ProjectContext and BuildSpec inheritance. ProjectContext.build_spec is a serialized dict, not an object reference. Persistence serializes model values; nested collections use ordinary associations.',
 'Each agent owns a separate harness. GeminiModelClient.__new__ reads Settings.LLM_PROVIDER and returns LocalModelClient for lmstudio. The providers are alternatives with no inheritance. Harness calls a bound generate callback.',
 'Orchestrator constructs CodingAgent and TestRunner. Graph and scheduler are local variables, not permanent attributes. Scheduler and tool context refer to injected collaborators. Tests run through the SafeCommandExecutor.'][index]);
 const scale=.82,ox=178,oy=63;const pt=([x,y])=>[ox+x*scale,oy+y*scale];
 for(const [k,n] of Object.entries(p.nodes)){
  const [x,y]=pt([n.x,n.y]);shape(s,'',x,y,n.w*scale,n.h*scale,{stroke:'#111111'});
  const ah=Math.max(24,n.attrs.length*19+10);
  poly(s,[[x,y+29*scale],[x+n.w*scale,y+29*scale]],{color:'#111111'});poly(s,[[x,y+(29+ah)*scale],[x+n.w*scale,y+(29+ah)*scale]],{color:'#111111'});
  text(s,n.name,x+4,y+4,n.w*scale-8,24*scale,16*scale,true,'#111111','center','Times New Roman');
  text(s,n.attrs.join('\n'),x+7,y+33*scale,n.w*scale-14,ah*scale-4,16*scale,false,'#111111','left','Times New Roman');
  text(s,n.ops.join('\n'),x+7,y+(33+ah)*scale,n.w*scale-14,Math.max(16,(n.h-33-ah)*scale),16*scale,false,'#111111','left','Times New Roman');
 }
 for(const e of p.edges){const pts=e.pts.map(pt);arrow(s,pts,'',e.kind,e.kind==='composition'?'start':'end');
  if(e.label){const mid=pts[Math.floor((pts.length-1)/2)];text(s,e.label,mid[0]-24,mid[1]-23,130,20,13,false,C.ink,'center','Times New Roman');}
  if(e.mult){const last=pts.at(-1);text(s,e.mult,last[0]-28,last[1]-20,45,18,13,false,C.ink,'center','Times New Roman');}
 }
 diagramNote(s,['Serialized models and navigable references; triangles point to BaseModel.','Factory creation is distinct from provider inheritance. Each agent owns one harness.','Filled diamonds show constructed collaborators; ordinary arrows show references.'][index]);
}
diagrams.class_views.forEach(classDiagram);

function sequenceDiagram(p,index){
 const s=slide(['Project creation and clarification','Background specialist planning','Build execution and final report'][index],'2.4 SEQUENCE DIAGRAM '+String.fromCharCode(65+index),
 `Source: C:/Users/HET/Downloads/ProjectForge_UML_Sequence_Diagrams_A4.pdf, page ${index+1}. Rebuilt as editable native shapes. `+
 ['Time flows downward. Success and heuristic fallback have different alternatives. Every persisted response follows the save. Clarify updates requirements, version and the next pending question; it does not rerun evaluate_requirements().',
 'Analyze saves state, schedules a background coroutine, then returns started. Offline agents run Product, AI/ML, Engineering, UX, Security, QA. Validation failures or conflicts stop progress. SSE is an independent API stream that reads persistent events. PIPELINE_COMPLETED means planning returned normally; current code may still mark the specification BLOCKED.',
 'The API waits for shield(worker), even though execution uses a thread. Graph and scheduler are local. Source-complete and runtime-available guards control testing. Orchestrator may invoke at most three eligible backend repair attempts. Both report outcomes rejoin before persistence and the HTTP response. Unexpected API exceptions may return HTTP 500.'][index]);
 const scale=.82,ox=175,oy=38;const xp=i=>(p.parts.length===8?85+i*136:65+i*155);const pt=([x,y])=>[ox+x*scale,oy+y*scale];
 for(let i=0;i<p.parts.length;i++){
  const [name,role]=p.parts[i];const [x,y]=pt([xp(i),120]);
  shape(s,name==='Understanding'?'Understanding agent':name==='RequirementEngine'?'Requirement engine':name,x-57,y,114,44,{size:13,bold:true});poly(s,[[x,y+44],[x,oy+737*scale]],{dashed:true,width:1});
 }
 for(const [x,y,w,h,label,divider] of p.frames){const a=pt([x,y]);shape(s,'',a[0],a[1],w*scale,h*scale,{stroke:'#5D6B77',fill:'none'});if(divider)poly(s,[pt([x,divider[0]]),pt([x+w,divider[0]])],{dashed:true});}
 for(const [i,y,h] of p.activations){const [x,yy]=pt([xp(i),y]);shape(s,'',x-3,yy,6,h*scale,{stroke:'#364854'});}
 for(const m of p.messages){let pts=m.a===m.b?[[xp(m.a),m.y],[xp(m.a)+40,m.y],[xp(m.a)+40,m.y+13],[xp(m.a),m.y+13]]:[[xp(m.a),m.y],[xp(m.b),m.y]];
  arrow(s,pts.map(pt),'',m.kind);const a=pt([xp(m.a),m.y]),b=pt([xp(m.b),m.y]);const mid=(a[0]+b[0])/2+(m.a===m.b?78:0);
  const width=Math.max(300,Math.abs(a[0]-b[0])+90);text(s,m.label.replace('Update requirement/version; find next PENDING','Update answer; find next pending').replace('Next question or REQUIREMENTS_VALIDATED','Next question / requirements validated').replace('Check current spec + guided approval','Check spec and approval').replace('Scoped AgentToolContext -> repository write','Scoped tool: write source').replace('BLOCKED / FAILED / REQUIRES_HUMAN','Failure / human review report'),mid-width/2,a[1]-14,width,14,11,false,C.ink,'center','Times New Roman');
 }
 for(const [x,y,w,h,label,divider] of p.frames){let a=pt([x,y]);const bg=shape(s,'',a[0]+2,a[1]+1,Math.min(w*scale-4,label.length*6.2),17,{stroke:'none'});text(s,label,a[0]+5,a[1]+1,w*scale-10,18,12.2,true,C.ink,'left','Times New Roman');if(divider){a=pt([x,divider[0]]);text(s,divider[1],a[0]+4,a[1]+1,w*scale-8,17,11.5,false,C.ink,'left','Times New Roman');}}
 diagramNote(s,['An answered question updates the saved context before the API returns.','Offline specialist order is sequential; failures and contradictions are visible outcomes.','Build HTTP response follows worker completion and final report persistence.'][index]);
}
diagrams.sequence_views.forEach(sequenceDiagram);

{
 const s=slide('ProjectForge snapshots','3.1 DATABASE TABLES', 'Source: C:/Users/HET/Downloads/Section_3_1_Database_Tables.docx, Table 3.1 and Table 3.7. '+code+'api/persistence.py. Database: backend/data/projects.sqlite3. project_id uses TEXT PRIMARY KEY without an explicit NOT NULL declaration. payload is JSON serialized into TEXT.');
 text(s,'Platform database: SQLite',60,155,1140,40,29,true,C.accent);
 table(s,['Column','Type','Constraint','Stored information'],[['project_id','TEXT','Primary key','Unique application-generated project ID'],['payload','TEXT','NOT NULL','Latest state, context and build specification as JSON']],[220,145,235,568],{top:227,height:240,font:26});
 text(s,'The platform replaces the current snapshot when project data changes. Agent outputs remain nested JSON data.',60,520,1140,98,29);
}
{
 const s=slide('ProjectForge history and events','3.1 DATABASE TABLES','Source: C:/Users/HET/Downloads/Section_3_1_Database_Tables.docx, Tables 3.2–3.3. '+code+'api/persistence.py. history.project_id is nullable; events.project_id is NOT NULL. Neither declares a foreign key.');
 table(s,['Table','Column','Type / constraint','Purpose'],[
 ['history','id','INTEGER primary key','Saved-state change identifier'],['history','project_id','TEXT; nullable','Associated project'],['history','payload','TEXT; NOT NULL','Earlier serialized project snapshot'],['events','id','INTEGER PK; AUTOINCREMENT','Global replay sequence'],['events','project_id','TEXT; NOT NULL','Associated project'],['events','payload','TEXT; NOT NULL','Serialized execution-event details']],[175,210,335,448],{height:430,font:23});
 caption(s,'History records changed snapshots; events support ordered activity replay after reconnection.');
}
{
 const s=slide('Generated NoteKeeper notes','3.1 GENERATED APPLICATION DATABASE','Source: C:/Users/HET/Downloads/Section_3_1_Database_Tables.docx, Tables 3.4 and 3.7. NoteKeeper has its own backend/notes.db, separate from ProjectForge. Supplied blank text is rejected, but missing-field validation has a documented gap due to server defaults. No login/user table or timestamp columns are implemented.');
 table(s,['Column','Type','Constraint','Purpose'],[['id','INTEGER','Primary key; NOT NULL','Unique note identifier'],['title','TEXT','NOT NULL; default empty string','Note title'],['body','TEXT','NOT NULL; default empty string','Note content']],[200,150,410,408],{height:310,font:26});
 text(s,'This database belongs to the generated example website. It is separate from the platform’s project-state database.',60,515,1130,80,29);
 caption(s,'NOT NULL rejects NULL values; it does not reject an empty string.');
}
{
 const s=slide('Database indexes and relationships','3.1 INTEGRITY AND STORAGE','Source: C:/Users/HET/Downloads/Section_3_1_Database_Tables.docx, Tables 3.5–3.7. Logical one-to-many links are application-maintained. sqlite_sequence is internal SQLite bookkeeping and the unused ORM projects table is not an active platform table.');
 table(s,['Index / relationship','Implementation'],[
 ['snapshots primary-key index','sqlite_autoindex_snapshots_1 enforces project ID uniqueness.'],['events_project','Composite index on events(project_id, id) supports event replay.'],['snapshots to history','Logical one-to-many relationship through project_id.'],['snapshots to events','Logical one-to-many relationship through project_id.'],['Foreign keys','No declared foreign-key constraints or cascade deletion.'],['Internal table','sqlite_sequence maintains AUTOINCREMENT bookkeeping.']],[425,743],{height:450,font:24});
}

await fs.writeFile(build+'/slide-map.json',JSON.stringify(sectionMap,null,2));
await fs.mkdir(build+'/previews',{recursive:true});
const candidate=build+'/candidate.pptx';
await (await PresentationFile.exportPptx(deck)).save(candidate);
console.log('Exported',deck.slides.items.length,'slides');
for(let i=0;i<deck.slides.items.length;i++){
 const png=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});
 await fs.writeFile(build+`/previews/slide-${String(i+1).padStart(2,'0')}.png`,new Uint8Array(await png.arrayBuffer()));
 console.log('Rendered slide',i+1);
}
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const finalPath=work+'/output/ProjectForge_AI_SRS_Presentation.pptx';
const result=await finalizePresentation({workspaceDir:work,candidatePath:candidate,finalPath,
 pythonExecutable:runtime+'/python/python.exe',
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:tableOwners,fontPolicy:{basis:'design',families:['Arial','Times New Roman']},verifyArtifactToolImport:true,
 receiptPath:build+'/delivery-validation.json'});
console.log(JSON.stringify(result));






