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
// cores dos partidos, as mesmas do site (PARTY no index.html)
const PARTY = {PSOL:'#A3238E', Rede:'#14A39A', PCdoB:'#8A1325', PT:'#D6202C', PV:'#3A9A41', PSB:'#F2B705', PDT:'#E46AA2', Avante:'#3CC2D4',
  Solidariedade:'#C9773A', MDB:'#86B840', PSD:'#F28C1E', Podemos:'#1F8F6A', PSDB:'#2F6DB5', PRD:'#6C7A8C', 'União':'#1AA0D8', PP:'#8FB3E3',
  Republicanos:'#5446B8', 'Missão':'#E4CF4A', Novo:'#FF6A13', PL:'#2450B0', Cidadania:'#D8336D'};
const PORDER = ['PSOL','Rede','PCdoB','PT','PV','PSB','PDT','Avante','Solidariedade','Cidadania','MDB','PSD','Podemos','PSDB','PRD','União','PP','Republicanos','Missão','Novo','PL'];
// semicírculo com uma cor por cadeira (as que sobram em cinza), da esquerda para a direita
function hemiCores(T, rows, cores, r, R0 = 150){
  const R1 = 330, cx = 360, cy = 360;
  const radii = [...Array(rows)].map((_,i)=> R0 + (R1-R0)*i/(rows-1)), sum = radii.reduce((a,b)=>a+b,0);
  let seats = [];
  radii.forEach((rr,i)=>{ const n = i===rows-1 ? T - seats.length : Math.round(T*rr/sum); for (let k=0;k<n;k++){ const a = Math.PI*(1-(k+.5)/n); seats.push({x:cx + rr*Math.cos(a), y:cy - rr*Math.sin(a), a}); } });
  seats = seats.slice(0,T).sort((p,q)=> q.a-p.a);
  return `<svg viewBox="0 0 720 370" width="100%" style="display:block">${seats.map((p,i)=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r}" fill="${cores[i] || 'var(--gray)'}"/>`).join('')}</svg>`;
}
function visual(V, poder){
  if (!V) return '';
  // mulheres: um semicírculo por Casa, com as cadeiras das mulheres pintadas na cor do partido; embaixo, a porcentagem e os partidos
  if (V.tipo === 'mulheres'){
    const col = C => {
      const ps = [...C.partidos].sort((a,b)=> PORDER.indexOf(a[0]) - PORDER.indexOf(b[0]));
      const cores = ps.flatMap(([p,n])=> Array(n).fill(PARTY[p] || '#8A8B90'));
      const lista = [...C.partidos].sort((a,b)=> b[1]-a[1] || PORDER.indexOf(a[0]) - PORDER.indexOf(b[0]));
      return `<div class="mu"><small>${esc(C.titulo)}</small>${hemiCores(C.total, C.casa === 'senado' ? 5 : 11, cores, C.casa === 'senado' ? 19 : 9.5)}
        <div class="mu-n"><b>${esc(C.pct)}</b><span>${esc(C.l)}</span></div>
        <div class="mu-p">${lista.map(([p,n])=>`<span><i style="background:${PARTY[p] || '#8A8B90'}"></i>${esc(p)} <b>${n}</b></span>`).join('')}</div></div>`;
    };
    return `<div class="mus">${(V.casas || []).map(col).join('')}</div>`;
  }
  // plenário em faixa única: o mesmo semicírculo do `plenario`, preenchido da esquerda até a porcentagem
  if (V.tipo === 'percentual'){
    const pc = Math.max(0, Math.min(100, +V.valor || 0)), r = 240, L = Math.PI*r, arc = `M${360-r} 360 A${r} ${r} 0 0 1 ${360+r} 360`;
    return `<div><div style="position:relative;width:760px;max-width:100%;margin:0 auto"><svg viewBox="0 0 720 380" width="100%"><path d="${arc}" fill="none" stroke="var(--gray)" stroke-width="200"/><path d="${arc}" fill="none" stroke="var(--pc)" stroke-width="200" stroke-dasharray="${(L*pc/100).toFixed(1)} ${L.toFixed(1)}"/></svg><div style="position:absolute;left:0;right:0;bottom:calc(20px * 760 / 720);text-align:center;line-height:1"><b style="display:block;font-size:88px;font-weight:700;letter-spacing:-.04em">${pc}%</b></div></div>${V.numeros ? `<div class="nums" style="margin-top:30px">${V.numeros.map(x=>`<div><b>${esc(x.n)}</b><span>${esc(x.l)}</span></div>`).join('')}</div>` : ''}</div>`;
  }
  // degraus: uma coluna por valor, em escada; cada degrau traz o número publicado (a base não começa do zero)
  if (V.tipo === 'degraus'){
    const P = V.pontos || [], W = 912, H = 430, w = W / P.length, lo = Math.min(...P), hi = Math.max(...P), h = v => 130 + (hi > lo ? (v-lo)/(hi-lo)*200 : 0);
    const bars = P.map((v,i)=>`<rect x="${(i*w).toFixed(1)}" y="${H-h(v)}" width="${(w+.6).toFixed(1)}" height="${h(v)}" fill="var(--pc)"/><text x="${((i+.5)*w).toFixed(1)}" y="${H-h(v)+46}" text-anchor="middle" fill="#F3F3F3" font-size="30" font-weight="600" letter-spacing="-.5">${String(v).replace('.',',')}</text>`).join('');
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" style="max-width:100%;font-family:inherit">${bars}<text x="${W}" y="104" text-anchor="end" font-size="136" font-weight="700" letter-spacing="-6" fill="var(--ink)">${esc(V.valor||'')}</text><text x="${W}" y="178" text-anchor="end" font-size="30" fill="var(--muted)">${esc(V.sub||'')}</text></svg>`;
  }
  // distrital: o mesmo "estado" duas vezes, com as mesmas cadeiras (bolinhas de três partidos fictícios);
  // à esquerda, um território só que elege todas; à direita, cortado em distritos que elegem uma cada
  if (V.tipo === 'distrital'){
    const s = 46, h3 = Math.sqrt(3), cells = [];
    for (let q=-2;q<=2;q++) for (let r=-2;r<=2;r++){ if (Math.abs(q+r) > 2 || (q===2&&r===-2) || (q===-2&&r===2)) continue; cells.push([q,r]); }
    const C = ['var(--ink)','var(--pc)','#9A9BA0'], pat = [0,1,0,2,1,0,1,0,2,0,1,2,0,1,0,2,1];
    const hex = (cx,cy)=> [...Array(6)].map((_,i)=>{ const a = Math.PI/180*(60*i-30); return `${(cx+s*Math.cos(a)).toFixed(1)},${(cy+s*Math.sin(a)).toFixed(1)}`; }).join(' ');
    const map = (ox, cut)=> cells.map(([q,r],i)=>{ const x = ox + s*h3*(q+r/2), y = 215 + s*1.5*r;
      return `<polygon points="${hex(x,y)}" fill="var(--card2)" ${cut ? 'stroke="#F3F3F3" stroke-width="7" stroke-linejoin="round"' : 'stroke="var(--card2)" stroke-width="2"'}/>`; }).join('')
      + cells.map(([q,r],i)=>`<circle cx="${(ox + s*h3*(q+r/2)).toFixed(1)}" cy="${(215 + s*1.5*r).toFixed(1)}" r="15" fill="${C[pat[i]]}"/>`).join('');
    const R = V.rotulos || [['Hoje','um distrito, várias vagas'],['Distrital','um distrito, uma vaga']];
    const lab = (x,[t,sub])=>`<text x="${x}" y="470" text-anchor="middle" font-size="40" font-weight="700" letter-spacing="-1" fill="var(--ink)">${esc(t)}</text><text x="${x}" y="512" text-anchor="middle" font-size="28" fill="var(--muted)">${esc(sub)}</text>`;
    return `<svg viewBox="0 0 912 530" width="912" style="max-width:100%;font-family:inherit">${map(215,false)}${map(697,true)}${lab(215,R[0])}${lab(697,R[1])}</svg>`;
  }
  // sistemas: três linhas (proporcional, distrital, misto) com o mesmo estado fictício de 10 vagas e três partidos fictícios;
  // em cada linha, o nome e a regra, o mapa (com os votos ou com os distritos pintados pelo vencedor) e as cadeiras que resultam
  if (V.tipo === 'sistemas'){
    const PC = ['#E8603C','#16A08F','#7A52D1'], s = 31, w = s*Math.sqrt(3), rh = s*1.5;
    const pos = [[-1,0],[0,0],[1,0],[-1.5,1],[-.5,1],[.5,1],[1.5,1],[-1,2],[0,2],[1,2]];
    const vtx = (x,y)=> [...Array(6)].map((_,i)=>{ const a = Math.PI/180*(60*i-30); return [+(x+s*Math.cos(a)).toFixed(1), +(y+s*Math.sin(a)).toFixed(1)]; });
    // um mapa: cada célula pintada; fio claro só entre células de distritos diferentes
    const map = (ox, oy, dist, fill)=>{
      const C = pos.map(([a,b])=>({x:ox + a*w, y:oy + b*rh})), V6 = C.map(c=>vtx(c.x,c.y));
      let out = C.map((c,i)=>`<polygon points="${V6[i].map(p=>p.join(',')).join(' ')}" fill="${fill(i)}" stroke="${fill(i)}" stroke-width="1.5"/>`).join('');
      if (dist) for (let i=0;i<10;i++) for (let j=i+1;j<10;j++){ if (dist[i]===dist[j]) continue;
        const sh = V6[i].filter(p=> V6[j].some(q=> Math.abs(p[0]-q[0])<1 && Math.abs(p[1]-q[1])<1));
        if (sh.length===2) out += `<line x1="${sh[0][0]}" y1="${sh[0][1]}" x2="${sh[1][0]}" y2="${sh[1][1]}" stroke="#F3F3F3" stroke-width="6" stroke-linecap="round"/>`; }
      return out;
    };
    const seats = (x, y, list)=> list.map((p,i)=>`<circle cx="${x + (i%5)*40}" cy="${y + Math.floor(i/5)*42}" r="16" fill="${PC[p]}"/>`).join('');
    // uma linha por sistema, separadas por fios: nome e regra curta à esquerda, mapa no meio, cadeiras à direita
    const H = 196, row = (k, t, sub, mapSvg, seatSvg)=>{ const y = k*H;
      return `${k ? `<line x1="0" y1="${y}" x2="912" y2="${y}" stroke="var(--gray)" stroke-width="2"/>` : ''}<text x="0" y="${y+90}" font-size="36" font-weight="700" letter-spacing="-1" fill="var(--ink)">${esc(t)}</text><text x="0" y="${y+128}" font-size="26" fill="var(--muted)">${esc(sub)}</text>${mapSvg}${seatSvg}`; };
    const M = 440, my = k => k*H + 98 - rh; // centro do mapa em cada linha
    const r1 = map(M, my(0), null, ()=> 'var(--card2)') + `<rect x="${M-90}" y="${my(0)+rh-11}" width="90" height="22" fill="${PC[0]}"/><rect x="${M}" y="${my(0)+rh-11}" width="54" height="22" fill="${PC[1]}"/><rect x="${M+54}" y="${my(0)+rh-11}" width="36" height="22" fill="${PC[2]}"/>`;
    const win2 = [0,1,0,0,2,0,1,0,1,0];               // um vencedor por distrito: A 6, B 3, C 1
    const dist3 = [0,1,2,0,1,3,2,4,4,3], win3 = [0,0,1,0,2]; // 5 distritos de duas células
    const SX = 640, sy = k => k*H + 77;
    const legend = `<text x="0" y="${3*H+62}" font-size="24" fill="var(--muted)">Exemplo fictício: 10 vagas e três partidos</text>` + ['A 50%','B 30%','C 20%'].map((x,i)=>`<circle cx="${560+i*124}" cy="${3*H+54}" r="12" fill="${PC[i]}"/><text x="${580+i*124}" y="${3*H+62}" font-size="24" fill="var(--ink)">${x}</text>`).join('');
    return `<svg viewBox="0 0 912 ${3*H+80}" width="912" style="max-width:100%;font-family:inherit">
      ${row(0, 'Proporcional', 'como é hoje', r1, seats(SX, sy(0), [0,0,0,0,0,1,1,1,2,2]))}
      ${row(1, 'Distrital', 'um eleito por distrito', map(M, my(1), [0,1,2,3,4,5,6,7,8,9], i=>PC[win2[i]]), seats(SX, sy(1), [0,0,0,0,0,0,1,1,1,2]))}
      ${row(2, 'Misto', 'distritos + lista', map(M, my(2), dist3, i=>PC[win3[dist3[i]]]), seats(SX, sy(2), [0,0,0,1,2,0,0,0,1,2]) + `<text x="${SX+186}" y="${sy(2)+8}" font-size="22" fill="var(--muted)">distritos</text><text x="${SX+186}" y="${sy(2)+50}" font-size="22" fill="var(--muted)">lista</text>`)}
      <line x1="0" y1="${3*H}" x2="912" y2="${3*H}" stroke="var(--gray)" stroke-width="2"/>${legend}
    </svg>`;
  }
  // aparelhos: uma coluna por grupo (ex.: Senado e Câmara), com um desenho por aparelho (celular em pé ou tablet deitado);
  // `partes` pinta os primeiros na cor do poder e o resto em cinza, com a legenda e o valor embaixo
  if (V.tipo === 'aparelhos'){
    const col = G => {
      const tot = (G.partes || []).reduce((a,[n])=>a+n,0), cel = G.forma !== 'tablet';
      const w = cel ? 9 : 13, h = cel ? 16 : 9, gx = 4, gy = 4, W = 420, per = Math.floor((W+gx)/(w+gx)), rows = Math.ceil(tot/per);
      const first = (G.partes[0] || [0])[0];
      const units = [...Array(tot)].map((_,i)=>`<rect x="${(i%per)*(w+gx)}" y="${Math.floor(i/per)*(h+gy)}" width="${w}" height="${h}" rx="${cel ? 3 : 2.5}" fill="${i < first ? 'var(--pc)' : 'var(--gray)'}"/>`).join('');
      return `<div class="ap"><small>${esc(G.titulo)}</small><b>${esc(G.n)} <span>${esc(G.l)}</span></b>
        <svg viewBox="0 0 ${per*(w+gx)-gx} ${rows*(h+gy)-gy}" width="${W}">${units}</svg>
        <div class="ap-lg">${G.partes.map(([n,t],i)=>`<span><i style="background:${i ? 'var(--gray)' : 'var(--pc)'}"></i>${n} ${esc(t)}</span>`).join('')}</div>
        ${G.valor ? `<p class="ap-v">${esc(G.valor)}<small>${esc(G.sub || '')}</small></p>` : ''}</div>`;
    };
    return `<div class="aps">${(V.grupos || []).map(col).join('')}</div>`;
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
  // destaques: grade 2x2 de cartões coloridos, cada um na cor do poder, com um desenho, um número grande, o título e uma frase
  if (I.layout === 'destaques' && I.itens && I.itens.length){
    const des = x => {
      const D = x.desenho || {}, pw = PODER[x.poder] || 'leg';
      if (D.tipo === 'senado' || D.tipo === 'camara'){
        const T = D.tipo === 'senado' ? 81 : 513, sim = D.sim || 0, nao = D.nao || 0;
        return hemiCores(T, D.tipo === 'senado' ? 5 : 11, [...Array(T)].map((_,i)=> i < sim ? 'var(--tc)' : i < sim+nao ? '#E24B4A' : 'rgba(18,20,23,.13)'), D.tipo === 'senado' ? 16 : 9.5, 200);
      }
      if (D.tipo === 'mesa') return MESA.replace('stroke="var(--gray)"','stroke="var(--tc)"').replace(/fill="var\(--gray\)"/g,'fill="var(--tc)"');
      if (D.tipo === 'moedas'){ // pilhas de moedas
        const pil = (x0, n)=> [...Array(n)].map((_,i)=>`<ellipse cx="${x0}" cy="${300-i*30}" rx="70" ry="22" fill="var(--tc)" stroke="var(--tcard)" stroke-width="6"/>`).join('');
        return `<svg viewBox="0 0 520 340" width="100%">${pil(120,5)}${pil(260,8)}${pil(400,3)}</svg>`;
      }
      return `<svg viewBox="0 0 520 340" width="100%" style="font-family:inherit"><circle cx="260" cy="170" r="165" fill="var(--tc)"/>${D.texto ? `<text x="260" y="196" text-anchor="middle" font-size="78" font-weight="700" letter-spacing="-3" fill="#F3F3F3">${esc(D.texto)}</text>` : ''}</svg>`;
    };
    const TC = {leg:['#F2C200','color-mix(in srgb,#F2C200 26%,#F3F3F3)'], jud:['#1F4FB5','color-mix(in srgb,#1F4FB5 13%,#F3F3F3)'], exe:['#009C3B','color-mix(in srgb,#009C3B 15%,#F3F3F3)']};
    card = `<div class="dq">${I.itens.map(x=>{ const pw = PODER[x.poder] || 'leg', [c,bg] = TC[pw];
      return `<div class="dq-c" style="--tc:${c};--tcard:${bg};background:${bg}"><p class="dq-q">${esc(x.quando||'')}<span>${esc(x.dia||'')}</span></p>
        <div class="dq-d">${des(x)}${x.num ? `<b class="dq-n">${esc(x.num)}</b>` : ''}</div>
        <p class="dq-t">${esc(x.titulo)}</p>${x.texto ? `<p class="dq-s">${esc(x.texto)}</p>` : ''}</div>`; }).join('')}</div>`;
    return head + card + `<div class="foot"><span>Fonte: ${esc(I.fonte || '')}</span><span>coisapublica.io</span></div>`;
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
