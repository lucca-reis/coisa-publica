/* Gera a imagem de um post (posts/<id>/imagem.jpg, 1080x1350) a partir de posts/<id>/post.json, no visual do Coisa Pública.
   Uso: node scripts/posts/render.js posts/2026-11-01-manha
   O texto encolhe sozinho até caber na imagem. Precisa do Playwright (Chromium). */
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');

const CAT = {mp:['Medida provisória','#D9651E'], pec:['Emenda à Constituição','#C7343B'], plp:['Lei complementar','#B2347F'],
  pl:['Projeto de lei','#7B3FB3'], pdl:['Decreto legislativo','#8B5A33'], acao:['Ação no Supremo','#4B4F57'], re:['Recurso extraordinário','#8E6F7E']};
const PODER = {leg:'leg', legislativo:'leg', camara:'leg', senado:'leg', congresso:'leg', jud:'jud', stf:'jud', judiciario:'jud', exe:'exe', exec:'exe', executivo:'exe', presidencia:'exe'};
const DOT = {leg:'#F2C200', jud:'#1F4FB5', exe:'#009C3B'};
const PER = {manha:'Manhã', tarde:'Tarde', noite:'Noite'};
const MES = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function tag(t){
  if (t.cat && CAT[t.cat]) return `<span class="pill t" style="--tc:${CAT[t.cat][1]}">${esc(t.t || CAT[t.cat][0])}</span>`;
  return `<span class="pill ${PODER[t.poder] || ''}">${esc(t.t)}</span>`;
}
// placar: STF em U (11 cadeiras) ou semicírculo (Câmara 513, Senado 81) com sim, não e o resto em cinza
function plenario(P){
  const sim = P.sim || 0, nao = P.nao || 0;
  if (P.desenho === 'stf'){
    const s = [[115,185],[165,185],[65,185],[205,140],[25,140],[205,100],[25,100],[205,60],[25,60],[205,20],[25,20]];
    const c = s.map((_,i)=> i < sim ? '#121417' : i < sim+nao ? '#E24B4A' : '#D9D8D3');
    return `<svg width="230" height="200" viewBox="0 0 230 200"><path d="M55 20 V160 H175 V20" fill="none" stroke="#C9C8C2" stroke-width="3"/>${s.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="13" fill="${c[i]}"/>`).join('')}</svg>`;
  }
  if (P.desenho === 'camara' || P.desenho === 'senado'){
    const T = P.desenho === 'camara' ? 513 : 81, rows = P.desenho === 'camara' ? 9 : 4, R0 = 60, R1 = 150;
    const radii = [...Array(rows)].map((_,i)=> R0 + (R1-R0)*i/(rows-1)), sum = radii.reduce((a,b)=>a+b,0);
    let seats = [];
    radii.forEach((r,i)=>{ const n = i===rows-1 ? T - seats.length : Math.round(T*r/sum); for (let k=0;k<n;k++){ const a = Math.PI*(k+.5)/n; seats.push({x:160 - r*Math.cos(a), y:165 - r*Math.sin(a), a}); } });
    seats = seats.slice(0,T).sort((p,q)=> p.a-q.a);
    const r = P.desenho === 'camara' ? 4.2 : 8.5;
    return `<svg width="320" height="180" viewBox="0 0 320 180">${seats.map((p,i)=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r}" fill="${i < sim ? '#121417' : i < sim+nao ? '#E24B4A' : '#D9D8D3'}"/>`).join('')}</svg>`;
  }
  return '';
}
function html(P, id){
  const I = P.imagem || {}, [y,m,d] = (P.data || id.slice(0,10)).split('-').map(Number);
  const dot = I.cor || DOT[PODER[I.poder]] || '#009C3B';
  const head = `<div class="top"><span class="logo" style="--dot:${dot}">C<i></i>isa Pública</span><span>${PER[P.periodo] || ''} · ${d} ${MES[m-1]} ${y}</span></div>
    <p class="eye">${esc(I.eyebrow)}</p><h1>${esc(I.titulo)}</h1>${I.texto && I.itens ? `<p class="lede">${esc(I.texto)}</p>` : ''}`;
  let card;
  if (I.itens && I.itens.length){
    card = `<div class="card"><div class="list">${I.itens.map(x=>`<div class="it"><div class="d">${esc(x.quando||'')}<b>${esc(x.dia||'')}</b></div><div>
      ${x.tags && x.tags.length ? `<div class="tags">${x.tags.map(tag).join('')}</div>` : ''}<p class="ct">${esc(x.titulo)}</p>${x.texto ? `<p class="cs">${esc(x.texto)}</p>` : ''}</div></div>`).join('')}</div></div>`;
  } else {
    const pl = I.placar;
    card = `<div class="card">${I.tags && I.tags.length ? `<div class="tags">${I.tags.map(tag).join('')}</div>` : ''}${I.texto ? `<p class="cs">${esc(I.texto)}</p>` : ''}
      ${pl ? `<div class="row"><div><div class="big">${esc(pl.texto || `${pl.sim} a ${pl.nao}`)}</div><div class="leg2"><span><i style="background:#121417"></i>${esc((pl.rotulos||['sim'])[0])}</span><span><i style="background:#E24B4A"></i>${esc((pl.rotulos||[,'não'])[1])}</span></div></div>${plenario(pl)}</div>` : ''}</div>`;
  }
  return head + card + `<div class="foot"><span>Fonte: ${esc(I.fonte || '')}</span><span>coisapublica.io</span></div>`;
}

(async ()=>{
  const dir = process.argv[2]; if (!dir) { console.error('uso: node render.js posts/<id>'); process.exit(1); }
  const id = path.basename(path.resolve(dir));
  const P = JSON.parse(fs.readFileSync(path.join(dir, 'post.json'), 'utf8'));
  const base = fs.readFileSync(path.join(__dirname, 'modelo.html'), 'utf8');
  const b = await chromium.launch(), p = await b.newPage({viewport:{width:1080, height:1350}});
  await p.setContent(base.replace('<body></body>', '<body>' + html(P, id) + '</body>'));
  // encolhe o texto até tudo caber em 1350px
  for (let k = 1; k <= 12; k++){
    const over = await p.evaluate(()=> document.body.scrollHeight > 1350);
    if (!over) break;
    await p.evaluate(k=> document.documentElement.style.setProperty('--k', String(1 - k*0.04)), k);
  }
  const over = await p.evaluate(()=> document.body.scrollHeight > 1350);
  await p.screenshot({path: path.join(dir, 'imagem.jpg'), type:'jpeg', quality:90});
  await b.close();
  console.log(over ? 'ATENÇÃO: o texto não coube; encurte.' : 'ok', path.join(dir, 'imagem.jpg'));
  if (over) process.exit(2);
})();
