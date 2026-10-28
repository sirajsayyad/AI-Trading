from zipfile import ZipFile
from lxml import etree as E
from pathlib import Path

src=Path('C:/Users/siraj/Downloads/Mini project Phase 1 report.docx')
out=src.with_name('Mini project Phase 1 report - No Borders or Page Numbers.docx')
n={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
   'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
   'wps':'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
   'v':'urn:schemas-microsoft-com:vml',
   'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006',
   'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture'}
count=0; nums=[]
with ZipFile(src) as z,ZipFile(out,'w') as o:
 for item in z.infolist():
  data=z.read(item.filename)
  if item.filename=='word/document.xml':
   r=E.fromstring(data)
   for b in r.findall('.//w:pgBorders',n): b.getparent().remove(b)
   for s in r.findall('.//wps:wsp',n):
    extent=s.find('wps:spPr/a:xfrm/a:ext',n)
    if extent is not None and int(extent.get('cx','0'))>6000000 and int(extent.get('cy','0'))>9000000:
     s.getparent().remove(s); count+=1
   for s in r.findall('.//v:shape',n):
    path=s.get('path','')
    if 'r6749739' in path or 'r6695440' in path: s.getparent().remove(s)
    elif path.startswith('m,l,4216400em6743700,r,4216400e'):
     s.set('path',path[len('m,l,4216400em6743700,r,4216400e'):])
   # Two clipped page-border sides were embedded into the architecture group.
   for path in r.findall('.//a:path',n):
    if path.get('w')=='6743700' and path.get('h')=='4216400':
     pts=path.findall('.//a:pt',n)
     if len(pts)==2 and pts[0].get('x')==pts[1].get('x') and pts[0].get('y')=='0' and pts[1].get('y')=='4216400':
      path.getparent().remove(path)
   for ac in r.findall('.//mc:AlternateContent',n):
    if not ac.findall('.//wps:wsp',n) and not ac.findall('.//pic:pic',n) and not ac.findall('.//v:imagedata',n):
     ac.getparent().remove(ac)
   for p in r.findall('w:body/w:p',n):
    t=''.join(p.xpath('.//w:t/text()',namespaces=n)).strip()
    if t.isdigit() and 2<=int(t)<=20:
     nums.append(t)
     for node in p.findall('.//w:t',n): node.text=''
   data=E.tostring(r,encoding='UTF-8',xml_declaration=True,standalone=True)
  o.writestr(item,data)
print('Removed border shapes:',count,'Page numbers:',','.join(nums))
print(out)
