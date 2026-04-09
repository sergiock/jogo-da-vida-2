// obsidian-patch.js — adicionar ao Especificador.html antes de </script>

// ---- OBSIDIAN CLI ----
async function obsCmd(cmd, params) {
  setObsStatus('executando obsidian ' + cmd + '...');
  esconderResultado();
  try {
    let url = '/api/obsidian?cmd=' + cmd;
    if (params) Object.entries(params).forEach(([k,v]) => url += '&' + k + '=' + encodeURIComponent(v));
    const resp = await fetch(url);
    const data = await resp.json();
    if (data.ok) {
      mostrarResultado(data.stdout || '(sem output)');
      setObsStatus('✓ ok', 'ok');
    } else {
      const msg = data.erro || data.stderr || 'erro';
      setObsStatus('⚠ ' + msg, 'erro');
      if (data.stderr) mostrarResultado(data.stderr);
    }
  } catch(e) {
    setObsStatus('⚠ Servidor offline', 'erro');
  }
}

function obsSearch() {
  const q = document.getElementById('obs-q').value.trim();
  if (!q) { document.getElementById('obs-q').focus(); return; }
  obsCmd('search', { q });
}

function obsBuscarSessoes() {
  document.getElementById('obs-q').value = 'animalgame';
  obsCmd('search', { q: 'animalgame' });
}

function setObsStatus(msg, tipo) {
  const el = document.getElementById('obs-status');
  el.textContent = msg;
  el.className = 'obs-status' + (tipo ? ' ' + tipo : '');
}

function mostrarResultado(txt) {
  const el = document.getElementById('obs-resultado');
  el.textContent = txt;
  el.classList.add('visivel');
}

function esconderResultado() {
  document.getElementById('obs-resultado').classList.remove('visivel');
}
