import re,sys
d=sys.argv[1]; out=sys.argv[2]
css=open(d+'/css.txt').read(); body=open(d+'/body.txt').read()
fonts='<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,500;0,600;1,500&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap">\n'
def page(title,b): return f'<title>{title}</title>\n'+fonts+css+'\n'+b
teacher=body.replace('<!--T-->','').replace('<!--/T-->','')
student=re.sub(r'<!--T-->.*?<!--/T-->\n?','',body,flags=re.S)
student=student.replace('<li>13 задач по уровням</li>','<li>13 задач по уровням</li>')
assert 'Ответ</summary>' not in student and 'преподават' not in student.lower()
open(out+'/teacher.html','w').write(page('Текстовые задачи Клима (ответы)',teacher))
open(out+'/student.html','w').write(page('Текстовые задачи Клима',student))
def printify(h):
    h=re.sub(r'<link[^>]*>\n?','',h)
    h=re.sub(r'@media \(prefers-color-scheme:dark\)\{.*?\n\}\n','',h,flags=re.S)
    h=re.sub(r':root\[data-theme="dark"\]\{.*?\n\}\n','',h,flags=re.S)
    h=h.replace('<details>','<details open>')
    pc='@page{margin:14mm 12mm}\n@media print{body{font-size:14px;padding:0;background:#fff}.masthead{padding-block:0 12px}.task,.callout,.card,.eq,tr,.cheat{break-inside:avoid}h2,h3,h4,.blockhead{break-after:avoid}.eq,.callout,.card{box-shadow:none}section.block{margin-bottom:28px}}\n</style>'
    a,_,b=h.rpartition('</style>'); h=a+pc+b
    return '<!doctype html><html lang="ru"><head><meta charset="utf-8"></head><body>'+h+'</body></html>'
open(out+'/print-teacher.html','w').write(printify(page('Текстовые задачи Клима (ответы)',teacher)))
open(out+'/print-student.html','w').write(printify(page('Текстовые задачи Клима',student)))
print('built')
