"""Cartões automáticos: tudo o que foi tratado no mandato atual dos Três Poderes.

O mandato atual começa em 1º de janeiro do ano da posse do presidente (2023, 2027, 2031…; a partir de 2027 a posse é em 5 de janeiro)
e vale também para a legislatura do Congresso, que começa em 1º de fevereiro do mesmo ano. Entra no arquivo:
  1. Toda proposição (PL, PLP, PEC, MPV, PDL) votada no Plenário da Câmara desde o início do mandato.
  2. Toda medida provisória editada e toda proposta enviada pelo Poder Executivo desde o início do mandato.
  3. Toda proposição que virou norma jurídica desde o início do mandato.
  4. Toda matéria votada no Plenário do Senado (votação nominal) desde o início do mandato.
O Supremo não tem dados abertos parecidos; os cartões do STF continuam escritos à mão em index.html.

Fontes (dados abertos):
  Câmara  https://dadosabertos.camara.leg.br/arquivos/  votacoes, votacoesObjetos, votacoesProposicoes, proposicoes, proposicoesAutores (CSV anuais)
          https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}  para proposições de anos não baixados
  Senado  https://legis.senado.leg.br/dadosabertos/votacao?dataInicio=&dataFim=  e  /processo?sigla=&numero=&ano=
Grava data/projetos.json (os cartões, no mesmo formato de PROJECTS no index.html) e data/projetos-amostra.json
(cabeçalhos e exemplos das respostas, para conferir o formato). Só usa a biblioteca padrão."""
import csv, io, json, re, sys, time, datetime, zoneinfo, pathlib, unicodedata, urllib.request, urllib.parse

csv.field_size_limit(10**8)
BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data'
ARQ = 'https://dadosabertos.camara.leg.br/arquivos/'
API = 'https://dadosabertos.camara.leg.br/api/v2/'
SEN = 'https://legis.senado.leg.br/dadosabertos/'
UA = {'User-Agent': 'coisa-publica (coisapublica.io)', 'Accept': 'application/json'}
TIPOS = {'PL', 'PLP', 'PEC', 'MPV', 'PDL'}
NOME_TIPO = {'PL': 'Projeto de Lei', 'PLP': 'Projeto de Lei Complementar', 'PEC': 'Proposta de Emenda à Constituição',
             'MPV': 'Medida Provisória', 'PDL': 'Projeto de Decreto Legislativo'}
SIGLA_SEN = {'PLS': 'PL', 'PLC': 'PL', 'PDS': 'PDL', 'PDC': 'PDL', 'MPV': 'MPV', 'PEC': 'PEC', 'PL': 'PL', 'PLP': 'PLP', 'PDL': 'PDL', 'PLN': 'PL'}
log, amostra = [], {}

# ---------- início do mandato ----------
ano0 = 2023 + 4 * ((HOJE.year - 2023) // 4)
if HOJE < datetime.date(ano0, 1, 1): ano0 -= 4
INICIO = datetime.date(ano0, 1, 1).isoformat()
INICIO_LEG = datetime.date(ano0, 2, 1).isoformat()
FIM = HOJE.isoformat()

def baixar(url, tentativas=3):
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read().decode('utf-8-sig', 'replace')
        except Exception as ex:
            if i == tentativas - 1: raise
            time.sleep(5 * (i + 1))

def get(url, chave=None):
    try:
        time.sleep(0.25)
        js = json.loads(baixar(url, 2) or 'null')
        if chave and chave not in amostra: amostra[chave] = {'url': url, 'resposta': js[:3] if isinstance(js, list) else js}
        return js
    except Exception as ex:
        log.append(f'{url}: {ex}'); return None

def tabela(nome, ano):
    """Linhas de um CSV anual da Câmara (lista vazia se não existir)."""
    url = f'{ARQ}{nome}/csv/{nome}-{ano}.csv'
    try:
        linhas = list(csv.DictReader(io.StringIO(baixar(url)), delimiter=';'))
    except Exception as ex:
        log.append(f'{nome} {ano}: {ex}'); return []
    if f'{nome}-cab' not in amostra and linhas: amostra[f'{nome}-cab'] = {'url': url, 'colunas': list(linhas[0].keys()), 'exemplo': linhas[0]}
    return linhas

def col(r, *nomes):
    for n in nomes:
        if n in r and r[n] not in (None, ''): return str(r[n]).strip()
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

def listas(o, chave):
    out = []
    if isinstance(o, list):
        if o and isinstance(o[0], dict) and chave in o[0]: out.append(o)
        for v in o: out += listas(v, chave)
    elif isinstance(o, dict):
        for v in o.values(): out += listas(v, chave)
    return out

def br(iso):
    return f'{iso[8:10]}/{iso[5:7]}/{iso[:4]}' if len(iso) >= 10 else iso

# ---------- título curto a partir da ementa ----------
def titulo(ementa, sigla):
    e = re.sub(r'\s+', ' ', ementa or '').strip()
    if not e: return ''
    m = re.match(r'^(Altera|Acrescenta|Modifica|Revoga|Dá nova redação|Inclui|Insere)\b.*?\bpara\s+(.+)$', e, re.I)
    if m and len(m.group(2)) > 15 and not re.match(r'^\S+-(l[ao]s?|se|lhes?)\b', m.group(2)): e = m.group(2)
    else:
        m = re.match(r'^Disp(õe|oe) sobre\s+(.+)$', e, re.I)
        if m: e = m.group(2)
    e = re.split(r', e dá outras? providências?', e)[0]
    # corta na primeira frase, sem cortar em abreviações (art., arts., nº, inc., Ltda.)
    m = re.search(r'(?<!\bart)(?<!\barts)(?<!\binc)(?<!\bLtda)(?<!\bn)(?<!\bS\.A)(?<!\b[A-Z])(\.\s|\.$|;)', e)
    if m: e = e[:m.start()]
    e = e.strip().rstrip('.').strip()
    e = e[0].upper() + e[1:] if e else e
    if len(e) > 110:
        e = e[:110].rsplit(' ', 1)[0].rstrip(',;:') + '…'
    return e

# situação da Câmara em palavras simples
SIT = [(r'TRANSFORMAD[OA] EM NORMA', 'Virou norma jurídica'), (r'TRANSFORMADO NA LEI', 'Virou lei'), (r'AGUARDANDO SANCAO', 'Aguarda sanção do presidente'),
       (r'AGUARDANDO PROMULGACAO', 'Aguarda promulgação'), (r'APRECIACAO PELO SENADO', 'Aprovado na Câmara; aguarda o Senado'),
       (r'REMETIDA AO SENADO|ENVIADA AO SENADO', 'Aprovado na Câmara; enviado ao Senado'), (r'ARQUIVAD', 'Arquivado'),
       (r'PERDEU A EFICACIA|PERDA DE EFICACIA|VIGENCIA ENCERRADA|PRAZO DE VIGENCIA', 'MP perdeu a validade'),
       (r'PRONTA PARA PAUTA NO PLENARIO|PRONTA PARA PAUTA EM PLENARIO', 'Pronto para votação no Plenário da Câmara'),
       (r'AGUARDANDO DELIBERACAO DE RECURSO', 'Aguarda recurso na Câmara'), (r'AGUARDANDO PARECER', 'Aguarda parecer em comissão da Câmara'),
       (r'AGUARDANDO DESIGNACAO DE RELATOR', 'Aguarda relator em comissão da Câmara'), (r'TRAMITANDO EM CONJUNTO', 'Tramita junto com outra proposta na Câmara'),
       (r'AGUARDANDO DESPACHO', 'Aguardando despacho na Câmara'), (r'AGUARDANDO VOTACAO', 'Aguarda votação na Câmara'),
       (r'RETIRAD[OA] PELO AUTOR', 'Retirado pelo autor'), (r'DEVOLVID', 'Devolvido ao autor'), (r'VETAD|VETO TOTAL', 'Vetado'),
       (r'AGUARDANDO APRECIACAO|AGUARDANDO DELIBERACAO|EM TRAMITACAO', 'Em tramitação na Câmara')]
def capfix(t):
    for a, b in [('câmara dos deputados', 'Câmara dos Deputados'), ('senado federal', 'Senado Federal'), ('congresso nacional', 'Congresso Nacional'),
                 ('presidente da república', 'presidente da República'), ('senado', 'Senado'), ('câmara', 'Câmara')]:
        t = re.sub(r'\b' + a + r'\b', b, t)
    return t
def frase(t):
    t = (t or '').strip()
    return capfix(t[:1].upper() + t[1:].lower()) if t else ''
def situacao(t):
    n = norm(t)
    for re_, txt in SIT:
        if re.search(re_, n): return txt
    return frase(t) or 'Não informado'

# ---------- votações do Plenário da Câmara ----------
IMPORTANTE = re.compile(r'(APROVAD[OA]|REJEITAD[OA]).{0,40}(PROPOSTA|PROJETO|MEDIDA PROVISORIA|SUBSTITUTIVO|PARECER|REDACAO FINAL|EMENDA AGLUTINATIVA|PRIMEIRO TURNO|SEGUNDO TURNO|URGENCIA)'
                        r'|EM (PRIMEIRO|SEGUNDO) TURNO')
FORA = re.compile(r'DESTAQUE|MANTIDO O TEXTO|REQUERIMENTO DE (RETIRADA|ADIAMENTO|ENCERRAMENTO|VOTACAO POR PARTES|QUEBRA)|PRORROGACAO|EMENDA N|EMENDAS? DE PLENARIO|EMENDAS? DO SENADO N|SUPRESSIV|ADITIV|MODIFICATIV|ENCERRAMENTO DA DISCUSSAO|PREFERENCIA')
def peso(desc):
    n = norm(desc)
    if FORA.search(n) and not re.search(r'PRIMEIRO TURNO|SEGUNDO TURNO|SUBSTITUTIVO|RESSALVAD', n): return 0
    if not IMPORTANTE.search(n): return 0
    if re.search(r'URGENCIA', n): return 1
    if re.search(r'REDACAO FINAL|PARECER', n): return 2
    return 3
def placar(v):
    sim, nao = int(v['sim'] or 0), int(v['nao'] or 0)
    m = re.search(r'SIM:\s*(\d+)\D+NAO:\s*(\d+)', norm(v['desc']))
    if not (sim or nao) and m: sim, nao = int(m.group(1)), int(m.group(2))
    return sim, nao

anos_leg = list(range(ano0, HOJE.year + 1))
votacoes = {}
for ano in anos_leg:
    for r in tabela('votacoes', ano):
        if col(r, 'siglaOrgao') != 'PLEN': continue
        d = col(r, 'data')[:10]
        if not (INICIO_LEG <= d <= FIM): continue
        votacoes[col(r, 'id')] = {'d': d, 'h': col(r, 'dataHoraRegistro')[11:16], 'desc': col(r, 'descricao'),
                                  'ap': col(r, 'aprovacao'), 'sim': col(r, 'votosSim'), 'nao': col(r, 'votosNao')}
alvo = {}   # id da proposição → lista de votações
def liga(pid, sigla, vid):
    if sigla not in TIPOS or not pid or vid not in votacoes: return
    lst = alvo.setdefault(pid, [])
    if vid not in lst: lst.append(vid)
for ano in anos_leg:
    for nome in ('votacoesObjetos', 'votacoesProposicoes'):
        for r in tabela(nome, ano):
            liga(col(r, 'proposicao_id', 'idProposicao'), col(r, 'proposicao_siglaTipo', 'siglaTipo'), col(r, 'idVotacao', 'id'))
print(f'Câmara: {len(votacoes)} votações no Plenário, {len(alvo)} proposições votadas', flush=True)

# ---------- proposições (anos do mandato e anteriores, quando votadas agora) ----------
props, autores = {}, {}
def guarda(r):
    pid = col(r, 'id')
    props[pid] = {'id': pid, 's': col(r, 'siglaTipo'), 'n': col(r, 'numero'), 'a': col(r, 'ano'), 'e': col(r, 'ementa'),
                  'ap': col(r, 'dataApresentacao')[:10], 'st': col(r, 'ultimoStatus_descricaoSituacao', 'statusProposicao_descricaoSituacao'),
                  'std': col(r, 'ultimoStatus_dataHora', 'statusProposicao_dataHora')[:10],
                  'tram': col(r, 'ultimoStatus_descricaoTramitacao', 'statusProposicao_descricaoTramitacao'),
                  'teor': col(r, 'urlInteiroTeor')}
for ano in range(HOJE.year, 2002, -1):
    precisa = ano >= ano0
    linhas = tabela('proposicoes', ano)
    for r in linhas:
        s, pid = col(r, 'siglaTipo'), col(r, 'id')
        if s not in TIPOS: continue
        std = col(r, 'ultimoStatus_dataHora', 'statusProposicao_dataHora')[:10]
        norma = 'NORMA JURIDICA' in norm(col(r, 'ultimoStatus_descricaoSituacao', 'statusProposicao_descricaoSituacao')) and std >= INICIO
        if pid in alvo or norma or (precisa and s == 'MPV'): guarda(r)
        if norma: alvo.setdefault(pid, [])
    # autores: só dos anos que têm proposições guardadas
    if any(p['a'] == str(ano) for p in props.values()) or precisa:
        for r in tabela('proposicoesAutores', ano):
            pid = col(r, 'idProposicao')
            if precisa and pid not in props:
                # propostas do Poder Executivo apresentadas no mandato
                if norm(col(r, 'nomeAutor')) == 'PODER EXECUTIVO' and col(r, 'siglaTipo', 'proposicao_siglaTipo') in TIPOS | {''}:
                    autores.setdefault(pid, []).append(r)
                continue
            if pid in props: autores.setdefault(pid, []).append(r)
    del linhas
# propostas do Executivo do mandato que não estavam guardadas: lê de novo os anos do mandato
faltam = {pid for pid, rs in autores.items() if pid not in props and any(norm(col(x, 'nomeAutor')) == 'PODER EXECUTIVO' for x in rs)}
if faltam:
    for ano in anos_leg:
        for r in tabela('proposicoes', ano):
            if col(r, 'id') in faltam and col(r, 'siglaTipo') in TIPOS: guarda(r)
# votadas no mandato mas apresentadas antes de 2003: API
for pid in [p for p in alvo if p not in props][:300]:
    js = get(f'{API}proposicoes/{pid}', 'camara-proposicao')
    d = (js or {}).get('dados') or {}
    if not d: continue
    st = d.get('statusProposicao') or {}
    props[pid] = {'id': pid, 's': d.get('siglaTipo', ''), 'n': str(d.get('numero', '')), 'a': str(d.get('ano', '')), 'e': d.get('ementa', ''),
                  'ap': (d.get('dataApresentacao') or '')[:10], 'st': st.get('descricaoSituacao', ''), 'std': (st.get('dataHora') or '')[:10],
                  'tram': st.get('descricaoTramitacao', ''), 'teor': d.get('urlInteiroTeor', '')}
print(f'Câmara: {len(props)} proposições guardadas', flush=True)

def autoria(pid):
    rs = sorted(autores.get(pid, []), key=lambda x: int(col(x, 'ordemAssinatura') or 99))
    if not rs: return 'Não informado'
    r = rs[0]; nome = col(r, 'nomeAutor')
    if norm(nome) == 'PODER EXECUTIVO': return 'Poder Executivo'
    p, uf = col(r, 'siglaPartidoAutor'), col(r, 'siglaUFAutor')
    tipo = norm(col(r, 'tipoAutor'))
    pre = 'Dep. ' if 'DEPUTAD' in tipo else 'Sen. ' if 'SENADOR' in tipo else ''
    out = pre + nome + (f' ({p}-{uf})' if p and uf else f' ({p})' if p else '')
    return out + (f' e outros' if len(rs) > 1 else '')

def slug(s, n, a): return f'{s.lower()}-{int(n)}-{a}' if str(n).isdigit() else f'{s.lower()}-{n}-{a}'

cards = {}
def novo(sl, **kw):
    c = {'house': 'camara', 'type': '', 'code': '', 'title': '', 'summary': '', 'author': 'Não informado', 'rapporteur': 'Não informado',
         'status': 'Não informado', 'steps': [], 'links': [], 'sources': [], 'auto': 1}
    old = cards.get(sl)
    c.update(kw)
    if old:
        # o mesmo número nas duas Casas (PEC do Senado que chega à Câmara, por exemplo): junta as etapas, os links e a votação mais recente
        for st in old['steps']:
            if st not in c['steps']: c['steps'].append(st)
        c['steps'].sort(key=lambda x: x[0])
        fim = [st for st in c['steps'] if 'data do registro na Câmara' in st[1]]
        if len(fim) > 1: c['steps'] = [st for st in c['steps'] if st not in fim[1:]]
        c['links'] += [l for l in old['links'] if l not in c['links']]; c['sources'] += [x for x in old['sources'] if x not in c['sources']]
        if old.get('votes') and (not c.get('votes') or old['votes'].get('_d', '') > c['votes'].get('_d', '')): c['votes'] = old['votes']
        if old['house'] == 'exec': c['house'] = 'exec'
    cards[sl] = c; return c

for pid, p in props.items():
    s, n, a = p['s'], p['n'], p['a']
    if s not in TIPOS or not n or not a: continue
    # outorgas de rádio e TV (centenas por ano, aprovadas sem votação em Plenário) ficam de fora
    if s == 'PDL' and re.search(r'RADIODIFUS|RADIO COMUNIT|SERVICO DE RETRANSMISSAO|SONS E IMAGENS', norm(p['e'])) and not alvo.get(pid): continue
    aut = autoria(pid)
    exe = aut == 'Poder Executivo' or s == 'MPV'
    ficha = f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}'
    st = situacao(p['st'])
    steps = []
    if p['ap']:
        if s == 'MPV': steps.append([p['ap'], 'Presidente edita a MP, publicada no Diário Oficial'])
        elif exe: steps.append([p['ap'], 'Projeto enviado pelo Governo à Câmara'])
        elif norm(aut).startswith('SENADO'): steps.append([p['ap'], 'Chega à Câmara, vinda do Senado'])
        else: steps.append([p['ap'], 'Apresentado na Câmara'])
    vs = sorted((votacoes[v] for v in alvo.get(pid, []) if v in votacoes), key=lambda x: (x['d'], x['h']))
    por_dia = {}
    for v in vs:
        w = peso(v['desc'])
        k = (w, 1 if any(placar(v)) else 0)
        if w and (v['d'] not in por_dia or k >= por_dia[v['d']][0]): por_dia[v['d']] = (k, v)
    principais = [v for _, v in sorted(por_dia.values(), key=lambda x: (x[1]['d'], x[1]['h']))]
    for v in principais:
        txt = re.sub(r'\s+', ' ', v['desc']).strip().rstrip('.')
        steps.append([v['d'], f'Câmara: {txt[:200]}'])
    # fim do caminho, pela situação atual
    sn = norm(p['st'])
    if p['std']:
        if 'NORMA JURIDICA' in sn:
            if s == 'PEC': steps.append([p['std'], 'Congresso promulga a emenda constitucional (data do registro na Câmara)'])
            elif s == 'PDL': steps.append([p['std'], 'Congresso promulga o decreto legislativo (data do registro na Câmara)'])
            else: steps.append([p['std'], 'Sancionado; vira lei (data do registro na Câmara)'])
            st = 'Emenda promulgada' if s == 'PEC' else 'Promulgado' if s == 'PDL' else 'Sancionado; virou lei'
        elif 'SANCAO' in sn: steps.append([p['std'], 'Câmara envia o texto à sanção do presidente'])
        elif 'SENADO' in sn and 'APRECIACAO' in sn: steps.append([p['std'], 'Câmara: segue ao Senado'])
        elif re.search(r'PERD|VIGENCIA ENCERRADA', sn): steps.append([p['std'], 'Congresso: MP perde a validade'])
        elif 'ARQUIVAD' in sn: steps.append([p['std'], 'Câmara: arquivado'])
    # sem nada além da apresentação e fora do mandato: não entra
    if not (p['ap'] >= INICIO or principais or ('NORMA JURIDICA' in sn and p['std'] >= INICIO)): continue
    steps.sort(key=lambda x: x[0])
    votes = None
    if principais:
        # a última votação principal; se ela não tem placar e uma anterior do mesmo peso tem, mostra a que tem números
        fortes = [x for x in principais if peso(x['desc']) == 3]
        com = [x for x in fortes if any(placar(x))]
        v = com[-1] if com else fortes[-1] if fortes else principais[-1]
        sim, nao = placar(v)
        dn = norm(v['desc'])
        res = re.split(r'\.\s*Sim:|\. Sim|\.\s*$', re.sub(r'\s+', ' ', v['desc']).strip(), flags=re.I)[0].strip()
        if len(res) > 120: res = res[:120].rsplit(' ', 1)[0] + '…'
        if not res: res = 'Rejeitado' if 'REJEITAD' in dn else 'Aprovado' if ('APROVAD' in dn or v['ap'] == '1') else 'Não informado'
        if not (sim or nao) and 'UNANIMIDADE' in dn and 'unanimidade' not in res.lower(): res += ' por unanimidade'
        votes = {'label': f'Câmara · Plenário, {br(v["d"])}', 'result': res, '_d': v['d']}
        if sim or nao: votes['tally'] = [['Votação', sim, nao]]
        else: votes['note'] = 'Placar não divulgado nos dados abertos (votação simbólica ou sem registro nominal).'
    links = [{'l': 'Ficha de tramitação na Câmara', 'u': ficha}]
    if p['teor']: links.append({'l': 'Texto original (PDF)', 'u': p['teor']})
    c = novo(slug(s, n, a), house='exec' if exe else 'camara', type=NOME_TIPO[s], code=f'{"MP" if s == "MPV" else s} {n}/{a}',
             title=titulo(p['e'], s) or f'{NOME_TIPO[s]} {n}/{a}', summary=('Ementa oficial: ' + p['e']) if p['e'] else 'Não informado',
             author=aut, status=st, steps=steps, links=links,
             sources=[{'l': f'Dados abertos da Câmara dos Deputados: {s} {n}/{a}', 'u': ficha}])
    if votes: c['votes'] = votes
print(f'Câmara: {len(cards)} cartões', flush=True)

# ---------- Senado: votações do Plenário ----------
sen_vot = []
d0 = datetime.date.fromisoformat(INICIO_LEG)
while d0 <= HOJE:
    d1 = min(HOJE, (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1))
    js = get(f'{SEN}votacao?' + urllib.parse.urlencode({'dataInicio': d0.isoformat(), 'dataFim': d1.isoformat()}), 'senado-votacao')
    lst = js if isinstance(js, list) else (listas(js, 'codigoSessaoVotacao') or [[]])[0] if js else []
    sen_vot += [x for x in lst if isinstance(x, dict)]
    d0 = d1 + datetime.timedelta(days=1)
print(f'Senado: {len(sen_vot)} votações', flush=True)

def ident(v):
    s = achar(v, 'sigla', 'siglaMateria', 'SiglaMateria', 'siglaTipoMateria'); n = achar(v, 'numero', 'numeroMateria', 'NumeroMateria'); a = achar(v, 'ano', 'anoMateria', 'AnoMateria')
    if not (s and n and a):
        m = re.search(r'\b([A-Z]{2,4})\s+(\d+)/(\d{4})', str(achar(v, 'identificacao', 'identificacaoMateria', 'materia') or ''))
        if m: s, n, a = m.groups()
    if not (s and n and a): return None
    return SIGLA_SEN.get(str(s).upper().strip()), str(int(str(n))) if str(n).isdigit() else str(n), str(a)

sen_info = {}
for v in sen_vot:
    idt = ident(v)
    if not idt or not idt[0]: continue
    s, n, a = idt
    data = str(achar(v, 'dataSessao', 'dataHoraInicio', 'data') or '')[:10]
    if not (INICIO_LEG <= data <= FIM): continue
    desc = re.sub(r'\s+', ' ', str(achar(v, 'descricaoVotacao', 'descricao') or '')).strip().rstrip('.')
    lista = v.get('votos') or []
    vals = [norm(achar(x, 'siglaVotoParlamentar', 'descricaoVotoParlamentar', 'voto') or '') for x in lista]
    sim = achar(v, 'totalVotosSim', 'votosSim'); nao = achar(v, 'totalVotosNao', 'votosNao')
    sim = int(sim) if str(sim or '').isdigit() else sum(x == 'SIM' for x in vals)
    nao = int(nao) if str(nao or '').isdigit() else sum(x in ('NAO',) for x in vals)
    res = norm(achar(v, 'resultadoVotacao', 'resultado', 'descricaoResultado') or '')
    res = 'Aprovado' if res.startswith('A') else 'Rejeitado' if res.startswith('R') else ('Aprovado' if sim > nao else 'Rejeitado' if nao > sim else 'Não informado')
    cod = achar(v, 'codigoMateria', 'CodigoMateria')
    dn = norm(desc)
    principal = not re.search(r'DESTACAD|DESTAQUE|REQUERIMENTO(?!.*URGENCIA)|ADIAMENTO|CALENDARIO ESPECIAL|EMENDA N\S*\s*\d+(?!.*SUBSTITUTIVO)|ART\. \d+ D|CAPITULO|DISPOSITIVO', dn)
    sen_info.setdefault((s, n, a), []).append({'d': data, 'desc': desc, 'sim': sim, 'nao': nao, 'res': res, 'cod': cod, 'p': principal,
                                               'e': str(v.get('ementa') or ''), 'ap': str(v.get('dataApresentacao') or '')[:10]})

for (s, n, a), todas in sen_info.items():
    todas.sort(key=lambda x: x['d'])
    vs = [x for x in todas if x['p']]
    if not vs:
        x = dict(todas[-1]); x['desc'] = 'votação nominal de destaques ou requerimentos no Plenário'; x['res'] = 'ver a matéria'; x['nv'] = 1; vs = [x]
    sl = slug(s, n, a)
    cod = next((x['cod'] for x in vs if x['cod']), None)
    pag = f'https://www25.senado.leg.br/web/atividade/materias/-/materia/{cod}' if cod else 'https://www25.senado.leg.br/web/atividade/materias'
    c = cards.get(sl)
    if not c:
        pr = get(f'{SEN}processo?' + urllib.parse.urlencode({'sigla': 'PL' if s == 'PL' else s, 'numero': n, 'ano': a}), 'senado-processo')
        info = next((x for x in (pr if isinstance(pr, list) else []) if norm(x.get('identificacao', '')).endswith(f'{n}/{a}')), None) or {}
        e = info.get('ementa') or next((x['e'] for x in todas if x['e']), '')
        ap = (info.get('dataApresentacao') or '')[:10] or next((x['ap'] for x in todas if x['ap']), '')
        c = novo(sl, house='senado', type=NOME_TIPO.get(s, s), code=f'{"MP" if s == "MPV" else s} {n}/{a}',
                 title=((info.get('apelido') or '').strip()[:1].upper() + (info.get('apelido') or '').strip()[1:]) or titulo(e, s) or f'{NOME_TIPO.get(s, s)} {n}/{a}',
                 summary=('Ementa oficial: ' + e) if e else 'Não informado', author=(info.get('autoria') or 'Não informado').strip()[:120],
                 status=frase(info.get('situacaoAtual')) or 'Não informado',
                 steps=[[ap, 'Apresentado no Senado']] if ap else [], links=[{'l': 'Matéria no Senado', 'u': pag}],
                 sources=[{'l': f'Dados abertos do Senado Federal: {s} {n}/{a}', 'u': pag}])
        if c['status'] == 'Não informado' and vs[-1]['res'] != 'Não informado': c['status'] = f'{vs[-1]["res"]} no Plenário do Senado'
    else:
        c['links'].append({'l': 'Matéria no Senado', 'u': pag})
        c['sources'].append({'l': f'Dados abertos do Senado Federal: {s} {n}/{a}', 'u': pag})
    dias = {}
    for x in vs: dias[x['d']] = x
    for x in dias.values():
        if not any(st[0] == x['d'] and st[1].startswith('Senado') for st in c['steps']):
            c['steps'].append([x['d'], f'Senado: {x["desc"][:200] or "votação no Plenário"} ({x["res"].lower()})'])
    c['steps'].sort(key=lambda x: x[0])
    last = vs[-1]
    if last.get('nv'): continue
    if not c.get('votes') or last['d'] >= (re.search(r'(\d{2})/(\d{2})/(\d{4})', c['votes']['label']) and '-'.join(reversed(re.search(r'(\d{2})/(\d{2})/(\d{4})', c['votes']['label']).groups())) or ''):
        c['votes'] = {'label': f'Senado · Plenário, {br(last["d"])}', 'result': last['res'], '_d': last['d']}
        if last['sim'] or last['nao']: c['votes']['tally'] = [['Votação', last['sim'], last['nao']]]
for c in cards.values():
    (c.get('votes') or {}).pop('_d', None)
    for k in ('rapporteur', 'author'):
        if c.get(k) == 'Não informado': del c[k]
print(f'Total: {len(cards)} cartões', flush=True)

# ---------- grava ----------
OUT.mkdir(exist_ok=True)
amostra['_erros'] = log[:60]
(OUT / 'projetos-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1)[:60000], encoding='utf-8')
if len(cards) < 100:
    print('Poucos cartões; arquivo anterior mantido.', log[:10]); sys.exit(0)
(OUT / 'projetos.json').write_text(json.dumps({'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'), 'inicio': INICIO,
                                               'total': len(cards), 'projetos': cards, 'erros': log[:40]},
                                              ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'cartoes': len(cards), 'camara': sum(c['house'] == 'camara' for c in cards.values()),
                  'senado': sum(c['house'] == 'senado' for c in cards.values()), 'exec': sum(c['house'] == 'exec' for c in cards.values()),
                  'com_placar': sum('tally' in (c.get('votes') or {}) for c in cards.values()), 'erros': log[:8]}, ensure_ascii=False))
