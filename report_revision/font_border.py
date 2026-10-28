from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E

src=Path('C:/Users/siraj/Downloads/Mini project Phase 1 report SS - Final.docx')
out=src.with_name('Mini project Phase 1 report SS - Times New Roman and Borders.docx')
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ns={'w':W}
def tag(name): return '{'+W+'}'+name
def font(pr):
    f=pr.find(tag('rFonts'))
    if f is None: f=E.Element(tag('rFonts')); pr.insert(0,f)
    f.attrib.clear()
    for key in ['ascii','hAnsi','eastAsia','cs']: f.set(tag(key),'Times New Roman')

with ZipFile(src) as z,ZipFile(out,'w') as dest:
    for item in z.infolist():
        data=z.read(item.filename)
        if item.filename.startswith('word/') and item.filename.endswith('.xml') and not item.filename.endswith('numbering.xml'):
            root=E.fromstring(data)
            for pr in root.findall('.//w:rPr',ns): font(pr)
            for run in root.findall('.//w:r',ns):
                if run.find(tag('t')) is not None:
                    pr=run.find(tag('rPr'))
                    if pr is None: pr=E.Element(tag('rPr')); run.insert(0,pr)
                    font(pr)
            if item.filename=='word/styles.xml':
                for style in root.findall('w:style',ns):
                    pr=style.find(tag('rPr'))
                    if pr is None: pr=E.SubElement(style,tag('rPr'))
                    font(pr)
                for f in root.findall('.//w:rFonts',ns):
                    f.attrib.clear()
                    for key in ['ascii','hAnsi','eastAsia','cs']: f.set(tag(key),'Times New Roman')
            if item.filename=='word/document.xml':
                for sec in root.findall('.//w:sectPr',ns):
                    for old in sec.findall(tag('pgBorders')): sec.remove(old)
                    borders=E.Element(tag('pgBorders'))
                    borders.set(tag('offsetFrom'),'page'); borders.set(tag('display'),'allPages')
                    borders.set(tag('zOrder'),'back')
                    for side in ['top','left','bottom','right']:
                        b=E.SubElement(borders,tag(side))
                        for key,val in [('val','single'),('sz','6'),('space','24'),('color','000000')]: b.set(tag(key),val)
                    # Insert before page numbering to preserve the section-property order.
                    after=sec.find(tag('pgMar'))
                    sec.insert(sec.index(after)+1 if after is not None else 0,borders)
            data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        dest.writestr(item,data)
print(out)
