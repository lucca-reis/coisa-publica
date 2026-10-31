"""Dados do Executivo no Portal da Transparência (CGU): cartão de pagamento da Presidência, da
Vice-Presidência e de cada ministério nos últimos 12 meses.

Usa a API oficial (https://api.portaldatransparencia.gov.br/swagger-ui/index.html), que exige uma chave
gratuita. A chave fica no segredo PORTAL_TRANSPARENCIA_KEY do GitHub e nunca vai para o repositório.
Grava data/transparencia/exec.json. Roda uma vez por dia (.github/workflows/transparencia.yml).

A primeira versão também grava amostras das respostas em data/transparencia/exec-amostra.json, para conferir
o formato de cada endpoint (são dados públicos; a chave não aparece nelas)."""
import json, os, re, sys, time, datetime, zoneinfo, pathlib, unicodedata, urllib.request, urllib.parse

KEY = os.environ.get('PORTAL_TRANSPARENCIA_KEY', '').strip()
if not KEY:
    print('Sem chave do Portal da Transparência; nada a fazer.'); sys.exit(0)

API = 'https://api.portaldatransparencia.gov.br/api-de-dados/'
BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'transparencia'
log, amostra = [], {}
chamadas = 0

def get(path, **q):
    global chamadas
    url = API + path + ('?' + urllib.parse.urlencode(q) if q else '')
    for n in range(3):
        try:
            req = urllib.request.Request(url, headers={'chave-api-dados': KEY, 'Accept': 'application/json',
                                                       'User-Agent': 'quorum (github.com/lucca-reis/quorum)'})
            time.sleep(0.5); chamadas += 1
            with urllib.request.urlopen(req, timeout=60) as r:
                js = json.loads(r.read().decode('utf-8') or 'null')
            if path not in amostra: amostra[path] = {'params': q, 'resposta': js[:2] if isinstance(js, list) else js}
            return js
        except urllib.error.HTTPError as ex:
            if ex.code == 429: time.sleep(30); continue
            corpo = ''
            try: corpo = ex.read().decode('utf-8', 'replace')[:300]
            except Exception: pass
            log.append(f'{path} {q}: HTTP {ex.code} {corpo}'); return None
        except Exception as ex:
            if n == 2: log.append(f'{path} {q}: {ex}'); return None
            time.sleep(5)

def paginas(path, limite=40, **q):
    out = []
    for p in range(1, limite + 1):
        js = get(path, pagina=p, **q)
        if not js: break
        out += js
        if len(js) < 15: break
    return out

def norm(t):
    t = unicodedata.normalize('NFD', str(t or ''))
    return re.sub(r'\s+', ' ', ''.join(c for c in t if not unicodedata.combining(c))).upper().strip()

def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', norm(t).lower()).strip('-')

def valor(v):
    if isinstance(v, (int, float)): return float(v)
    t = str(v or '').strip()
    if ',' in t: t = t.replace('.', '').replace(',', '.')
    try: return float(t)
    except ValueError: return 0.0

def dig(o, *ks):
    for k in ks:
        if not isinstance(o, dict): return None
        o = o.get(k)
    return o

MESES = []
d = HOJE.replace(day=1)
for _ in range(12):
    MESES.append(d)
    d = (d - datetime.timedelta(days=1)).replace(day=1)
MESES.reverse()

# ---------- quem é quem: presidente, vice e ministros, lidos do próprio site ----------
html = (ROOT / 'index.html').read_text(encoding='utf-8')
topo = html[html.index('const EXEC_TOP = ['):]
topo = topo[:topo.index('];')]
pessoas = [{'n': n, 'cargo': c} for n, c in re.findall(r"\{n:'([^']+)', role:'([^']+)'", topo)]
bloco = html[html.index('const EXEC_MIN = ['):]
bloco = bloco[:bloco.index('];')]
pessoas += [{'n': n, 'cargo': 'Ministro(a): ' + pasta, 'pasta': pasta} for pasta, n in re.findall(r"\['([^']+)','([^']+)'", bloco)]

# ---------- órgãos: Presidência (20101), Vice-Presidência e ministérios ----------
def lista_orgaos(desc):
    return [{'codigo': str(o.get('codigo')), 'nome': o.get('descricao') or o.get('nome') or ''} for o in (paginas('orgaos-siafi', 15, descricao=desc) or [])]
ORG = {o['codigo']: o for o in lista_orgaos('Presidência') + lista_orgaos('Vice-Presidência') + lista_orgaos('Ministério')}
def acha_orgao(chave, *excluir):
    k = norm(chave)
    for o in ORG.values():
        n = norm(o['nome'])
        if k in n and not any(norm(e) in n for e in excluir): return o
    return None
PRES = ORG.get('20101') or acha_orgao('PRESIDENCIA DA REPUBLICA', 'VICE', 'VINCULO')
VICE = acha_orgao('VICE-PRESIDENCIA')
# pasta do site -> órgão SIAFI do ministério (pelo nome; o que não casar fica sem órgão)
STOP = {'E', 'A', 'DA', 'DE', 'DO', 'DAS', 'DOS', 'EM', 'MINISTERIO'}
def palavras(t):
    t = norm(t).split(' - ')[0]          # tira "- Unidades com vínculo direto"
    return {w for w in re.split(r'[^A-Z]+', t) if w and w not in STOP}
def orgao_da_pasta(pasta):
    """O órgão "Ministério ..." que tem todas as palavras do nome curto da pasta; no empate, o nome mais parecido
    e, depois, o código mais novo. Pastas que são da Presidência (Casa Civil, Secom, GSI...) ficam sem órgão próprio."""
    alvo = palavras(pasta)
    melhor, nota = None, (0, 0)
    for o in sorted(ORG.values(), key=lambda o: o['codigo'], reverse=True):
        n = norm(o['nome'])
        if not n.startswith('MINISTERIO') or 'EXTINCAO' in n or n.startswith('MINISTERIO PUBLICO'): continue
        ws = palavras(o['nome'])
        sc = (len(alvo & ws) / max(1, len(alvo)), len(alvo & ws) / max(1, len(alvo | ws)))
        if sc > nota: melhor, nota = o, sc
    return melhor if nota[0] == 1 else None

def cartao_de(orgao, limite=60):
    if not orgao: return None
    itens, completo = [], True
    for m in MESES:
        mm = m.strftime('%m/%Y')
        pg = paginas('cartoes', limite, mesExtratoInicio=mm, mesExtratoFim=mm, codigoOrgao=orgao['codigo'])
        if len(pg) >= limite * 15: completo = False   # bateu no limite de páginas: o mês pode ter mais gastos
        for x in pg:
            data = str(x.get('dataTransacao') or '')
            iso = None
            for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                try: iso = datetime.datetime.strptime(data[:10], fmt).date().isoformat(); break
                except ValueError: pass
            # sem data da transação (comum nos gastos sigilosos) fica só o mês do extrato
            itens.append({'d': iso, 'm': m.strftime('%Y-%m'), 'v': round(valor(x.get('valorTransacao')), 2),
                          'e': (dig(x, 'estabelecimento', 'nome') or 'Não informado')[:80],
                          'ug': (dig(x, 'unidadeGestora', 'nome') or '')[:80]})
    itens.sort(key=lambda i: i['d'] or i['m'], reverse=True)
    por_mes = {m.strftime('%Y-%m'): 0.0 for m in MESES}
    for i in itens: por_mes[i['m']] = por_mes.get(i['m'], 0) + i['v']
    sig = sum(i['v'] for i in itens if norm(i['e']).startswith('SIGILOS'))
    estab = {}
    for i in itens:
        if not norm(i['e']).startswith('SIGILOS'): estab[i['e']] = estab.get(i['e'], 0) + i['v']
    return {'orgao': orgao, 'total': round(sum(i['v'] for i in itens), 2), 'sigiloso': round(sig, 2), 'transacoes': len(itens), 'completo': completo,
            'estab': [[k, round(v, 2)] for k, v in sorted(estab.items(), key=lambda kv: -kv[1])[:10]],
            'meses': [[m, round(v, 2)] for m, v in por_mes.items()], 'itens': [i for i in itens if not norm(i['e']).startswith('SIGILOS')][:300],
            'fonte': f"https://portaldatransparencia.gov.br/cartoes/consulta?ordenarPor=dataTransacao&direcao=desc&orgaos={orgao['codigo']}"}

cartoes = {}
if PRES: cartoes['presidencia'] = cartao_de(PRES)
if VICE: cartoes['vice'] = cartao_de(VICE)

# ministérios: o cartão de pagamento do órgão de cada pasta (gastos do órgão, não do ministro), com limite de tempo
ministerios, t0 = {}, time.time()
for p in pessoas:
    if not p.get('pasta'): continue
    k = slug(p['pasta'])
    if time.time() - t0 > 20 * 60:
        log.append('ministérios: tempo esgotado em ' + p['pasta']); break
    o = orgao_da_pasta(p['pasta'])
    c = cartao_de(o, 8) if o else None
    ministerios[k] = {'pasta': p['pasta'], 'ministro': p['n'], **({k2: v for k2, v in c.items() if k2 != 'itens'} | {'itens': c['itens'][:40]} if c else {'orgao': None})}

# Remuneração de presidente, vice e ministros: testada e deixada de fora por enquanto. O endpoint de servidores
# só aceita busca por órgão do SIAPE ou CPF, e presidente, vice e ministros não aparecem por nome nesses órgãos.

OUT.mkdir(parents=True, exist_ok=True)
res = {'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'), 'periodo': [MESES[0].isoformat(), HOJE.isoformat()],
       'cartoes': cartoes, 'ministerios': ministerios, 'orgaos': sorted(ORG.values(), key=lambda o: o['codigo']), 'chamadas': chamadas, 'erros': log[:60]}
(OUT / 'exec.json').write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
(OUT / 'exec-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1)[:60000], encoding='utf-8')
print(json.dumps({'pres': PRES, 'vice': VICE, 'cartoes': {k: v and v['transacoes'] for k, v in cartoes.items()},
                  'ministerios': {k: (v.get('orgao') or {}).get('codigo') for k, v in ministerios.items()},
                  'chamadas': chamadas, 'erros': log[:10]}, ensure_ascii=False))
