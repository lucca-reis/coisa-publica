"""Comissões permanentes da Câmara e do Senado: quem as compõe hoje (titulares e suplentes, com partido e estado,
presidente e vice) e o que cada uma votou nos últimos 12 meses.

Fontes (dados abertos, sem chave):
  Câmara  https://dadosabertos.camara.leg.br/api/v2/orgaos  (lista e membros)
          arquivos anuais votacoes, votacoesObjetos e votacoesProposicoes  (o que cada comissão votou)
  Senado  https://legis.senado.leg.br/dadosabertos/comissao/lista/colegiados  (lista)
          https://legis.senado.leg.br/dadosabertos/composicao/comissao/{código}  (membros)
          https://legis.senado.leg.br/dadosabertos/comissao/agenda/{início}/{fim}  (reuniões e o que entrou em pauta)

Grava data/comissoes.json:
  {"atualizado", "camara": [comissão...], "senado": [...]}
  comissão = {"sigla","nome","id","url","membros":[[nome, partido, uf, cargo]...] (titulares e cargos da mesa primeiro),
              "suplentes": [...], "itens":[{"data","slug","code","desc","res"}...] (mais recentes primeiro, até 60)}
Não grava se vierem menos de 15 comissões numa das Casas. data/comissoes-amostra.json guarda exemplos das respostas.
Só usa a biblioteca padrão."""
import csv, io, json, re, sys, time, datetime, zoneinfo, pathlib, urllib.request, urllib.parse

BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
D0 = HOJE - datetime.timedelta(days=365)
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data'
CAM = 'https://dadosabertos.camara.leg.br/api/v2/'
ARQ = 'https://dadosabertos.camara.leg.br/arquivos/'
SEN = 'https://legis.senado.leg.br/dadosabertos/'
UA = {'User-Agent': 'coisa-publica (coisapublica.io)', 'Accept': 'application/json'}
TIPOS = {'PL', 'PLP', 'PEC', 'MPV', 'PDL', 'PLS', 'PDS', 'PLN'}
log, amostra = [], {}

def baixar(url, tent=3, timeout=120):
    for i in range(tent):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read().decode('utf-8-sig', 'replace')
        except Exception as ex:
            if i == tent - 1: raise
            time.sleep(4 * (i + 1))

def get(url, chave=None):
    try:
        time.sleep(0.2)
        js = json.loads(baixar(url, 2) or 'null')
        if chave and chave not in amostra: amostra[chave] = {'url': url, 'resposta': cortar(js)}
        return js
    except Exception as ex:
        log.append(f'{url}: {ex}'); return None

def cortar(o, n=0):
    if n > 6: return '…'
    if isinstance(o, list): return [cortar(x, n + 1) for x in o[:3]]
    if isinstance(o, dict): return {k: cortar(v, n + 1) for k, v in list(o.items())[:40]}
    return o

def lista(o):
    if o is None: return []
    return o if isinstance(o, list) else [o]

def achar_listas(o, chave):
    """todas as listas (ou objetos únicos) guardadas sob 'chave' em qualquer nível"""
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k == chave: out += lista(v)
            else: out += achar_listas(v, chave)
    elif isinstance(o, list):
        for v in o: out += achar_listas(v, chave)
    return out

def slug(s, n, a):
    s = {'PLS': 'PL', 'PLC': 'PL', 'PDS': 'PDL', 'PDC': 'PDL', 'PLN': 'PL'}.get(s, s)
    return f'{s.lower()}-{int(n)}-{a}' if str(n).isdigit() else ''

def tabela(nome, ano):
    url = f'{ARQ}{nome}/csv/{nome}-{ano}.csv'
    try:
        return list(csv.DictReader(io.StringIO(baixar(url, timeout=300)), delimiter=';'))
    except Exception as ex:
        log.append(f'{nome} {ano}: {ex}'); return []

# ---------------- Câmara ----------------
camara = []
orgs = []
for tipo in (2,):   # 2 = comissão permanente
    js = get(f'{CAM}orgaos?codTipoOrgao={tipo}&itens=100&ordem=ASC&ordenarPor=sigla', 'camara-orgaos')
    orgs += (js or {}).get('dados', [])
ORDEM_CARGO = lambda c: 0 if re.match(r'Presidente', c or '') else 1 if re.search(r'Vice', c or '') else 2
for o in orgs:
    sig = o.get('sigla') or ''
    if not sig or o.get('dataFim'): continue
    js = get(f"{CAM}orgaos/{o['id']}/membros?dataInicio={HOJE.isoformat()}&itens=200", 'camara-membros')
    mem, sup = [], []
    for m in (js or {}).get('dados', []):
        if m.get('dataFim') and m['dataFim'][:10] < HOJE.isoformat(): continue
        x = [m.get('nome') or '', m.get('siglaPartido') or '', m.get('siglaUf') or '', m.get('titulo') or '']
        (sup if re.search(r'Suplente', x[3] or '', re.I) else mem).append(x)
    mem.sort(key=lambda x: (ORDEM_CARGO(x[3]), x[0]))
    sup.sort(key=lambda x: x[0])
    camara.append({'sigla': sig, 'nome': o.get('nome') or o.get('apelido') or sig, 'id': o['id'],
                   'url': f"https://www.camara.leg.br/comissoes/{o['id']}" if False else (o.get('urlWebsite') or f"https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-permanentes/{sig.lower()}"),
                   'membros': mem, 'suplentes': sup, 'itens': []})
# o que cada comissão votou: arquivos anuais
por_sig = {c['sigla']: c for c in camara}
vot = {}
for ano in sorted({D0.year, HOJE.year}):
    for r in tabela('votacoes', ano):
        s = (r.get('siglaOrgao') or '').strip()
        d = (r.get('data') or '')[:10]
        if s in por_sig and d >= D0.isoformat():
            vot[r.get('id')] = {'sig': s, 'data': d, 'desc': (r.get('descricao') or '').strip()[:200],
                                'res': 'Aprovado' if r.get('aprovacao') == '1' else 'Rejeitado' if r.get('aprovacao') == '0' else ''}
vistos = set()
for ano in sorted({D0.year, HOJE.year}):
    for nome in ('votacoesObjetos', 'votacoesProposicoes'):
        for r in tabela(nome, ano):
            v = vot.get(r.get('idVotacao'))
            s, n, a = (r.get('proposicao_siglaTipo') or '').strip(), (r.get('proposicao_numero') or '').strip(), (r.get('proposicao_ano') or '').strip()
            if not v or s not in TIPOS or not (n and a): continue
            k = (v['sig'], s, n, a, v['data'])
            if k in vistos: continue
            vistos.add(k)
            por_sig[v['sig']]['itens'].append({'data': v['data'], 'slug': slug(s, n, a), 'code': f'{s} {n}/{a}',
                                               'desc': (r.get('proposicao_ementa') or v['desc'])[:220], 'res': v['res']})
print(f'Câmara: {len(camara)} comissões, {len(vot)} votações em comissão', flush=True)

# ---------------- Senado ----------------
senado = []
js = get(f'{SEN}comissao/lista/colegiados.json', 'senado-colegiados')
cols = achar_listas(js, 'Colegiado')
for c in cols:
    tipo = str(c.get('SiglaTipoColegiado') or c.get('TipoColegiado') or c.get('DescricaoTipoColegiado') or '')
    sig = str(c.get('SiglaColegiado') or '')
    casa = str(c.get('SiglaCasa') or c.get('Casa') or 'SF')
    if not sig or casa not in ('SF', 'Senado Federal') or not re.search(r'PERMANENTE|^CP$', tipo.upper()): continue
    cod = c.get('CodigoColegiado')
    comp = get(f'{SEN}composicao/comissao/{cod}.json', 'senado-composicao')
    mem, sup = [], []
    for m in achar_listas(comp, 'Membro'):
        nome = m.get('NomeParlamentar') or (m.get('IdentificacaoParlamentar') or {}).get('NomeParlamentar') or ''
        if not nome: continue
        part = m.get('SiglaPartidoParlamentar') or (m.get('IdentificacaoParlamentar') or {}).get('SiglaPartidoParlamentar') or ''
        uf = m.get('UfParlamentar') or (m.get('IdentificacaoParlamentar') or {}).get('UfParlamentar') or ''
        cargo = str(m.get('DescricaoParticipacao') or m.get('TipoVaga') or '')
        x = [nome, part, uf, cargo]
        (sup if re.search(r'Suplente', cargo, re.I) else mem).append(x)
    for car in achar_listas(comp, 'Cargo'):
        nome = car.get('NomeParlamentar') or ''
        desc = str(car.get('DescricaoCargo') or '')
        for x in mem:
            if x[0] == nome and desc: x[3] = desc.title() if desc.isupper() else desc
    mem.sort(key=lambda x: (ORDEM_CARGO(x[3]), x[0]))
    sup.sort(key=lambda x: x[0])
    senado.append({'sigla': sig, 'nome': c.get('NomeColegiado') or sig, 'id': cod,
                   'url': f'https://legis.senado.leg.br/comissoes/comissao?codcol={cod}', 'membros': mem, 'suplentes': sup, 'itens': []})
por_sig_s = {c['sigla']: c for c in senado}
# pautas das reuniões, mês a mês
d0, vistos = D0, set()
while d0 <= HOJE:
    d1 = min(HOJE, (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1))
    ag = get(f"{SEN}comissao/agenda/{d0.strftime('%Y%m%d')}/{d1.strftime('%Y%m%d')}.json", 'senado-agenda')
    d0 = d1 + datetime.timedelta(days=1)
    for r in achar_listas(ag, 'Reuniao'):
        sig = ''
        for k in ('SiglaComissao', 'Sigla', 'SiglaColegiado'):
            v = r.get(k) or (r.get('Comissoes') or {}).get(k) if isinstance(r, dict) else None
            if v: sig = str(v); break
        if not sig:
            cs = achar_listas(r, 'Comissao')
            if cs and isinstance(cs[0], dict): sig = str(cs[0].get('Sigla') or cs[0].get('SiglaComissao') or '')
        if sig not in por_sig_s: continue
        data = str(r.get('Data') or r.get('DataReuniao') or r.get('dataInicio') or '')[:10]
        if '/' in data: dd, mm, aa = data.split('/'); data = f'{aa}-{mm}-{dd}'
        for it in achar_listas(r, 'Item') + achar_listas(r, 'Materia'):
            if not isinstance(it, dict): continue
            ident = str(it.get('Identificacao') or it.get('DescricaoIdentificacao') or it.get('IdentificacaoMateria') or '')
            m = re.search(r'\b(PL|PLS|PLC|PLP|PEC|MPV|PDL|PDS|PLN)\s+(\d+)/(\d{4})', ident)
            if not m:
                s0, n0, a0 = it.get('Sigla') or it.get('SiglaMateria'), it.get('Numero') or it.get('NumeroMateria'), it.get('Ano') or it.get('AnoMateria')
                if not (s0 and n0 and a0): continue
                m = re.match(r'(\w+)\s+(\d+)/(\d{4})', f'{s0} {int(str(n0))}/{a0}')
                if not m: continue
            s, n, a = m.group(1), str(int(m.group(2))), m.group(3)
            k = (sig, s, n, a, data)
            if k in vistos: continue
            vistos.add(k)
            desc = str(it.get('Ementa') or it.get('EmentaMateria') or it.get('Descricao') or '')[:220]
            res = str(it.get('Resultado') or it.get('DescricaoResultado') or it.get('Decisao') or '')[:80]
            por_sig_s[sig]['itens'].append({'data': data, 'slug': slug(s, n, a), 'code': f'{s} {n}/{a}', 'desc': desc, 'res': res})
print(f'Senado: {len(senado)} comissões', flush=True)

for c in camara + senado:
    c['itens'] = sorted(c['itens'], key=lambda x: x['data'], reverse=True)[:60]
amostra['_erros'] = log[:60]
(OUT / 'comissoes-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1)[:60000], encoding='utf-8')
resumo = {'camara': [(c['sigla'], len(c['membros']), len(c['suplentes']), len(c['itens'])) for c in camara],
          'senado': [(c['sigla'], len(c['membros']), len(c['suplentes']), len(c['itens'])) for c in senado], 'erros': log[:8]}
print(json.dumps(resumo, ensure_ascii=False))
if len(camara) < 15 or len(senado) < 10:
    print('Poucas comissões; arquivo anterior mantido.'); sys.exit(0)
(OUT / 'comissoes.json').write_text(json.dumps({'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'),
                                                'camara': camara, 'senado': senado}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
