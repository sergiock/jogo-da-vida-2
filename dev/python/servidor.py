import json
import os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import mimetypes

DRIVES = {
    "OneDrive Personal": Path.home() / "Library/CloudStorage/OneDrive-Personal",
    "Local - Documents": Path.home() / "Documents",
}

EXTENSOES_IMAGEM = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.heic'}

# Coleta todas as imagens uma vez ao iniciar
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

print("Carregando imagens... aguarde...")
TODAS = []
DRIVES_LISTA = []
for nome, caminho in DRIVES.items():
    if caminho.exists():
        imgs = coletar_imagens(caminho)
        for img in imgs:
            img["drive"] = nome
        imgs.sort(key=lambda x: x["mtime"], reverse=True)
        TODAS.extend(imgs)
        DRIVES_LISTA.append(nome)
        print(f"  {nome}: {len(imgs)} imagens")

print(f"  Total: {len(TODAS)} imagens\n")

POR_PAGINA = 24

HTML = """<!DOCTYPE html>
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
        button.buscar { background: #a0c4ff; color: #1a1a2e; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; min-height: 200px; }
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
        .loading { color: #888; padding: 40px; text-align: center; }
    </style>
</head>
<body>
    <h1>&#128248; Mapa de Imagens</h1>
    <p class="info" id="totalInfo">Carregando...</p>
    <div class="controles">
        <input type="text" id="busca" placeholder="&#128269; Buscar por nome ou pasta..." onkeydown="if(event.key==='Enter') buscar()">
        <select id="filtroDrive" onchange="buscar()">
            <option value="">Todos os drives</option>
            DRIVES_OPTIONS
        </select>
        <button class="buscar" onclick="buscar()">Buscar</button>
        <span id="contagem" class="info"></span>
    </div>
    <div class="grid" id="grid"><p class="loading">Carregando imagens...</p></div>
    <div class="paginacao" id="paginacao"></div>
    <div id="modal">
        <span class="fechar" onclick="fecharModal()">&#10005;</span>
        <img id="modalImg" src="">
        <div class="modal-info" id="modalInfo"></div>
    </div>
    <script>
        let pagina = 1;
        let totalFiltradas = 0;
        let totalGeral = 0;
        const POR_PAGINA = 24;

        async function buscar(pag) {
            pagina = pag || 1;
            const busca = document.getElementById('busca').value;
            const drive = document.getElementById('filtroDrive').value;
            document.getElementById('grid').innerHTML = '<p class="loading">Carregando...</p>';

            const params = new URLSearchParams({ pagina, busca, drive });
            const resp = await fetch('/api/imagens?' + params);
            const data = await resp.json();

            totalFiltradas = data.total;
            totalGeral = data.total_geral;
            document.getElementById('totalInfo').textContent =
                'Total: ' + totalGeral + ' imagens';
            document.getElementById('contagem').textContent =
                data.total + ' encontradas';

            renderGrid(data.imagens);
            renderPaginacao(data.total, data.paginas);
        }

        function renderGrid(imagens) {
            const grid = document.getElementById('grid');
            if (!imagens.length) {
                grid.innerHTML = '<p class="loading">Nenhuma imagem encontrada.</p>';
                return;
            }
            grid.innerHTML = imagens.map(img => {
                const src = '/imagem?path=' + encodeURIComponent(img.caminho);
                return '<div class="card" onclick="abrirModal(\'' +
                    src + '\',\'' + img.nome.replace(/'/g,"\\'") + '\',\'' +
                    img.pasta.replace(/'/g,"\\'") + '\')">' +
                    '<img src="' + src + '" loading="lazy" onerror="this.style.background=\'#2a2a4a\'">' +
                    '<div class="meta">' +
                    '<div class="nome" title="' + img.nome + '">' + img.nome + '</div>' +
                    '<div class="drive">' + img.drive + '</div>' +
                    '<div>' + img.data + ' &middot; ' + Math.round(img.tamanho/1024) + 'KB</div>' +
                    '</div></div>';
            }).join('');
        }

        function renderPaginacao(total, totalPags) {
            const pag = document.getElementById('paginacao');
            if (totalPags <= 1) { pag.innerHTML = ''; return; }
            let btns = '';
            if (pagina > 1) btns += '<button onclick="buscar(' + (pagina-1) + ')">&#8592; Anterior</button>';
            const ini = Math.max(1, pagina-2);
            const fim = Math.min(totalPags, pagina+2);
            if (ini > 1) btns += '<button onclick="buscar(1)">1</button><span>...</span>';
            for (let i = ini; i <= fim; i++) {
                btns += '<button class="' + (i===pagina?'ativo':'') + '" onclick="buscar('+i+')">'+i+'</button>';
            }
            if (fim < totalPags) btns += '<span>...</span><button onclick="buscar('+totalPags+')">'+totalPags+'</button>';
            if (pagina < totalPags) btns += '<button onclick="buscar('+(pagina+1)+')">Pr&#243;xima &#8594;</button>';
            btns += '<span class="info-pag">P&#225;gina ' + pagina + ' de ' + totalPags + '</span>';
            pag.innerHTML = btns;
        }

        function abrirModal(src, nome, pasta) {
            document.getElementById('modalImg').src = src;
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

        buscar();
    </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silencia logs

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == '/' or path == '/index.html':
            drives_options = "".join(
                '<option value="' + d + '">' + d + '</option>' for d in DRIVES_LISTA
            )
            conteudo = HTML.replace("DRIVES_OPTIONS", drives_options).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(conteudo)
           drives_options = "".join(
            '<option value="' + d + '">' + d + '</option>' for d in DRIVES_LISTA
            )
            conteudo = HTML.replace("DRIVES_OPTIONS", drives_options)
            conteudo = conteudo.replace('"', '&quot;') # <- REMOVA essa linha se existir
            conteudo = conteudo.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(conteudo)

        elif path == '/api/imagens':
            pagina = int(params.get('pagina', [1])[0])
            busca = params.get('busca', [''])[0].lower()
            drive = params.get('drive', [''])[0]

            filtradas = TODAS
            if busca:
                filtradas = [i for i in filtradas if busca in i['nome'].lower() or busca in i['pasta'].lower()]
            if drive:
                filtradas = [i for i in filtradas if i['drive'] == drive]

            total = len(filtradas)
            total_pags = max(1, -(-total // POR_PAGINA))  # ceil division
            inicio = (pagina - 1) * POR_PAGINA
            pagina_imgs = filtradas[inicio:inicio + POR_PAGINA]

            resposta = {
                "total": total,
                "total_geral": len(TODAS),
                "pagina": pagina,
                "paginas": total_pags,
                "imagens": [{k: v for k, v in img.items() if k != 'mtime'} for img in pagina_imgs]
            }
            corpo = json.dumps(resposta, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(corpo)

        elif path == '/imagem':
            caminho = params.get('path', [''])[0]
            try:
                with open(caminho, 'rb') as f:
                    dados = f.read()
                mime = mimetypes.guess_type(caminho)[0] or 'image/jpeg'
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.end_headers()
                self.wfile.write(dados)
            except Exception:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


print("Servidor rodando em http://localhost:8080")
print("Pressione Ctrl+C para parar.\n")
HTTPServer(('localhost', 8080), Handler).serve_forever()