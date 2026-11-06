"""Orçamento federal do ano para a página #orcamento: o total, por área (função > subfunção > ação), por órgão
(órgão superior > órgão > unidade orçamentária) e por tipo de despesa (grupo > elemento), com a dívida separada
(juros, amortização e rolagem/refinanciamento).

Fonte: Portal da Transparência (CGU), arquivo anual "Orçamento da despesa", sem chave:
  https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/AAAA
Cada valor vem em quatro números: orçamento inicial (da lei), atualizado (com créditos e cortes), empenhado
(comprometido) e realizado (pago). Grava data/orcamento-federal.json. Só usa a biblioteca padrão. Roda todo domingo
(.github/workflows/orcamento-federal.yml)."""
import csv, io, json, re, datetime, zoneinfo, pathlib, unicodedata, urllib.request, zipfile, traceback

BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
AGORA = datetime.datetime.now(BR)
ANO = AGORA.year
OUT = pathlib.Path(__file__).resolve().parent.parent / 'data'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; coisa-publica; +https://coisapublica.io)'}
log = []

def norm(t):
    t = unicodedata.normalize('NFD', str(t or ''))
    return re.sub(r'\s+', ' ', ''.join(c for c in t if not unicodedata.combining(c))).upper().strip()

def valor(t):
    t = str(t or '').strip()
    if not t: return 0.0
    if ',' in t: t = t.replace('.', '').replace(',', '.')
    try: return float(t)
    except ValueError: return 0.0

def coluna(cab, *partes, sem=()):
    for c in cab:
        n = norm(c)
        if all(p in n for p in partes) and not any(s in n for s in sem): return c
    return None

# nomes em letra normal (o arquivo traz ações e programas em maiúsculas)
MIN = {'de','da','do','das','dos','e','a','o','as','os','em','no','na','nos','nas','para','por','com','ao','aos','à','às','sem','sob'}
SIGLAS = {'SUS','INSS','FGTS','FIES','PIS','PASEP','BPC','LOAS','FUNDEB','FNDE','RGPS','FAT','FCO','FNE','FNO','PAC','ANP','ANEEL','IBGE','IPEA','STF','STJ','TSE','TST','STM','CNJ','TCU','MPU','DPU','PF','PRF','ONU','BNDES','CAPES','CNPQ','EBSERH','SIAFI','ENEM','PNAE','PDDE','MEI','ICMS','IPI','IR','CIDE','FPE','FPM','DF','RJ','SP','UF','TV','TI','EBC','SUAS','CRAS','CREAS','RMV'}
# acentos que o arquivo perde ao vir em maiúsculas sem acento (só as palavras mais comuns nos nomes de ações)
ACENTO = {w.lower().translate(str.maketrans('áàâãéêíóôõúçÁÉÍÓÚÂÊÔÃÕÇ', 'aaaaeeiooouc' + 'aeiouaeoaoc')): w for w in """
Transferência Transferências Benefício Benefícios Prestação Deficiência Vitalícia Auxílio Gás Serviço Serviços Gestão Único Assistência
Segurança Dívida Pública Público Públicas Públicos Mobiliária Previdência Previdenciários Previdenciária Saúde Atenção Média Educação Básica
Manutenção Valorização União Pensões Operações Operação Crédito Sentenças Precatórios Família Famílias Beneficiárias Beneficiários Água
Elétrica Ciência Inovação Formação Promoção Implantação Implementação Ampliação Construção Recuperação Adequação Concessão Aquisição
Distribuição Produção Participação Participações Contribuição Contribuições Assunção Novação Compensação Variações Salário Salarial
Médicos Médica Odontológica Farmacêutica Estratégicos Estratégica Prevenção Imunização Vigilância Epidemiológica Conservação Fiscalização
Regularização Fundiária Agrária Equalização Subvenção Econômica Econômico Exportações Integração Hídrica Rodoviária Ferroviária
Ferroviário Aéreo Aeroportuária Inativos Administração Comunicação Tecnológica Científica Instituições Primária Comunitários
Cooperação Espaço Indígenas Proteção Habitação Básico Trânsito Tributária Arrecadação Orçamento Orçamentária Patrimônio Histórico
Nação Municípios Petróleo Mudança Adaptação Mitigação Reembolsável Amortização Interna Execução Políticas Política Tecnologia
Instituição Pós-Graduação Graduação Território Territorial Agropecuária Agrícola Pecuária Veículos Órgãos Órgão Gratuidade Atuação
Avaliação Informação Informações Inclusão Erradicação Alimentação Escolar Bolsa Rurais Saneamento Fomento Indenizações Indenização
Emergência Calamidade Calamidades Hospitais Universitários Acadêmica Pesquisas Inteligência Polícia Penitenciário Prisional
Estruturação Ressarcimento Compensações Exercício Exercícios Contratuais Federativos Federativo Consórcios Tecnológico Científico Econômicos
""".split()}
def acentua(w):
    k = w.lower()
    if k not in ACENTO: return w
    r = ACENTO[k]; return (r[:1].lower() if w[:1].islower() else r[:1].upper()) + r[1:]
def bonito(t):
    t = re.sub(r'\s+', ' ', str(t or '')).strip()
    if not t: return 'Não informado'
    if t != t.upper(): return ' '.join(acentua(w) if re.fullmatch(r'[A-Za-z]+', w) else w for w in t.split(' '))
    out = []
    for i, w in enumerate(t.split(' ')):
        base = re.sub(r'[^\wÀ-ÿ]', '', w)
        if base.upper() in SIGLAS: out.append(w)
        elif i and w.lower() in MIN: out.append(w.lower())
        else:
            x = w[:1].upper() + w[1:].lower(); m = re.match(r'^([\wÀ-ÿ-]+)(.*)$', x)
            out.append(acentua(m.group(1)) + m.group(2) if m else x)
    return ' '.join(out)

def baixar():
    for url in (f'https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/{ANO}',
                f'https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/orcamento-despesa/{ANO}_OrcamentoDespesa.zip'):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900) as r:
                return zipfile.ZipFile(io.BytesIO(r.read())), url
        except Exception as ex:
            log.append(f'{url}: {ex}')
    return None, None

def no(nome, cod=''):
    return {'n': nome, 'k': cod, 'v': [0.0, 0.0, 0.0, 0.0], 'r': [0.0, 0.0, 0.0, 0.0], 'c': {}}

def soma(nd, v, rol=False):
    # r: a parte que é rolagem da dívida (refinanciamento), para a página poder mostrar tudo sem ela
    for i in range(4):
        nd['v'][i] += v[i]
        if rol: nd['r'][i] += v[i]

def filho(nd, cod, nome):
    c = nd['c'].get(cod)
    if not c: c = nd['c'][cod] = no(nome, cod)
    return c

def fecha(nd, lim, prof=0):
    """Dicionário de filhos vira lista ordenada pelo atualizado; depois do limite, o resto vira 'Outros'."""
    L = sorted(nd['c'].values(), key=lambda x: -max(x['v'][1], x['v'][3]))
    L = [x for x in L if any(abs(v) >= 0.5 for v in x['v'])]
    lim_aqui = lim[prof] if prof < len(lim) else 0
    if lim_aqui and len(L) > lim_aqui:
        resto = L[lim_aqui:]; L = L[:lim_aqui]
        o = no(f'Outros ({len(resto)})', 'outros')
        for x in resto:
            soma(o, x['v'])
            for i in range(4): o['r'][i] += x['r'][i]
        o['outros'] = len(resto)
        L.append(o)
    for x in L:
        if x['c']: fecha(x, lim, prof + 1)
        else: x.pop('c', None)
    nd['c'] = L
    nd['v'] = [round(v, 2) for v in nd['v']]
    if any(abs(x) >= 0.5 for x in nd['r']): nd['r'] = [round(v, 2) for v in nd['r']]
    else: nd.pop('r', None)
    if not L: nd.pop('c', None)
    return nd

areas, orgaos, tipos = no('Orçamento federal'), no('Orçamento federal'), no('Orçamento federal')
divida = {'juros': [0.0]*4, 'amortizacao': [0.0]*4, 'rolagem': [0.0]*4}
total = [0.0]*4
linhas = 0
z, fonte = baixar()
if z:
    try:
        for nome in [n for n in z.namelist() if n.lower().endswith('.csv')]:
            with z.open(nome) as f:
                leitor = csv.DictReader(io.TextIOWrapper(f, encoding='latin-1'), delimiter=';')
                cab = leitor.fieldnames or []
                C = {k: coluna(cab, *p) for k, p in {
                    'sup': ('CODIGO', 'ORGAO SUPERIOR'), 'nsup': ('NOME', 'ORGAO SUPERIOR'),
                    'org': ('CODIGO', 'ORGAO SUBORDINADO'), 'norg': ('NOME', 'ORGAO SUBORDINADO'),
                    'uo': ('CODIGO', 'UNIDADE ORCAMENTARIA'), 'nuo': ('NOME', 'UNIDADE ORCAMENTARIA'),
                    'fun': ('CODIGO', 'FUNCAO'), 'nfun': ('NOME', 'FUNCAO'),
                    'sub': ('CODIGO', 'SUBFUNCAO'), 'nsub': ('NOME', 'SUBFUNCAO'),
                    'acao': ('CODIGO', 'ACAO'), 'nacao': ('NOME', 'ACAO'),
                    'gr': ('CODIGO', 'GRUPO DE DESPESA'), 'ngr': ('NOME', 'GRUPO DE DESPESA'),
                    'el': ('CODIGO', 'ELEMENTO DE DESPESA'), 'nel': ('NOME', 'ELEMENTO DE DESPESA'),
                    'ini': ('INICIAL',), 'atu': ('ATUALIZADO',), 'emp': ('EMPENHADO',)}.items()}
                C['fun'] = coluna(cab, 'CODIGO', 'FUNCAO', sem=('SUB',)); C['nfun'] = coluna(cab, 'NOME', 'FUNCAO', sem=('SUB',))
                C['rea'] = coluna(cab, 'REALIZADO', sem=('%',))
                faltam = [k for k, v in C.items() if not v]
                if faltam: log.append(f'{nome}: colunas não encontradas {faltam}'); continue
                g = lambda r, k: (r.get(C[k]) or '').strip()
                for r in leitor:
                    v = [valor(r.get(C['ini'])), valor(r.get(C['atu'])), valor(r.get(C['emp'])), valor(r.get(C['rea']))]
                    if not any(v): continue
                    linhas += 1
                    for i in range(4): total[i] += v[i]
                    # dívida: juros (grupo 2), amortização (grupo 6) e, dentro dela, a rolagem (refinanciamento)
                    sub = norm(g(r, 'nsub')); gr = g(r, 'gr')
                    rol = 'REFINANCIAMENTO' in sub
                    k = 'rolagem' if rol else 'juros' if gr == '2' else 'amortizacao' if gr == '6' else None
                    if k:
                        for i in range(4): divida[k][i] += v[i]
                    # por área
                    a1 = filho(areas, g(r, 'fun'), bonito(g(r, 'nfun')))
                    a2 = filho(a1, g(r, 'sub'), bonito(g(r, 'nsub')))
                    a3 = filho(a2, g(r, 'acao'), bonito(g(r, 'nacao')))
                    for x in (areas, a1, a2, a3): soma(x, v, rol)
                    # por órgão
                    o1 = filho(orgaos, g(r, 'sup'), bonito(g(r, 'nsup')))
                    o2 = filho(o1, g(r, 'uo'), bonito(g(r, 'nuo')))
                    for x in (orgaos, o1, o2): soma(x, v, rol)
                    # por tipo de despesa
                    t1 = filho(tipos, g(r, 'gr'), bonito(g(r, 'ngr')))
                    t2 = filho(t1, g(r, 'el'), bonito(g(r, 'nel')))
                    for x in (tipos, t1, t2): soma(x, v, rol)
        log.append(f'{linhas} linhas lidas')
    except Exception:
        log.append(traceback.format_exc()[-600:])

if linhas < 1000:
    print(json.dumps({'erro': 'poucas linhas, nada gravado', 'log': log}, ensure_ascii=False)); raise SystemExit(0)

res = {'atualizado': AGORA.isoformat(timespec='minutes'), 'ano': ANO, 'fonte': fonte,
       'colunas': ['inicial', 'atualizado', 'empenhado', 'pago'],
       'total': [round(x, 2) for x in total],
       'divida': {k: [round(x, 2) for x in v] for k, v in divida.items()},
       'areas': fecha(areas, [0, 12, 15]), 'orgaos': fecha(orgaos, [0, 15]), 'tipos': fecha(tipos, [0, 12]),
       'log': log[:20]}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'orcamento-federal.json').write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'total': res['total'], 'divida': res['divida'], 'areas': len(res['areas']['c']), 'orgaos': len(res['orgaos']['c']), 'log': log[:5]}, ensure_ascii=False))
