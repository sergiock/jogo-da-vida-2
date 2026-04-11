"""
servidor_unico.py
Servidor único que unifica especificador (:8181) e cores (:8282).

Uso:
    python3 servidor_unico.py
    Especificador: http://localhost:8080/
    Cores:         http://localhost:8080/cores
    Chat B:        http://localhost:8080/chatb
    Status:        http://localhost:8080/api/status
    Obsidian:      http://localhost:8080/api/obsidian

Migração:
    Substitui servidor_especificador.py (:8181) e servidor_cores.py (:8282).
    Todas as rotas originais mantidas — apenas a porta muda.
    Novas rotas de integração adicionadas (backlog itens 1-4).
"""

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE     = Path.home() / "Documents/actualsc/jogo-da-vida"
OBSIDIAN = BASE / "especificador/obsidian"
REGISTROS  = OBSIDIAN / "registros"
CONSULTAS  = OBSIDIAN / "consultas"
TEMAS      = OBSIDIAN / "temas"
EVENTOS    = OBSIDIAN / "eventos"
STATUS     = OBSIDIAN / "status.json"

HTML_ESPECIFICADOR = BASE / "especificador/prototipos/Especificador.html"
HTML_CORES         = BASE / "cores/prototipos/cores.html"
HTML_CHATB         = BASE / "chatb/index.html"

PORT = 8080

# ── APIs ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY    = os.environ.get("GOOGLE_API_KEY", "")

# ── Jogos ─────────────────────────────────────────────────────────────────────
JOGOS = {
    '01':'Caça','02':'Guerra','03':'Superação','04':'Sedução',
    '05':'Estratégia','06':'Oráculo','07':'Vício','08':'Brincadeira',
    '09':'Play','10':'Projeção','11':'Simulação','12':'Antecipação'
}

# ── Obsidian CLI ───────────────────────────────────────────────────────────────
OBSIDIAN_VAULT = str(BASE / "especificador/obsidian")

OBSIDIAN_CMDS_PERMITIDOS = {
    'files', 'search', 'read', 'daily', 'status',
}

def _executar_obsidian(args: list[str], timeout: int = 10) -> dict:
    """Executa comando obsidian CLI via subprocess. Retorna {ok, stdout, stderr}."""
    try:
        resultado = subprocess.run(
            ['obsidian'] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, 'HOME': str(Path.home())}
        )
        return {
            'ok': resultado.returncode == 0,
            'stdout': resultado.stdout.strip(),
            'stderr': resultado.stderr.strip(),
            'returncode': resultado.returncode,
        }
    except FileNotFoundError:
        return {'ok': False, 'erro': 'obsidian CLI não encontrado no PATH. Habilite em Settings → General → Command line interface.'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'erro': f'Timeout após {timeout}s'}
    except Exception as e:
        return {'ok': False, 'erro': str(e)}


# ══════════════════════════════════════════════════════════════════════════════
class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        # ── Apps ──────────────────────────────────────────────────────────────
        if path in ('/', '/index.html', '/especificador', '/especificador/'):
            self._serve_file(HTML_ESPECIFICADOR, "text/html; charset=utf-8")

        elif path in ('/cores', '/cores/'):
            self._serve_file(HTML_CORES, "text/html; charset=utf-8")

        elif path in ('/chatb', '/chatb/'):
            self._serve_file(HTML_CHATB, "text/html; charset=utf-8")

        # ── Status (compartilhado) ─────────────────────────────────────────────
        elif path == '/api/status':
            if STATUS.exists():
                self._json(json.loads(STATUS.read_text(encoding='utf-8')))
            else:
                self._json({'fase': '', 'jogo': ''})

        # ══════════════════════════════════════════════════════════════════════
        # OBSIDIAN CLI — GET /api/obsidian?cmd=files|search|read|daily|status
        # Exemplos:
        #   /api/obsidian?cmd=files
        #   /api/obsidian?cmd=search&q=animalgame
        #   /api/obsidian?cmd=read&file=registros/2026-03-25.md
        #   /api/obsidian?cmd=daily
        # ══════════════════════════════════════════════════════════════════════
        elif path == '/api/obsidian':
            cmd = qs.get('cmd', [''])[0]
            if not cmd:
                self._json({'ok': False, 'erro': 'Parâmetro cmd obrigatório'})
                return

            if cmd not in OBSIDIAN_CMDS_PERMITIDOS:
                self._json({'ok': False, 'erro': f'Comando não permitido: {cmd}. Permitidos: {sorted(OBSIDIAN_CMDS_PERMITIDOS)}'})
                return

            args = [cmd]

            if cmd == 'search':
                q = qs.get('q', [''])[0]
                if not q:
                    self._json({'ok': False, 'erro': 'Parâmetro q obrigatório para search'})
                    return
                args += [q]

            elif cmd == 'read':
                file = qs.get('file', [''])[0]
                if not file:
                    self._json({'ok': False, 'erro': 'Parâmetro file obrigatório para read'})
                    return
                # Sanitiza path — sem traversal
                if '..' in file or file.startswith('/'):
                    self._json({'ok': False, 'erro': 'Path inválido'})
                    return
                args += [f'file={file}']

            resultado = _executar_obsidian(args)
            self._json(resultado)

        # ══════════════════════════════════════════════════════════════════════
        # ROTAS DO ESPECIFICADOR (originais de :8181)
        # ══════════════════════════════════════════════════════════════════════

        elif path == "/api/registro/hoje":
            hoje = datetime.now().strftime('%Y-%m-%d')
            arquivo = REGISTROS / f"{hoje}.md"
            if arquivo.exists():
                self._json(self._parse_registro(arquivo.read_text(encoding="utf-8")))
            else:
                self._json({})

        elif path == "/api/registros":
            arquivos = sorted(REGISTROS.glob("*.md"), reverse=True)
            lista = []
            for a in arquivos[:30]:
                try:
                    dados = self._parse_registro(a.read_text(encoding="utf-8"))
                    dados["arquivo"] = a.name
                    lista.append(dados)
                except Exception:
                    pass
            self._json(lista)

        elif path == "/api/notas":
            limite = int(qs.get("limite", [60])[0])
            notas  = []
            for a in REGISTROS.glob("*.md"):
                try:
                    dados = self._parse_registro(a.read_text(encoding="utf-8"))
                    dados["arquivo"]  = a.name
                    dados["tipo"]     = "registro"
                    dados["sort_key"] = dados.get("data","") + "T" + dados.get("hora","00:00")
                    notas.append(dados)
                except Exception:
                    pass
            for a in CONSULTAS.glob("*.md"):
                try:
                    conteudo = a.read_text(encoding="utf-8")
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ["servico","fase","jogo","data","hora","session_id","registro_origem","titulo"]:
                            if linha.startswith(campo + ":"):
                                dados[campo] = linha.split(":",1)[1].strip()
                    if not dados.get("titulo"):
                        for linha in conteudo.splitlines():
                            if linha.startswith("# "):
                                dados["titulo"] = linha[2:].strip(); break
                    secao = None
                    for linha in conteudo.splitlines():
                        if linha == "## Pergunta": secao = "pergunta"; continue
                        if linha == "## Resposta": secao = "resposta"; continue
                        if linha.startswith("## "): secao = None; continue
                        if secao == "pergunta" and not dados.get("pergunta") and linha.strip():
                            dados["pergunta"] = linha.strip()
                        if secao == "resposta" and not dados.get("resposta_preview") and linha.strip():
                            dados["resposta_preview"] = linha.strip()[:120]
                    dados["arquivo"]  = a.name
                    dados["tipo"]     = "consulta"
                    dados["sort_key"] = dados.get("data","") + "T" + dados.get("hora","00:00")
                    notas.append(dados)
                except Exception:
                    pass
            notas.sort(key=lambda x: x.get("sort_key",""), reverse=True)
            self._json(notas[:limite])

        elif path == "/api/temas":
            lista = []
            if TEMAS.exists():
                for a in sorted(TEMAS.glob("*.md"), reverse=True):
                    try:
                        conteudo = a.read_text(encoding="utf-8")
                        dados = {}
                        for linha in conteudo.splitlines():
                            for campo in ["nome","data","caminho_origem","arquivos_processados"]:
                                if linha.startswith(campo + ":"):
                                    dados[campo] = linha.split(":",1)[1].strip()
                        if not dados.get("nome"):
                            for linha in conteudo.splitlines():
                                if linha.startswith("# "):
                                    dados["nome"] = linha[2:].strip(); break
                        dados["arquivo"] = a.name
                        lista.append(dados)
                    except Exception:
                        pass
            self._json(lista)

        elif path == "/api/matriz":
            self._json(self._carregar_matriz())

        elif path == "/api/matriz/gerar":
            self._json(self._gerar_sugestoes_matriz())

        elif path == "/api/sessao":
            session_id = qs.get("id",[""])[0]
            formato    = qs.get("formato",["json"])[0]
            self._json(self._exportar_sessao(session_id, formato))

        elif path == "/api/anexos":
            registro = qs.get("registro", [""])[0]
            anexos_dir = OBSIDIAN / "anexos"
            if not registro:
                self._json({"arquivos": []})
            else:
                stem = registro.replace(".md", "")
                arquivos = sorted(f.name for f in anexos_dir.glob(f"{stem}_*")) if anexos_dir.exists() else []
                self._json({"arquivos": arquivos})

        elif path.startswith("/api/anexo") and "upload" not in path:
            arquivo = qs.get("arquivo", [""])[0]
            if not arquivo or ".." in arquivo or "/" in arquivo:
                self.send_response(404); self.end_headers(); return
            caminho = OBSIDIAN / "anexos" / arquivo
            if not caminho.exists():
                self.send_response(404); self.end_headers(); return
            ext = caminho.suffix.lower()
            tipos = {".pdf":"application/pdf",".jpg":"image/jpeg",".jpeg":"image/jpeg",
                     ".png":"image/png",".gif":"image/gif",".webp":"image/webp",
                     ".mp3":"audio/mpeg",".m4a":"audio/mp4",".txt":"text/plain",".md":"text/plain"}
            ct = tipos.get(ext, "application/octet-stream")
            conteudo = caminho.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(conteudo)
            return

        elif path == "/api/consultas":
            ref = qs.get("ref",[""])[0]
            lista = []
            for a in sorted(CONSULTAS.glob("*.md"), reverse=True)[:50]:
                try:
                    conteudo = a.read_text(encoding="utf-8")
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ["servico","fase","jogo","data","hora","registro_origem","titulo"]:
                            if linha.startswith(campo + ":"):
                                dados[campo] = linha.split(":",1)[1].strip()
                    if not dados.get("titulo"):
                        for linha in conteudo.splitlines():
                            if linha.startswith("# "):
                                dados["titulo"] = linha[2:].strip(); break
                    dados["arquivo"] = a.name
                    if not ref or dados.get("registro_origem","") == ref:
                        lista.append(dados)
                except Exception:
                    pass
            self._json(lista)

        # ══════════════════════════════════════════════════════════════════════
        # ROTAS DO CORES (originais de :8282)
        # ══════════════════════════════════════════════════════════════════════

        elif path == '/api/eventos':
            limite = int(qs.get('limite', [20])[0])
            arquivos = sorted(EVENTOS.glob('*.md'), reverse=True)
            lista = []
            for a in arquivos[:limite]:
                try:
                    dados = self._parse_evento(a.read_text(encoding='utf-8'))
                    dados['arquivo'] = a.name
                    lista.append(dados)
                except Exception:
                    pass
            self._json(lista)

        elif path == '/api/padroes':
            arquivos = sorted(EVENTOS.glob('*.md'), reverse=True)
            lista = []
            for a in arquivos[:50]:
                try:
                    dados = self._parse_evento(a.read_text(encoding='utf-8'))
                    dados['arquivo'] = a.name
                    lista.append(dados)
                except Exception:
                    pass
            self._json(lista)

        elif path == '/api/conexoes':
            self._json(self._buscar_conexoes(qs))

        # ══════════════════════════════════════════════════════════════════════
        # ROTAS DE INTEGRAÇÃO (backlog itens 1-4)
        # ══════════════════════════════════════════════════════════════════════

        elif path == '/api/integracao/contexto-registro':
            jogo  = qs.get('jogo',  [''])[0]
            limite = int(qs.get('limite', [3])[0])
            lista = []
            for a in sorted(REGISTROS.glob('*.md'), reverse=True)[:20]:
                try:
                    dados = self._parse_registro(a.read_text(encoding='utf-8'))
                    dados['arquivo'] = a.name
                    if not jogo or dados.get('jogo_ativo','').startswith(jogo):
                        lista.append({
                            'arquivo': dados['arquivo'],
                            'data':    dados.get('data',''),
                            'agora':   dados.get('agora','')[:200],
                            'foco':    dados.get('foco','')[:200],
                        })
                    if len(lista) >= limite:
                        break
                except Exception:
                    pass
            self._json({'ok': True, 'registros': lista})

        elif path == '/api/integracao/sugestoes-registro':
            jogo  = qs.get('jogo',  [''])[0]
            hoje  = datetime.now().strftime('%Y-%m-%d')
            lista = []
            for a in sorted(EVENTOS.glob('*.md'), reverse=True)[:30]:
                try:
                    dados = self._parse_evento(a.read_text(encoding='utf-8'))
                    dados['arquivo'] = a.name
                    data_evento = dados.get('data','')
                    if data_evento == hoje or data_evento >= hoje[:7]:
                        if not jogo or dados.get('jogo','') == jogo:
                            lista.append({
                                'arquivo':   dados['arquivo'],
                                'descricao': dados.get('descricao',''),
                                'tipo':      dados.get('tipo',[]),
                                'impacto':   dados.get('impacto',[]),
                                'data':      dados.get('data',''),
                                'hora':      dados.get('hora',''),
                            })
                except Exception:
                    pass
            self._json({'ok': True, 'eventos': lista[:10]})

        elif path == '/api/integracao/temas-evento':
            palavras = qs.get('q', [''])[0].lower().split()
            lista = []
            if TEMAS.exists() and palavras:
                for a in sorted(TEMAS.glob('*.md'), reverse=True)[:20]:
                    try:
                        conteudo = a.read_text(encoding='utf-8')
                        score = sum(1 for p in palavras if p in conteudo.lower())
                        if score > 0:
                            nome = ''
                            preview = ''
                            for linha in conteudo.splitlines():
                                if linha.startswith('# ') and not nome:
                                    nome = linha[2:].strip()
                                if linha.strip() and not linha.startswith('#') and not linha.startswith('---') and not linha.startswith('tags:') and not preview:
                                    preview = linha.strip()[:150]
                            lista.append({'arquivo': a.name, 'nome': nome, 'preview': preview, 'score': score})
                    except Exception:
                        pass
            lista.sort(key=lambda x: x['score'], reverse=True)
            self._json({'ok': True, 'temas': lista[:5]})

        elif path == '/api/integracao/matriz-cores':
            matriz = self._carregar_matriz()
            status = {}
            if STATUS.exists():
                try:
                    status = json.loads(STATUS.read_text(encoding='utf-8'))
                except Exception:
                    pass
            self._json({
                'ok':     True,
                'matriz': matriz.get('matriz', {}),
                'fase':   status.get('fase',''),
                'jogo':   status.get('jogo',''),
            })

        else:
            self._serve_static(path)

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)

        # Upload de arquivo (multipart)
        if path == '/api/anexo/upload':
            self._json(self._upload_anexo(body, self.headers))
            return

        try:
            dados = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # ── Especificador POSTs ───────────────────────────────────────────────
        if path == "/api/registro/salvar":
            self._json(self._salvar_registro(dados))

        elif path == "/api/status/salvar":
            self._json(self._salvar_status(dados))

        elif path == "/api/objetivo/salvar":
            self._json(self._salvar_objetivo(dados))

        elif path == "/api/consulta/claude":
            self._json(self._consultar_claude(dados))

        elif path == "/api/consulta/gemini":
            self._json(self._consultar_gemini(dados))

        elif path == "/api/consulta/salvar":
            self._json(self._salvar_consulta(dados))

        elif path == "/api/tema/inspecionar":
            self._json(self._inspecionar_tema(dados))

        elif path == "/api/tema/processar":
            self._json(self._processar_tema(dados))

        elif path == "/api/matriz/salvar":
            self._json(self._salvar_matriz(dados))

        elif path == "/api/excluir":
            self._json(self._excluir_nota(dados))

        elif path == "/api/registro/sessao":
            self._json(self._atualizar_sessao(dados))

        elif path == "/api/sessao/gerar":
            self._json(self._gerar_arquivo_sessao(dados))

        # ── Cores POSTs ───────────────────────────────────────────────────────
        elif path == '/api/evento/salvar':
            self._json(self._salvar_evento(dados))

        elif path == '/api/consulta/salvar/cores':
            self._json(self._salvar_consulta_cores(dados))

        # ── Integração POSTs ──────────────────────────────────────────────────
        elif path == '/api/integracao/sessao/salvar':
            self._json(self._salvar_sessao_desenvolvimento(dados))

        # ══════════════════════════════════════════════════════════════════════
        # OBSIDIAN CLI — POST /api/obsidian
        # Body: { "cmd": "create", "name": "...", "content": "..." }
        #       { "cmd": "append", "file": "...", "content": "..." }
        # ══════════════════════════════════════════════════════════════════════
        elif path == '/api/obsidian':
            cmd = dados.get('cmd', '')
            CMDS_POST = {'create', 'append'}

            if cmd not in CMDS_POST:
                self._json({'ok': False, 'erro': f'Comando POST não permitido: {cmd}. Permitidos: {sorted(CMDS_POST)}'})
                return

            args = [cmd]

            if cmd == 'create':
                name    = dados.get('name', '').strip()
                content = dados.get('content', '')
                if not name:
                    self._json({'ok': False, 'erro': 'Campo name obrigatório para create'})
                    return
                args += [f'name={name}', f'content={content}']

            elif cmd == 'append':
                file    = dados.get('file', '').strip()
                content = dados.get('content', '')
                if not file:
                    self._json({'ok': False, 'erro': 'Campo file obrigatório para append'})
                    return
                if '..' in file or file.startswith('/'):
                    self._json({'ok': False, 'erro': 'Path inválido'})
                    return
                args += [f'file={file}', f'content={content}']

            resultado = _executar_obsidian(args)
            self._json(resultado)

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS COMPARTILHADOS
    # ══════════════════════════════════════════════════════════════════════════

    def _serve_static(self, path):
        STATIC = {
            '/hub.html':     BASE / 'hub.html',
            '/chatb':        BASE / 'chatb/index.html',
        }
        if path.startswith('/chatb/'):
            arquivo = BASE / path.lstrip('/')
        elif path in STATIC:
            arquivo = STATIC[path]
        else:
            self.send_response(404)
            self.end_headers()
            return
        try:
            ext = Path(path).suffix.lower()
            tipos = {'.html':'text/html; charset=utf-8', '.js':'application/javascript', '.css':'text/css'}
            ct = tipos.get(ext, 'text/plain')
            self._serve_file(arquivo, ct)
        except Exception:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, filepath, content_type):
        try:
            conteudo = Path(filepath).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(conteudo)
        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Arquivo não encontrado: {filepath}".encode())

    def _json(self, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(corpo)

    # ══════════════════════════════════════════════════════════════════════════
    # LÓGICA DO ESPECIFICADOR
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_registro(self, conteudo):
        dados = {
            'titulo':'','data':'','hora':'','fase':'','jogo_ativo':'',
            'agora':'','foco':'','reflexao':'','session_id':''
        }
        secao = None
        linhas_secao = []
        for linha in conteudo.splitlines():
            for campo in ['titulo','data','hora','fase','jogo_ativo','session_id']:
                if linha.startswith(campo + ':'):
                    dados[campo] = linha.split(':',1)[1].strip()
            if linha.startswith('## Agora'):   secao = 'agora';    linhas_secao = []; continue
            if linha.startswith('## Foco'):    secao = 'foco';     linhas_secao = []; continue
            if linha.startswith('## Reflexão'):secao = 'reflexao'; linhas_secao = []; continue
            if linha.startswith('## '):        secao = None
            if secao and linha.strip() and not linha.startswith('---'):
                linhas_secao.append(linha.strip())
                dados[secao] = ' '.join(linhas_secao)
        return dados

    def _salvar_registro(self, dados):
        agora_dt  = datetime.now()
        hoje      = agora_dt.strftime('%Y-%m-%d')
        hora_br   = agora_dt.strftime('%H:%M')
        data_br   = agora_dt.strftime('%d/%m/%Y')

        titulo     = dados.get('titulo','').strip() or f"Registro {data_br}"
        agora_txt  = dados.get('agora','').strip()
        foco_txt   = dados.get('foco','').strip()
        reflexao   = dados.get('reflexao','').strip()
        fase       = dados.get('fase','')
        jogo_ativo = dados.get('jogo_ativo','')
        session_id = dados.get('session_id','')

        status = {}
        if STATUS.exists():
            try: status = json.loads(STATUS.read_text(encoding='utf-8'))
            except: pass
        fase       = fase       or status.get('fase','')
        jogo_ativo = jogo_ativo or status.get('jogo','')

        tags = ['registro']
        if fase:       tags.append(f'fase/{fase}')
        if jogo_ativo: tags.append(f'jogo/{jogo_ativo[:2]}')
        tags_str = ', '.join(tags)

        conteudo = f"""---
tags: [{tags_str}]
titulo: {titulo}
data: {hoje}
hora: {hora_br}
fase: {fase}
jogo_ativo: {jogo_ativo}
session_id: {session_id}
---

# {titulo}

> {data_br} · {hora_br} · {fase} · {jogo_ativo}

## Agora
{agora_txt or '_não preenchido_'}

## Foco
{foco_txt or '_não preenchido_'}

## Reflexão
{reflexao or '_não preenchido_'}
"""
        REGISTROS.mkdir(parents=True, exist_ok=True)
        arquivo = REGISTROS / f"{hoje}.md"
        arquivo.write_text(conteudo, encoding='utf-8')
        print(f"  ✅ Registro salvo: {arquivo.name}")
        return {'ok': True, 'arquivo': arquivo.name}

    def _salvar_status(self, dados):
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  ✅ Status salvo: fase={dados.get('fase')} jogo={dados.get('jogo')}")
        return {'ok': True}

    def _salvar_objetivo(self, dados):
        arquivo = OBSIDIAN / "objetivos/atual.md"
        conteudo = arquivo.read_text(encoding='utf-8') if arquivo.exists() else "# Objetivos\n\n"
        frente = dados.get('frente','geral')
        texto  = dados.get('texto','')
        conteudo += f"\n- [ ] {texto} #{frente}"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo, encoding='utf-8')
        return {'ok': True}

    def _upload_anexo(self, body, headers):
        """Recebe multipart/form-data com 'file' e 'registro', salva em obsidian/anexos/."""
        import email
        from email import policy as epolicy
        ct = headers.get('Content-Type', '')
        if 'boundary=' not in ct:
            return {'ok': False, 'erro': 'Content-Type inválido'}
        boundary = ct.split('boundary=')[-1].strip()
        # Parse manual do multipart
        sep = ('--' + boundary).encode()
        partes = body.split(sep)
        nome_arquivo = None
        conteudo_arquivo = None
        registro = ''
        for parte in partes:
            if b'Content-Disposition' not in parte:
                continue
            header_end = parte.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            header_bytes = parte[:header_end]
            data_bytes   = parte[header_end+4:].rstrip(b'\r\n--')
            header_str   = header_bytes.decode('utf-8', errors='ignore')
            if 'name="registro"' in header_str:
                registro = data_bytes.decode('utf-8', errors='ignore').strip()
            elif 'name="file"' in header_str:
                m = re.search(r'filename="([^"]+)"', header_str)
                if m:
                    nome_arquivo   = m.group(1)
                    conteudo_arquivo = data_bytes
        if not nome_arquivo or conteudo_arquivo is None:
            return {'ok': False, 'erro': 'arquivo não recebido'}
        # Prefixo com stem do registro para associação
        stem = registro.replace('.md', '') if registro else 'avulso'
        # Sanitiza nome
        nome_seguro = re.sub(r'[^\w.\-]', '_', nome_arquivo)
        nome_final  = f"{stem}_{nome_seguro}"
        anexos_dir  = OBSIDIAN / 'anexos'
        anexos_dir.mkdir(parents=True, exist_ok=True)
        destino = anexos_dir / nome_final
        destino.write_bytes(conteudo_arquivo)
        print(f"  ✅ Anexo salvo: anexos/{nome_final}")
        # Adiciona link no .md do registro
        if registro:
            arq_reg = REGISTROS / registro
            if arq_reg.exists():
                texto = arq_reg.read_text(encoding='utf-8')
                link  = f"![[anexos/{nome_final}]]"
                if '## Anexos' in texto:
                    texto = texto.replace('## Anexos\n', f'## Anexos\n{link}\n')
                else:
                    texto += f'\n\n## Anexos\n{link}\n'
                arq_reg.write_text(texto, encoding='utf-8')
        return {'ok': True, 'arquivo': nome_final}

    def _gerar_arquivo_sessao(self, dados):
        """Gera e salva um .md completo com registros + consultas de uma sessão."""
        session_id = dados.get('session_id', '').strip()
        if not session_id:
            return {'ok': False, 'erro': 'session_id não informado'}

        agora = datetime.now()
        hoje  = agora.strftime('%Y-%m-%d')
        hora  = agora.strftime('%H:%M')

        # Coleta registros
        registros = []
        for a in sorted(REGISTROS.glob('*.md')):
            try:
                conteudo = a.read_text(encoding='utf-8')
                d = self._parse_registro(conteudo)
                if d.get('session_id') == session_id:
                    d['arquivo'] = a.name
                    d['conteudo_raw'] = conteudo
                    registros.append(d)
            except: pass

        # Coleta consultas com conteúdo completo
        consultas = []
        for a in sorted(CONSULTAS.glob('*.md')):
            try:
                conteudo = a.read_text(encoding='utf-8')
                if session_id not in conteudo:
                    continue
                d = {'arquivo': a.name, 'pergunta': '', 'resposta': '', 'servico': '', 'data': '', 'hora': ''}
                secao = None
                linhas_secao = []
                for linha in conteudo.splitlines():
                    for campo in ['servico', 'data', 'hora', 'session_id']:
                        if linha.startswith(campo + ':'):
                            d[campo] = linha.split(':', 1)[1].strip()
                    if linha == '## Pergunta':
                        if secao: d[secao] = '\n'.join(linhas_secao).strip()
                        secao = 'pergunta'; linhas_secao = []
                    elif linha == '## Resposta':
                        if secao: d[secao] = '\n'.join(linhas_secao).strip()
                        secao = 'resposta'; linhas_secao = []
                    elif secao and not linha.startswith('##') and not linha.startswith('---'):
                        linhas_secao.append(linha)
                if secao: d[secao] = '\n'.join(linhas_secao).strip()
                if d.get('session_id') == session_id:
                    consultas.append(d)
            except: pass

        if not registros and not consultas:
            return {'ok': False, 'erro': f'Nenhum conteúdo encontrado para sessão: {session_id}'}

        # Monta o documento
        linhas = [
            f'---',
            f'tags: [sessao, exportacao]',
            f'session_id: {session_id}',
            f'data_export: {hoje}',
            f'hora_export: {hora}',
            f'total_registros: {len(registros)}',
            f'total_consultas: {len(consultas)}',
            f'---',
            f'',
            f'# Sessão: {session_id}',
            f'',
            f'> Exportado em {hoje} às {hora}  ',
            f'> {len(registros)} registro(s) · {len(consultas)} consulta(s)',
            f'',
            f'---',
            f'',
        ]

        for r in registros:
            linhas += [
                f'## Registro — {r.get("data","")} {r.get("hora","")}',
                f'**Título:** {r.get("titulo","—")}  ',
                f'**Fase:** {r.get("fase","—")} · **Jogo:** {r.get("jogo","—")}',
                f'',
            ]
            if r.get('agora'):
                linhas += [f'### Como estava', r['agora'], '']
            if r.get('foco'):
                linhas += [f'### Foco', r['foco'], '']
            if r.get('reflexao'):
                linhas += [f'### Reflexão', r['reflexao'], '']
            linhas.append('---')
            linhas.append('')

        for c in consultas:
            linhas += [
                f'## Consulta {c.get("servico","").title()} — {c.get("data","")} {c.get("hora","")}',
                f'',
            ]
            if c.get('pergunta'):
                linhas += [f'**Pergunta:**', c['pergunta'], '']
            if c.get('resposta'):
                linhas += [f'**Resposta:**', c['resposta'], '']
            linhas.append('---')
            linhas.append('')

        conteudo_final = '\n'.join(linhas)

        # Salva em especificador/obsidian/sessoes/
        sessoes_dir = OBSIDIAN / 'sessoes'
        sessoes_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r'[^a-z0-9-]', '-', session_id.lower())[:50]
        nome_arquivo = f'{hoje}-{slug}.md'
        caminho = sessoes_dir / nome_arquivo
        caminho.write_text(conteudo_final, encoding='utf-8')
        print(f'  ✅ Sessão exportada: sessoes/{nome_arquivo}')

        return {
            'ok': True,
            'arquivo': f'sessoes/{nome_arquivo}',
            'total_registros': len(registros),
            'total_consultas': len(consultas),
            'texto': conteudo_final
        }

    def _atualizar_sessao(self, dados):
        arquivo = dados.get('arquivo', '')
        novo_id = dados.get('session_id', '').strip()
        if not arquivo or '..' in arquivo or '/' in arquivo:
            return {'ok': False, 'erro': 'arquivo inválido'}
        caminho = REGISTROS / arquivo
        if not caminho.exists():
            return {'ok': False, 'erro': 'arquivo não encontrado'}

        # Atualiza o registro
        conteudo = caminho.read_text(encoding='utf-8')
        if re.search(r'^session_id:', conteudo, re.MULTILINE):
            conteudo = re.sub(r'^session_id:.*$', f'session_id: {novo_id}', conteudo, flags=re.MULTILINE)
        else:
            conteudo = conteudo.replace('---\n\n#', f'session_id: {novo_id}\n---\n\n#', 1)
        caminho.write_text(conteudo, encoding='utf-8')
        print(f"  ✅ Sessão atualizada: {arquivo} → {novo_id}")

        # Propaga para consultas associadas (registro_origem == arquivo)
        consultas_atualizadas = 0
        nome_sem_ext = arquivo.replace('.md', '')
        for c in CONSULTAS.glob('*.md'):
            try:
                texto = c.read_text(encoding='utf-8')
                if f'registro_origem: {arquivo}' not in texto and f'registro_origem: {nome_sem_ext}' not in texto:
                    continue
                if re.search(r'^session_id:', texto, re.MULTILINE):
                    texto = re.sub(r'^session_id:.*$', f'session_id: {novo_id}', texto, flags=re.MULTILINE)
                else:
                    texto = texto.replace('---\n\n#', f'session_id: {novo_id}\n---\n\n#', 1)
                c.write_text(texto, encoding='utf-8')
                consultas_atualizadas += 1
                print(f"  ✅ Consulta propagada: {c.name} → {novo_id}")
            except: pass

        return {'ok': True, 'arquivo': arquivo, 'session_id': novo_id, 'consultas_atualizadas': consultas_atualizadas}

    def _excluir_nota(self, dados):
        tipo    = dados.get('tipo','')
        arquivo = dados.get('arquivo','')
        if not arquivo or '..' in arquivo or '/' in arquivo:
            return {'ok': False, 'erro': 'Arquivo inválido'}
        if tipo == 'registro':   caminho = REGISTROS / arquivo
        elif tipo == 'consulta': caminho = CONSULTAS / arquivo
        else: return {'ok': False, 'erro': 'Tipo inválido'}
        if not caminho.exists():
            return {'ok': False, 'erro': 'Arquivo não encontrado'}
        if tipo == 'registro':
            for consulta in CONSULTAS.glob('*.md'):
                try:
                    texto = consulta.read_text(encoding='utf-8')
                    if arquivo in texto:
                        texto = texto.replace(f"[[registros/{arquivo}]]", f"_(excluído: {arquivo})_")
                        consulta.write_text(texto, encoding='utf-8')
                except Exception:
                    pass
        caminho.unlink()
        print(f"  🗑️  Excluído: {caminho.name}")
        return {'ok': True, 'arquivo': arquivo}

    def _consultar_claude(self, dados):
        if not ANTHROPIC_API_KEY:
            return {'ok': False, 'erro': 'ANTHROPIC_API_KEY não configurada'}
        nota     = dados.get('nota','')
        pergunta = dados.get('pergunta','').strip()
        ref      = dados.get('ref','')
        fase     = dados.get('fase','')
        jogo     = dados.get('jogo','')
        if not pergunta:
            pergunta = "Analise esta nota sob a perspectiva do jogo da vida e das fases (Fogo, Ar, Água, Terra, Éter). Identifique padrões, o jogo dominante e sugira próximos passos."
        prompt = f"{pergunta}\n\n---\n{nota}"
        try:
            payload = json.dumps({
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resultado = json.loads(resp.read().decode('utf-8'))
                resposta  = resultado["content"][0]["text"]
            arquivo = self._salvar_consulta({
                "servico": "claude", "pergunta": pergunta,
                "resposta": resposta, "ref": ref, "fase": fase, "jogo": jogo
            })
            return {"ok": True, "resposta": resposta, "arquivo": arquivo.get("arquivo","")}
        except Exception as e:
            return {"ok": False, "erro": str(e)}

    def _consultar_gemini(self, dados):
        if not GOOGLE_API_KEY:
            return {'ok': False, 'erro': 'GOOGLE_API_KEY não configurada'}
        nota     = dados.get('nota','')
        pergunta = dados.get('pergunta','Analise esta nota sob a perspectiva do jogo da vida.')
        ref      = dados.get('ref','')
        prompt   = f"{pergunta}\n\n---\n{nota}"
        try:
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                resultado = json.loads(resp.read().decode('utf-8'))
                resposta  = resultado["candidates"][0]["content"]["parts"][0]["text"]
            arquivo = self._salvar_consulta({"servico": "gemini", "pergunta": pergunta, "resposta": resposta, "ref": ref})
            return {"ok": True, "resposta": resposta, "arquivo": arquivo.get("arquivo","")}
        except Exception as e:
            return {"ok": False, "erro": str(e)}

    def _salvar_consulta(self, dados):
        agora_dt  = datetime.now()
        timestamp = agora_dt.strftime('%Y-%m-%d-%H%M')
        data_br   = agora_dt.strftime('%d/%m/%Y %H:%M')
        servico    = dados.get('servico','manual')
        pergunta   = dados.get('pergunta','')
        resposta   = dados.get('resposta','')
        ref        = dados.get('ref','')
        fase       = dados.get('fase','')
        jogo       = dados.get('jogo','')
        session_id = dados.get('session_id','')
        if not fase or not jogo:
            if STATUS.exists():
                try:
                    status = json.loads(STATUS.read_text(encoding='utf-8'))
                    fase = fase or status.get('fase','')
                    jogo = jogo or status.get('jogo','')
                except: pass
        nome_arquivo = f"{timestamp}-consulta-{servico}.md"
        tags = ['consulta', f'consulta/{servico}']
        if fase: tags.append(f'fase/{fase}')
        if jogo: tags.append(f'jogo/{jogo[:2]}')
        ref_stem = ref.replace('.md','') if ref else ''
        titulo   = f"{ref_stem} · {servico.title()} · {data_br}" if ref_stem else f"{servico.title()} · {data_br}"
        conteudo = f"""---
tags: [{', '.join(tags)}]
data: {agora_dt.strftime('%Y-%m-%d')}
hora: {agora_dt.strftime('%H:%M')}
servico: {servico}
session_id: {session_id}
fase: {fase}
jogo: {jogo}
registro_origem: {ref}
---

# {titulo}

{('> Origem: [[registros/' + ref + ']]') if ref else ''}
{('> Sessão: ' + session_id) if session_id else ''}

## Pergunta
{pergunta or '_prompt padrão_'}

## Resposta
{resposta}
"""
        CONSULTAS.mkdir(parents=True, exist_ok=True)
        (CONSULTAS / nome_arquivo).write_text(conteudo, encoding='utf-8')
        print(f"  ✅ Consulta salva: {nome_arquivo}")
        if ref:
            arq_reg = REGISTROS / ref
            if arq_reg.exists():
                texto = arq_reg.read_text(encoding='utf-8')
                link  = f"- [[consultas/{nome_arquivo}]] — {servico.title()} · {data_br}"
                if '## Consultas' in texto:
                    texto = texto.replace('## Consultas', '## Consultas\n' + link)
                else:
                    texto += f'\n\n## Consultas\n{link}\n'
                arq_reg.write_text(texto, encoding='utf-8')
        return {'ok': True, 'arquivo': nome_arquivo}

    def _carregar_matriz(self):
        matriz_json = OBSIDIAN / "objetivos/matriz.json"
        if matriz_json.exists():
            try: return {"ok": True, "matriz": json.loads(matriz_json.read_text(encoding='utf-8'))}
            except: pass
        return {"ok": True, "matriz": {}}

    def _gerar_sugestoes_matriz(self):
        PADROES = {
            "pessoal":    ["saúde","corpo","mente","lucidez","consciência","equilíbrio","bem-estar","energia","foco","descanso","autoconhecimento","identidade","propósito"],
            "social":     ["relação","pessoa","família","amigo","coletivo","comunidade","impacto","sociedade","parceria","colaboração","projeto","financiamento","usuário"],
            "frentes":    ["especificador","cores","desenvolvimento","código","programar","site","html","python","obsidian","funding","api","protótipo","servidor","deploy"],
            "obstaculos": ["dificuldade","problema","bloqueio","travado","confuso","perdido","dependência","vício","automático","obstáculo","barreira","limitação"],
            "proximos":   ["preciso","vou","quero","próximo","agora","hoje","amanhã","implementar","criar","fazer","resolver","testar","validar","decidir","começar"]
        }
        sugestoes = {k: [] for k in PADROES}
        frases_vistas = set()
        registros_analisados = 0
        for a in sorted(REGISTROS.glob('*.md'), reverse=True)[:20]:
            try:
                conteudo = a.read_text(encoding='utf-8')
                registros_analisados += 1
                texto = ' '.join(l for l in conteudo.splitlines() if l.strip() and not l.startswith('---') and not l.startswith('tags:'))
                for frase in re.split(r'[.!?]+', texto):
                    frase = frase.strip()
                    if not (15 <= len(frase) <= 200): continue
                    chave = frase[:50].lower()
                    if chave in frases_vistas: continue
                    for secao, palavras in PADROES.items():
                        if any(p in frase.lower() for p in palavras):
                            sugestoes[secao].append({"texto": frase[0].upper()+frase[1:], "feito": False, "origem": True})
                            frases_vistas.add(chave)
                            break
            except: pass
        for secao in sugestoes:
            sugestoes[secao] = sugestoes[secao][:8]
        return {"ok": True, "sugestoes": sugestoes, "registros_analisados": registros_analisados}

    def _salvar_matriz(self, dados):
        matriz = dados.get('matriz', {})
        agora  = datetime.now()
        hoje   = agora.strftime('%Y-%m-%d')
        hora   = agora.strftime('%H:%M')
        obj_dir = OBSIDIAN / "objetivos"
        obj_dir.mkdir(parents=True, exist_ok=True)
        (obj_dir / "matriz.json").write_text(json.dumps(matriz, ensure_ascii=False, indent=2), encoding='utf-8')
        SECOES = {
            "pessoal":    ("◎","Objetivos Pessoais","saúde, lucidez, desenvolvimento"),
            "social":     ("◉","Objetivos Sociais","relações, coletivo, impacto"),
            "frentes":    ("◈","Frentes de Ação","especificador, cores, dev"),
            "obstaculos": ("◐","Obstáculos","padrões a superar"),
            "proximos":   ("◇","Próximos Passos","ações concretas imediatas"),
        }
        secoes_md = []
        for sid, (ico, titulo, desc) in SECOES.items():
            itens = matriz.get(sid, [])
            if not itens: continue
            linhas = [f"- [{'x' if i.get('feito') else ' '}] {i.get('texto','')}{' _(registros)_' if i.get('origem') else ''}" for i in itens]
            secoes_md.append(f"## {ico} {titulo}\n_{desc}_\n\n" + "\n".join(linhas))
        md = f"---\ntags: [matriz, objetivos]\ndata: {hoje}\natualizado: {hoje} {hora}\n---\n\n# Matriz de Objetivos\n\n> Atualizada em {hoje} às {hora}\n\n" + "\n\n".join(secoes_md) + "\n"
        (obj_dir / "matriz.md").write_text(md, encoding='utf-8')
        print(f"  ✅ Matriz salva")
        return {'ok': True}

    def _exportar_sessao(self, session_id, formato="json"):
        if not session_id:
            return {'ok': False, 'erro': 'session_id não informado'}
        registros = []
        for a in REGISTROS.glob('*.md'):
            try:
                conteudo = a.read_text(encoding='utf-8')
                if session_id in conteudo:
                    dados = self._parse_registro(conteudo)
                    dados['arquivo'] = a.name
                    registros.append(dados)
            except: pass
        consultas = []
        for a in CONSULTAS.glob('*.md'):
            try:
                conteudo = a.read_text(encoding='utf-8')
                if session_id in conteudo:
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ['servico','fase','jogo','data','hora','titulo']:
                            if linha.startswith(campo + ':'): dados[campo] = linha.split(':',1)[1].strip()
                    dados['arquivo'] = a.name
                    consultas.append(dados)
            except: pass
        return {'ok': True, 'session_id': session_id, 'registros': registros, 'consultas': consultas}

    def _inspecionar_tema(self, dados):
        caminho = Path(dados.get('caminho','')).expanduser()
        if not caminho.exists():
            return {'ok': False, 'erro': f'Diretório não encontrado: {caminho}'}
        exts = {'.md','.txt','.py','.js','.html','.css','.json','.yaml','.yml','.csv','.pdf','.docx'}
        arquivos = []
        total_chars = 0
        for f in sorted(caminho.rglob('*')):
            if f.is_file() and not f.name.startswith('.') and f.suffix.lower() in exts:
                try:
                    stat = f.stat()
                    arquivos.append({'nome': f.name, 'caminho': str(f), 'tamanho': stat.st_size, 'ext': f.suffix})
                    total_chars += stat.st_size
                except: pass
        return {'ok': True, 'caminho': str(caminho), 'total_arquivos': len(arquivos), 'total_chars': total_chars, 'arquivos': arquivos[:100]}

    def _processar_tema(self, dados):
        caminho  = Path(dados.get('caminho','')).expanduser()
        nome     = dados.get('nome','') or caminho.name
        if not caminho.exists():
            return {'ok': False, 'erro': f'Diretório não encontrado: {caminho}'}
        agora    = datetime.now()
        hoje     = agora.strftime('%Y-%m-%d')
        hora     = agora.strftime('%H:%M')
        exts_txt = {'.md','.txt','.py','.js','.html','.css','.json','.yaml','.yml','.csv'}
        secoes   = []
        arquivos_ok = 0
        for f in sorted(caminho.rglob('*')):
            if f.is_file() and not f.name.startswith('.') and f.suffix.lower() in exts_txt:
                try:
                    texto = f.read_text(encoding='utf-8', errors='ignore')[:3000]
                    if texto.strip():
                        secoes.append(f"### {f.name}\n\n{texto[:800]}\n")
                        arquivos_ok += 1
                except: pass
        conteudo_tema = f"""---
tags: [tema]
nome: {nome}
data: {hoje}
caminho_origem: {caminho}
arquivos_processados: {arquivos_ok}
---

# Tema: {nome}

> Processado em {hoje} às {hora}
> Origem: `{caminho}`
> Arquivos: {arquivos_ok}

## Conteúdo condensado

{''.join(secoes[:20])}
"""
        TEMAS.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r'[^a-z0-9-]', '-', nome.lower())[:40]
        arq  = TEMAS / f"{hoje}-{slug}.md"
        arq.write_text(conteudo_tema, encoding='utf-8')
        print(f"  ✅ Tema salvo: {arq.name}")
        return {'ok': True, 'arquivo': arq.name, 'arquivos_processados': arquivos_ok}

    # ══════════════════════════════════════════════════════════════════════════
    # LÓGICA DO CORES
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_evento(self, conteudo):
        dados = {'descricao':'','jogo':'','tipo':[],'impacto':[],'ameaca':[],'pessoa':[],'data':'','hora':'','jogo_nome':''}
        for linha in conteudo.splitlines():
            for campo in ['descricao','jogo','data','hora']:
                if linha.startswith(campo + ':'):
                    dados[campo] = linha.split(':',1)[1].strip()
            for campo in ['tipo','impacto','ameaca','pessoa']:
                if linha.startswith(campo + ':'):
                    val = linha.split(':',1)[1].strip()
                    try:    dados[campo] = json.loads(val)
                    except: dados[campo] = [v.strip() for v in val.split(',') if v.strip()]
        dados['jogo_nome'] = JOGOS.get(dados['jogo'],'')
        return dados

    def _salvar_evento(self, dados):
        agora_dt  = datetime.now()
        hoje      = agora_dt.strftime('%Y-%m-%d')
        hora      = agora_dt.strftime('%H%M')
        hora_br   = agora_dt.strftime('%H:%M')
        data_br   = agora_dt.strftime('%d/%m/%Y')
        descricao = dados.get('descricao','').strip()
        jogo      = dados.get('jogo','')
        tipo      = dados.get('tipo',[])
        impacto   = dados.get('impacto',[])
        ameaca    = dados.get('ameaca',[])
        pessoa    = dados.get('pessoa',[])
        jogo_nome = JOGOS.get(jogo,'')
        slug = re.sub(r'[^a-z0-9-]','',descricao.lower()[:30].replace(' ','-'))
        nome_arquivo = f"{hoje}-{hora}-{slug}.md"
        tags = ['evento']
        if jogo: tags.append(f'jogo/{jogo}')
        tags += [f'tipo/{t.lower()}' for t in tipo]
        tags += [f'impacto/{i.lower()}' for i in impacto]
        conteudo = f"""---
tags: [{', '.join(tags)}]
data: {hoje}
hora: {hora_br}
descricao: {descricao}
jogo: {jogo}
jogo_nome: {jogo_nome}
tipo: {json.dumps(tipo, ensure_ascii=False)}
impacto: {json.dumps(impacto, ensure_ascii=False)}
ameaca: {json.dumps(ameaca, ensure_ascii=False)}
pessoa: {json.dumps(pessoa, ensure_ascii=False)}
---

# {descricao}

> Data: {data_br} · {hora_br}
> Jogo: {jogo} · {jogo_nome}

## Classificação

| Dimensão    | Seleções |
|-------------|----------|
| Tipo        | {', '.join(tipo)    or '—'} |
| Impacto     | {', '.join(impacto) or '—'} |
| Ameaça      | {', '.join(ameaca)  or '—'} |
| Personagens | {', '.join(pessoa)  or '—'} |

## Notas
_adicione observações no Obsidian_
"""
        EVENTOS.mkdir(parents=True, exist_ok=True)
        (EVENTOS / nome_arquivo).write_text(conteudo, encoding='utf-8')
        print(f"  ✅ Evento salvo: {nome_arquivo}")
        return {'ok': True, 'arquivo': nome_arquivo}

    def _salvar_consulta_cores(self, dados):
        import base64 as b64mod
        agora_dt  = datetime.now()
        timestamp = agora_dt.strftime('%Y-%m-%d-%H%M')
        data_br   = agora_dt.strftime('%d/%m/%Y %H:%M')
        servico   = dados.get('servico','lm')
        resposta  = dados.get('resposta','')
        imagens   = dados.get('imagens',[])
        ref_evento= dados.get('ref_evento','')
        descricao = dados.get('descricao','')
        jogo      = dados.get('jogo','')
        jogo_nome = JOGOS.get(jogo,'')
        consultas_dir = OBSIDIAN / 'consultas'
        assets_dir    = consultas_dir / 'assets'
        consultas_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)
        links_imagens = ''
        for img in imagens:
            try:
                nome    = img.get('nome', f'img-{timestamp}.png')
                b64data = img.get('base64','')
                if ',' in b64data: b64data = b64data.split(',',1)[1]
                (assets_dir / nome).write_bytes(b64mod.b64decode(b64data))
                links_imagens += f'\n![[assets/{nome}]]'
            except Exception as e:
                print(f"  ⚠ Imagem: {e}")
        nome_arquivo = f"{timestamp}-cores-{servico}.md"
        link_evento  = f"[[eventos/{ref_evento}]]" if ref_evento else ''
        titulo       = f"{descricao[:50]} · {servico.title()} · {data_br}"
        conteudo = f"""---
tags: [consulta, consulta/{servico}, cores]
data: {agora_dt.strftime('%Y-%m-%d')}
hora: {agora_dt.strftime('%H:%M')}
servico: {servico}
jogo: {jogo}
evento_origem: {ref_evento}
---

# {titulo}

{('> Evento: ' + link_evento) if link_evento else ''}
{('> Situação: ' + descricao) if descricao else ''}
{('> Jogo: ' + jogo + ' · ' + jogo_nome) if jogo else ''}

## Resposta
{resposta}
{links_imagens}
"""
        (consultas_dir / nome_arquivo).write_text(conteudo, encoding='utf-8')
        if ref_evento:
            arq = EVENTOS / ref_evento
            if arq.exists():
                texto = arq.read_text(encoding='utf-8')
                link  = f"- [[consultas/{nome_arquivo}]] — {servico.title()} · {data_br}"
                if '## Consultas' in texto:
                    texto = texto.replace('## Consultas', '## Consultas\n' + link)
                else:
                    texto += f'\n\n## Consultas\n{link}\n'
                arq.write_text(texto, encoding='utf-8')
        print(f"  ✅ Consulta Cores salva: {nome_arquivo}")
        return {'ok': True, 'arquivo': nome_arquivo}

    def _buscar_conexoes(self, qs):
        jogo    = qs.get('jogo',   [''])[0]
        tipo    = [t for t in qs.get('tipo',   [''])[0].split(',') if t]
        impacto = [t for t in qs.get('impacto',[''])[0].split(',') if t]
        resultado = {}
        if jogo:
            jogos_dir = OBSIDIAN / 'jogos'
            if jogos_dir.exists():
                for f in jogos_dir.glob('*.md'):
                    if f.name.startswith(jogo.zfill(2)):
                        conteudo = f.read_text(encoding='utf-8')
                        linhas   = conteudo.splitlines()
                        titulo   = next((l[2:].strip() for l in linhas if l.startswith('# ')), f.stem)
                        preview  = ' '.join(l for l in linhas if l and not l.startswith('#') and not l.startswith('---'))[:200]
                        resultado['jogo_nota'] = {'arquivo': f.name, 'titulo': titulo, 'preview': preview}
                        break
        if STATUS.exists():
            try:
                status = json.loads(STATUS.read_text(encoding='utf-8'))
                fase   = status.get('fase','')
                if fase:
                    fases_dir = OBSIDIAN / 'fases'
                    if fases_dir.exists():
                        for f in fases_dir.glob('*.md'):
                            if fase in f.name:
                                conteudo = f.read_text(encoding='utf-8')
                                linhas   = conteudo.splitlines()
                                titulo   = next((l[2:].strip() for l in linhas if l.startswith('# ')), f.stem)
                                preview  = ' '.join(l for l in linhas if l and not l.startswith('#') and not l.startswith('---'))[:200]
                                resultado['fase_nota'] = {'arquivo': f.name, 'titulo': titulo, 'preview': preview}
                                break
            except: pass
        if REGISTROS.exists():
            encontrados = []
            for f in sorted(REGISTROS.glob('*.md'), reverse=True)[:50]:
                try:
                    conteudo = f.read_text(encoding='utf-8')
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ['titulo','jogo_ativo','fase','data','foco','agora']:
                            if linha.startswith(campo + ':'): dados[campo] = linha.split(':',1)[1].strip()
                    if jogo and dados.get('jogo_ativo','').startswith(jogo):
                        preview = (dados.get('agora','') or dados.get('foco',''))[:120]
                        encontrados.append({'arquivo': f.name, 'titulo': dados.get('titulo','') or f.stem, 'data': dados.get('data',''), 'preview': preview})
                        if len(encontrados) >= 3: break
                except: pass
            if encontrados: resultado['registros'] = encontrados
        return resultado

    def _salvar_sessao_desenvolvimento(self, dados):
        agora    = datetime.now()
        hoje     = agora.strftime('%Y-%m-%d')
        hora     = agora.strftime('%H:%M')

        titulo     = dados.get('titulo', f'Sessão {hoje}')
        conteudo_md= dados.get('conteudo','')
        fase       = dados.get('fase','')
        jogo       = dados.get('jogo','')
        session_id = dados.get('session_id','')
        servico    = dados.get('servico','claude')
        modelo     = dados.get('modelo','claude-sonnet-4-6')
        temas      = dados.get('temas',[])
        campos     = dados.get('campos',[])
        estado     = dados.get('estado',[])
        proximos   = dados.get('proximos',[])

        sessoes_dir = OBSIDIAN / 'sessoes'
        sessoes_dir.mkdir(parents=True, exist_ok=True)

        tags = ['sessao-desenvolvimento']
        if fase: tags.append(f'fase/{fase}')
        if jogo: tags.append(f'jogo/{jogo[:2]}')
        tags += [f'tema/{t}' for t in temas]

        frontmatter = f"""---
data: {hoje}
hora: {hora}
tipo: sessao-desenvolvimento
fase: {fase}
jogo: {jogo}
session_id: {session_id}
servico: {servico}
modelo: {modelo}
temas: {json.dumps(temas, ensure_ascii=False)}
campos: {json.dumps(campos, ensure_ascii=False)}
estado: {json.dumps(estado, ensure_ascii=False)}
proximos: {json.dumps(proximos, ensure_ascii=False)}
tags: [{', '.join(tags)}]
---

# {titulo}

"""
        arq_nome = f"{hoje}-sessao-{session_id or 'dev'}.md"
        arq      = sessoes_dir / arq_nome
        arq.write_text(frontmatter + conteudo_md, encoding='utf-8')
        print(f"  ✅ Sessão salva: {arq_nome}")
        return {'ok': True, 'arquivo': arq_nome}


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 56)
print("  Jogo da Vida — Servidor Único")
print("=" * 56)
print(f"  Base:      {BASE}")
print(f"  Obsidian:  {OBSIDIAN}")
print()
print(f"  Especificador → http://localhost:{PORT}/")
print(f"  Cores         → http://localhost:{PORT}/cores")
print(f"  Chat B        → http://localhost:{PORT}/chatb")
print()
print("  Rotas Obsidian CLI:")
print(f"  GET  /api/obsidian?cmd=files")
print(f"  GET  /api/obsidian?cmd=search&q=termo")
print(f"  GET  /api/obsidian?cmd=read&file=registros/2026-03-25.md")
print(f"  GET  /api/obsidian?cmd=daily")
print(f"  POST /api/obsidian  {{cmd:create, name:..., content:...}}")
print(f"  POST /api/obsidian  {{cmd:append, file:..., content:...}}")
print()
print("  Rotas de integração:")
print(f"  GET  /api/integracao/contexto-registro")
print(f"  GET  /api/integracao/sugestoes-registro")
print(f"  GET  /api/integracao/temas-evento")
print(f"  GET  /api/integracao/matriz-cores")
print(f"  POST /api/integracao/sessao/salvar")
print()

for d in [REGISTROS, CONSULTAS, EVENTOS, TEMAS]:
    d.mkdir(parents=True, exist_ok=True)

print(f"  Ouvindo em http://localhost:{PORT}")
print("  Ctrl+C para parar.\n")

HTTPServer(('localhost', PORT), Handler).serve_forever()
