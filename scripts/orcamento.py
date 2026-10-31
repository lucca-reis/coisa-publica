"""Orçamento federal executado no ano, por poder e por órgão: Legislativo, Judiciário, Executivo, Ministério Público e
Defensoria. É a única base oficial que reúne os gastos dos tribunais, das casas do Congresso e do governo no mesmo formato.

Fonte: Portal da Transparência (CGU), arquivos mensais "Despesas - Execução" (dados abertos, sem chave):
  https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/AAAAMM
Cada linha traz o órgão superior, o órgão, e os valores empenhado, liquidado e pago no mês.
Grava data/transparencia/orcamento.json (totais do ano por poder, por órgão e por mês) e orcamento-amostra.json
(cabeçalho e algumas linhas de um arquivo, para conferir o formato). Só usa a biblioteca padrão."""
import csv, io, json, re, datetime, zoneinfo, pathlib, unicodedata, urllib.request, zipfile, traceback

BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
ANO = HOJE.year
OUT = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'transparencia'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; quorum; +https://github.com/lucca-reis/quorum)'}
log, amostra = [], {}

def norm(t):
    t = unicodedata.normalize('NFD', str(t or ''))
    return re.sub(r'\s+', ' ', ''.join(c for c in t if not unicodedata.combining(c))).upper().strip()

def valor(t):
    t = str(t or '').strip()
    if not t: return 0.0
    if ',' in t: t = t.replace('.', '').replace(',', '.')
    try: return float(t)
    except ValueError: return 0.0

def baixar(mes):
    """O zip do mês: primeiro pelo endereço de download do Portal, depois pelo servidor de arquivos da CGU."""
    for url in (f'https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/{mes}',
                f'https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/despesas-execucao/{mes}_Despesas.zip'):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
                dados = r.read()
            return zipfile.ZipFile(io.BytesIO(dados)), url
        except Exception as ex:
            log.append(f'{mes} {url}: {ex}')
    return None, None

def poder(nome_sup):
    n = norm(nome_sup)
    if 'TRIBUNAL DE CONTAS' in n or 'CAMARA DOS DEPUTADOS' in n or 'SENADO FEDERAL' in n: return 'leg'
    if 'MINISTERIO PUBLICO' in n or 'DEFENSORIA' in n or 'CONSELHO NACIONAL DO MINISTERIO PUBLICO' in n: return 'mpu'
    if 'JUSTICA' in n and not n.startswith('MINISTERIO') or 'TRIBUNAL' in n or 'SUPREMO' in n or 'CONSELHO NACIONAL DE JUSTICA' in n: return 'jud'
    return 'exec'

def coluna(cab, *partes, sem=()):
    for c in cab:
        n = norm(c)
        if all(p in n for p in partes) and not any(s in n for s in sem): return c
    return None

orgaos, meses_lidos = {}, []
for m in range(1, 13):
    if datetime.date(ANO, m, 1) > HOJE: break
    mes = f'{ANO}{m:02d}'
    z, url = baixar(mes)
    if not z: continue
    try:
        nomes = [n for n in z.namelist() if n.lower().endswith('.csv')]
        linhas_mes = 0
        for nome in nomes:
            with z.open(nome) as f:
                leitor = csv.DictReader(io.TextIOWrapper(f, encoding='latin-1'), delimiter=';')
                cab = leitor.fieldnames or []
                c_sup, c_nsup = coluna(cab, 'CODIGO', 'ORGAO SUPERIOR'), coluna(cab, 'NOME', 'ORGAO SUPERIOR')
                c_org, c_norg = coluna(cab, 'CODIGO', 'ORGAO SUBORDINADO'), coluna(cab, 'NOME', 'ORGAO SUBORDINADO')
                c_emp, c_liq = coluna(cab, 'EMPENHADO', sem=('RESTO',)), coluna(cab, 'LIQUIDADO', sem=('RESTO',))
                c_pag = coluna(cab, 'PAGO', sem=('RESTO', 'PAGAR'))
                if 'cabecalho' not in amostra: amostra['cabecalho'] = {'arquivo': nome, 'url': url, 'colunas': cab, 'usadas': [c_sup, c_nsup, c_org, c_norg, c_emp, c_liq, c_pag]}
                if not (c_nsup and c_pag):
                    log.append(f'{mes} {nome}: colunas não encontradas'); continue
                for i, r in enumerate(leitor):
                    if i < 3 and 'linhas' not in amostra: amostra.setdefault('_l', []).append(r)
                    sup, nsup = r.get(c_sup) or '', r.get(c_nsup) or ''
                    org, norg = (r.get(c_org) or sup), (r.get(c_norg) or nsup)
                    k = org or norg
                    o = orgaos.setdefault(k, {'codigo': org, 'nome': norg.strip(), 'sup': sup, 'sup_nome': nsup.strip(), 'poder': poder(nsup),
                                              'empenhado': 0.0, 'liquidado': 0.0, 'pago': 0.0, 'meses': {}})
                    e, l, p = valor(r.get(c_emp)), valor(r.get(c_liq)), valor(r.get(c_pag))
                    o['empenhado'] += e; o['liquidado'] += l; o['pago'] += p
                    o['meses'][mes] = o['meses'].get(mes, 0.0) + p
                    linhas_mes += 1
        if '_l' in amostra: amostra['linhas'] = amostra.pop('_l')
        meses_lidos.append(mes); log.append(f'{mes}: {linhas_mes} linhas')
    except Exception:
        log.append(f'{mes}: ' + traceback.format_exc()[-400:])

# por poder: totais e órgãos (os órgãos sem nenhum valor no ano ficam de fora)
NOMES = {'leg': 'Legislativo', 'jud': 'Judiciário', 'exec': 'Executivo', 'mpu': 'Ministério Público e Defensoria'}
poderes = {}
for k, nome in NOMES.items():
    L = [o for o in orgaos.values() if o['poder'] == k and (o['pago'] or o['empenhado'])]
    L.sort(key=lambda o: -o['pago'])
    poderes[k] = {'nome': nome, 'empenhado': round(sum(o['empenhado'] for o in L), 2), 'liquidado': round(sum(o['liquidado'] for o in L), 2),
                  'pago': round(sum(o['pago'] for o in L), 2),
                  'orgaos': [{**{x: o[x] for x in ('codigo', 'nome', 'sup', 'sup_nome')}, 'empenhado': round(o['empenhado'], 2), 'liquidado': round(o['liquidado'], 2),
                              'pago': round(o['pago'], 2), 'meses': [[mm, round(o['meses'].get(mm, 0.0), 2)] for mm in meses_lidos]} for o in L[:120 if k == 'exec' else 80]]}

OUT.mkdir(parents=True, exist_ok=True)
res = {'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'), 'ano': ANO, 'meses': meses_lidos, 'poderes': poderes,
       'fonte': 'https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao', 'erros': log[:40]}
(OUT / 'orcamento.json').write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
(OUT / 'orcamento-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1, default=str)[:30000], encoding='utf-8')
print(json.dumps({'meses': meses_lidos, 'poderes': {k: [v['pago'], len(v['orgaos'])] for k, v in poderes.items()}, 'erros': log[:8]}, ensure_ascii=False))
