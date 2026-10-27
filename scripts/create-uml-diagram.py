"""Build editable mxGraph UML pages and matching A4 print previews."""
from pathlib import Path
import math
import shutil
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4, landscape

OUT = Path(__file__).resolve().parents[1] / 'docs/diagrams'
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1123, 794
pages = []

def page(title, subtitle):
    p = dict(title=title, subtitle=subtitle, nodes={}, edges=[], notes=[])
    pages.append(p)
    return p

def box(p, key, name, x, y, attrs, ops, height=170, width=300):
    p['nodes'][key] = dict(name=name, x=x, y=y, w=width, h=height, attrs=attrs, ops=ops)

def edge(p, a, b, kind, points, label='', mult=''):
    p['edges'].append(dict(a=a,b=b,kind=kind,pts=points,label=label,mult=mult))

p = page('ProjectForge AI UML Class Diagram', 'Figure 2.3(a)  Project data and specification classes')
box(p,'persist','ProjectPersistence',40,100,['+ path: Path'],['+ save(id, state, context, spec)','+ load_all(): list','+ append_event(id, payload)','+ events_after(id, sequence)'])
box(p,'context','ProjectContext',410,100,['+ project_id: str','+ version: int','+ requirements: List','+ execution_state: str'],['+ model_post_init(context)'])
box(p,'requirement','ExtractedRequirementItem',780,100,['+ id: str','+ dimension: str','+ description: str','+ source: RequirementSource'],[],170)
box(p,'state','ProjectState',40,340,['+ project_id: str','+ revision: int','+ status: ProjectStatus','+ product_spec: Optional','+ final_blueprint_markdown: str'],[],170)
box(p,'spec','BuildSpec',410,340,['+ project_id: str','+ version: int','+ status: BuildSpecStatus','+ source_generation_strategy: str','+ acceptance_checks: List','+ browser_checks: List'],[],190)
box(p,'file','TargetFileDef',780,340,['+ file_path: str','+ description: str','+ dependencies: List[str]','+ traceable_requirements: List'],[],170)
box(p,'base','BaseModel',40,595,['Pydantic framework class'],[],90)
box(p,'compiler','BuildSpecCompiler',410,595,[],['+ compile_model(context, state, llm)','+ compile(context, state): BuildSpec'],115)
box(p,'buildreq','BuildRequirementItem',780,595,['+ id: str','+ description: str','+ source: RequirementSourceType'],[],115)
edge(p,'persist','context','dependency',[(340,185),(410,185)],'serializes')
edge(p,'persist','state','dependency',[(190,270),(190,340)],'serializes')
edge(p,'context','requirement','composition',[(710,185),(780,185)],mult='0..*')
edge(p,'context','spec','association',[(560,270),(560,340)],mult='0..1')
edge(p,'state','base','generalization',[(190,510),(190,595)])
edge(p,'spec','file','composition',[(710,425),(780,425)],mult='0..*')
edge(p,'compiler','spec','dependency',[(560,595),(560,530)],'creates')
edge(p,'spec','buildreq','composition',[(710,495),(745,495),(745,650),(780,650)],mult='0..*')
p['notes'] = ['Selected members shown. ProjectState, ProjectContext and BuildSpec are Pydantic models.',
              'SQLite tables: snapshots, history, events. Nested JSON models are not separate SQL tables.']

p = page('ProjectForge AI UML Class Diagram', 'Figure 2.3(b)  Specialist agents and model access')
agents = [('product','ProductAgent'),('aiml','AIMLAgent'),('eng','EngineeringAgent'),
          ('ux','UXAgent'),('security','SecurityAgent'),('qa','QAAgent')]
for i,(key,name) in enumerate(agents):
    y = 100+i*96
    box(p,key,name,40,y,['- _harness: AgentExecutionHarness'],['+ analyze(state): HarnessResult'],86)
box(p,'harness','AgentExecutionHarness<T>',410,300,['+ target_schema: Type[T]','+ agent_name: str','+ llm_client: Callable','+ lint_rules: List'],['+ execute(context, max_retries)'],190)
box(p,'local','LocalModelClient',780,140,['+ settings: Settings','+ calls: int','+ input_tokens: int'],['+ generate(prompt): str','+ generate_sync(prompt): str','+ usage(): dict'],190)
box(p,'cloud','GeminiModelClient',780,460,['+ settings: Settings','+ client: genai.Client'],['+ __new__(): provider selection','+ generate(prompt): str','+ generate_sync(prompt): str'],170)
for i,(key,name) in enumerate(agents):
    edge(p,key,'harness','composition',[(340,143+i*96),(410,325+i*28)])
edge(p,'harness','local','dependency',[(710,345),(745,345),(745,235),(780,235)],'callback')
edge(p,'harness','cloud','dependency',[(710,445),(745,445),(745,545),(780,545)],'callback')
edge(p,'cloud','local','dependency',[(930,460),(930,330)],'selects local provider')
p['notes'] = ['Each agent owns its own harness instance; six agents do not share one harness object.',
              'LocalModelClient and GeminiModelClient are alternative providers, not subclasses of each other.']

p = page('ProjectForge AI UML Class Diagram', 'Figure 2.3(c)  Source generation and isolated verification')
box(p,'graph','TaskGraph',40,100,['+ tasks: Dict','+ adj_list: Dict','+ in_degree: Dict'],['+ build_from_spec(spec)','+ validate_dag(): List[str]'])
box(p,'orchestrator','CodingOrchestrator',410,100,['+ workspace_root: Path','+ repo: RepositoryManager','+ coding_agent: CodingAgent','+ test_runner: TestRunner'],['+ execute_build(spec): Report'])
box(p,'coding','CodingAgent',780,100,['+ agent_name: str','+ model_client: object'],['+ execute_task(task, context, tools)'])
box(p,'scheduler','TaskScheduler',40,340,['+ graph: TaskGraph'],['+ get_ready_tasks(): List','+ mark_completed(task_id)','+ mark_failed(task_id, error)','+ is_finished(): bool'])
box(p,'test','TestRunner',410,340,['+ workspace_root: Path','+ executor: SafeCommandExecutor'],['+ run_backend_tests(): Result','+ run_frontend_build(): Result','+ run_acceptance(checks): Result','+ run_browser_checks(journeys)'],190)
box(p,'tools','AgentToolContext',780,340,['+ repo: RepositoryManager','+ task_id: str','+ allowed_files: List[str]'],['+ read_file(path): str','+ write_file(path, content): str'])
box(p,'task','ImplementationTask',40,595,['+ task_id: str','+ dependencies: List[str]','+ status: TaskStatus'],[],115)
box(p,'executor','SafeCommandExecutor',410,580,['+ workspace_root: Path','+ image: str'],['+ preflight(): tuple','+ execute(command): ExecutionResult'],125)
box(p,'repo','RepositoryManager',780,580,['+ workspace_root: Path'],['+ initialize_project()','+ write_task_file(...)','+ create_checkpoint(name): bool'],125)
edge(p,'orchestrator','graph','dependency',[(410,185),(340,185)],'creates')
edge(p,'orchestrator','coding','composition',[(710,185),(780,185)])
edge(p,'orchestrator','test','composition',[(560,270),(560,340)])
edge(p,'scheduler','graph','aggregation',[(190,340),(190,270)])
edge(p,'graph','task','composition',[(40,220),(20,220),(20,650),(40,650)],mult='0..*')
edge(p,'coding','tools','dependency',[(930,270),(930,340)],'uses')
edge(p,'test','executor','composition',[(560,530),(560,580)])
edge(p,'tools','repo','aggregation',[(930,510),(930,580)])
p['notes'] = ['Graph and scheduler are created inside execute_build(); their links are dependencies, not stored fields.',
              'Selected core classes only. Repair, conflict-resolution and blueprint helper details are omitted.']

mx = ET.Element('mxfile', host='app.diagrams.net', version='24.7.17', type='device')
for number,p in enumerate(pages,1):
    diagram = ET.SubElement(mx,'diagram',id=f'projectforge-{number}',name=f'2.3{chr(96+number)} {p["subtitle"].split("  ")[1]}')
    model = ET.SubElement(diagram,'mxGraphModel',dx=str(W),dy=str(H),grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth=str(W),pageHeight=str(H),math='0',shadow='0')
    root = ET.SubElement(model,'root'); ET.SubElement(root,'mxCell',id='0'); ET.SubElement(root,'mxCell',id='1',parent='0')
    def cell(key,value,x,y,w,h,style,parent='1'):
        c=ET.SubElement(root,'mxCell',id=key,value=value,style=style,vertex='1',parent=parent)
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    textstyle='text;html=0;whiteSpace=wrap;overflow=hidden;fontFamily=Times New Roman;fontSize=16;align=left;verticalAlign=middle;spacing=5;'
    cell('title',p['title'],30,20,1060,30,textstyle+'fontSize=21;fontStyle=1;align=center;')
    cell('subtitle',p['subtitle'],30,52,1060,28,textstyle+'fontSize=18;align=center;')
    for k,n in p['nodes'].items():
        cell(k,'',n['x'],n['y'],n['w'],n['h'],'rounded=0;html=0;fillColor=#FFFFFF;strokeColor=#000000;strokeWidth=1;')
        ah=max(24,len(n['attrs'])*19+10)
        cell(k+'-name',n['name'],0,0,n['w'],29,textstyle+'fontStyle=1;align=center;strokeColor=#000000;fillColor=#FFFFFF;',k)
        cell(k+'-attr','\n'.join(n['attrs']) or ' ',0,29,n['w'],ah,textstyle+'strokeColor=#000000;fillColor=#FFFFFF;',k)
        cell(k+'-ops','\n'.join(n['ops']) or ' ',0,29+ah,n['w'],n['h']-29-ah,textstyle+'fillColor=#FFFFFF;',k)
    for i,e in enumerate(p['edges']):
        a,b=p['nodes'][e['a']],p['nodes'][e['b']]; pts=e['pts']; start,end=pts[0],pts[-1]
        arrows={'dependency':'dashed=1;endArrow=open;endFill=0;','association':'endArrow=open;endFill=0;',
                'composition':'startArrow=diamond;startFill=1;endArrow=none;',
                'aggregation':'startArrow=diamond;startFill=0;endArrow=none;',
                'generalization':'endArrow=block;endFill=0;'}[e['kind']]
        style=f'html=0;rounded=0;strokeColor=#000000;strokeWidth=1.2;fontFamily=Times New Roman;fontSize=14;labelBackgroundColor=#FFFFFF;{arrows}'
        style+=f'exitX={(start[0]-a["x"])/a["w"]};exitY={(start[1]-a["y"])/a["h"]};entryX={(end[0]-b["x"])/b["w"]};entryY={(end[1]-b["y"])/b["h"]};exitPerimeter=0;entryPerimeter=0;'
        c=ET.SubElement(root,'mxCell',id=f'edge-{i}',value=e['label'],style=style,edge='1',parent='1',source=e['a'],target=e['b'])
        g=ET.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
        if len(pts)>2:
            arr=ET.SubElement(g,'Array',attrib={'as':'points'})
            for x,y in pts[1:-1]: ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
        if e['mult']:
            lab=ET.SubElement(root,'mxCell',id=f'mult-{i}',value=e['mult'],style='edgeLabel;html=0;resizable=0;fontFamily=Times New Roman;fontSize=14;labelBackgroundColor=#FFFFFF;',vertex='1',connectable='0',parent=f'edge-{i}')
            geo=ET.SubElement(lab,'mxGeometry',x='0.75',y='-12',relative='1',attrib={'as':'geometry'})
            ET.SubElement(geo,'mxPoint',x='0',y='0',attrib={'as':'offset'})
    for i,note in enumerate(p['notes']):cell(f'note-{i}',note,35,716+i*19,1050,20,textstyle+'fontSize=14;')
    cell('legend','UML: filled diamond = composition; hollow diamond = aggregation; dashed arrow = dependency; hollow triangle = inheritance.',35,757,1050,20,textstyle+'fontSize=14;')
    cell('page',f'A4 landscape | Selected implementation classes | {number} / {len(pages)}',35,778,1050,15,textstyle+'fontSize=12;align=center;')

ET.indent(mx)
drawio=OUT/'ProjectForge_UML_Class_Diagram_A4.drawio'
ET.ElementTree(mx).write(drawio,encoding='utf-8',xml_declaration=True)
shutil.copyfile(drawio,OUT/'ProjectForge_UML_Class_Diagram_A4.xml')

# Render the same class geometry and relationship symbols for print and QA.
pdfmetrics.registerFont(TTFont('TimesCustom','C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('TimesCustomBold','C:/Windows/Fonts/timesbd.ttf'))
pdf=canvas.Canvas(str(OUT/'ProjectForge_UML_Class_Diagram_A4.pdf'),pagesize=landscape(A4))
for num,p in enumerate(pages,1):
    im=Image.new('RGB',(W*2,H*2),'white'); d=ImageDraw.Draw(im)
    pw,ph=landscape(A4); sx=pw/W; sy=ph/H
    def text(x,y,value,size=16,bold=False,center=False):
        font=ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf' if bold else 'C:/Windows/Fonts/times.ttf',size*2)
        for i,line in enumerate(value.split('\n')):
            xx=x*2-(d.textlength(line,font=font)/2 if center else 0)
            d.text((xx,(y+i*19)*2),line,font=font,fill='black')
            pdf.setFont('TimesCustomBold' if bold else 'TimesCustom',size*sx)
            if center:pdf.drawCentredString(x*sx,ph-(y+i*19+size*.85)*sy,line)
            else:pdf.drawString(x*sx,ph-(y+i*19+size*.85)*sy,line)
    def line(points,dashed=False):
        for a,b in zip(points,points[1:]):
            length=math.dist(a,b)
            if dashed:
                for t in range(0,max(1,int(length)),10):
                    end=min(t+5,length)
                    d.line([(2*(a[0]+(b[0]-a[0])*v/length),2*(a[1]+(b[1]-a[1])*v/length)) for v in (t,end)],fill='black',width=2)
            else:d.line([(x*2,y*2) for x,y in (a,b)],fill='black',width=2)
        pdf.setDash(4,3) if dashed else pdf.setDash()
        path=pdf.beginPath();path.moveTo(points[0][0]*sx,ph-points[0][1]*sy)
        for x,y in points[1:]:path.lineTo(x*sx,ph-y*sy)
        pdf.drawPath(path);pdf.setDash()
    def poly(points,fill):
        d.polygon([(x*2,y*2) for x,y in points],fill=fill,outline='black',width=2)
        path=pdf.beginPath();path.moveTo(points[0][0]*sx,ph-points[0][1]*sy)
        for x,y in points[1:]:path.lineTo(x*sx,ph-y*sy)
        path.close();pdf.setFillColorRGB(0,0,0) if fill=='black' else pdf.setFillColorRGB(1,1,1)
        pdf.drawPath(path,stroke=1,fill=1);pdf.setFillColorRGB(0,0,0)
    text(W/2,21,p['title'],21,True,True);text(W/2,56,p['subtitle'],18,False,True)
    for n in p['nodes'].values():
        x,y,w,h=n['x'],n['y'],n['w'],n['h'];ah=max(24,len(n['attrs'])*19+10)
        line([(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)])
        line([(x,y+29),(x+w,y+29)]);line([(x,y+29+ah),(x+w,y+29+ah)])
        text(x+w/2,y+5,n['name'],16,True,True)
        text(x+8,y+34,'\n'.join(n['attrs']));text(x+8,y+34+ah,'\n'.join(n['ops']))
    for e in p['edges']:
        pts=e['pts'];line(pts,e['kind']=='dependency')
        if e['kind'] in ('composition','aggregation'):
            (x,y),(xx,yy)=pts[:2];length=math.dist((x,y),(xx,yy));ux,uy=(xx-x)/length,(yy-y)/length
            poly([(x,y),(x+ux*8-uy*5,y+uy*8+ux*5),(x+ux*16,y+uy*16),(x+ux*8+uy*5,y+uy*8-ux*5)],'black' if e['kind']=='composition' else 'white')
        else:
            (xx,yy),(x,y)=pts[-2:];length=math.dist((x,y),(xx,yy));ux,uy=(xx-x)/length,(yy-y)/length
            arrow=[(x+ux*12-uy*6,y+uy*12+ux*6),(x,y),(x+ux*12+uy*6,y+uy*12-ux*6)]
            if e['kind']=='generalization':poly(arrow,'white')
            else:line(arrow)
        if e['label']:
            a,b=pts[len(pts)//2-1:len(pts)//2+1];text((a[0]+b[0])/2,(a[1]+b[1])/2-19,e['label'],14,False,True)
        if e['mult']:text(pts[-1][0]-37,pts[-1][1]-23,e['mult'],14)
    for i,note in enumerate(p['notes']):text(35,717+i*19,note,14)
    text(35,758,'UML: filled diamond = composition; hollow diamond = aggregation; dashed arrow = dependency; hollow triangle = inheritance.',14)
    text(W/2,781,f'A4 landscape | Selected implementation classes | {num} / {len(pages)}',12,False,True)
    im.save(OUT/f'uml-preview-{num}.png');pdf.showPage()
pdf.save()

# Confirm mxGraph references and page boundaries before delivery.
for diagram in mx.findall('diagram'):
    cells=diagram.find('mxGraphModel/root').findall('mxCell'); ids={c.get('id') for c in cells}
    for c in cells:
        for attr in ('parent','source','target'):
            assert c.get(attr) is None or c.get(attr) in ids
for p in pages:
    for n in p['nodes'].values():
        assert n['x']>=0 and n['y']>=0 and n['x']+n['w']<=W and n['y']+n['h']<=H
        assert 29+max(24,len(n['attrs'])*19+10)+len(n['ops'])*19+5<=n['h'],n['name']
print('Created 3 A4 landscape pages: editable drawio/XML, PDF, and QA previews.')

