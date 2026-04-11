"""
servidor_especificador.py
Serve o especificador.html e salva registros como .md no Obsidian.

Uso:
    python3.13 servidor_especificador.py
    Abrir: http://localhost:8181
"""

import json
import os
import re
import urllib.request
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Caminhos
BASE       = Path.home() / "Documents/actualsc/jogo-da-vida"
OBSIDIAN   = BASE / "especificador/obsidian"
REGISTROS  = OBSIDIAN / "registros"
CONSULTAS  = OBSIDIAN / "consultas"
TEMAS      = OBSIDIAN / "temas"
HTML_FILE  = BASE / "especificador/prototipos/especificador.html"
PORT       = 8181

# Chaves de API (configure aqui ou em variáveis de ambiente)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY    = os.environ.get("GOOGLE_API_KEY", "")


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_file(HTML_FILE, "text/html; charset=utf-8")

        elif path == "/api/registro/hoje":
            # Retorna o registro de hoje se existir
            hoje = datetime.now().strftime('%Y-%m-%d')
            arquivo = REGISTROS / f"{hoje}.md"
            if arquivo.exists():
                conteudo = arquivo.read_text(encoding="utf-8")
                dados = self._parse_registro(conteudo)
                self._json(dados)
            else:
                self._json({})

        elif path == "/api/registros":
            # Lista todos os registros
            arquivos = sorted(REGISTROS.glob("*.md"), reverse=True)
            lista = []
            for a in arquivos[:30]:  # últimos 30
                conteudo = a.read_text(encoding="utf-8")
                dados = self._parse_registro(conteudo)
                dados["arquivo"] = a.name
                lista.append(dados)
            self._json(lista)

        elif path == "/api/notas":
            # Vista lógica: registros + consultas juntos, ordem cronológica
            limite = int(qs.get("limite", [60])[0])
            notas  = []

            # Coleta registros
            for a in REGISTROS.glob("*.md"):
                try:
                    conteudo = a.read_text(encoding="utf-8")
                    dados = self._parse_registro(conteudo)
                    dados["arquivo"]  = a.name
                    dados["tipo"]     = "registro"
                    dados["sort_key"] = dados.get("data","") + "T" + dados.get("hora","00:00")
                    notas.append(dados)
                except Exception:
                    pass

            # Coleta consultas
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
                                dados["titulo"] = linha[2:].strip()
                                break
                    # Extrai pergunta e resposta resumida
                    secao = None
                    linhas_secao = []
                    for linha in conteudo.splitlines():
                        if linha == "## Pergunta":
                            secao = "pergunta"; linhas_secao = []
                        elif linha == "## Resposta":
                            if secao: dados[secao] = "\n".join(linhas_secao).strip()
                            secao = "resposta"; linhas_secao = []
                        elif secao and not linha.startswith("#") and not linha.startswith("---") and not linha.startswith(">"):
                            linhas_secao.append(linha)
                    if secao: dados[secao] = "\n".join(linhas_secao).strip()
                    dados["arquivo"]  = a.name
                    dados["tipo"]     = "consulta"
                    dados["sort_key"] = dados.get("data","") + "T" + dados.get("hora","00:00")
                    notas.append(dados)
                except Exception:
                    pass

            # Ordena por data+hora decrescente e limita
            notas.sort(key=lambda x: x.get("sort_key",""), reverse=True)
            notas = notas[:limite]
            for n in notas:
                n.pop("sort_key", None)
            self._json(notas)

        elif path == "/api/temas":
            # Lista temas gerados
            # Lista temas gerados
            TEMAS.mkdir(parents=True, exist_ok=True)
            arquivos = sorted(TEMAS.glob("*.md"), reverse=True)
            lista = []
            for a in arquivos:
                try:
                    conteudo = a.read_text(encoding="utf-8")
                    dados = {"arquivo": a.name, "nome": "", "data": "", "tags": [], "arquivos": 0, "preview": ""}
                    for linha in conteudo.splitlines():
                        if linha.startswith("nome:"):
                            dados["nome"] = linha.split(":",1)[1].strip()
                        elif linha.startswith("data:"):
                            dados["data"] = linha.split(":",1)[1].strip()
                        elif linha.startswith("arquivos_processados:"):
                            try: dados["arquivos"] = int(linha.split(":",1)[1].strip())
                            except: pass
                        elif linha.startswith("tags:"):
                            raw = linha.split(":",1)[1].strip()
                            dados["tags"] = [t.strip().strip('[]') for t in raw.split(',') if t.strip()]
                    # Preview do conteúdo
                    linhas_texto = [l for l in conteudo.splitlines() if l and not l.startswith('#') and not l.startswith('---') and not l.startswith('tags:') and not l.startswith('nome:') and not l.startswith('data:') and not l.startswith('arquivos')]
                    dados["preview"] = ' '.join(linhas_texto)[:150]
                    lista.append(dados)
                except Exception:
                    pass
            self._json(lista)

        elif path == "/api/matriz":
            self._json(self._carregar_matriz())

        elif path == "/api/matriz/gerar":
            self._json(self._gerar_sugestoes_matriz())

        elif path == "/api/sessao":
            session_id = qs.get("id", [""])[0]
            formato    = qs.get("formato", ["json"])[0]
            self._json(self._exportar_sessao(session_id, formato))

        elif path == "/api/consultas":
            # Lista consultas de um registro específico
            ref = qs.get("ref", [""])[0]
            arquivos = sorted(CONSULTAS.glob("*.md"), reverse=True)
            lista = []
            for a in arquivos:
                try:
                    conteudo = a.read_text(encoding="utf-8")
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ["servico","fase","jogo","data","hora","registro_origem","titulo"]:
                            if linha.startswith(campo + ":"):
                                dados[campo] = linha.split(":",1)[1].strip()
                    # Extrai título do H1 se não tiver no frontmatter
                    if not dados.get("titulo"):
                        for linha in conteudo.splitlines():
                            if linha.startswith("# "):
                                dados["titulo"] = linha[2:].strip()
                                break
                    # Extrai pergunta e resposta
                    secao = None
                    linhas_secao = []
                    for linha in conteudo.splitlines():
                        if linha == "## Pergunta":
                            secao = "pergunta"; linhas_secao = []
                        elif linha == "## Resposta":
                            if secao: dados[secao] = "\n".join(linhas_secao).strip()
                            secao = "resposta"; linhas_secao = []
                        elif secao and not linha.startswith("#") and not linha.startswith("---") and not linha.startswith(">"):
                            linhas_secao.append(linha)
                    if secao: dados[secao] = "\n".join(linhas_secao).strip()
                    dados["arquivo"] = a.name
                    if not ref or dados.get("registro_origem") == ref:
                        lista.append(dados)
                except Exception:
                    pass
            self._json(lista)

        elif path == "/api/status":
            if status_file.exists():
                dados = json.loads(status_file.read_text(encoding="utf-8"))
            else:
                dados = {"fase": "fogo", "jogo": "05-estrategia"}
            self._json(dados)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            dados = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        if path == "/api/registro/salvar":
            resultado = self._salvar_registro(dados)
            self._json(resultado)

        elif path == "/api/status/salvar":
            resultado = self._salvar_status(dados)
            self._json(resultado)

        elif path == "/api/objetivo/salvar":
            resultado = self._salvar_objetivo(dados)
            self._json(resultado)

        elif path == "/api/consulta/claude":
            resultado = self._consultar_claude(dados)
            self._json(resultado)

        elif path == "/api/consulta/gemini":
            resultado = self._consultar_gemini(dados)
            self._json(resultado)

        elif path == "/api/consulta/salvar":
            resultado = self._salvar_consulta(dados)
            self._json(resultado)

        elif path == "/api/tema/inspecionar":
            self._json(self._inspecionar_tema(dados))

        elif path == "/api/tema/processar":
            self._json(self._processar_tema(dados))

        elif path == "/api/matriz/salvar":
            self._json(self._salvar_matriz(dados))

        elif path == "/api/excluir":
            resultado = self._excluir_nota(dados)
            self._json(resultado)

        elif path == "/api/registro/sessao":
            resultado = self._atualizar_sessao(dados)
            self._json(resultado)

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- HELPERS ----

    def _serve_file(self, filepath, content_type):
        try:
            conteudo = Path(filepath).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(conteudo)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _json(self, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(corpo)

    def _parse_registro(self, conteudo):
        """Extrai campos do markdown do registro."""
        dados = {"titulo": "", "agora": "", "foco": "", "reflexao": "", "fase": "", "jogo": "", "data": "", "hora": "", "session_id": ""}
        secao = None
        linhas_secao = []

        for linha in conteudo.splitlines():
            if linha.startswith("fase:"):
                dados["fase"] = linha.replace("fase:", "").strip()
            elif linha.startswith("jogo_ativo:"):
                dados["jogo"] = linha.replace("jogo_ativo:", "").strip()
            elif linha.startswith("data:"):
                dados["data"] = linha.replace("data:", "").strip()
            elif linha.startswith("hora:"):
                dados["hora"] = linha.replace("hora:", "").strip()
            elif linha.startswith("titulo:"):
                dados["titulo"] = linha.replace("titulo:", "").strip()
            elif linha.startswith("session_id:"):
                dados["session_id"] = linha.replace("session_id:", "").strip()
            elif linha == "## Como estou agora":
                if secao: dados[secao] = "\n".join(linhas_secao).strip()
                secao = "agora"; linhas_secao = []
            elif linha == "## Foco do dia":
                if secao: dados[secao] = "\n".join(linhas_secao).strip()
                secao = "foco"; linhas_secao = []
            elif linha == "## Reflexão":
                if secao: dados[secao] = "\n".join(linhas_secao).strip()
                secao = "reflexao"; linhas_secao = []
            elif secao and not linha.startswith("#") and not linha.startswith("---"):
                linhas_secao.append(linha)

        if secao:
            dados[secao] = "\n".join(linhas_secao).strip()

        return dados

    def _salvar_registro(self, dados):
        """Salva novo registro com timestamp + título no Obsidian."""
        agora_dt = datetime.now()
        hoje     = agora_dt.strftime('%Y-%m-%d')
        hora     = agora_dt.strftime('%H%M')
        hora_br  = agora_dt.strftime('%H:%M')
        data_br  = agora_dt.strftime('%d/%m/%Y')

        titulo     = dados.get("titulo", "").strip()
        session_id = dados.get("session_id", "").strip() or (titulo if titulo else agora_dt.strftime('%Y-%m-%d-%H%M'))
        agora      = dados.get("agora", "")
        foco       = dados.get("foco", "")
        reflexao   = dados.get("reflexao", "")
        fase       = dados.get("fase", "")
        jogo       = dados.get("jogo", "")

        # Nome do arquivo: data-hora-slug-do-titulo.md
        if titulo:
            slug = titulo.lower()
            slug = slug.replace(" ", "-")
            for c in "áàãâäéèêëíìîïóòõôöúùûüçñ":
                slug = slug.replace(c, {'á':'a','à':'a','ã':'a','â':'a','ä':'a',
                    'é':'e','è':'e','ê':'e','ë':'e','í':'i','ì':'i','î':'i','ï':'i',
                    'ó':'o','ò':'o','õ':'o','ô':'o','ö':'o','ú':'u','ù':'u','û':'u',
                    'ü':'u','ç':'c','ñ':'n'}.get(c, c))
            slug = ''.join(c for c in slug if c.isalnum() or c == '-')[:40]
            nome_arquivo = f"{hoje}-{hora}-{slug}.md"
        else:
            nome_arquivo = f"{hoje}-{hora}.md"

        arquivo = REGISTROS / nome_arquivo

        conteudo = f"""---
tags: [registro, ciclo/dia]
data: {hoje}
hora: {hora_br}
titulo: {titulo}
session_id: {session_id}
fase: {fase}
jogo_ativo: {jogo}
---

# {titulo or ('Registro — ' + data_br + ' ' + hora_br)}

## Como estou agora
{agora}

## Foco do dia
{foco}

## Reflexão
{reflexao}
"""
        REGISTROS.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo, encoding="utf-8")
        print(f"  ✅ Registro salvo: {arquivo.name}")
        return {"ok": True, "arquivo": arquivo.name}

    def _salvar_status(self, dados):
        """Salva fase e jogo atual."""
        status_file = OBSIDIAN / "status.json"
        status_file.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ Status salvo: fase={dados.get('fase')} jogo={dados.get('jogo')}")
        return {"ok": True}

    def _salvar_objetivo(self, dados):
        """Adiciona objetivo ao arquivo atual.md."""
        arquivo = OBSIDIAN / "objetivos/atual.md"
        conteudo = arquivo.read_text(encoding="utf-8") if arquivo.exists() else "# Objetivos\n\n"
        frente = dados.get("frente", "geral")
        texto  = dados.get("texto", "")
        conteudo += f"\n- [ ] {texto} #{frente}"
        arquivo.write_text(conteudo, encoding="utf-8")
        print(f"  ✅ Objetivo salvo: {texto}")
        return {"ok": True}


    def _excluir_nota(self, dados):
        """Exclui um arquivo de registro ou consulta."""
        tipo    = dados.get("tipo", "")   # "registro" ou "consulta"
        arquivo = dados.get("arquivo", "")

        if not arquivo or ".." in arquivo or "/" in arquivo:
            return {"ok": False, "erro": "Arquivo inválido"}

        if tipo == "registro":
            caminho = REGISTROS / arquivo
        elif tipo == "consulta":
            caminho = CONSULTAS / arquivo
        else:
            return {"ok": False, "erro": "Tipo inválido"}

        if not caminho.exists():
            return {"ok": False, "erro": "Arquivo não encontrado"}

        # Se for registro, remove também os links nas consultas associadas
        if tipo == "registro":
            for consulta in CONSULTAS.glob("*.md"):
                try:
                    texto = consulta.read_text(encoding="utf-8")
                    if arquivo in texto:
                        texto = texto.replace(f"[[registros/{arquivo}]]", f"_(registro excluído: {arquivo})_")
                        consulta.write_text(texto, encoding="utf-8")
                except Exception:
                    pass

        caminho.unlink()
        print(f"  🗑️  Excluído: {caminho.name}")
        return {"ok": True, "arquivo": arquivo}

    def _consultar_claude(self, dados):
        """Envia nota para Claude API e salva resposta."""
        if not ANTHROPIC_API_KEY:
            return {"ok": False, "erro": "ANTHROPIC_API_KEY não configurada. Execute: export ANTHROPIC_API_KEY='sua-chave'"}

        nota      = dados.get("nota", "")
        pergunta  = dados.get("pergunta", "").strip()
        ref       = dados.get("ref", "")
        fase      = dados.get("fase", "")
        jogo      = dados.get("jogo", "")

        if not pergunta:
            pergunta = "Analise esta nota sob a perspectiva do jogo da vida e das fases de desenvolvimento (Fogo, Ar, Água, Terra, Éter). Identifique padrões, o jogo dominante e sugira próximos passos."

        prompt = f"{pergunta}\n\n---\n{nota}"

        try:
            payload = json.dumps({
                "model": "claude-sonnet-4-5",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }).encode("utf-8")

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
                resultado = json.loads(resp.read().decode("utf-8"))
                resposta = resultado["content"][0]["text"]

            arquivo = self._salvar_consulta({
                "servico": "claude",
                "pergunta": pergunta,
                "resposta": resposta,
                "ref": ref,
                "fase": fase,
                "jogo": jogo
            })
            return {"ok": True, "resposta": resposta, "arquivo": arquivo.get("arquivo", "")}

        except Exception as e:
            return {"ok": False, "erro": str(e)}

    def _consultar_gemini(self, dados):
        """Envia nota para Gemini API e salva resposta."""
        if not GOOGLE_API_KEY:
            return {"ok": False, "erro": "GOOGLE_API_KEY não configurada"}

        nota     = dados.get("nota", "")
        pergunta = dados.get("pergunta", "Analise esta nota sob a perspectiva do jogo da vida e das fases de desenvolvimento.")
        ref      = dados.get("ref", "")

        prompt = f"{pergunta}\n\n---\n{nota}"

        try:
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}]
            }).encode("utf-8")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resultado = json.loads(resp.read().decode("utf-8"))
                resposta = resultado["candidates"][0]["content"]["parts"][0]["text"]

            arquivo = self._salvar_consulta({
                "servico": "gemini",
                "pergunta": pergunta,
                "resposta": resposta,
                "ref": ref
            })
            return {"ok": True, "resposta": resposta, "arquivo": arquivo.get("arquivo", "")}

        except Exception as e:
            return {"ok": False, "erro": str(e)}

    def _salvar_consulta(self, dados):
        """Salva consulta em consultas/ e atualiza registro original com link."""
        agora_dt  = datetime.now()
        timestamp = agora_dt.strftime('%Y-%m-%d-%H%M')
        data_br   = agora_dt.strftime('%d/%m/%Y %H:%M')

        servico    = dados.get("servico", "manual")
        pergunta   = dados.get("pergunta", "")
        resposta   = dados.get("resposta", "")
        ref        = dados.get("ref", "")
        fase       = dados.get("fase", "")
        jogo       = dados.get("jogo", "")
        session_id = dados.get("session_id", "")

        # Carrega fase/jogo do status.json se não vieram nos dados
        if not fase or not jogo:
            status_file = OBSIDIAN / "status.json"
            if status_file.exists():
                try:
                    status = json.loads(status_file.read_text(encoding="utf-8"))
                    fase = fase or status.get("fase", "")
                    jogo = jogo or status.get("jogo", "")
                except Exception:
                    pass

        nome_arquivo = f"{timestamp}-consulta-{servico}.md"
        arquivo_consulta = CONSULTAS / nome_arquivo

        # Tags combinadas: consulta + fase + jogo
        tags_lista = ["consulta", f"consulta/{servico}"]
        if fase: tags_lista.append(f"fase/{fase}")
        if jogo: tags_lista.append(f"jogo/{jogo[:2]}")
        tags_str = ", ".join(tags_lista)

        link_ref    = f"[[registros/{ref}]]"      if ref  else ""
        jogo_label  = f"jogo/{jogo[:2]}"          if jogo else ""
        fase_label  = f"fase/{fase}"              if fase else ""

        # Título composto: nome do registro + serviço + data
        ref_stem   = ref.replace('.md','') if ref else ''
        titulo_consulta = f"{ref_stem} · {servico.title()} · {data_br}" if ref_stem else f"{servico.title()} · {data_br}"

        conteudo = f"""---
tags: [{tags_str}]
data: {agora_dt.strftime('%Y-%m-%d')}
hora: {agora_dt.strftime('%H:%M')}
servico: {servico}
session_id: {session_id}
fase: {fase}
jogo: {jogo}
registro_origem: {ref}
---

# {titulo_consulta}

{('> Origem: ' + link_ref) if link_ref else ''}
{('> Sessão: ' + session_id) if session_id else ''}
{('> Fase: #' + fase_label) if fase_label else ''}
{('> Jogo: #' + jogo_label) if jogo_label else ''}

## Pergunta
{pergunta or '_sem pergunta adicional — prompt padrão_'}

## Resposta
{resposta}
"""
        CONSULTAS.mkdir(parents=True, exist_ok=True)
        arquivo_consulta.write_text(conteudo, encoding="utf-8")
        print(f"  ✅ Consulta salva: {arquivo_consulta.name}")

        # Atualiza o registro original adicionando link para esta consulta
        if ref:
            arquivo_registro = REGISTROS / ref
            if arquivo_registro.exists():
                texto_registro = arquivo_registro.read_text(encoding="utf-8")
                link_consulta = f"- [[consultas/{nome_arquivo}]] — {servico.title()} · {data_br}"

                if "## Consultas" in texto_registro:
                    # Já existe seção — adiciona linha
                    texto_registro = texto_registro.replace(
                        "## Consultas",
                        "## Consultas\n" + link_consulta
                    )
                else:
                    # Cria seção no final
                    texto_registro += f"\n\n## Consultas\n{link_consulta}\n"

                arquivo_registro.write_text(texto_registro, encoding="utf-8")
                print(f"  🔗 Registro atualizado: {ref}")

        return {"ok": True, "arquivo": nome_arquivo}


    def _inspecionar_tema(self, dados):
        """Inspeciona um diretório e retorna estatísticas dos arquivos."""
        caminho = Path(dados.get("caminho","")).expanduser()
        if not caminho.exists():
            return {"ok": False, "erro": f"Diretório não encontrado: {caminho}"}
        if not caminho.is_dir():
            return {"ok": False, "erro": "O caminho não é um diretório"}

        exts = {'.md':0, '.pdf':0, '.html':0, '.txt':0, '.jpg':0, '.jpeg':0, '.png':0, '.outros':0}
        total = 0
        for f in caminho.rglob("*"):
            if f.is_file() and not f.name.startswith('.'):
                ext = f.suffix.lower()
                total += 1
                if ext in exts:
                    exts[ext] += 1
                else:
                    exts['.outros'] += 1

        por_tipo = {k: v for k, v in exts.items() if v > 0}
        return {"ok": True, "total": total, "por_tipo": por_tipo, "caminho": str(caminho)}

    # ---- CLASSIFICADOR TEMÁTICO ----
    TEMAS_JOGO = {
        "definicao": {
            "titulo": "O que é o Jogo da Vida",
            "palavras": [
                "jogo da vida", "vida é um jogo", "game of life", "o que é", "conceito",
                "definição", "significado", "essência", "natureza", "fundamento",
                "piloto da mente", "lucidez", "consciência", "despertar", "boot",
                "modo automático", "girando em falso", "caverna", "platão"
            ]
        },
        "como_jogar": {
            "titulo": "Como se Joga — Regras e Mecânicas",
            "palavras": [
                "como jogar", "regras", "mecânica", "funcionamento", "processo",
                "metodologia", "prática", "aplicação", "utilização", "ferramenta",
                "prótese digital", "especificador", "cores", "sessão", "registro",
                "bootstrap", "background", "padrão", "script", "algoritmo",
                "multiway", "grafo", "nó", "vértice", "aresta"
            ]
        },
        "doze_jogos": {
            "titulo": "Os 12 Tipos de Jogos",
            "palavras": [
                "caça", "guerra", "superação", "sedução", "estratégia", "oráculo",
                "vício", "brincadeira", "play", "projeção", "simulação", "antecipação",
                "12 jogos", "doze jogos", "tipos de jogo", "guerreiro", "conquista",
                "gambling", "paidia", "espetáculo", "laboratório", "lúdico",
                "animal", "game", "hunting", "competition"
            ]
        },
        "fases": {
            "titulo": "Fases de Desenvolvimento",
            "palavras": [
                "fogo", "ar", "água", "terra", "éter", "fases", "estágios",
                "desenvolvimento", "evolução", "jornada", "transição",
                "urgência", "salto", "estabilização", "fluidez", "estruturação",
                "sutileza", "pirâmide invertida", "lucidez", "dependência",
                "fase fogo", "fase ar", "fase água", "fase terra", "fase éter"
            ]
        },
        "personas": {
            "titulo": "Personas e Padrões de Comportamento",
            "palavras": [
                "persona", "usuário", "comportamento", "padrão", "perfil",
                "individuo", "indivíduo", "pessoa", "sujeito", "ator",
                "característica", "deficiência", "capacidade", "atitude",
                "identidade", "papel", "protagonismo", "postura", "modo",
                "automático", "reativo", "adaptativo", "reflexivo"
            ]
        },
        "conexoes": {
            "titulo": "Conexões com Outros Sistemas",
            "palavras": [
                "tarot", "i ching", "astrologia", "zodíaco", "arcano",
                "símbolo", "arquétipo", "wolfram", "multicomputação",
                "teoria", "sistema", "modelo", "paradigma", "filosofia",
                "jung", "campbell", "mitologia", "herói", "jornada",
                "biosfera", "ecologia", "ciclo", "solstício", "equinócio",
                "budismo", "taoismo", "estoicismo", "spinoza"
            ]
        }
    }

    def _classificar_trecho(self, texto):
        """Classifica um trecho de texto numa das seções temáticas."""
        texto_lower = texto.lower()
        pontuacao = {}

        for chave, tema in self.TEMAS_JOGO.items():
            pontos = sum(1 for p in tema["palavras"] if p in texto_lower)
            if pontos > 0:
                pontuacao[chave] = pontos

        if not pontuacao:
            return None  # descartado

        return max(pontuacao, key=pontuacao.get)

    def _lista_para_prosa(self, texto):
        """Converte listas markdown (bullets e numeradas) em parágrafos de prosa."""
        linhas = texto.splitlines()
        resultado = []
        i = 0

        while i < len(linhas):
            linha = linhas[i]

            # Detecta item de lista (bullet ou numerado, qualquer indentação)
            eh_lista = re.match(r'^(\s*)([-*+]|\d+[.)]) (.+)', linha)

            if eh_lista:
                # Coleta bloco de lista contíguo
                bloco = []
                while i < len(linhas):
                    item = re.match(r'^(\s*)([-*+]|\d+[.)]) (.+)', linhas[i])
                    continuacao = linhas[i].startswith('  ') and bloco  # linha continuada
                    if item:
                        nivel = len(item.group(1)) // 2  # nível de indentação
                        texto_item = item.group(3).strip()
                        bloco.append((nivel, texto_item))
                        i += 1
                    elif continuacao:
                        # Texto continuado do item anterior
                        if bloco:
                            nivel_ant, texto_ant = bloco[-1]
                            bloco[-1] = (nivel_ant, texto_ant + ' ' + linhas[i].strip())
                        i += 1
                    else:
                        break

                if not bloco:
                    continue

                # Agrupa itens de mesmo nível em frases
                # Itens de nível 0 viram frases principais
                # Itens de nível > 0 são incorporados ao item pai
                itens_raiz = []
                contexto = {}

                for nivel, texto_item in bloco:
                    # Garante que termina com ponto
                    if texto_item and texto_item[-1] not in '.!?:':
                        texto_item += '.'

                    if nivel == 0:
                        itens_raiz.append(texto_item)
                        contexto[0] = len(itens_raiz) - 1
                    else:
                        # Incorpora ao item pai mais próximo
                        pai_nivel = nivel - 1
                        while pai_nivel >= 0 and pai_nivel not in contexto:
                            pai_nivel -= 1
                        if pai_nivel >= 0 and contexto.get(pai_nivel) is not None:
                            idx = contexto[pai_nivel]
                            if idx < len(itens_raiz):
                                itens_raiz[idx] = itens_raiz[idx].rstrip('.') + ' ' + texto_item
                        else:
                            itens_raiz.append(texto_item)
                        contexto[nivel] = len(itens_raiz) - 1

                # Agrupa de 3 em 3 em parágrafos
                for j in range(0, len(itens_raiz), 3):
                    grupo = ' '.join(itens_raiz[j:j+3])
                    resultado.append(grupo)
                resultado.append('')  # linha em branco após a lista

            else:
                resultado.append(linha)
                i += 1

        return '\n'.join(resultado)

    def _tabela_para_prosa(self, texto):
        """Converte tabelas markdown em frases legíveis."""
        linhas = texto.splitlines()
        resultado = []
        i = 0

        while i < len(linhas):
            linha = linhas[i]

            # Detecta início de tabela (linha com pipes)
            if '|' in linha and linha.strip().startswith('|'):
                bloco_tabela = []
                while i < len(linhas) and '|' in linhas[i]:
                    bloco_tabela.append(linhas[i])
                    i += 1

                # Extrai cabeçalho e linhas de dados
                linhas_tabela = [l for l in bloco_tabela if not re.match(r'^\s*\|[\s\-:|]+\|\s*$', l)]

                if not linhas_tabela:
                    continue

                # Primeira linha = cabeçalho
                cabecalho = [c.strip() for c in linhas_tabela[0].split('|') if c.strip()]

                # Demais linhas = dados
                for linha_dados in linhas_tabela[1:]:
                    celulas = [c.strip() for c in linha_dados.split('|') if c.strip()]
                    if not celulas:
                        continue

                    # Monta frase: "Coluna1: valor1. Coluna2: valor2."
                    partes = []
                    for j, celula in enumerate(celulas):
                        if j < len(cabecalho) and cabecalho[j] and celula:
                            partes.append(f"{cabecalho[j]}: {celula}")
                        elif celula:
                            partes.append(celula)

                    if partes:
                        frase = '. '.join(partes) + '.'
                        resultado.append(frase)
            else:
                resultado.append(linha)
                i += 1

        return '\n'.join(resultado)

    def _resolver_links(self, texto, caminho_base, profundidade=0):
        """Resolve ![[link]] substituindo pelo conteúdo do arquivo referenciado."""
        if profundidade > 3:  # evita loops infinitos
            return texto

        def substituir_link(match):
            ref = match.group(1).strip()
            ref = ref.split('#')[0].strip()
            if '.' not in ref:
                ref += '.md'

            # Ignora imagens
            EXTS_IMAGEM = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.heic'}
            if Path(ref).suffix.lower() in EXTS_IMAGEM:
                return ''

            # Busca o arquivo no diretório base e nos pais
            candidatos = list(caminho_base.rglob(ref))
            if not candidatos:
                # Tenta buscar no vault inteiro (OBSIDIAN)
                candidatos = list(OBSIDIAN.rglob(ref))
            if not candidatos:
                return f'[conteúdo de {ref} não encontrado]'

            try:
                # Verifica se é binário
                raw = candidatos[0].read_bytes()[:512]
                non_text = sum(1 for b in raw if b < 9 or (14 <= b < 32) or b > 126)
                if non_text / max(len(raw), 1) > 0.15:
                    return ''

                conteudo_ref = candidatos[0].read_text(encoding='utf-8', errors='ignore')
                # Remove frontmatter
                if conteudo_ref.startswith('---'):
                    partes = conteudo_ref.split('---', 2)
                    conteudo_ref = partes[2] if len(partes) > 2 else conteudo_ref
                # Resolve links recursivamente
                conteudo_ref = self._resolver_links(conteudo_ref, candidatos[0].parent, profundidade + 1)
                return conteudo_ref.strip()
            except Exception:
                return f'[erro ao carregar {ref}]'

        # Resolve ![[link]] (transclusion)
        texto = re.sub(r'!\[\[([^\]]+)\]\]', substituir_link, texto)
        return texto

    def _extrair_texto_arquivo(self, f):
        """Extrai texto de um arquivo, resolvendo links Obsidian."""
        ext = f.suffix.lower()
        EXTS_TEXTO = {'.md', '.txt', '.html'}

        if ext in EXTS_TEXTO:
            # Verifica se é binário antes de ler
            try:
                raw = f.read_bytes()[:512]
                # Se tiver muitos bytes não-texto, pula
                non_text = sum(1 for b in raw if b < 9 or (14 <= b < 32) or b > 126)
                if non_text / max(len(raw), 1) > 0.15:
                    print(f"  ⚠ Arquivo binário ignorado: {f.name}")
                    return ""
            except Exception:
                return ""

            texto = f.read_text(encoding='utf-8', errors='ignore')
            # Remove frontmatter yaml
            if texto.startswith('---'):
                partes = texto.split('---', 2)
                texto = partes[2] if len(partes) > 2 else texto
            # Resolve ![[links]] do Obsidian ANTES de qualquer outro processamento
            if ext == '.md':
                texto = self._resolver_links(texto, f.parent)
            # Remove tags HTML
            if ext == '.html':
                texto = re.sub(r'<[^>]+>', ' ', texto)
            # Converte tabelas markdown em prosa
            texto = self._tabela_para_prosa(texto)
            # Converte listas em prosa
            texto = self._lista_para_prosa(texto)
            texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)
            return texto.strip()

        elif ext == '.pdf':
            try:
                import subprocess
                script = (
                    "import sys\n"
                    "try:\n"
                    "    import pdfplumber\n"
                    f"    with pdfplumber.open(r'{f}') as pdf:\n"
                    "        t='\\n'.join(p.extract_text() or '' for p in pdf.pages[:15])\n"
                    "    print(t[:5000])\n"
                    "except Exception as e:\n"
                    "    print('')\n"
                )
                resultado = subprocess.run(
                    ['python3', '-c', script],
                    capture_output=True, text=True, timeout=20
                )
                return resultado.stdout.strip()
            except Exception:
                return ""

        return ""

    def _processar_tema(self, dados):
        """Analisa diretório e gera .md com texto corrido estruturado por seções temáticas."""
        caminho = Path(dados.get("caminho","")).expanduser()
        nome    = dados.get("nome","").strip()
        tags_extra = [t.strip() for t in dados.get("tags","").split(",") if t.strip()]

        if not caminho.exists():
            return {"ok": False, "erro": f"Diretório não encontrado: {caminho}"}
        if not nome:
            return {"ok": False, "erro": "Nome do tema é obrigatório"}

        TEMAS.mkdir(parents=True, exist_ok=True)

        # Inicializa buckets temáticos
        buckets = {chave: [] for chave in self.TEMAS_JOGO}
        descartados = []
        arquivos_processados = 0
        EXTS_VALIDAS = {'.md', '.txt', '.html', '.pdf'}

        for f in sorted(caminho.rglob("*")):
            if not f.is_file() or f.name.startswith('.'): continue
            if f.suffix.lower() not in EXTS_VALIDAS: continue

            texto = self._extrair_texto_arquivo(f)
            if not texto: continue

            arquivos_processados += 1

            # Divide em parágrafos e classifica cada um
            paragrafos = [p.strip() for p in re.split(r'\n{2,}', texto) if len(p.strip()) > 60]

            for paragrafo in paragrafos:
                secao = self._classificar_trecho(paragrafo)
                # Limpa o parágrafo: remove marcadores markdown, títulos, etc.
                texto_limpo = re.sub(r'^#{1,6}\s+', '', paragrafo)   # títulos
                texto_limpo = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', texto_limpo)  # bold/italic
                texto_limpo = re.sub(r'`[^`]+`', '', texto_limpo)    # code
                texto_limpo = re.sub(r'[-*]\s+', '', texto_limpo)    # bullets
                texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()

                if len(texto_limpo) < 40: continue

                if secao:
                    buckets[secao].append(texto_limpo)
                else:
                    descartados.append(texto_limpo[:100])

        # Monta o texto corrido por seção
        slug = nome.lower().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)[:40]
        hoje = datetime.now().strftime('%Y-%m-%d')
        nome_arquivo = f"{hoje}-{slug}.md"

        total_aproveitado = sum(len(v) for v in buckets.values())
        total_descartado  = len(descartados)
        tags_lista = ['tema', 'biblioteca'] + tags_extra
        tags_str   = ', '.join(tags_lista)

        secoes_md = []

        for chave, tema in self.TEMAS_JOGO.items():
            trechos = buckets[chave]
            if not trechos: continue

            # Deduplica trechos muito similares (primeiros 80 chars)
            vistos = set()
            trechos_unicos = []
            for t in trechos:
                chave_dedup = t[:80].lower()
                if chave_dedup not in vistos:
                    vistos.add(chave_dedup)
                    trechos_unicos.append(t)

            # Agrupa em parágrafos de ~3 frases cada
            paragrafos_secao = []
            buffer = []
            for trecho in trechos_unicos[:30]:  # máx 30 trechos por seção
                # Garante que termina com ponto
                if trecho and trecho[-1] not in '.!?':
                    trecho += '.'
                buffer.append(trecho)
                # A cada ~3 trechos forma um parágrafo
                if len(buffer) >= 3:
                    paragrafos_secao.append(' '.join(buffer))
                    buffer = []
            if buffer:
                paragrafos_secao.append(' '.join(buffer))

            texto_secao = '\n\n'.join(paragrafos_secao)
            secoes_md.append(f"\n## {tema['titulo']}\n\n{texto_secao}")

        # Seção de descartados — só contagem, sem texto
        if descartados:
            secoes_md.append(
                f"\n## Fora do Escopo\n\n"
                f"_{total_descartado} trechos de {arquivos_processados} arquivo(s) "
                f"não apresentaram correspondência com os temas do jogo da vida e foram omitidos._"
            )

        if not secoes_md:
            return {"ok": False, "erro": "Nenhum conteúdo classificado. Verifique os arquivos do diretório."}

        md = f"""---
tags: [{tags_str}]
nome: {nome}
data: {hoje}
caminho_origem: {caminho}
arquivos_processados: {arquivos_processados}
trechos_aproveitados: {total_aproveitado}
trechos_descartados: {total_descartado}
---

# {nome}

{''.join(secoes_md)}
"""
        (TEMAS / nome_arquivo).write_text(md, encoding='utf-8')
        print(f"  ✅ Tema: {nome_arquivo} | {arquivos_processados} arqs | {total_aproveitado} trechos | {total_descartado} descartados")

        return {
            "ok": True,
            "arquivo": nome_arquivo,
            "arquivos_processados": arquivos_processados,
            "chars": total_aproveitado,
            "trechos_descartados": total_descartado
        }


    def _carregar_matriz(self):
        """Carrega matriz existente do Obsidian."""
        matriz_json = OBSIDIAN / "objetivos" / "matriz.json"
        if matriz_json.exists():
            try:
                return {"ok": True, "matriz": json.loads(matriz_json.read_text(encoding="utf-8"))}
            except Exception:
                pass
        return {"ok": True, "matriz": {}}

    def _gerar_sugestoes_matriz(self):
        """Analisa registros e gera sugestões para a matriz de objetivos."""

        # Palavras-chave por seção
        PADROES = {
            "pessoal": [
                "saúde", "corpo", "mente", "lucidez", "consciência", "equilíbrio",
                "bem-estar", "energia", "foco", "atenção", "descanso", "meditação",
                "autoconhecimento", "identidade", "propósito", "lucidez", "piloto"
            ],
            "social": [
                "relação", "pessoa", "família", "amigo", "coletivo", "comunidade",
                "impacto", "sociedade", "parceria", "colaboração", "ong", "projeto",
                "financiamento", "stakeholder", "usuário", "parceiro"
            ],
            "frentes": [
                "especificador", "cores", "desenvolvimento", "código", "programar",
                "site", "html", "python", "obsidian", "funding", "google", "api",
                "prototipo", "protótipo", "servidor", "deploy", "publicar"
            ],
            "obstaculos": [
                "dificuldade", "problema", "bloqueio", "travado", "confuso", "perdido",
                "dependência", "vício", "automático", "girando em falso", "caverna",
                "obstáculo", "barreira", "limitação", "deficiência", "falta"
            ],
            "proximos": [
                "preciso", "vou", "quero", "próximo", "agora", "hoje", "amanhã",
                "implementar", "criar", "fazer", "resolver", "testar", "validar",
                "conversar", "decidir", "definir", "começar", "terminar"
            ]
        }

        sugestoes = {k: [] for k in PADROES}
        registros_analisados = 0
        frases_vistas = set()

        arquivos = sorted(REGISTROS.glob("*.md"), reverse=True)[:20]

        for a in arquivos:
            try:
                conteudo = a.read_text(encoding="utf-8")
                registros_analisados += 1

                # Extrai seções relevantes
                texto = ""
                em_secao = False
                for linha in conteudo.splitlines():
                    if linha.startswith("## "):
                        em_secao = True
                    if em_secao and linha.strip() and not linha.startswith("---") and not linha.startswith("tags:"):
                        texto += linha + " "

                # Divide em frases
                frases = re.split(r'[.!?]+', texto)
                for frase in frases:
                    frase = frase.strip()
                    if len(frase) < 15 or len(frase) > 200:
                        continue
                    chave_dedup = frase[:50].lower()
                    if chave_dedup in frases_vistas:
                        continue

                    frase_lower = frase.lower()
                    for secao, palavras in PADROES.items():
                        if any(p in frase_lower for p in palavras):
                            sugestoes[secao].append({
                                "texto": frase[0].upper() + frase[1:],
                                "feito": False,
                                "origem": True
                            })
                            frases_vistas.add(chave_dedup)
                            break

            except Exception:
                pass

        # Limita sugestões por seção
        for secao in sugestoes:
            sugestoes[secao] = sugestoes[secao][:8]

        total = sum(len(v) for v in sugestoes.values())
        return {
            "ok": True,
            "sugestoes": sugestoes,
            "total_sugestoes": total,
            "registros_analisados": registros_analisados
        }

    def _salvar_matriz(self, dados):
        """Salva a matriz como JSON e como .md no Obsidian."""
        matriz = dados.get("matriz", {})
        hoje   = datetime.now().strftime('%Y-%m-%d')
        hora   = datetime.now().strftime('%H:%M')

        objetivos_dir = OBSIDIAN / "objetivos"
        objetivos_dir.mkdir(parents=True, exist_ok=True)

        # Salva JSON para reload
        (objetivos_dir / "matriz.json").write_text(
            json.dumps(matriz, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Gera .md legível
        SECOES = {
            "pessoal":    ("◎", "Objetivos Pessoais",        "saúde, lucidez, desenvolvimento"),
            "social":     ("◉", "Objetivos Sociais",         "relações, coletivo, impacto"),
            "frentes":    ("◈", "Frentes de Ação",           "especificador, cores, dev, funding"),
            "obstaculos": ("◐", "Obstáculos Identificados",  "padrões a superar"),
            "proximos":   ("◇", "Próximos Passos",           "ações concretas imediatas"),
        }

        secoes_md = []
        for secao_id, (icone, titulo, desc) in SECOES.items():
            itens = matriz.get(secao_id, [])
            if not itens:
                continue
            linhas = []
            for item in itens:
                check = "x" if item.get("feito") else " "
                origem = " _(registros)_" if item.get("origem") else ""
                linhas.append(f"- [{check}] {item.get('texto','')}{origem}")
            secoes_md.append(f"## {icone} {titulo}\n_{desc}_\n\n" + "\n".join(linhas))

        md = f"""---
tags: [matriz, objetivos]
data: {hoje}
atualizado: {hoje} {hora}
---

# Matriz de Objetivos

> Atualizada em {hoje} às {hora}

{"".join(chr(10)*2 + s for s in secoes_md)}
"""
        (objetivos_dir / "matriz.md").write_text(md, encoding="utf-8")
        print(f"  ✅ Matriz salva: objetivos/matriz.md")
        return {"ok": True}


    def _exportar_sessao(self, session_id, formato="json"):
        """Exporta todos os registros e consultas de uma sessão."""
        if not session_id:
            return {"ok": False, "erro": "session_id não informado"}

        registros_encontrados = []
        consultas_encontradas = []

        # Busca registros com esse session_id
        for a in sorted(REGISTROS.glob("*.md"), reverse=True):
            try:
                conteudo = a.read_text(encoding="utf-8")
                dados = self._parse_registro(conteudo)
                if dados.get("session_id") == session_id:
                    dados["arquivo"] = a.name
                    registros_encontrados.append(dados)
            except Exception:
                pass

        # Busca consultas com esse session_id
        for a in sorted(CONSULTAS.glob("*.md"), reverse=True):
            try:
                conteudo = a.read_text(encoding="utf-8")
                dados = {}
                for linha in conteudo.splitlines():
                    for campo in ["servico","fase","jogo","data","hora","session_id","titulo","pergunta"]:
                        if linha.startswith(campo + ":"):
                            dados[campo] = linha.split(":",1)[1].strip()
                # Extrai resposta
                em_resp = False
                linhas_resp = []
                for linha in conteudo.splitlines():
                    if linha == "## Resposta":
                        em_resp = True; continue
                    if em_resp and not linha.startswith("#") and not linha.startswith("---"):
                        linhas_resp.append(linha)
                dados["resposta"] = "\n".join(linhas_resp).strip()
                dados["arquivo"]  = a.name
                if dados.get("session_id") == session_id:
                    consultas_encontradas.append(dados)
            except Exception:
                pass

        if formato == "texto":
            # Gera texto corrido para colar num chat
            linhas = [f"# Sessão: {session_id}\n"]
            for r in registros_encontrados:
                linhas.append(f"## Registro — {r.get('data','')} {r.get('hora','')}")
                if r.get("titulo"):   linhas.append(f"**{r['titulo']}**")
                if r.get("fase"):     linhas.append(f"Fase: {r['fase']} | Jogo: {r.get('jogo','')}")
                if r.get("agora"):    linhas.append(f"\nComo estava:\n{r['agora']}")
                if r.get("foco"):     linhas.append(f"\nFoco:\n{r['foco']}")
                if r.get("reflexao"): linhas.append(f"\nReflexão:\n{r['reflexao']}")
                linhas.append("")

            for c in consultas_encontradas:
                linhas.append(f"## Consulta {c.get('servico','').title()} — {c.get('data','')} {c.get('hora','')}")
                if c.get("pergunta"): linhas.append(f"Pergunta: {c['pergunta']}")
                if c.get("resposta"): linhas.append(f"\nResposta:\n{c['resposta']}")
                linhas.append("")

            return {
                "ok": True,
                "texto": "\n".join(linhas),
                "total_registros": len(registros_encontrados),
                "total_consultas": len(consultas_encontradas)
            }

        # Formato JSON completo
        return {
            "ok": True,
            "session_id": session_id,
            "registros": registros_encontrados,
            "consultas": consultas_encontradas,
            "total_registros": len(registros_encontrados),
            "total_consultas": len(consultas_encontradas)
        }


    def _atualizar_sessao(self, dados):
        """Atualiza o session_id de um registro existente."""
        arquivo  = dados.get("arquivo", "")
        novo_id  = dados.get("session_id", "").strip()

        if not arquivo or ".." in arquivo or "/" in arquivo:
            return {"ok": False, "erro": "arquivo inválido"}

        caminho = REGISTROS / arquivo
        if not caminho.exists():
            return {"ok": False, "erro": "arquivo não encontrado"}

        conteudo = caminho.read_text(encoding="utf-8")

        # Substitui session_id no frontmatter
        if re.search(r'^session_id:', conteudo, re.MULTILINE):
            conteudo = re.sub(r'^session_id:.*$', f'session_id: {novo_id}', conteudo, flags=re.MULTILINE)
        else:
            # Adiciona antes do fechamento do frontmatter
            conteudo = conteudo.replace('---\n\n#', f'session_id: {novo_id}\n---\n\n#', 1)

        caminho.write_text(conteudo, encoding="utf-8")
        print(f"  ✅ Sessão atualizada: {arquivo} → {novo_id}")
        return {"ok": True, "arquivo": arquivo, "session_id": novo_id}


# ---- EXECUÇÃO ----
print("=" * 50)
print("  Especificador — Servidor Local")
print("=" * 50)
print(f"  Base:     {BASE}")
print(f"  Obsidian: {OBSIDIAN}")
print(f"  HTML:     {HTML_FILE}")
print()

if not HTML_FILE.exists():
    print(f"  ⚠️  especificador.html não encontrado em:")
    print(f"     {HTML_FILE}")
    print(f"  Salve o arquivo lá e reinicie o servidor.")
    print()

print(f"  Abrindo em http://localhost:{PORT}")
print("  Ctrl+C para parar.")
print()

HTTPServer(("localhost", PORT), Handler).serve_forever()
