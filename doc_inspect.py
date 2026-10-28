from docx import Document
import re

p = r"C:\Users\siraj\Downloads\LY Capstone Project_Progress-I Report.docx"
d = Document(p)
print("inline_shapes", len(d.inline_shapes))
for i in [3,25,35,37,41,42,43,44,45,47,49,51,53,55,57,59,61,63,65,66,68,70,72,74,76,79,81,83,86,87,88,89,90,91,92,97,99,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187]:
    t = d.paragraphs[i].text
    print(i, len(re.findall(r"\b[\w'-]+\b", t)), t[:100])
