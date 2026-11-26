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

def get(url, chave=None, timeout=45):
    try:
        time.sleep(0.2)
        t0 = time.time()
        js = json.loads(baixar(url, 2, timeout) or 'null')
        if time.time() - t0 > 10: print(f'lento ({time.time() - t0:.0f}s): {url}', flush=True)
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
def ORDEM_CARGO(c):
    c = c or ''
    if re.match(r'Presidente', c): return 0
    m = re.search(r'(\d)', c) if re.search(r'Vice', c) else None
    return 1 + int(m.group(1)) / 10 if m else 1.9 if re.search(r'Vice', c) else 2
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
    sig = str(c.get('Sigla') or c.get('SiglaColegiado') or '')
    casa = str(c.get('SiglaCasa') or c.get('Casa') or 'SF')
    if not sig or casa not in ('SF', 'Senado Federal') or not re.search(r'PERMANENTE|^CP$', tipo.upper()): continue
    cod = c.get('Codigo') or c.get('CodigoColegiado')
    # comissao/{cod}.json: membros por bloco (nome, partido, UF, titular ou suplente) e a mesa em Cargos
    comp = get(f'{SEN}comissao/{cod}.json', 'senado-comissao')
    sem = lambda n: re.sub(r'^Senadora? ', '', str(n or '')).strip()
    mem, sup, vistos_m = [], [], set()
    for m in achar_listas(comp, 'Membro'):
        nome = sem(m.get('NomeParlamentar'))
        if not nome or nome.upper() == 'VAGO' or str(m.get('OrigemParlamentar') or 'Senado') != 'Senado': continue
        k = (nome, str(m.get('TipoVaga')))
        if k in vistos_m: continue
        vistos_m.add(k)
        x = [nome, m.get('Partido') or '', m.get('SiglaUf') or '', 'Titular']
        (sup if re.search(r'Suplente', str(m.get('TipoVaga') or ''), re.I) else mem).append(x)
    for car in achar_listas(comp, 'Cargo'):
        nome, desc = sem(car.get('NomeParlamentar')), str(car.get('TipoCargo') or '')
        desc = desc.capitalize().replace('Vice-presidente', 'Vice-Presidente')
        for x in mem:
            if x[0] == nome and desc: x[3] = desc
    mem.sort(key=lambda x: (ORDEM_CARGO(x[3]), x[0]))
    sup.sort(key=lambda x: x[0])
    senado.append({'sigla': sig, 'nome': c.get('Nome') or c.get('NomeColegiado') or sig, 'id': cod,
                   'url': f'https://legis.senado.leg.br/comissoes/comissao?codcol={cod}', 'membros': mem, 'suplentes': sup, 'itens': []})
por_sig_s = {c['sigla']: c for c in senado}
# pautas das reuniões, mês a mês
d0, vistos = D0, set()
while d0 <= HOJE:
    d1 = min(HOJE, (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1))
    ag = get(f"{SEN}comissao/agenda/{d0.strftime('%Y%m%d')}/{d1.strftime('%Y%m%d')}.json", 'senado-agenda')
    d0 = d1 + datetime.timedelta(days=1)
    for r in achar_listas(ag, 'reuniao') + achar_listas(ag, 'Reuniao'):
        if not isinstance(r, dict): continue
        cc = r.get('colegiadoCriador') or r.get('colegiados') or {}
        if isinstance(cc, list): cc = cc[0] if cc else {}
        sig = str(cc.get('sigla') or '')
        if sig not in por_sig_s: continue
        data = str(r.get('dataInicio') or r.get('Data') or '')[:10]
        if 'senado-reuniao-inteira' not in amostra and re.search(r'"(sigla|siglaMateria)": ?"(PL|PEC|PLP|PDL|MPV)"', json.dumps(r.get('partes'), ensure_ascii=False)):
            amostra['senado-reuniao-inteira'] = json.dumps(r.get('partes'), ensure_ascii=False)[:15000]
        def anda(o, pai=None):
            if isinstance(o, list):
                for x in o: anda(x, pai)
            elif isinstance(o, dict):
                low = {k.lower(): v for k, v in o.items()}
                sg = str(low.get('sigla') or low.get('siglamateria') or low.get('siglasubtipo') or '').upper()
                nu, an = low.get('numero') or low.get('numeromateria'), low.get('ano') or low.get('anomateria')
                ident = str(low.get('identificacao') or low.get('descricaoidentificacao') or '')
                m = re.search(r'\b(PL|PLS|PLC|PLP|PEC|MPV|PDL|PDS|PLN)\s+(\d+)/(\d{4})', ident)
                hit = None
                if sg in TIPOS | {'PLC'} and nu and an and str(nu).strip().isdigit(): hit = (sg, str(int(str(nu).strip())), str(an)[:4])
                elif m: hit = (m.group(1), str(int(m.group(2))), m.group(3))
                if hit:
                    k = (sig,) + hit + (data,)
                    if k not in vistos:
                        vistos.add(k)
                        par = {kk.lower(): vv for kk, vv in (pai or {}).items()} if isinstance(pai, dict) else {}
                        desc = str(low.get('ementa') or par.get('ementa') or low.get('descricao') or '')[:220]
                        if re.match(r'(Emenda|Requerimento|Parecer)\b', desc): desc = ''
                        res = str(par.get('resultado') or par.get('descricaoresultado') or low.get('resultado') or par.get('situacao') or '')
                        if isinstance(par.get('resultado'), dict): res = str(par['resultado'].get('descricao') or '')
                        por_sig_s[sig]['itens'].append({'data': data, 'slug': slug(*hit), 'code': f'{hit[0]} {hit[1]}/{hit[2]}', 'desc': desc, 'res': res[:80]})
                    return
                for v in o.values(): anda(v, o)
        anda(r.get('partes'))
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
