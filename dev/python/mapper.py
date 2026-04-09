import json
from pathlib import Path
from datetime import datetime

DRIVES = {
    "OneDrive Personal": Path.home() / "Library/CloudStorage/OneDrive-Personal",
    "Local - Documents": Path.home() / "Documents",
}

EXTENSOES_IMAGEM = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.heic'}


def coletar_imagens(caminho):
    imagens = []
    try:
        for item in Path(caminho).rglob('*'):
            if item.suffix.lower() in EXTENSOES_IMAGEM and not item.name.startswith('.'):
                try:
                    stat = item.stat()
                    imagens.append({
                        "nome": item.name,
                        "caminho": str(item),
                        "pasta": str(item.parent),
                        "tamanho": stat.st_size,
                        "mtime": stat.st_mtime,
                        "data": datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y')
                    })
                except Exception:
                    pass
    except PermissionError:
        pass
    return imagens


def gerar_html(imagens_por_drive):
    total = sum(len(v) for v in imagens_por_drive.values())
    todas = []
    for drive, imgs in imagens_por_drive.items():
        for img in imgs:
            img_copia = dict(img)
            img_copia["drive"] = drive
            img_copia.pop("mtime", None)
            todas.append(img_copia)

    todas.sort(key=lambda x: x.get("data", ""), reverse=True)
    dados_json = json.dumps(todas, ensure_ascii=False)
    drives_options = "".join(
        f'<option value="{d}">{d}</option>' for d in imagens_por_drive.keys()
    )
    data_geracao = datetime.now().strftime('%d/%m/%Y às %H:%M')

    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Mapa de Imagens</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }
        h1 { color: #a0c4ff; border-bottom: 1px solid #444; padding-bottom: 10px; margin-bottom: 20px; }
        .info { color: #888; font-size: 0.85em; margin-bottom: 20px; }
        .controles { display: flex; gap: 10px; align-items: center; margin-bottom: 20px; flex-wrap: wrap; }
        input[type=text] { background: #16213e; border: 1px solid #444; color: #e0e0e0; padding: 6px 12px; border-radius: 4px; width: 300px; }
        select { background: #16213e; border: 1px solid #444; color: #e0e0e0; padding: 6px 12px; border-radius: 4px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
        .card { background: #16213e; border-radius: 8px; overflow: hidden; cursor: pointer; transition: transform 0.1s; }
        .card:hover { transform: scale(1.02); }
        .card img { width: 100%; height: 130px; object-fit: cover; display: block; background: #0d0d1a; }
        .card .meta { padding: 8px; font-size: 0.72em; color: #aaa; }
        .card .meta .nome { color: #e0e0e0; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .card .meta .drive { color: #ffd6a5; }
        .paginacao { display: flex; gap: 8px; align-items: center; margin-top: 20px; flex-wrap: wrap; }
        .paginacao button { background: #16213e; border: 1px solid #444; color: #e0e0e0; padding: 6px 14px; border-radius: 4px; cursor: pointer; }
        .paginacao button:hover { background: #a0c4ff; color: #1a1a2e; }
        .paginacao button.ativo { background: #a0c4ff; color: #1a1a2e; font-weight: bold; }
        .paginacao .info-pag { color: #888; font-size: 0.85em; }
        #modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 100; align-items: center; justify-content: center; flex-direction: column; gap: 10px; }
        #modal.aberto { display: flex; }
        #modal img { max-width: 90vw; max-height: 80vh; border-radius: 8px; }
        #modal .modal-info { color: #e0e0e0; font-size: 0.85em; text-align: center; max-width: 80vw; word-break: break-all; }
        #modal .fechar { position: fixed; top: 20px; right: 30px; font-size: 2em; cursor: pointer; color: #fff; }
    </style>
</head>
<body>
    <h1>🖼️ Mapa de Imagens</h1>
    <p class="info">Total: TOTAL_PLACEHOLDER imagens — Gerado em DATA_PLACEHOLDER</p>
    <div class="controles">
        <input type="text" id="busca" placeholder="🔍 Buscar por nome ou pasta..." oninput="filtrar()">
        <select id="filtroDrive" onchange="filtrar()">
            <option value="">Todos os drives</option>
            DRIVES_OPTIONS_PLACEHOLDER
        </select>
        <span id="contagem" class="info"></span>
    </div>
    <div class="grid" id="grid"></div>
    <div class="paginacao" id="paginacao"></div>
    <div id="modal">
        <span class="fechar" onclick="fecharModal()">&#10005;</span>
        <img id="modalImg" src="">
        <div class="modal-info" id="modalInfo"></div>
    </div>
    <script>
        const TODAS = DADOS_JSON_PLACEHOLDER;
        const POR_PAGINA = 24;
        let filtradas = [...TODAS];
        let pagina = 1;

        function filtrar() {
            const busca = document.getElementById('busca').value.toLowerCase();
            const drive = document.getElementById('filtroDrive').value;
            filtradas = TODAS.filter(img => {
                const matchBusca = !busca || img.nome.toLowerCase().includes(busca) || img.pasta.toLowerCase().includes(busca);
                const matchDrive = !drive || img.drive === drive;
                return matchBusca && matchDrive;
            });
            pagina = 1;
            renderizar();
        }

        function renderizar() {
            const inicio = (pagina - 1) * POR_PAGINA;
            const fim = inicio + POR_PAGINA;
            const pagAtual = filtradas.slice(inicio, fim);
            const totalPags = Math.ceil(filtradas.length / POR_PAGINA);

            document.getElementById('contagem').textContent = filtradas.length + ' imagens';

            const grid = document.getElementById('grid');
            grid.innerHTML = pagAtual.map(img => {
                const caminho = img.caminho.replace(/\\/g, '/');
                const nomeEsc = img.nome.replace(/'/g, "\\'");
                const pastaEsc = img.pasta.replace(/'/g, "\\'");
                return '<div class="card" onclick="abrirModal(\'' + caminho + '\',\'' + nomeEsc + '\',\'' + pastaEsc + '\')">' +
                    '<img src="file://' + caminho + '" loading="lazy" onerror="this.style.background=\'#2a2a4a\'">' +
                    '<div class="meta">' +
                    '<div class="nome" title="' + img.nome + '">' + img.nome + '</div>' +
                    '<div class="drive">' + img.drive + '</div>' +
                    '<div>' + img.data + ' &middot; ' + Math.round(img.tamanho / 1024) + 'KB</div>' +
                    '</div></div>';
            }).join('');

            const pag = document.getElementById('paginacao');
            if (totalPags <= 1) { pag.innerHTML = ''; return; }

            let btns = '';
            if (pagina > 1) btns += '<button onclick="irPara(' + (pagina - 1) + ')">&#8592; Anterior</button>';
            const ini = Math.max(1, pagina - 2);
            const fim2 = Math.min(totalPags, pagina + 2);
            if (ini > 1) btns += '<button onclick="irPara(1)">1</button><span>...</span>';
            for (let i = ini; i <= fim2; i++) {
                btns += '<button class="' + (i === pagina ? 'ativo' : '') + '" onclick="irPara(' + i + ')">' + i + '</button>';
            }
            if (fim2 < totalPags) btns += '<span>...</span><button onclick="irPara(' + totalPags + ')">' + totalPags + '</button>';
            if (pagina < totalPags) btns += '<button onclick="irPara(' + (pagina + 1) + ')">Pr&#243;xima &#8594;</button>';
            btns += '<span class="info-pag">P&#225;gina ' + pagina + ' de ' + totalPags + '</span>';
            pag.innerHTML = btns;
        }

        function irPara(n) {
            pagina = n;
            window.scrollTo(0, 0);
            renderizar();
        }

        function abrirModal(caminho, nome, pasta) {
            document.getElementById('modalImg').src = 'file://' + caminho;
            document.getElementById('modalInfo').textContent = nome + ' — ' + pasta;
            document.getElementById('modal').classList.add('aberto');
        }

        function fecharModal() {
            document.getElementById('modal').classList.remove('aberto');
            document.getElementById('modalImg').src = '';
        }

        document.getElementById('modal').addEventListener('click', function(e) {
            if (e.target === this) fecharModal();
        });

        filtrar();
    </script>
</body>
</html>"""

    html = html.replace("TOTAL_PLACEHOLDER", str(total))
    html = html.replace("DATA_PLACEHOLDER", data_geracao)
    html = html.replace("DRIVES_OPTIONS_PLACEHOLDER", drives_options)
    html = html.replace("DADOS_JSON_PLACEHOLDER", dados_json)
    return html


# === EXECUÇÃO ===
print("Coletando imagens...")
imagens_por_drive = {}
todas = []

for nome, caminho in DRIVES.items():
    if caminho.exists():
        print(f"  Mapeando {nome}  ->  {caminho}")
        imgs = coletar_imagens(caminho)
        imgs.sort(key=lambda x: x["mtime"], reverse=True)
        imagens_por_drive[nome] = imgs
        todas.extend(imgs)
        print(f"     {len(imgs)} imagens encontradas")
    else:
        print(f"  Nao encontrado: {nome}")

print(f"\n  Total: {len(todas)} imagens")

saida = Path.home() / "Documents" / "mapa_imagens.html"
saida.write_text(gerar_html(imagens_por_drive), encoding="utf-8")
print(f"Salvo em: {saida}")