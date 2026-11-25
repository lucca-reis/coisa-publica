"""Votos nominais de cada deputado e senador nas votações do Plenário, para todos os cartões do site.

Fontes (dados abertos, sem chave):
  Câmara  arquivos anuais  votacoes, votacoesObjetos, votacoesProposicoes, votacoesVotos  (CSV)
          https://dadosabertos.camara.leg.br/arquivos/
  Senado  https://legis.senado.leg.br/dadosabertos/votacao?dataInicio=&dataFim=  (cada votação já traz os votos)

Grava data/votos.json num formato enxuto, porque são milhares de votações:
  {"atualizado", "rotulos": ["Sim","Não",...],
   "pessoas": {"camara": [[nome, partido, uf], ...], "senado": [...]},
   "projetos": {slug: [{"casa","id","data","descricao","fonte","res","p", "v": "0011-2..."}, ...]}}
  Em "v", cada caractere é o voto da pessoa de mesmo índice em pessoas[casa] (índice do rótulo em base 36), "-" = não
  estava nessa votação. A mesma pessoa em dois partidos vira duas entradas (o partido é o da hora do voto).
  "p" = 1 na votação principal (texto, turno), 0 em requerimentos, destaques e emendas. Votação secreta: "secreta": 1, sem "v".
Os cartões escritos à mão (PROJECTS, no index.html) também entram pelo slug deles, quando a sigla não bate com o automático.
Votações simbólicas não têm voto individual e não aparecem aqui. Só usa a biblioteca padrão."""
import csv, io, json, re, sys, time, datetime, zoneinfo, pathlib, unicodedata, urllib.request, urllib.parse

BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data'
ARQ = 'https://dadosabertos.camara.leg.br/arquivos/'
SEN = 'https://legis.senado.leg.br/dadosabertos/'
UA = {'User-Agent': 'coisa-publica (coisapublica.io)', 'Accept': 'application/json'}
TIPOS = {'PL', 'PLP', 'PEC', 'MPV', 'PDL'}
SIGLA_SEN = {'PLS': 'PL', 'PLC': 'PL', 'PDS': 'PDL', 'PDC': 'PDL', 'MPV': 'MPV', 'PEC': 'PEC', 'PL': 'PL', 'PLP': 'PLP', 'PDL': 'PDL', 'PLN': 'PL'}
log, amostra = [], {}

ano0 = 2023 + 4 * ((HOJE.year - 2023) // 4)
if HOJE < datetime.date(ano0, 1, 1): ano0 -= 4
INICIO_LEG = datetime.date(ano0, 2, 1).isoformat()
FIM = HOJE.isoformat()

def baixar(url, tentativas=3):
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read().decode('utf-8-sig', 'replace')
        except Exception:
            if i == tentativas - 1: raise
            time.sleep(5 * (i + 1))

def get(url, chave=None):
    try:
        time.sleep(0.25)
        js = json.loads(baixar(url, 2) or 'null')
        if chave and chave not in amostra: amostra[chave] = {'url': url, 'resposta': js[:2] if isinstance(js, list) else js}
        return js
    except Exception as ex:
        log.append(f'{url}: {ex}'); return None

def tabela(nome, ano):
    url = f'{ARQ}{nome}/csv/{nome}-{ano}.csv'
    try:
        linhas = list(csv.DictReader(io.StringIO(baixar(url)), delimiter=';'))
    except Exception as ex:
        log.append(f'{nome} {ano}: {ex}'); return []
    if f'{nome}-cab' not in amostra and linhas: amostra[f'{nome}-cab'] = {'url': url, 'colunas': list(linhas[0].keys()), 'exemplo': linhas[0]}
    return linhas

def col(r, *nomes):
    for n in nomes:
        if r.get(n) not in (None, ''): return r[n].strip()
    return ''

def norm(t):
    t = unicodedata.normalize('NFD', str(t or ''))
    return re.sub(r'\s+', ' ', ''.join(c for c in t if not unicodedata.combining(c))).upper().strip()

def achar(o, *nomes):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in nomes and v not in (None, ''): return v
        for v in o.values():
            r = achar(v, *nomes)
            if r not in (None, ''): return r
    elif isinstance(o, list):
        for v in o:
            r = achar(v, *nomes)
            if r not in (None, ''): return r
    return None

def slug(s, n, a): return f'{s.lower()}-{int(n)}-{a}' if str(n).isdigit() else f'{s.lower()}-{n}-{a}'

# votação principal: o texto ou um turno; requerimentos, destaques e emendas ficam como secundárias
SECUNDARIA = re.compile(r'REQUERIMENTO|DESTAQUE|DESTACAD|ADIAMENTO|RETIRADA DE PAUTA|CALENDARIO ESPECIAL|EMENDA|ART\. \d+ D|DISPOSITIVO|PREFERENCIA|ENCERRAMENTO|QUEBRA DE INTERSTICIO|DISPENSA')
def principal(desc):
    d = norm(desc)
    if re.search(r'SUBSTITUTIVO|TEXTO|TURNO|REDACAO FINAL|PROJETO|PROPOSTA|MEDIDA PROVISORIA|PARECER', d) and not re.search(r'REQUERIMENTO|DESTAQUE|DESTACAD', d): return 1
    return 0 if SECUNDARIA.search(d) else 1

# ---------- pessoas e rótulos (formato enxuto) ----------
ROT, rot_i = [], {}
def rot(t):
    t = (t or '').strip() or 'Não informado'
    if t not in rot_i:
        rot_i[t] = len(ROT); ROT.append(t)
    return rot_i[t]
PESSOAS = {'camara': [], 'senado': []}
pess_i = {'camara': {}, 'senado': {}}
def pessoa(casa, chave, nome, partido, uf):
    k = (chave, partido or '')
    if k not in pess_i[casa]:
        pess_i[casa][k] = len(PESSOAS[casa]); PESSOAS[casa].append([nome, partido or '', uf or ''])
    return pess_i[casa][k]
B36 = '0123456789abcdefghijklmnopqrstuvwxyz'

projetos = {}   # slug → lista de votações
def junta(sl, vot):
    projetos.setdefault(sl, []).append(vot)

# ---------- Câmara ----------
anos = list(range(ano0, HOJE.year + 1))
vot_c = {}
for ano in anos:
    for r in tabela('votacoes', ano):
        if col(r, 'siglaOrgao') != 'PLEN': continue
        d = col(r, 'data')[:10]
        if not (INICIO_LEG <= d <= FIM): continue
        vot_c[col(r, 'id')] = {'data': (col(r, 'dataHoraRegistro') or d)[:16].replace(' ', 'T'), 'descricao': col(r, 'descricao')[:240],
                               'res': 'Aprovado' if col(r, 'aprovacao') == '1' else 'Rejeitado' if col(r, 'aprovacao') == '0' else ''}
liga = {}   # id da votação → slugs das proposições
for ano in anos:
    for nome in ('votacoesObjetos', 'votacoesProposicoes'):
        for r in tabela(nome, ano):
            vid, s = col(r, 'idVotacao'), col(r, 'proposicao_siglaTipo')
            if vid not in vot_c or s not in TIPOS: continue
            n, a = col(r, 'proposicao_numero'), col(r, 'proposicao_ano')
            if not (n and a): continue
            liga.setdefault(vid, set()).add(slug(s, n, a))
votos_c = {}   # id da votação → {índice da pessoa: rótulo}
for ano in anos:
    for r in tabela('votacoesVotos', ano):
        vid = col(r, 'idVotacao')
        if vid not in liga: continue
        i = pessoa('camara', col(r, 'deputado_id'), col(r, 'deputado_nome'), col(r, 'deputado_siglaPartido'), col(r, 'deputado_siglaUf'))
        votos_c.setdefault(vid, {})[i] = rot(col(r, 'voto'))
for vid, sls in liga.items():
    vv = votos_c.get(vid)
    if not vv: continue   # simbólica
    info = vot_c[vid]
    for sl in sls:
        junta(sl, {'casa': 'camara', 'id': vid, **info, 'p': principal(info['descricao']), '_v': vv,
                   'fonte': f'https://www.camara.leg.br/presenca-comissoes/votacao-portal?reuniao=&itemVotacao={vid}'})
print(f'Câmara: {len(vot_c)} votações no Plenário, {len(votos_c)} nominais ligadas a proposições', flush=True)

# ---------- Senado ----------
d0 = datetime.date.fromisoformat(INICIO_LEG); ns = 0
while d0 <= HOJE:
    d1 = min(HOJE, (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1))
    js = get(f'{SEN}votacao?' + urllib.parse.urlencode({'dataInicio': d0.isoformat(), 'dataFim': d1.isoformat()}), 'senado-votacao')
    d0 = d1 + datetime.timedelta(days=1)
    for v in (js if isinstance(js, list) else []):
        if not isinstance(v, dict): continue
        s = SIGLA_SEN.get(str(v.get('sigla') or '').upper()); n = str(v.get('numero') or ''); a = str(v.get('ano') or '')
        if not (s and n and a):
            m = re.search(r'\b([A-Z]{2,4})\s+(\d+)/(\d{4})', str(v.get('identificacao') or ''))
            if not m: continue
            s, n, a = SIGLA_SEN.get(m.group(1)), m.group(2), m.group(3)
            if not s: continue
        data = str(v.get('dataSessao') or '')[:10]
        if not (INICIO_LEG <= data <= FIM): continue
        desc = re.sub(r'\s+', ' ', str(v.get('descricaoVotacao') or '')).strip()[:240]
        res = str(v.get('resultadoVotacao') or '')
        vot = {'casa': 'senado', 'id': str(v.get('codigoSessaoVotacao') or ''), 'data': data, 'descricao': desc,
               'res': 'Aprovado' if res.startswith('A') else 'Rejeitado' if res.startswith('R') else '', 'p': principal(desc),
               'fonte': f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{v.get('codigoMateria')}" if v.get('codigoMateria') else 'https://www25.senado.leg.br/web/atividade/materias'}
        if str(v.get('votacaoSecreta') or '').upper() == 'S':
            vot['secreta'] = 1
            vot['tot'] = [v.get('totalVotosSim'), v.get('totalVotosNao'), v.get('totalVotosAbstencao')]
        else:
            vv = {}
            for x in v.get('votos') or []:
                i = pessoa('senado', str(x.get('codigoParlamentar') or x.get('nomeParlamentar')), x.get('nomeParlamentar') or '',
                           x.get('siglaPartidoParlamentar'), x.get('siglaUFParlamentar'))
                vv[i] = rot(x.get('descricaoVotoParlamentar') or x.get('siglaVotoParlamentar'))
            if not vv: continue
            vot['_v'] = vv
        junta(slug(s, n, a), vot); ns += 1
print(f'Senado: {ns} votações nominais', flush=True)

# ---------- cartões escritos à mão: o slug deles quando é diferente do automático ----------
html = (ROOT / 'index.html').read_text(encoding='utf-8')
bloco = html[html.index('const PROJECTS = {'):]
for ref, code in re.findall(r"\n  '([a-z0-9-]+)':\{ house:'(?:camara|senado|exec)', type:'[^']*', code:'([^']+)'", bloco):
    m = re.match(r'(PL|PEC|PLP|PDL|MP|MPV|PDS|PLS)\s+(\d+)/(\d{4})', code)
    if not m: continue
    s = {'MP': 'MPV', 'PDS': 'PDL', 'PLS': 'PL'}.get(m.group(1), m.group(1))
    auto = slug(s, m.group(2), m.group(3))
    if auto != ref and auto in projetos: projetos[ref] = projetos[auto]

# ---------- grava ----------
def enxuto(v):
    v = dict(v); vv = v.pop('_v', None)
    if vv is not None:
        tam = max(vv) + 1
        v['v'] = ''.join(B36[vv[i]] if i in vv else '-' for i in range(tam))
    return v
saida = {sl: [enxuto(v) for v in sorted(vs, key=lambda x: x['data'])] for sl, vs in projetos.items()}
amostra['_erros'] = log[:60]
(OUT / 'votos-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1)[:40000], encoding='utf-8')
if len(saida) < 50 or len(ROT) > 36:
    print('Poucos projetos ou rótulos demais; arquivo anterior mantido.', len(saida), len(ROT), log[:10]); sys.exit(0)
OUT.mkdir(exist_ok=True)
(OUT / 'votos.json').write_text(json.dumps({'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'), 'rotulos': ROT,
                                            'pessoas': PESSOAS, 'projetos': saida, 'erros': log[:40]},
                                           ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'projetos_com_votos': len(saida), 'votacoes': sum(len(v) for v in saida.values()), 'rotulos': ROT,
                  'pessoas': {k: len(v) for k, v in PESSOAS.items()}, 'erros': log[:6]}, ensure_ascii=False))
