"""Propostas que o governo mandou ao Congresso nos últimos 12 meses, com o ministério que as preparou.

Toda proposta do Executivo (medida provisória, projeto de lei, PLP, PEC, PLN) chega com uma Exposição de Motivos
assinada pelo ministério (ou ministérios) que a escreveu, no fim marcada pela sigla da pasta, como "EM nº 12/2026 MF"
ou "EMI nº 3/2026 MPO MF". O robô:
  1. lista as proposições de autoria do Poder Executivo apresentadas na Câmara (API de dados abertos da Câmara);
  2. abre o inteiro teor (PDF) de cada uma e lê as siglas da Exposição de Motivos;
  3. liga cada sigla à pasta do site (EXEC_MIN, em index.html).
Grava data/ministerios.json (as propostas, a situação atual e as pastas de cada uma) e ministerios-amostra.json
(trechos das Exposições de Motivos que não casaram com nenhuma pasta, para ajustar o mapa de siglas).
Roda uma vez por semana (.github/workflows/ministerios.yml). Precisa de pypdf para ler os PDFs."""
import io, json, re, time, datetime, zoneinfo, pathlib, unicodedata, urllib.request, urllib.parse
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

API = 'https://dadosabertos.camara.leg.br/api/v2/'
BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
INICIO = HOJE - datetime.timedelta(days=365)
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data'
UA = {'Accept': 'application/json', 'User-Agent': 'quorum (github.com/lucca-reis/quorum)'}
TIPOS = ['MPV', 'PL', 'PLP', 'PEC', 'PLN']
log, amostra = [], {'sem_pasta': [], 'sem_em': [], 'siglas_desconhecidas': {}}

def get(url, raw=False):
    for n in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA if not raw else {'User-Agent': UA['User-Agent']}), timeout=90) as r:
                b = r.read()
            return b if raw else json.loads(b.decode('utf-8'))
        except Exception as ex:
            if n == 2: log.append(f'{url[:120]}: {ex}'); return None
            time.sleep(4)

def norm(t):
    t = unicodedata.normalize('NFD', str(t or ''))
    return re.sub(r'\s+', ' ', ''.join(c for c in t if not unicodedata.combining(c))).strip()

def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', norm(t).lower()).strip('-')

# ---------- as pastas do site ----------
html = (ROOT / 'index.html').read_text(encoding='utf-8')
bloco = html[html.index('const EXEC_MIN = ['):]
bloco = bloco[:bloco.index('];')]
PASTAS = [p for p, n in re.findall(r"\['([^']+)','([^']+)'", bloco)]
POR_NOME = {slug(p): p for p in PASTAS}

def pasta(trecho):
    """Primeira pasta do site cujo nome curto começa com o trecho dado (ex.: 'Fazenda')."""
    for p in PASTAS:
        if norm(p).lower().startswith(norm(trecho).lower()): return slug(p)
    return None

SIGLAS = {
    'MF': 'Fazenda', 'MPO': 'Planejamento', 'MS': 'Saúde', 'MEC': 'Educação', 'MJSP': 'Justiça', 'MD': 'Defesa',
    'MRE': 'Relações Exteriores', 'MME': 'Minas e Energia', 'MAPA': 'Agricultura', 'MDA': 'Desenvolvimento Agrário',
    'MDS': 'Desenvolvimento e Assistência', 'MTE': 'Trabalho', 'MPS': 'Previdência', 'MCID': 'Cidades', 'MCIDADES': 'Cidades',
    'MT': 'Transportes', 'MPOR': 'Portos', 'MIDR': 'Integração', 'MCOM': 'Comunicações', 'MINC': 'Cultura', 'MTUR': 'Turismo',
    'MESP': 'Esporte', 'ME': 'Esporte', 'MIR': 'Igualdade Racial', 'MDHC': 'Direitos Humanos', 'MPI': 'Povos Indígenas',
    'MMA': 'Meio Ambiente', 'MCTI': 'Ciência', 'MDIC': 'Desenvolvimento, Indústria', 'MGI': 'Gestão', 'MPA': 'Pesca',
    'MEMP': 'Empreendedorismo', 'MMULHERES': 'Mulheres', 'MM': 'Mulheres', 'CC': 'Casa Civil', 'SRI': 'Relações Institucionais',
    'SG': 'Secretaria-Geral', 'SGPR': 'Secretaria-Geral', 'SECOM': 'Comunicação Social', 'GSI': 'Gabinete de Segurança',
    'AGU': 'Advocacia-Geral', 'CGU': 'Controladoria-Geral',
}
SIGLAS = {k: pasta(v) for k, v in SIGLAS.items()}
IGNORAR = {'PR', 'E', 'N', 'DE', 'DO', 'DA', 'BCB', 'BACEN', 'BC', 'CNJ', 'MPU', 'EM', 'EMI', 'NO', 'NA'}
EM_RE = re.compile(r'\bE\.?\s?M\.?\s?(?:I\.?)?\s*(?:n|N)\s*[ºo°.]+\s*0*\d+\s*/\s*20\d\d\s*[-–—]?\s*((?:[A-Za-z]{1,10}(?:\s*/\s*PR)?[\s,;e]*){1,7})')

def pastas_do_texto(txt):
    achadas, trechos = [], []
    for m in EM_RE.finditer(txt):
        bruto = m.group(1)
        trechos.append(m.group(0)[:120])
        for tok in re.findall(r'[A-Za-z]+', bruto.replace('/PR', ' ')):
            t = tok.upper()
            if t in IGNORAR: continue
            if t in SIGLAS and SIGLAS[t]:
                if SIGLAS[t] not in achadas: achadas.append(SIGLAS[t])
            elif len(tok) >= 2 and tok[0] in 'MSCAG' and tok[:1].isupper():
                amostra['siglas_desconhecidas'][tok] = amostra['siglas_desconhecidas'].get(tok, 0) + 1
            else:
                break   # passou da sigla: o resto já é texto
    return achadas, trechos

def texto_pdf(url):
    if not url or not PdfReader: return ''
    b = get(url, raw=True)
    if not b: return ''
    try:
        r = PdfReader(io.BytesIO(b))
        return '\n'.join((p.extract_text() or '') for p in r.pages[:40])
    except Exception as ex:
        log.append(f'pdf {url[:80]}: {ex}'); return ''

# ---------- 1. proposições do Executivo, mês a mês ----------
props, ini = {}, INICIO
while ini <= HOJE:
    fim = min(HOJE, (ini.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1))
    pag = 1
    while True:
        q = {'siglaTipo': ','.join(TIPOS), 'dataApresentacaoInicio': ini.isoformat(), 'dataApresentacaoFim': fim.isoformat(),
             'autor': 'Poder Executivo', 'itens': 100, 'pagina': pag, 'ordem': 'ASC', 'ordenarPor': 'id'}
        js = get(API + 'proposicoes?' + urllib.parse.urlencode(q))
        dados = (js or {}).get('dados') or []
        for p in dados: props[p['id']] = p
        if len(dados) < 100: break
        pag += 1
    ini = fim + datetime.timedelta(days=1)
log.append(f'{len(props)} proposições listadas')

# ---------- 2. detalhe, autoria e Exposição de Motivos ----------
out, sem = {}, []
for pid, p in sorted(props.items()):
    d = (get(API + f'proposicoes/{pid}') or {}).get('dados') or {}
    if not d: continue
    autores = (get(API + f'proposicoes/{pid}/autores') or {}).get('dados') or []
    if autores and not any('EXECUTIVO' in norm(a.get('nome', '') + ' ' + a.get('tipo', '')).upper() for a in autores):
        continue     # o filtro por autor da API às vezes traz outras autorias
    st = d.get('statusProposicao') or {}
    txt = texto_pdf(d.get('urlInteiroTeor'))
    ps, trechos = pastas_do_texto(txt)
    if not ps:
        (amostra['sem_em'] if not trechos else amostra['sem_pasta']).append({'id': pid, 'sigla': f"{d.get('siglaTipo')} {d.get('numero')}/{d.get('ano')}", 'trechos': trechos[:3], 'pdf': d.get('urlInteiroTeor'), 'chars': len(txt)})
    out[pid] = {'id': pid, 'sigla': d.get('siglaTipo'), 'numero': d.get('numero'), 'ano': d.get('ano'),
                'ementa': (d.get('ementa') or '').strip(),
                'data': (d.get('dataApresentacao') or '')[:10], 'situacao': st.get('descricaoSituacao') or '',
                'sit_data': (st.get('dataHora') or '')[:10], 'tramitacao': (st.get('descricaoTramitacao') or ''),
                'orgao': st.get('siglaOrgao') or '', 'pastas': ps, 'em': trechos[:2],
                'url': f'https://www.camara.leg.br/propostas-legislativas/{pid}'}
    if not ps: sem.append(pid)

pastas = {}
for x in sorted(out.values(), key=lambda x: x['data'], reverse=True):
    for s in x['pastas']: pastas.setdefault(s, []).append(x['id'])

OUT.mkdir(parents=True, exist_ok=True)
res = {'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'), 'periodo': [INICIO.isoformat(), HOJE.isoformat()],
       'props': {str(k): v for k, v in out.items()}, 'pastas': {k: {'pasta': POR_NOME.get(k, k), 'itens': [str(i) for i in v]} for k, v in pastas.items()},
       'sem_pasta': [str(i) for i in sem], 'fonte': 'https://dadosabertos.camara.leg.br', 'erros': log[:40]}
(OUT / 'ministerios.json').write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
(OUT / 'ministerios-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1)[:60000], encoding='utf-8')
print(json.dumps({'props': len(out), 'com_pasta': len(out) - len(sem), 'pastas': {k: len(v) for k, v in pastas.items()},
                  'desconhecidas': amostra['siglas_desconhecidas'], 'erros': log[:8]}, ensure_ascii=False))
