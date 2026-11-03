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
   `preparar` também grava data/aovivo.json (o que está aberto agora na Câmara e no Senado, Plenário e comissões), que a
   seção "Ao vivo agora" do site lê; só reescreve quando a lista muda ou a cada ~50 minutos, para não encher o histórico.
   Confirmação antes do story (confirmar): Câmara e Senado, a própria Casa diz que a reunião está aberta e dá o vídeo
   oficial, que precisa existir no YouTube (oEmbed); com a chave YOUTUBE_API_KEY (segredo), o YouTube ainda confirma
   que o vídeo está ao vivo. STF e Presidência só com a chave (busca a transmissão ao vivo do canal oficial). A página
   /live do YouTube não serve: vista dos servidores do GitHub, pede login e não mostra o vídeo.
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
    const day = (A[k]?.days||[]).find(d=> d.date===hoje && !d.label && (d.live || (k!=='exec' && /sess|live/i.test(d.kind||''))));
    if (!day) continue;
    const st = hm(day.time || JANELA[k].start); if (st == null) continue;
    const en = day.end ? hm(day.end) : st + JANELA[k].hours*60;
    if (agora < st || agora >= en) continue;
    const it = (day.items||[])[0] || {}, pr = it.ref && P[it.ref];
    const desc = pr ? `${pr.title}${pr.code ? ` (${pr.code})` : ''}` : (it.id || '');
    out.push({chave:`${k}-${hoje}-${st}`, casa:k, desde:hTxt(st), tipo:tipoBonito(day.kind), descricao: limpa(desc).slice(0, 180)});
  }
  return out;
}

// a transmissão está mesmo no ar? Sem confirmação, não sai story (tenta de novo na rodada seguinte).
const YTKEY = (process.env.YOUTUBE_API_KEY||'').trim();
// canais oficiais no YouTube (o identificador de cada um é pedido à API pelo nome do canal)
const CANAL = {camara:'@camaradosdeputados', senado:'@tvsenado', stf:'@STF_oficial', exec:'@canalgov'}, CANAL_ID = {camara:'UC-ZkSRh-7UEuwXJQ9UMCFJA'};
async function canalId(casa){
  if (!CANAL_ID[casa]) CANAL_ID[casa] = (((await ytApi(`channels?part=id&forHandle=${encodeURIComponent(CANAL[casa])}`)).items||[])[0]||{}).id || null;
  return CANAL_ID[casa];
}
const vid = u => (/(?:v=|youtu\.be\/|\/live\/|\/embed\/)([\w-]{11})/.exec(u||'') || [])[1] || null;
async function ytApi(q){ const r = await fetch(`https://www.googleapis.com/youtube/v3/${q}&key=${encodeURIComponent(YTKEY)}`); if (!r.ok) throw new Error(`YouTube API: HTTP ${r.status}`); return r.json(); }
async function confirmar(x){
  try {
    const v = vid(x.video);
    if (YTKEY){
      if (v){ const j = await ytApi(`videos?part=snippet&id=${v}`); return (j.items||[])[0]?.snippet?.liveBroadcastContent === 'live' ? v : null; }
      const ch = (x.casa==='stf' || x.casa==='exec' || x.plenario) ? await canalId(x.casa) : null;
      if (ch){
        const j = await ytApi(`search?part=id&channelId=${ch}&eventType=live&type=video&maxResults=1`);
        return (j.items||[])[0]?.id?.videoId || null;
      }
      return null;
    }
    // sem a chave: Câmara e Senado valem pela própria Casa (reunião aberta) e, quando ela dá o vídeo, ele precisa existir
    if (x.casa==='camara' || x.casa==='senado'){ if (!v) return 'sem-video'; return (await oembed(x.video)) ? v : null; }
    return null;                                     // STF e Presidência: sem a chave, não há como confirmar
  } catch (e) { console.error(`confirmar ${x.chave}: ${e.message}`); return null; }
}

// data/aovivo.json: o que está aberto agora na Câmara e no Senado, para o site
const AOVIVO = path.join(ROOT, 'data', 'aovivo.json');
function gravarAoVivo(lista){
  const itens = lista.filter(x=> x.casa==='camara' || x.casa==='senado').map(({casa, plenario, sigla, nome, tipo, descricao, desde, video})=> ({casa, plenario:!!plenario, sigla, nome, tipo, descricao, desde, video: video || null}));
  const velho = ler(AOVIVO, null), mesmo = velho && JSON.stringify(velho.itens) === JSON.stringify(itens);
  if (mesmo && Date.now() - Date.parse(velho.atualizado) < 50*60e3) return;
  fs.writeFileSync(AOVIVO, JSON.stringify({atualizado: new Date().toISOString().slice(0,16) + 'Z', itens}, null, 1));
}

async function preparar(){
  const {data:hoje, min:agora} = agoraBR();
  const est = ler(EST, {}), achados = [];
  for (const [nome, fn] of [['camara', ()=> camara(hoje)], ['senado', ()=> senado(hoje)], ['senado-comissoes', ()=> senadoComissoes(hoje)], ['agenda', async ()=> agenda(hoje, agora)]]){
    try { achados.push(...await fn()); } catch (e) { console.error(`${nome}: ${e.message}`); }
  }
  try { gravarAoVivo(achados); } catch (e) { console.error(`aovivo.json: ${e.message}`); }
  // comissões: só uma por Casa a cada 3 horas, e nunca com o Plenário daquela Casa aberto
  const recente = casa => Object.entries(est).some(([k, v])=> v.comissao && v.casa===casa && Date.now() - Date.parse(v.quando) < 3*3600e3);
  const vez = new Set(), novos = [];
  for (const x of achados.filter(x=> !est[x.chave])){
    if (x.plenario === false){
      if (achados.some(y=> y.casa===x.casa && y.plenario) || recente(x.casa) || vez.has(x.casa)) continue;
    }
    const v = await confirmar(x);
    if (v){ if (v !== 'sem-video') x.video = v; if (x.plenario === false) vez.add(x.casa); novos.push(x); }
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
  for (const x of pend){ await p.setContent(html(x)); await p.screenshot({path: path.join(DIR, `${x.chave}.jpg`), type:'jpeg', quality:90}); }
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
