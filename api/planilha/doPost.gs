// true = os blocos da coluna A (1a rodada) ficam travados: o script recusa gravar neles.
// Mude para false se precisar reavaliar alguma celula da 1a rodada.
var TRAVAR_COLUNA_A = true;

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var d = JSON.parse(e.postData.contents);
    function norm(s){
      return String(s == null ? '' : s).toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
        .replace(/planning/g,'planing').replace(/[^a-z0-9]/g,'');
    }
    function sim(x){ return x === true || norm(x) === 'true'; }
    var alias = {zero:'zeroshot', few:'fewshot',
      espzero:'especialistazeroshot', espfew:'especialistafewshot',
      planzero:'planingzeroshot', planfew:'planingfewshot'};
    var estN = norm(d.estrategia); estN = alias[estN] || estN;
    // separa as causas de falha (a 1a rodada so tinha "Nao passou")
    var falha = !sim(d.compilou) ? 'Não compilou'
              : !sim(d.executou) ? 'Timeout'
              : !sim(d.passou)   ? 'Não passou' : '';
    // sem cobertura (nao compilou / timeout) -> deixa a FSM em branco, nao "Sem FSM"
    var temCob = !(d.linha_pct === '' || d.linha_pct == null);
    var val = {
      linha: d.linha_pct, desvio: d.desvio_pct, alternancia: d.alternancia_pct,
      maquina: !temCob ? '' : ((d.fsm_pct === '' || d.fsm_pct == null) ? 'Sem FSM' : d.fsm_pct),
      mutantes: falha || (String(d.mutantes_mortos)+'/'+String(d.mutantes_avaliados))
    };
    function chave(txt){
      var k = norm(txt);
      if (k === 'linha') return 'linha';
      if (k === 'desvio') return 'desvio';
      if (k.indexOf('alternanc') === 0) return 'alternancia';
      if (k.indexOf('maquina') === 0) return 'maquina';
      if (k === 'mutantes') return 'mutantes';
      return null;
    }
    var modN = norm(d.modulo);
    if (modN === '') return json({ok:false, erro:'modulo vazio'});
    var sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
    for (var s = 0; s < sheets.length; s++) {
      var sh = sheets[s], v = sh.getDataRange().getValues();
      // o nome do bloco pode estar em QUALQUER coluna (1a rodada na A, 2a rodada ao lado)
      var mr = -1, mc = -1;
      for (var r = 0; r < v.length && mr === -1; r++)
        for (var c = 0; c < v[r].length; c++)
          if (norm(v[r][c]) === modN) { mr = r; mc = c; break; }
      if (mr === -1) continue;
      if (TRAVAR_COLUNA_A && mc === 0)
        return json({ok:false, erro:'bloco "'+d.modulo+'" e da 1a rodada (coluna A) e esta travado'});
      // coluna da estrategia: so a DIREITA do nome do bloco (ate 9 colunas), na linha do
      // modulo ou ate 3 linhas acima -- assim um bloco nunca pega o cabecalho do bloco vizinho
      var col = -1;
      for (var rr = Math.max(0, mr - 3); rr <= mr + 1 && rr < v.length && col === -1; rr++)
        for (var c = mc + 1; c <= mc + 9 && c < v[rr].length; c++)
          if (estN !== '' && norm(v[rr][c]) === estN) { col = c; break; }
      if (col === -1)
        return json({ok:false, erro:'estrategia "'+d.estrategia+'" nao achada perto de '+d.modulo});
      // escreve cada metrica: varre da linha do modulo para baixo; os rotulos ficam ate
      // 2 colunas a direita do nome; para quando a coluna do nome tiver outro texto
      var feitas = [];
      for (var r = mr; r < v.length && r <= mr + 6; r++) {
        if (r > mr && norm(v[r][mc]) !== '' && norm(v[r][mc]) !== modN) break;
        for (var c = mc; c <= mc + 2 && c < v[r].length; c++) {
          var k = chave(v[r][c]);
          if (k && feitas.indexOf(k) === -1) {
            sh.getRange(r + 1, col + 1).setValue(val[k]); feitas.push(k); break;
          }
        }
      }
      var faltou = ['linha','desvio','alternancia','maquina','mutantes']
        .filter(function(k){ return feitas.indexOf(k) === -1; });
      return json({ok: faltou.length === 0, aba: sh.getName(), modulo: d.modulo,
                   estrategia: d.estrategia, escreveu: feitas, faltou: faltou});
    }
    return json({ok:false, erro:'modulo "'+d.modulo+'" nao encontrado (crie o bloco antes)'});
  } finally { lock.releaseLock(); }
  function json(o){ return ContentService.createTextOutput(JSON.stringify(o))
                      .setMimeType(ContentService.MimeType.JSON); }
}
