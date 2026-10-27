"""Editable UML sequence diagrams with matching A4 PDF and QA images."""
from pathlib import Path
import math
import shutil
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4, landscape

OUT=Path(__file__).resolve().parents[1]/'docs/diagrams'
OUT.mkdir(parents=True,exist_ok=True)
W,H=1123,794
pages=[]
def page(title, participants, note):
    p=dict(title=title,parts=participants,messages=[],frames=[],activations=[],note=note)
    pages.append(p);return p
def msg(p,a,b,y,label,kind='sync'):
    p['messages'].append(dict(a=a,b=b,y=y,label=label,kind=kind))
def frame(p,x,y,w,h,label,divider=None):p['frames'].append((x,y,w,h,label,divider))
def active(p,i,y,h):p['activations'].append((i,y,h))

p=page('Figure 2.4(a)  Project creation and requirement clarification',
 [('User','actor'),('Frontend','boundary'),('Projects API','control'),('Understanding','control'),('Local model','control'),('RequirementEngine','control'),('SQLite store','entity')],
 'Understanding denotes execute_understanding(); failed model extraction returns labelled heuristic suggestions.')
for a,b,y,l,k in [
 (0,1,180,'Submit project idea','sync'),(1,2,208,'POST /api/projects','sync'),
 (2,6,236,'Save snapshot and PROJECT_CREATED event','sync'),
 (2,1,264,'project_id + version','return'),
 (1,2,292,'POST /{id}/understand','sync'),
 (2,3,320,'execute_understanding(raw_request)','sync'),
 (3,4,348,'generate(prompt)','sync'),(4,3,376,'Model response','return'),
 (3,2,404,'Validated extraction / labelled suggestions','return'),
 (2,5,432,'evaluate_requirements(output)','sync'),
 (5,2,460,'Questions + readiness','return'),
 (2,6,488,'Save context and understanding events','sync'),
 (2,1,516,'Context + next_clarification','return'),
 (1,0,544,'Show requirements / clarification','return'),
 (0,1,592,'Provide clarification answer','sync'),
 (1,2,620,'POST /{id}/clarify','sync'),
 (2,6,648,'Save updated requirements + version','sync'),
 (2,1,676,'Updated context + next question','return')]:msg(p,a,b,y,l,k)
frame(p,25,548,1050,145,'loop [while clarification questions remain]')
for args in [(1,180,510),(2,208,475),(3,320,90),(4,348,34),(5,432,34),(6,236,18),(6,488,18),(6,648,18)]:active(p,*args)

p=page('Figure 2.4(b)  Offline specialist analysis and build specification',
 [('Frontend','boundary'),('Projects API','control'),('Pipeline','control'),('Specialist','control'),('Harness','control'),('Local model','control'),('Spec compiler','control')],
 'Specialist loop order: Product, AI/ML, Engineering, UX, Security, QA. Contradictions or invalid output stop planning.')
for a,b,y,l,k in [
 (0,1,180,'POST /{id}/analyze','sync'),(1,0,208,'status: started','return'),
 (1,2,236,'Schedule background pipeline','async'),
 (2,3,286,'analyze(state)','sync'),(3,4,316,'execute(context)','sync'),
 (4,5,346,'generate(prompt)','sync'),(5,4,376,'JSON response','return'),
 (4,3,406,'Validated HarnessResult','return'),(3,2,436,'Specialist output','return'),
 (2,1,466,'Save output + emit AGENT_COMPLETED','sync'),
 (1,0,496,'SSE: agent progress','async'),
 (2,2,526,'Check conflicts; create blueprint','sync'),
 (2,6,574,'compile_model(context, state, model)','sync'),
 (6,5,604,'Generate and validate spec sections','sync'),
 (5,6,634,'Section JSON responses','return'),
 (6,2,664,'Validated BuildSpec','return'),
 (2,1,694,'Save spec + emit PIPELINE_COMPLETED','sync'),
 (1,0,722,'SSE: planning complete','async')]:msg(p,a,b,y,l,k)
frame(p,315,245,570,236,'loop [each specialist]')
frame(p,315,551,770,127,'opt [no conflicts]')
for args in [(1,180,30),(2,236,466),(3,286,156),(4,316,96),(5,346,36),(6,574,96),(5,604,36)]:active(p,*args)

p=page('Figure 2.4(c)  Source generation and isolated verification',
 [('Frontend','boundary'),('Projects API','control'),('Orchestrator','control'),('CodingAgent','control'),('Repository','entity'),('TestRunner','control'),('Docker sandbox','control')],
 'Current offline strategy: DECLARATIVE_CRUD. Backend/API/browser/build checks run without container network access.')
for a,b,y,l,k in [
 (0,1,180,'POST /{id}/build','sync'),(1,2,210,'to_thread(execute_build)','async'),
 (2,4,240,'Initialize workspace + task graph metadata','sync'),
 (2,3,286,'execute_task(...)','sync'),(3,4,316,'write_task_file(...)','sync'),
 (4,3,346,'Write result','return'),(3,2,376,'Task result','return'),
 (2,4,406,'Record checkpoint','sync'),
 (2,5,466,'Run declared checks','sync'),(5,6,496,'execute(command)','sync'),
 (6,5,526,'Exit code + output','return'),(5,2,556,'Verification results','return'),
 (2,1,612,'VERIFIED report','return'),(2,1,680,'BLOCKED / REQUIRES_HUMAN','return'),
 (1,0,710,'Persisted final build report','return')]:msg(p,a,b,y,l,k)
frame(p,315,245,460,177,'loop [ready tasks in dependency order]')
frame(p,315,424,770,148,'loop [backend, frontend, API, browser checks]')
frame(p,170,573,350,124,'alt [all required checks pass]',(638,'[check fails / runtime unavailable]'))
for args in [(1,180,536),(2,210,477),(3,286,96),(4,240,16),(4,316,36),(5,466,96),(6,496,36)]:active(p,*args)

def xpos(i):return 65+i*155
def points(m):
    x1,x2=xpos(m['a']),xpos(m['b']);y=m['y']
    return [(x1,y),(x1+45,y),(x1+45,y+15),(x1,y+15)] if x1==x2 else [(x1,y),(x2,y)]

mx=ET.Element('mxfile',host='app.diagrams.net',version='24.7.17',type='device')
for n,p in enumerate(pages,1):
    diagram=ET.SubElement(mx,'diagram',id=f'sequence-{n}',name=f'2.4{chr(96+n)}')
    model=ET.SubElement(diagram,'mxGraphModel',dx=str(W),dy=str(H),grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(W),pageHeight=str(H),math='0',shadow='0')
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    def vertex(key,value,x,y,w,h,style):
        c=ET.SubElement(root,'mxCell',id=key,value=value,style=style,vertex='1',parent='1')
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    def line(key,pts,label='',style=''):
        c=ET.SubElement(root,'mxCell',id=key,value=label,edge='1',parent='1',style='html=0;rounded=0;strokeColor=#000000;fontFamily=Times New Roman;fontSize=16;labelBackgroundColor=#FFFFFF;'+style)
        g=ET.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
        for role,(x,y) in [('sourcePoint',pts[0]),('targetPoint',pts[-1])]:ET.SubElement(g,'mxPoint',x=str(x),y=str(y),attrib={'as':role})
        if len(pts)>2:
            arr=ET.SubElement(g,'Array',attrib={'as':'points'})
            for x,y in pts[1:-1]:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
        ET.SubElement(g,'mxPoint',x='0',y='-12',attrib={'as':'offset'})
    textstyle='text;html=0;whiteSpace=wrap;fontFamily=Times New Roman;fontSize=16;align=center;verticalAlign=middle;'
    vertex('title','ProjectForge AI UML Sequence Diagram',25,20,1070,30,textstyle+'fontStyle=1;fontSize=21;')
    vertex('caption',p['title'],25,54,1070,28,textstyle+'fontSize=18;')
    for i,(name,role) in enumerate(p['parts']):
        x=xpos(i)
        if role=='actor':
            vertex(f'actor-{i}','',x-15,94,30,48,'shape=umlActor;fillColor=#FFFFFF;strokeColor=#000000;')
            vertex(f'name-{i}',name,x-63,142,126,23,textstyle)
        else:
            displayed='Requirement\nEngine' if name=='RequirementEngine' else name
            vertex(f'head-{i}',f'«{role}»\n{displayed}',x-66,100,132,59,'rounded=0;whiteSpace=wrap;html=0;fillColor=#FFFFFF;strokeColor=#000000;fontFamily=Times New Roman;fontSize=16;align=center;')
        line(f'life-{i}',[(x,165),(x,733)],style='dashed=1;endArrow=none;')
    for i,f in enumerate(p['frames']):
        x,y,w,h,label,divider=f
        vertex(f'frame-{i}',label,x,y,w,h,'shape=umlFrame;whiteSpace=wrap;html=0;fillColor=none;strokeColor=#000000;fontFamily=Times New Roman;fontSize=16;align=left;verticalAlign=top;spacingLeft=7;spacingTop=4;')
        if divider:
            yy,guard=divider;line(f'divider-{i}',[(x,yy),(x+w,yy)],style='dashed=1;endArrow=none;')
            vertex(f'guard-{i}',guard,x+5,yy+2,w-10,21,textstyle+'fontSize=14;align=left;')
    for i,(part,y,h) in enumerate(p['activations']):vertex(f'activation-{i}','',xpos(part)-5,y,10,h,'rounded=0;fillColor=#FFFFFF;strokeColor=#000000;')
    for i,m in enumerate(p['messages']):
        arrows='endArrow=block;endFill=1;' if m['kind']=='sync' else 'endArrow=open;endFill=0;'
        if m['kind']=='return':arrows+='dashed=1;'
        line(f'message-{i}',points(m),m['label'],arrows)
    for i,(x,y,w,h,label,divider) in enumerate(p['frames']):
        vertex(f'frame-label-{i}',label,x+4,y+1,min(w-8,len(label)*7+12),23,textstyle+'fontSize=14;align=left;fillColor=#FFFFFF;')
        if divider:
            yy,guard=divider
            vertex(f'guard-label-{i}',guard,x+4,yy+2,w-8,21,textstyle+'fontSize=12;align=left;fillColor=#FFFFFF;')
    vertex('note',p['note'],28,741,1060,20,textstyle+'fontSize=14;align=left;')
    vertex('legend','Filled arrow: call | Open arrow: asynchronous message | Dashed arrow: return | Narrow rectangle: activation',28,762,1060,19,textstyle+'fontSize=14;align=left;')
    vertex('page',f'A4 landscape | Section 2.4 | {n} / 3',28,781,1060,13,textstyle+'fontSize=12;')
ET.indent(mx)
path=OUT/'ProjectForge_UML_Sequence_Diagrams_A4.drawio'
ET.ElementTree(mx).write(path,encoding='utf-8',xml_declaration=True)
shutil.copyfile(path,OUT/'ProjectForge_UML_Sequence_Diagrams_A4.xml')

pdfmetrics.registerFont(TTFont('SequenceTimes','C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('SequenceTimesBold','C:/Windows/Fonts/timesbd.ttf'))
pdf=canvas.Canvas(str(OUT/'ProjectForge_UML_Sequence_Diagrams_A4.pdf'),pagesize=landscape(A4))
for num,p in enumerate(pages,1):
    im=Image.new('RGB',(W*2,H*2),'white');d=ImageDraw.Draw(im)
    pw,ph=landscape(A4);sx=pw/W;sy=ph/H
    def text(x,y,value,size=16,bold=False,center=True):
        font=ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf' if bold else 'C:/Windows/Fonts/times.ttf',size*2)
        for i,l in enumerate(value.split('\n')):
            xx=x*2-(d.textlength(l,font=font)/2 if center else 0)
            # White backing keeps dashed lifelines out of message labels.
            bounds=d.textbbox((xx,(y+i*18)*2),l,font=font)
            d.rectangle((bounds[0]-2,bounds[1]-1,bounds[2]+2,bounds[3]+1),fill='white')
            d.text((xx,(y+i*18)*2),l,font=font,fill='black')
            pdf.setFont('SequenceTimesBold' if bold else 'SequenceTimes',size*sx)
            width=pdfmetrics.stringWidth(l,'SequenceTimesBold' if bold else 'SequenceTimes',size*sx)
            left=x*sx-width/2 if center else x*sx
            pdf.setFillColorRGB(1,1,1);pdf.rect(left-1,ph-(y+i*18+size)*sy,width+2,size*sy,fill=1,stroke=0);pdf.setFillColorRGB(0,0,0)
            pdf.drawString(left,ph-(y+i*18+size*.85)*sy,l)
    def line(pts,dashed=False):
        for a,b in zip(pts,pts[1:]):
            length=math.dist(a,b)
            if dashed:
                for t in range(0,max(1,int(length)),9):
                    d.line([(2*(a[0]+(b[0]-a[0])*v/length),2*(a[1]+(b[1]-a[1])*v/length)) for v in (t,min(t+5,length))],fill='black',width=2)
            else:d.line([(x*2,y*2) for x,y in (a,b)],fill='black',width=2)
        pdf.setDash(4,3) if dashed else pdf.setDash()
        q=pdf.beginPath();q.moveTo(pts[0][0]*sx,ph-pts[0][1]*sy)
        for x,y in pts[1:]:q.lineTo(x*sx,ph-y*sy)
        pdf.drawPath(q);pdf.setDash()
    def rect(x,y,w,h):
        d.rectangle((x*2,y*2,(x+w)*2,(y+h)*2),fill='white',outline='black',width=2)
        pdf.setFillColorRGB(1,1,1);pdf.rect(x*sx,ph-(y+h)*sy,w*sx,h*sy,fill=1,stroke=1);pdf.setFillColorRGB(0,0,0)
    text(W/2,21,'ProjectForge AI UML Sequence Diagram',21,True);text(W/2,56,p['title'],18)
    for i,(name,role) in enumerate(p['parts']):
        x=xpos(i)
        if role=='actor':
            d.ellipse(((x-7)*2,94*2,(x+7)*2,108*2),outline='black',width=2);pdf.circle(x*sx,ph-101*sy,7*sx)
            for pts in [[(x,108),(x,131)],[(x-13,118),(x+13,118)],[(x,131),(x-11,143)],[(x,131),(x+11,143)]]:line(pts)
            text(x,145,name)
        else:
            rect(x-66,100,132,59);text(x,106,'«'+role+'»');
            # Split long participant names for a readable header.
            if name=='RequirementEngine':text(x,126,'Requirement\nEngine',14)
            else:text(x,129,name,16)
        line([(x,165),(x,733)],True)
    for x,y,w,h,label,divider in p['frames']:
        line([(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)])
        text(x+7,y+3,label,14,False,False)
        if divider:
            yy,guard=divider;line([(x,yy),(x+w,yy)],True);text(x+6,yy+2,guard,12,False,False)
    for i,y,h in p['activations']:rect(xpos(i)-5,y,10,h)
    for m in p['messages']:
        pts=points(m);line(pts,m['kind']=='return')
        a,b=pts[-2:];dx,dy=a[0]-b[0],a[1]-b[1];length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
        arr=[(b[0]+ux*10-uy*4,b[1]+uy*10+ux*4),b,(b[0]+ux*10+uy*4,b[1]+uy*10-ux*4)]
        if m['kind']=='sync':
            d.polygon([(x*2,y*2) for x,y in arr],fill='black');q=pdf.beginPath();q.moveTo(arr[0][0]*sx,ph-arr[0][1]*sy)
            for x,y in arr[1:]:q.lineTo(x*sx,ph-y*sy)
            q.close();pdf.drawPath(q,fill=1)
        else:line(arr)
        x=(pts[0][0]+pts[-1][0])/2
        if m['a']==m['b']:x+=100
        text(x,m['y']-19,m['label'],16)
    for x,y,w,h,label,divider in p['frames']:
        text(x+7,y+3,label,14,False,False)
        if divider:
            yy,guard=divider;text(x+6,yy+2,guard,12,False,False)
    text(28,741,p['note'],14,False,False)
    text(28,763,'Filled arrow: call | Open arrow: asynchronous message | Dashed arrow: return | Narrow rectangle: activation',14,False,False)
    text(W/2,782,f'A4 landscape | Section 2.4 | {num} / 3',12)
    im.save(OUT/f'sequence-preview-{num}.png');pdf.showPage()
pdf.save()
assert len(ET.parse(path).findall('diagram'))==3
for p in pages:
    assert all(0<=m['a']<7 and 0<=m['b']<7 and 165<m['y']<734 for m in p['messages'])
print('Created editable XML/drawio and 3-page A4 PDF sequence diagrams.')
