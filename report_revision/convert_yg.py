from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from collections import defaultdict
import re
import pdfplumber
from pypdf import PdfReader

ROOT=Path('C:/Users/siraj/Downloads/Secure Password Manager Overleaf')
OUT=ROOT/'report-complete.tex'
SOURCE=Path('C:/Users/siraj/Downloads/Mini-Project_Progress-I Report YG.pdf')
ASSETS=ROOT/'images/yg-report'
ASSETS.mkdir(parents=True,exist_ok=True)
# Preserve the previous open document in the task work area before replacing it.
Path('E:/AI_Trading/report_revision/report-before-yg.tex').write_bytes(OUT.read_bytes())

def esc(s):
    replacements={'\\':r'\textbackslash{}','{':r'\{','}':r'\}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','^':r'\textasciicircum{}','~':r'\textasciitilde{}','●':r'\textbullet{}','•':r'\textbullet{}','\u00a0':' '}
    return ''.join(replacements.get(c,c) for c in s)

def style(name):
    f=name.lower(); typ='YGserif'
    if 'calibri' in f or 'arial' in f: typ='YGsans'
    italic='italic' in f
    bold='bold' in f
    return '\\'+typ+('\\bfseries' if bold else '\\mdseries')+('\\itshape' if italic else '\\upshape')

def rgb(c):
    if c is None: return '0,0,0'
    if isinstance(c,(float,int)): a=[float(c)]*3
    elif len(c)==1:a=list(c)*3
    elif len(c)==4:
        cy,ma,ye,k=c;a=[(1-cy)*(1-k),(1-ma)*(1-k),(1-ye)*(1-k)]
    else:a=list(c)[:3]
    return ','.join(str(round(max(0,min(1,x))*255)) for x in a)

head=r'''% Faithful page-by-page reconstruction of the supplied 21-page PDF.
% Compiler: pdfLaTeX, XeLaTeX or LuaLaTeX.
% Text is editable. Positions and line breaks are deliberately fixed to match
% the reference; long edits may require adjusting the corresponding coordinates.
% YGtext arguments: x, baseline from top, original width, font size, style, RGB, text.
\documentclass[12pt,letterpaper]{article}
\usepackage[paperwidth=612bp,paperheight=792bp,margin=0pt]{geometry}
\usepackage{iftex}
\ifPDFTeX
  \usepackage[T1]{fontenc}
  \usepackage[utf8]{inputenc}
  \usepackage{tgtermes,tgheros}
  \newcommand{\YGserif}{\rmfamily}
  \newcommand{\YGsans}{\sffamily}
\else
  \usepackage{fontspec}
  \IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}%
    {\setmainfont{TeX Gyre Termes}}
  \IfFontExistsTF{Calibri}{\setsansfont{Calibri}}%
    {\setsansfont{TeX Gyre Heros}}
  \newcommand{\YGserif}{\rmfamily}
  \newcommand{\YGsans}{\sffamily}
\fi
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{tikz}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\setlength{\topskip}{0pt}
\newcommand{\YGtext}[7]{%
  \node[anchor=base west,inner sep=0pt,outer sep=0pt] at (#1,#2)
    {{\fontsize{#4bp}{#4bp}\selectfont#5\color[RGB]{#6}%
      \makebox[#3bp][s]{#7}}};%
}
\newcommand{\YGimage}[5]{%
  \node[anchor=north west,inner sep=0pt,outer sep=0pt] at (#1,#2)
    {\includegraphics[width=#3bp,height=#4bp]{#5}};%
}
\newcommand{\YGbeginpage}{%
  \null\begin{tikzpicture}[remember picture,overlay,x=1bp,y=-1bp]
  \begin{scope}[shift={(current page.north west)}]}
\newcommand{\YGendpage}{\end{scope}\end{tikzpicture}\newpage}
\begin{document}
'''

labels={1:'Cover',2:'Certificate',3:'Title, Abstract and Introduction',4:'Introduction and Significance',5:'Societal, Industrial, Academic and Innovative Significance',6:'Literature Review',7:'Literature Review continued',8:'Literature Review and Research Gap',9:'Research Gap, Problem Statement and Objectives',10:'Scope and Methodology',11:'Software Tools and Flow Chart',12:'Flow Chart Explanation and Work Completed',13:'System Architecture and Prototype Development',14:'Modified File Detection and Baseline Creation',15:'Added and Deleted Files and Test Cases',16:'Analysis, Results and Discussion',17:'Remaining Work Plan and Completion Date',18:'References 1 to 10',19:'References 11 to 22',20:'References 23 to 30 and Submission Date',21:'Student and Faculty Signatures'}

reader=PdfReader(SOURCE)
lines=[head]; textlines=0; saved=[]
with pdfplumber.open(SOURCE) as pdf:
    for idx,page in enumerate(pdf.pages):
        lines += ['','% ============================================================',f'% PAGE {idx+1}: {labels[idx+1]}','% ============================================================',r'\YGbeginpage']
        # Reconstruct the original border, table rules and cell backgrounds as vectors.
        for rect in page.rects:
            if not rect.get('fill') and not rect.get('stroke'):continue
            col=rgb(rect.get('non_stroking_color') if rect.get('fill') else rect.get('stroking_color'))
            fill='fill=YGcolor,draw=none' if rect.get('fill') else f'draw=YGcolor,line width={rect.get("linewidth",.5):.4f}bp'
            lines.append(r'\definecolor{YGcolor}{RGB}{'+col+'}')
            lines.append(f'\\path[{fill}] ({rect["x0"]:.4f},{rect["top"]:.4f}) rectangle ({rect["x1"]:.4f},{rect["bottom"]:.4f});')
        # Retain original screenshots and diagrams at their original resolution.
        images={im.name.rsplit('.',1)[0]:im for im in reader.pages[idx].images}
        for j,image in enumerate(page.images):
            original=images[image['name']]
            filename=f'page-{idx+1:02d}-image-{j+1:02d}.png'
            original.image.save(ASSETS/filename)
            rel='images/yg-report/'+filename; saved.append(rel)
            lines.append(f'\\YGimage{{{image["x0"]:.4f}}}{{{image["top"]:.4f}}}{{{image["width"]:.4f}}}{{{image["height"]:.4f}}}{{{rel}}}')
        # Extract each word, retaining its source font and baseline. Group adjacent
        # words into editable lines, preserving mixed bold/italic spans and cells.
        words=page.extract_words(x_tolerance=1.5,y_tolerance=2,extra_attrs=['fontname','size'],return_chars=True)
        rows=defaultdict(list)
        for word in words:
            baseline=page.height-word['chars'][0]['matrix'][5]
            rows[round(baseline,2)].append(word)
        for baseline,row in sorted(rows.items()):
            row.sort(key=lambda w:w['x0']); groups=[]; current=[]
            for word in row:
                if current:
                    prev=current[-1]
                    if word['fontname']!=prev['fontname'] or abs(word['size']-prev['size'])>.05 or word['x0']-prev['x1']>23:
                        groups.append(current);current=[]
                current.append(word)
            if current:groups.append(current)
            for group in groups:
                text=' '.join(w['text'] for w in group)
                if not text.strip():continue
                x=group[0]['x0'];width=group[-1]['x1']-x;size=group[0]['size']; font=style(group[0]['fontname'])
                color=rgb(group[0]['chars'][0].get('non_stroking_color'))
                lines.append(f'\\YGtext{{{x:.4f}}}{{{baseline:.4f}}}{{{width:.4f}}}{{{size:.4f}}}{{{font}}}{{{color}}}{{{esc(text)}}}')
                textlines+=1
        lines.append(r'\YGendpage' if idx<len(pdf.pages)-1 else r'\end{scope}\end{tikzpicture}')
lines.append(r'\end{document}')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')

readme='''# Mini-Project Progress-I Report — Overleaf conversion

This is a page-preserving conversion of Mini-Project_Progress-I Report YG.pdf: Hash based File Integrity Tester using Python. It retains the original report text, student names, page breaks, numbered headings, tables, borders, printed page numbers, images, captions, references and signatures across 21 US Letter pages.

Upload this ZIP to Overleaf and set report-complete.tex as the main document. The source supports pdfLaTeX, XeLaTeX and LuaLaTeX. XeLaTeX uses Times New Roman and Calibri when installed; on Overleaf, Times-compatible TeX Gyre Termes and a compatible sans font are used instead. The output is a close layout reconstruction; substituted fonts can differ slightly from the PDF.

The report text, table-cell text and page rules are editable LaTeX. The original diagrams and prototype screenshots remain image assets. This is not a whole-PDF embedding. Text is placed in page coordinates to preserve the reference layout; long text edits do not automatically reflow and may require coordinate adjustments. Each page is identified by a comment in the source. YGtext arguments are x position, baseline from the top, width, font size, style, RGB color and editable text.

The source PDF has a numbering jump from section 12 to section 15, incomplete bibliography entries, and some sparse pages. Those details are preserved because the request is to reproduce the report as it is. Source claims and experimental results are transcribed, not independently validated.
'''
(ROOT/'YG-Overleaf-README.md').write_text(readme,encoding='utf-8')
zipout=Path('C:/Users/siraj/Downloads/Mini Project Progress I YG - Overleaf.zip')
with ZipFile(zipout,'w',ZIP_DEFLATED) as z:
    z.write(OUT,'report-complete.tex')
    z.write(ROOT/'YG-Overleaf-README.md','README.md')
    for rel in saved:z.write(ROOT/rel,rel)
print('Source:',OUT)
print('ZIP:',zipout)
print('Pages: 21; editable text blocks:',textlines,'; images:',len(saved))
