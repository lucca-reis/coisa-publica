/* Stories "ao vivo": quando a Câmara, o Senado, o STF ou a Presidência começa uma transmissão oficial, publica um story
   no Instagram com a arte de story-live.js. Roda em .github/workflows/stories.yml, a cada 10 minutos durante o dia.
     node scripts/posts/stories.js preparar   -> acha o que está ao vivo agora e ainda não teve story e lista em
                                                posts/stories/pendentes.json
     node scripts/posts/stories.js arte       -> gera a arte de cada pendente em posts/stories/<chave>.jpg (Playwright)
     node scripts/posts/stories.js publicar   -> (depois do commit, quando o site já serve a imagem) publica cada pendente
                                                como story e anota em posts/stories/estado.json, para nunca repetir
   Câmara e Senado: APIs de dados abertos (sessão do Plenário e reuniões de comissão em andamento). STF e Presidência: a
   AGENDA do index.html, com a mesma regra da seção "Ao vivo agora" do site (dia de hoje, sessão com horário, dentro da
   janela da transmissão).
   `preparar` também grava data/aovivo.json (o que está no ar agora: Plenário e comissões da Câmara e do Senado, STF e
   Presidência, com o vídeo de cada um), que a
   seção "Ao vivo agora" do site lê; só reescreve quando a lista muda ou a cada ~50 minutos, para não encher o histórico.
   Confirmação antes do story (confirmar): Câmara e Senado, a própria Casa diz que a reunião está aberta; STF e
   Presidência, a AGENDA diz que é a hora da transmissão. Nos quatro, é preciso achar o vídeo oficial (videoDe: o que a
   Casa informa, ou o vídeo de hoje no feed RSS do canal oficial no YouTube), e ele precisa existir (oEmbed); o story
   sai sempre com a imagem dessa transmissão. Com a chave YOUTUBE_API_KEY (segredo), o YouTube ainda confirma que o
   vídeo está ao vivo. A página /live do YouTube não serve: vista dos servidores do GitHub, pede login.
   Comissões: no máximo um story de comissão por Casa a cada 3 horas, e nunca com o Plenário daquela Casa aberto
   (é o que costuma estar na TV Senado e na TV Câmara).
   O Instagram não aceita link clicável (figurinha de link) em story publicado pela API: a arte manda para o site.
   Chaves só nos segredos do GitHub (IG_USER_ID, IG_TOKEN). */
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..', '..');
const DIR = path.join(ROOT, 'posts', 'stories');
const EST = path.join(DIR, 'estado.json'), PEND = path.join(DIR, 'pendentes.json');
const SITE = 'https://coisapublica.io/', GRAPH = 'https://graph.facebook.com/v21.0/';
const UA = {'User-Agent': 'coisa-publica (coisapublica.io)', 'Accept': 'application/json'};
const ler = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return d; } };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// hora de Brasília
const agoraBR = () => { const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {timeZone:'America/Sao_Paulo', year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hourCycle:'h23'}).formatToParts(new Date()).map(x=> [x.type, x.value]));
  return {data:`${p.year}-${p.month}-${p.day}`, min:(+p.hour)*60 + (+p.minute)}; };
const hm = t => { const m = /(\d{1,2})h(\d{2})?/.exec(t||''); return m ? (+m[1])*60 + (+(m[2]||0)) : null; };
const hTxt = m => `${Math.floor(m/60)}h${m%60 ? String(m%60).padStart(2,'0') : ''}`;
const minIso = s => { const m = /T(\d{2}):(\d{2})/.exec(s||''); return m ? (+m[1])*60 + (+m[2]) : null; };
const limpa = s => String(s||'').replace(/\s+/g, ' ').trim();
const tipoBonito = s => limpa(s).toLowerCase().replace(/^./, c=> c.toUpperCase()) || 'Sessão';

async function get(url){ const r = await fetch(url, {headers: UA}); if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json(); }

// ---------- Câmara: Plenário e comissões em andamento (todos os eventos do dia) ----------
async function camara(hoje){
  const js = await get(`https://dadosabertos.camara.leg.br/api/v2/eventos?dataInicio=${hoje}&dataFim=${hoje}&ordem=ASC&ordenarPor=dataHoraInicio&itens=100`);
  return (js.dados||[]).filter(e=> /andamento/i.test(e.situacao||'')).map(e=>{
    const o = (e.orgaos||[])[0] || {}, plen = (e.orgaos||[]).some(x=> x.sigla==='PLEN' || x.id===180);
    const desc = limpa((e.descricao||'').split(/\r?\n/)[0]).slice(0, 180);
    return {chave:`camara-${e.id}`, casa:'camara', plenario:plen, sigla: plen ? 'Plenário' : (o.sigla||''), nome: plen ? 'Plenário da Câmara' : (o.nome||o.nomePublicacao||''),
      desde: minIso(e.dataHoraInicio)!=null ? hTxt(minIso(e.dataHoraInicio)) : '', video: e.urlRegistro || null,
      tipo: plen ? tipoBonito(e.descricaoTipo) : (o.nome || tipoBonito(e.descricaoTipo)),
      descricao: plen ? desc : [tipoBonito(e.descricaoTipo), desc].filter(Boolean).join(': ').slice(0, 180)};
  });
}
// ---------- Senado: sessão do Plenário de hoje aberta ou em andamento ----------
function achar(o, k){ if (Array.isArray(o)) { for (const v of o){ const r = achar(v, k); if (r.length) return r; } return []; }
  if (o && typeof o === 'object'){ for (const [kk, v] of Object.entries(o)){ if (kk.toLowerCase()===k.toLowerCase()) return Array.isArray(v) ? v : [v]; const r = achar(v, k); if (r.length) return r; } } return []; }
const ABERTA = /andamento|aberta|iniciada/i;
async function senado(hoje){
  const js = await get(`https://legis.senado.leg.br/dadosabertos/plenario/agenda/dia/${hoje.replace(/-/g,'')}.json`);
  return achar(js, 'Sessao').filter(s=> s && typeof s === 'object').map(s=>{
    let sit = s.SituacaoSessao || s.Situacao || ''; if (typeof sit === 'object') sit = sit.Descricao || sit.DescricaoSituacao || '';
    let tipo = s.TipoSessao || s.DescricaoTipoSessao || ''; if (typeof tipo === 'object') tipo = tipo.Descricao || '';
    const hora = s.HoraInicioSessao || s.HoraInicio || s.Hora || '';
    return {sit: String(sit), x: {chave:`senado-${s.CodigoSessao || hoje}`, casa:'senado', plenario:true, sigla:'Plenário', nome:'Plenário do Senado',
      desde: hora ? hTxt(hm(hora.slice(0,5).replace(':','h'))) : '', video:null,
      tipo: tipoBonito(tipo), descricao: limpa(s.NomeSessao || s.DescricaoSessao || '').slice(0, 180)}};
  }).filter(o=> ABERTA.test(o.sit)).map(o=> o.x);
}
// ---------- Senado: reuniões de comissão abertas (agenda das comissões, com o vídeo oficial de cada uma) ----------
async function senadoComissoes(hoje){
  const js = await get(`https://legis.senado.leg.br/dadosabertos/comissao/agenda/${hoje.replace(/-/g,'')}.json`);
  const out = [];
  for (const r of achar(js, 'reuniao').filter(r=> r && typeof r === 'object' && ABERTA.test(r.situacao || r.status || ''))){
    const c = r.colegiadoCriador || r.colegiados || {}, vs = [].concat(r.videos || []).filter(Boolean), video = (vs[0] || {}).url || null;
    const yt = video ? await oembed(video) : null;
    const partes = [].concat(r.partes || []).map(p=> p && p.descricaoTipo).filter(Boolean);
    out.push({chave:`senado-com-${r.codigo}`, casa:'senado', plenario:false, sigla: c.sigla || '', nome: c.nome || '',
      desde: minIso(r.dataInicio)!=null ? hTxt(minIso(r.dataInicio)) : '', video,
      tipo: c.nome || 'Reunião de comissão', descricao: limpa(yt && yt.title ? yt.title.replace(/^ao vivo:\s*/i, '').replace(/\s*[–-]\s*\d{1,2}\/\d{1,2}\/\d{2,4}\s*$/, '') : (partes[0] ? `Reunião ${partes[0].toLowerCase()}` : r.titulo || '')).slice(0, 180)});
  }
  return out;
}
// o vídeo existe e é público no YouTube? (oEmbed responde mesmo para os servidores do GitHub)
async function oembed(url){
  try { const r = await fetch(`https://www.youtube.com/oembed?format=json&url=${encodeURIComponent(url)}`, {headers: UA}); return r.ok ? await r.json() : null; }
  catch (e) { return null; }
}
// ---------- STF e Presidência: AGENDA escrita à mão no index.html ----------
const VAZIO = Object.assign(()=> '', {toString:()=> '', valueOf:()=> ''});
function objeto(src, nome){                       // lê `const NOME = {...}` do index.html, respeitando textos e comentários
  const i = src.indexOf(`const ${nome} = {`); if (i < 0) return null;
  let j = src.indexOf('{', i), d = 0, q = null;
  for (let k = j; k < src.length; k++){
    const c = src[k];
    if (q){ if (c === '\\') { k++; continue; } if (c === q) q = null; continue; }
    if (c === "'" || c === '"' || c === '`'){ q = c; continue; }
    if (c === '/' && src[k+1] === '/'){ k = src.indexOf('\n', k); continue; }
    if (c === '/' && src[k+1] === '*'){ k = src.indexOf('*/', k) + 1; continue; }
    if (c === '{') d++; else if (c === '}' && --d === 0){
      // constantes do site citadas dentro do objeto (como CAM, o começo dos links da Câmara) viram texto vazio
      const escopo = new Proxy({}, {has:()=> true, get:(t, n)=> n === Symbol.unscopables ? undefined : (n in globalThis ? globalThis[n] : VAZIO)});
      return new Function('escopo', `with (escopo) { return (${src.slice(j, k+1)}); }`)(escopo);
    }
  }
  return null;
}
const JANELA = {stf:{start:'14h', hours:5}, exec:{start:'', hours:3}};   // as mesmas do LIVE do site
function agenda(hoje, agora){
  const src = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const A = objeto(src, 'AGENDA') || {};
  let P = {}; try { P = objeto(src, 'PROJECTS') || {}; } catch (e) { console.error('PROJECTS:', e.message); }
  const out = [];
  for (const k of ['stf', 'exec']){
    const day = (A[k]?.days||[]).find(d=> d.date===hoje && !d.label && (d.live || (k!=='exec' && /sess|live|audi[eê]ncia p[uú]blica/i.test(d.kind||''))));
    if (!day) continue;
    const st = hm(day.time || JANELA[k].start); if (st == null) continue;
    const en = day.end ? hm(day.end) : st + JANELA[k].hours*60;
    if (agora < st || agora >= en) continue;
    const it = (day.items||[])[0] || {}, pr = it.ref && P[it.ref];
    const desc = pr ? `${pr.title}${pr.code ? ` (${pr.code})` : ''}` : (it.short || it.id || '');
    out.push({chave:`${k}-${hoje}-${st}`, casa:k, plenario:true, sigla:'', nome: k==='stf' ? 'STF' : 'Presidência', desde:hTxt(st), tipo:tipoBonito(day.kind), descricao: limpa(desc).slice(0, 180)});
  }
  return out;
}

// o vídeo de cada transmissão (para o story sair sempre com a imagem dela e o site tocar a live)
// 1) Câmara e Senado dão o vídeo das comissões (e a Câmara, às vezes, o do Plenário);
// 2) sem isso, o feed RSS do canal oficial no YouTube (responde aos servidores do GitHub, ao contrário da página /live):
//    o vídeo de hoje com o assunto certo no título; para o Plenário do Senado, a transmissão contínua "Ao vivo - TV Senado".
// Os identificadores dos canais foram lidos das páginas oficiais de cada um no YouTube.
// lula: o canal @LulaOficial, só para os atos oficiais do presidente transmitidos ao vivo (reuniões, cerimônias...);
// o que é de partido ou de campanha fica de fora (EXCLUI)
const CANAL_ID = {camara:'UC-ZkSRh-7UEuwXJQ9UMCFJA', senado:'UCLgti7NuK0RuW9wty-fxPjQ', stf:'UCsW4QSB1USsu9ouuFUWe4Iw', exec:'UCjaWLFTNqLkq3ZY2BJ4NYRg', lula:'UCvO2BExvkAbGMsTGnEnI_Ng'};
const vid = u => /^[\w-]{11}$/.test(u||'') ? u : (/(?:v=|youtu\.be\/|\/live\/|\/embed\/)([\w-]{11})/.exec(u||'') || [])[1] || null;
const RSS = {};
async function rss(casa){
  if (!RSS[casa]){
    RSS[casa] = (async ()=>{
      const r = await fetch(`https://www.youtube.com/feeds/videos.xml?channel_id=${CANAL_ID[casa]}`, {headers: UA}); if (!r.ok) return [];
      const x = await r.text(), un = t => t.replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
      return [...x.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(m=> ({id:(/<yt:videoId>([^<]+)</.exec(m[1])||[])[1], titulo:un((/<title>([^<]*)</.exec(m[1])||[])[1]||''), quando:(/<published>([^<]+)</.exec(m[1])||[])[1]||''}));
    })().catch(()=> []);
  }
  return RSS[casa];
}
const TIPO_RE = {camara:/sess[aã]o|plen[aá]rio/i, senado:/sess[aã]o|plen[aá]rio/i, stf:/audi[eê]ncia|sess[aã]o|plen[aá]rio|julgamento/i, exec:/presidente|lula|pronunciamento|cerim[oô]nia|lan[cç]amento/i};
async function videoDoCanal(x, hoje){
  if (!CANAL_ID[x.casa]) return null;
  const [y, m, d] = hoje.split('-').map(Number), lista = await rss(x.casa);
  const data = new RegExp(`(^|[^\\d])0?${d}/0?${m}(?!\\d)`), deHoje = e => data.test(e.titulo) || e.quando.slice(0,10) === hoje;
  const tipo = TIPO_RE[x.casa], assunto = x.sigla && !x.plenario ? new RegExp(`\\b${x.sigla}\\b`) : null;
  const e = lista.find(e=> deHoje(e) && (assunto ? assunto.test(e.titulo) : tipo.test(e.titulo)))
    || (x.casa==='senado' && x.plenario ? lista.find(e=> /^ao vivo\s*[-–]\s*tv senado/i.test(e.titulo)) : null);
  return e ? e.id : null;
}
// está ao vivo agora? A página do vídeo responde aos servidores do GitHub e traz "isLiveNow" (a página /live do canal,
// não). true ou false; null se a página não respondeu (aí nada muda)
async function noAr(v){
  try {
    const r = await fetch(`https://www.youtube.com/watch?v=${v}`, {headers:{...UA, 'Accept-Language':'pt-BR'}}); if (!r.ok) return null;
    const m = /"isLiveNow":(true|false)/.exec(await r.text()); return m ? m[1] === 'true' : false;
  } catch (e) { return null; }
}
// atos oficiais do presidente ao vivo no canal @LulaOficial (não precisam estar na AGENDA)
const OFICIAL = /reuni[aã]o|conselho|cerim[oô]nia|san[cç][aã]o|assinatura|lan[cç]amento|inaugura|pronunciamento|entrevista|coletiva|c[uú]pula|visita|posse|an[uú]ncio|cadeia nacional|declara[cç][aã]o/i;
const EXCLUI = /milit[aâ]ncia|campanha|com[ií]cio|\bPT\b|partido|vit[oó]ria|elei[cç]|candidat|caminhada|carreata|apoiador|anivers[aá]rio/i;
async function lulaAoVivo(){
  const lista = await rss('lula'), out = [];
  for (const e of lista.filter(e=> e.id && Date.now() - Date.parse(e.quando) < 14*3600e3 && OFICIAL.test(e.titulo) && !EXCLUI.test(e.titulo))){
    if (await noAr(e.id) !== true) continue;
    const t = new Date(Date.parse(e.quando) - 3*3600e3), desde = hTxt(t.getUTCHours()*60 + t.getUTCMinutes());
    const tipo = /reuni[aã]o/i.test(e.titulo) ? 'Reunião' : /cerim[oô]nia|posse/i.test(e.titulo) ? 'Cerimônia' : /pronunciamento|cadeia/i.test(e.titulo) ? 'Pronunciamento' : /entrevista|coletiva/i.test(e.titulo) ? 'Entrevista' : 'Agenda oficial';
    const desc = e.titulo.replace(/^presidente lula\s+(participa|faz|realiza|preside|conduz|concede)\s+(d[aoe]s?\s+)?/i, '').replace(/^./, c=> c.toUpperCase());
    out.push({chave:`exec-lula-${e.id}`, casa:'exec', plenario:true, sigla:'', nome:'Presidência', desde, tipo, descricao: limpa(desc).slice(0, 180), video:`https://www.youtube.com/watch?v=${e.id}`});
  }
  return out;
}
async function videoDe(x, hoje){
  return vid(x.video) || await videoDoCanal(x, hoje);
}
// a transmissão está mesmo no ar? Sem confirmação, não sai story (tenta de novo na rodada seguinte).
// Câmara e Senado: a própria Casa diz que a reunião está aberta; STF e Presidência: a AGENDA diz que é a hora da
// transmissão e o canal oficial tem o vídeo de hoje. Em todos, o vídeo precisa existir no YouTube (oEmbed).
// Com a chave YOUTUBE_API_KEY (segredo), o YouTube ainda confirma que o vídeo está ao vivo.
const YTKEY = (process.env.YOUTUBE_API_KEY||'').trim();
async function ytApi(q){ const r = await fetch(`https://www.googleapis.com/youtube/v3/${q}&key=${encodeURIComponent(YTKEY)}`); if (!r.ok) throw new Error(`YouTube API: HTTP ${r.status}`); return r.json(); }
async function confirmar(x){
  try {
    const v = vid(x.video); if (!v) return null;          // sem o vídeo não há imagem: o story espera
    if (YTKEY){ const j = await ytApi(`videos?part=snippet&id=${v}`); return (j.items||[])[0]?.snippet?.liveBroadcastContent === 'live' ? v : null; }
    return (await oembed(`https://www.youtube.com/watch?v=${v}`)) ? v : null;
  } catch (e) { console.error(`confirmar ${x.chave}: ${e.message}`); return null; }
}

// data/aovivo.json: o que está no ar agora (Câmara e Senado: Plenário e comissões; STF e Presidência: a sessão da AGENDA),
// com o vídeo de cada um, para o site
const AOVIVO = path.join(ROOT, 'data', 'aovivo.json');
function gravarAoVivo(lista){
  const itens = lista.map(({casa, plenario, sigla, nome, tipo, descricao, desde, video})=> ({casa, plenario:!!plenario, sigla, nome, tipo, descricao, desde, video: video || null}));
  const velho = ler(AOVIVO, null), mesmo = velho && JSON.stringify(velho.itens) === JSON.stringify(itens);
  if (mesmo && Date.now() - Date.parse(velho.atualizado) < 25*60e3) return;
  fs.writeFileSync(AOVIVO, JSON.stringify({atualizado: new Date().toISOString().slice(0,16) + 'Z', itens}, null, 1));
}

async function preparar(){
  const {data:hoje, min:agora} = agoraBR();
  const est = ler(EST, {}), achados = [];
  for (const [nome, fn] of [['camara', ()=> camara(hoje)], ['senado', ()=> senado(hoje)], ['senado-comissoes', ()=> senadoComissoes(hoje)], ['agenda', async ()=> agenda(hoje, agora)], ['lula', lulaAoVivo]]){
    try { achados.push(...await fn()); } catch (e) { console.error(`${nome}: ${e.message}`); }
  }
  for (const x of achados){ try { const v = await videoDe(x, hoje); x.video = v ? `https://www.youtube.com/watch?v=${v}` : null; } catch (e) { x.video = null; } }
  // STF e Presidência vêm da janela da AGENDA, que não sabe quando a transmissão acaba: com a chave do YouTube,
  // sai da lista o que não está mais ao vivo (o vídeo da manhã que terminou, por exemplo)
  // (sem a chave, a própria página do vídeo diz se ainda está ao vivo)
  for (const x of achados.filter(x=> (x.casa==='stf' || x.casa==='exec') && !/^exec-lula-/.test(x.chave))){
    try { const v = vid(x.video);
      if (YTKEY){ const j = v ? await ytApi(`videos?part=snippet&id=${v}`) : null;
        if (!j || (j.items||[])[0]?.snippet?.liveBroadcastContent !== 'live') x.fora = true; }
      else if (v && await noAr(v) === false) x.fora = true; } catch (e) {}
  }
  // com uma transmissão oficial achada no canal do presidente, a janela da AGENDA da Presidência sem vídeo não entra
  if (achados.some(x=> /^exec-lula-/.test(x.chave))) achados.forEach(x=>{ if (x.casa==='exec' && !/^exec-lula-/.test(x.chave) && !x.video) x.fora = true; });
  for (let i = achados.length - 1; i >= 0; i--) if (achados[i].fora) achados.splice(i, 1);
  try { gravarAoVivo(achados); } catch (e) { console.error(`aovivo.json: ${e.message}`); }
  // comissões: só uma por Casa a cada 3 horas, e nunca com o Plenário daquela Casa aberto
  const recente = casa => Object.entries(est).some(([k, v])=> v.comissao && v.casa===casa && Date.now() - Date.parse(v.quando) < 3*3600e3);
  const vez = new Set(), novos = [];
  for (const x of achados.filter(x=> !est[x.chave])){
    if (x.plenario === false){
      if (achados.some(y=> y.casa===x.casa && y.plenario) || recente(x.casa) || vez.has(x.casa)) continue;
    }
    const v = await confirmar(x);
    if (v){ x.video = v; if (x.plenario === false) vez.add(x.casa); novos.push(x); }
    else console.log(`${x.chave}: marcada como ao vivo, mas a transmissão ainda não foi confirmada; sem story por enquanto`);
  }
  console.log('ao vivo agora:', achados.map(x=> x.chave).join(', ') || 'nada', '| novos:', novos.map(x=> x.chave).join(', ') || 'nenhum');
  if (novos.length){ fs.mkdirSync(DIR, {recursive:true}); fs.writeFileSync(PEND, JSON.stringify(novos, null, 1)); }
  else fs.rmSync(PEND, {force:true});              // o que ficou pendente e já saiu do ar não vira story
}

async function arte(){
  const pend = ler(PEND, []); if (!pend.length) return;
  const {chromium} = require('playwright'), {html} = require('./story-live.js');
  const b = await chromium.launch(), p = await b.newPage({viewport:{width:1080, height:1920}});
  for (const x of pend){ await p.setContent(html(x), {waitUntil:'networkidle'}); await p.screenshot({path: path.join(DIR, `${x.chave}.jpg`), type:'jpeg', quality:90}); }
  await b.close();
}

async function publicar(){
  const pend = ler(PEND, []); if (!pend.length) return;
  const ID = (process.env.IG_USER_ID||'').trim(), TOKEN = (process.env.IG_TOKEN||'').trim();
  if (!ID || !TOKEN){ console.log('Instagram sem chave: nada publicado'); return; }
  const est = ler(EST, {}), resta = [];
  for (const x of pend){
    try {
      const f = path.join(DIR, `${x.chave}.jpg`), h = crypto.createHash('sha1').update(fs.readFileSync(f)).digest('hex');
      const url = `${SITE}posts/stories/${x.chave}.jpg?v=${h.slice(0,10)}`;
      let ok = false;                                  // espera o site servir esta imagem (até ~10 min)
      for (let i = 0; i < 40 && !ok; i++){
        try { const r = await fetch(url, {headers: UA}); ok = r.ok && crypto.createHash('sha1').update(Buffer.from(await r.arrayBuffer())).digest('hex') === h; } catch (e) {}
        if (!ok) await sleep(15000);
      }
      if (!ok) throw new Error('o site ainda não serve a imagem');
      const post = async (u, q) => { const r = await fetch(GRAPH + u, {method:'POST', body:new URLSearchParams({...q, access_token:TOKEN})}); const j = await r.json(); if (!r.ok || j.error) throw new Error(JSON.stringify(j.error||j).slice(0, 300)); return j; };
      const c = (await post(`${ID}/media`, {image_url:url, media_type:'STORIES'})).id;
      for (let i = 0; i < 30; i++){
        const r = await (await fetch(`${GRAPH}${c}?fields=status_code&access_token=${encodeURIComponent(TOKEN)}`)).json();
        if (r.status_code === 'FINISHED') break; if (r.status_code === 'ERROR') throw new Error('Instagram recusou a imagem');
        await sleep(5000);
      }
      const m = (await post(`${ID}/media_publish`, {creation_id:c})).id;
      est[x.chave] = {ref:m, quando:new Date().toISOString().slice(0,16) + 'Z', casa:x.casa, comissao: x.plenario === false};
      console.log(`${x.chave}: story publicado (${m})`);
    } catch (e) { console.error(`${x.chave}: erro: ${e.message}`); resta.push(x); }
  }
  fs.writeFileSync(EST, JSON.stringify(est, null, 1));
  if (resta.length) fs.writeFileSync(PEND, JSON.stringify(resta, null, 1)); else fs.rmSync(PEND, {force:true});
}

const modo = process.argv[2];
({publicar, arte, preparar}[modo] || preparar)().catch(e=> { console.error(e); process.exit(1); });
