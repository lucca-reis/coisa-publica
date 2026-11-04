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
// desenhos grandes dos posts de fundo cheio
const GLY = {
  jud:'<svg viewBox="0 0 12 12" fill="currentColor"><circle cx="1.3" cy="1.3" r="1.15"/><circle cx="1.3" cy="4.05" r="1.15"/><circle cx="1.3" cy="6.8" r="1.15"/><circle cx="1.3" cy="9.55" r="1.15"/><circle cx="10.7" cy="1.3" r="1.15"/><circle cx="10.7" cy="4.05" r="1.15"/><circle cx="10.7" cy="6.8" r="1.15"/><circle cx="10.7" cy="9.55" r="1.15"/><circle cx="3.65" cy="10.7" r="1.15"/><circle cx="6" cy="10.7" r="1.15"/><circle cx="8.35" cy="10.7" r="1.15"/></svg>',
  leg:'<svg viewBox="0 0 20.2 11.6" fill="currentColor"><circle cx="1.5" cy="10.1" r="1.5"/><circle cx="2.65" cy="5.8" r="1.5"/><circle cx="5.8" cy="2.65" r="1.5"/><circle cx="10.1" cy="1.5" r="1.5"/><circle cx="14.4" cy="2.65" r="1.5"/><circle cx="17.55" cy="5.8" r="1.5"/><circle cx="18.7" cy="10.1" r="1.5"/><circle cx="5.9" cy="10.1" r="1.5"/><circle cx="8" cy="6.46" r="1.5"/><circle cx="12.2" cy="6.46" r="1.5"/><circle cx="14.3" cy="10.1" r="1.5"/></svg>',
  exe:'<svg viewBox="0 0 12 12" fill="currentColor"><circle cx="6" cy="6" r="3.7"/></svg>'
};
// a mesa do STF como no site: o U de cantos arredondados e as 11 cadeiras em volta
const MESA = (()=>{ const seats = [[345,450],[450,450],[240,450],[533,360],[157,360],[533,285],[157,285],[533,210],[157,210],[533,135],[157,135]];
  return `<svg class="mesa" viewBox="120 70 450 420"><g transform="translate(345 283) scale(1) translate(-345 -283)"><path d="M195 103 L195 392 Q195 412 215 412 L475 412 Q495 412 495 392 L495 103 Q495 96 488 96 L456 96 Q449 96 449 103 L449 354 Q449 366 437 366 L253 366 Q241 366 241 354 L241 103 Q241 96 234 96 L202 96 Q195 96 195 103 Z" fill="none" stroke="var(--gray)" stroke-width="5" stroke-linejoin="round"/>${seats.map(([x,y])=>`<circle cx="${x}" cy="${y}" r="22" fill="var(--gray)"/>`).join('')}</g></svg>`; })();
// semicírculo grande (Câmara 513 ou Senado 81) com as primeiras `destaque` cadeiras na cor do texto
function hemi(casa, destaque){
  const T = casa === 'senado' ? 81 : 513, rows = casa === 'senado' ? 5 : 11, R0 = 150, R1 = 330, cx = 360, cy = 360;
  const radii = [...Array(rows)].map((_,i)=> R0 + (R1-R0)*i/(rows-1)), sum = radii.reduce((a,b)=>a+b,0);
  let seats = [];
  radii.forEach((r,i)=>{ const n = i===rows-1 ? T - seats.length : Math.round(T*r/sum); for (let k=0;k<n;k++){ const a = Math.PI*(1-(k+.5)/n); seats.push({x:cx + r*Math.cos(a), y:cy - r*Math.sin(a), a}); } });
  seats = seats.slice(0,T).sort((p,q)=> q.a-p.a);
  const r = casa === 'senado' ? 19 : 9.5;
  return `<svg viewBox="0 0 720 380" width="760">${seats.map((p,i)=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r}" fill="${i < destaque ? 'var(--pc)' : 'var(--gray)'}"/>`).join('')}</svg>`;
}
function visual(V, poder){
  if (!V) return '';
  // plenário em faixa única: o mesmo semicírculo do `plenario`, preenchido da esquerda até a porcentagem
  if (V.tipo === 'percentual'){
    const pc = Math.max(0, Math.min(100, +V.valor || 0)), r = 240, L = Math.PI*r, arc = `M${360-r} 360 A${r} ${r} 0 0 1 ${360+r} 360`;
    return `<div><div style="position:relative;width:760px;max-width:100%;margin:0 auto"><svg viewBox="0 0 720 380" width="100%"><path d="${arc}" fill="none" stroke="var(--gray)" stroke-width="200"/><path d="${arc}" fill="none" stroke="var(--pc)" stroke-width="200" stroke-dasharray="${(L*pc/100).toFixed(1)} ${L.toFixed(1)}"/></svg><div style="position:absolute;left:0;right:0;bottom:calc(20px * 760 / 720);text-align:center;line-height:1"><b style="display:block;font-size:88px;font-weight:700;letter-spacing:-.04em">${pc}%</b></div></div>${V.numeros ? `<div class="nums" style="margin-top:30px">${V.numeros.map(x=>`<div><b>${esc(x.n)}</b><span>${esc(x.l)}</span></div>`).join('')}</div>` : ''}</div>`;
  }
  if (V.tipo === 'plenario') return `<div>${hemi(V.casa, V.destaque || 0)}${V.numeros ? `<div class="nums">${V.numeros.map(x=>`<div><b>${esc(x.n)}</b><span>${esc(x.l)}</span></div>`).join('')}</div>` : ''}</div>`;
  if (V.tipo === 'data') return `<div class="dat">${(V.simbolo || poder) === 'jud' ? MESA : `<div class="circ">${GLY[V.simbolo || poder] || ''}</div>`}<div>${V.rotulo ? `<small>${esc(V.rotulo)}</small>` : ''}<b>${esc(V.valor)}</b>${V.sub ? `<small style="margin-top:8px">${esc(V.sub)}</small>` : ''}</div></div>`;
  return '';
}
function html(P, id){
  const I = P.imagem || {}, [y,m,d] = (P.data || id.slice(0,10)).split('-').map(Number);
  const dot = I.cor || DOT[PODER[I.poder]] || '#009C3B';
  const head = `<div class="top"><span class="logo" style="--dot:${dot}">C<i></i>isa Pública</span><span>${PER[P.periodo] || ''} · ${d} ${MES[m-1]} ${y}</span></div>
    <p class="eye">${esc(I.eyebrow)}${I.pergunta && I.titulo ? ' · ' + esc(I.titulo) : ''}</p><h1>${esc(I.titulo)}</h1>${I.texto && I.itens ? `<p class="lede">${esc(I.texto)}</p>` : ''}`;
  let card;
  // pergunta em destaque: a pergunta do assunto é o título grande; embaixo, depois de um fio, o símbolo do poder e a data
  if (!(I.itens && I.itens.length) && I.pergunta){
    const pw = PODER[I.poder], sym = pw === 'jud' ? MESA.replace('stroke="var(--gray)"','stroke="var(--pc)"').replace(/fill="var\(--gray\)"/g,'fill="var(--pc)"') : (GLY[pw] || '');
    const R = I.rodape || {};
    return head.replace(`<h1>${esc(I.titulo)}</h1>`, '') + `<div class="perg"><p>${esc(I.pergunta)}</p></div>`
      + ((R.valor || R.rotulo) ? `<div class="prod"><span class="psym" style="color:var(--pc)">${sym}</span><div>${R.rotulo ? `<small>${esc(R.rotulo)}</small>` : ''}<b>${esc(R.valor || '')}</b></div></div>` : '')
      + `<div class="foot"><span>Fonte: ${esc(I.fonte || '')}</span><span>coisapublica.io</span></div>`;
  }
  // um assunto só, de um poder: fundo cheio na cor do poder, desenho grande no meio, sem caixa
  if (!(I.itens && I.itens.length) && PODER[I.poder] && I.fundo !== 'claro'){
    const pl = I.placar;
    const mid = I.visual ? visual(I.visual, PODER[I.poder]) : pl ? `<div class="row"><div><div class="big">${esc(pl.texto || `${pl.sim} a ${pl.nao}`)}</div><div class="leg2"><span><i style="background:var(--ink)"></i>${esc((pl.rotulos||['sim'])[0])}</span><span><i style="background:#E24B4A"></i>${esc((pl.rotulos||[,'não'])[1])}</span></div></div>${plenario(pl)}</div>` : '';
    // poucos elementos: o tema, o título, o desenho, uma frase e a fonte (as etiquetas ficam na legenda)
    return head + `<div class="vis">${mid}</div>`
      + (I.texto ? `<p class="txt">${esc(I.texto)}</p>` : '') + `<div class="foot"><span>Fonte: ${esc(I.fonte || '')}</span><span>coisapublica.io</span></div>`;
  }
  if (I.itens && I.itens.length){
    card = `<div class="card"><div class="list">${I.itens.map(x=>`<div class="it"><div class="d">${esc(x.quando||'')}<b${String(x.dia||'').length > 5 ? ' class="lg"' : ''}>${esc(x.dia||'')}</b></div><div>
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
  const I0 = P.imagem || {}, cheio = !(I0.itens && I0.itens.length) && PODER[I0.poder] && I0.fundo !== 'claro';
  await p.setContent(base.replace('<body></body>', `<body${cheio ? ` class="cheio p-${PODER[I0.poder]}"` : ''}>` + html(P, id) + '</body>'));
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
