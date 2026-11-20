"""Monta a prévia do site para ver no Claude (artifact): o index.html com os ocupantes embutidos e os dados lidos de
arquivos publicados ao lado da página (o artifact não deixa buscar nada em coisapublica.io). Grava em prévia/ (fora do git).
Uso: python3 scripts/previa.py  ->  previa/index.html e previa/data/...  (publicar index.html com os arquivos de data/)"""
import os, re, shutil, glob

OUT = 'previa'
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT + '/data/transparencia', exist_ok=True)
s = open('index.html', encoding='utf-8').read()
occ = open('data/ocupantes.js', encoding='utf-8').read()
s = s.replace('<script src="data/ocupantes.js"></script>', '<script>' + occ + '</script>', 1)
# dentro do artifact a página está num frame: buscar primeiro os arquivos publicados ao lado dela
s = s.replace("/^https?:$/.test(location.protocol) && !FRAMED ? ['data/consultas.json'] : []", "['data/consultas.json']")
s = s.replace("/^https?:$/.test(location.protocol) && !FRAMED ? [path, TR_BASE+path, TR_BASE2+path] : [TR_BASE+path, TR_BASE2+path]", "[path, TR_BASE+path, TR_BASE2+path]")
s = re.sub(r'<title>[^<]*</title>', '<title>Prévia Coisa Pública</title>', s, count=1)
open(OUT + '/index.html', 'w', encoding='utf-8').write(s)
files = [f for f in glob.glob('data/*.json') + glob.glob('data/transparencia/*.json') if 'amostra' not in f]
for f in files: shutil.copy(f, OUT + '/' + f)
print('\n'.join(files))
