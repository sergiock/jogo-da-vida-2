"""
servidor_cores.py
Serve o cores.html e salva eventos no Obsidian compartilhado.

Uso:
    python3.13 servidor_cores.py
    Abrir: http://localhost:8282
"""

import json
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Caminhos — usa o mesmo Obsidian do Especificador
BASE     = Path.home() / "Documents/actualsc/jogo-da-vida"
OBSIDIAN = BASE / "especificador/obsidian"
EVENTOS  = OBSIDIAN / "eventos"
STATUS   = OBSIDIAN / "status.json"
HTML     = BASE / "cores/prototipos/cores.html"
PORT     = 8282

JOGOS = {
    '01':'Caça','02':'Guerra','03':'Superação','04':'Sedução',
    '05':'Estratégia','06':'Oráculo','07':'Vício','08':'Brincadeira',
    '09':'Play','10':'Projeção','11':'Simulação','12':'Antecipação'
}


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        if path in ('/', '/index.html'):
            self._serve_file(HTML)

        elif path == '/api/status':
            if STATUS.exists():
                self._json(json.loads(STATUS.read_text(encoding='utf-8')))
            else:
                self._json({'fase': '', 'jogo': ''})

        elif path == '/api/eventos':
            limite = int(qs.get('limite', [20])[0])
            hoje   = datetime.now().strftime('%Y-%m-%d')
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
            # Retorna todos os eventos ordenados por data
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

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            dados = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        path = urlparse(self.path).path

        if path == '/api/evento/salvar':
            self._json(self._salvar_evento(dados))

        elif path == '/api/status/salvar':
            STATUS.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"  ✅ Status salvo: fase={dados.get('fase')}")
            self._json({'ok': True})

        elif path == '/api/consulta/salvar':
            self._json(self._salvar_consulta_cores(dados))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ---- HELPERS ----

    def _serve_file(self, filepath):
        try:
            conteudo = Path(filepath).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(conteudo)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _json(self, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(corpo)

    def _parse_evento(self, conteudo):
        dados = {'descricao':'','jogo':'','tipo':[],'impacto':[],'ameaca':[],'pessoa':[],'data':'','hora':'','jogo_nome':''}
        for linha in conteudo.splitlines():
            for campo in ['descricao','jogo','data','hora']:
                if linha.startswith(campo + ':'):
                    dados[campo] = linha.split(':',1)[1].strip()
            for campo in ['tipo','impacto','ameaca','pessoa']:
                if linha.startswith(campo + ':'):
                    val = linha.split(':',1)[1].strip()
                    try:
                        dados[campo] = json.loads(val)
                    except Exception:
                        dados[campo] = [v.strip() for v in val.split(',') if v.strip()]
        dados['jogo_nome'] = JOGOS.get(dados['jogo'], '')
        return dados

    def _salvar_evento(self, dados):
        agora_dt  = datetime.now()
        hoje      = agora_dt.strftime('%Y-%m-%d')
        hora      = agora_dt.strftime('%H%M')
        hora_br   = agora_dt.strftime('%H:%M')
        data_br   = agora_dt.strftime('%d/%m/%Y')

        descricao = dados.get('descricao', '').strip()
        jogo      = dados.get('jogo', '')
        tipo      = dados.get('tipo', [])
        impacto   = dados.get('impacto', [])
        ameaca    = dados.get('ameaca', [])
        pessoa    = dados.get('pessoa', [])
        jogo_nome = JOGOS.get(jogo, '')

        # Slug do arquivo
        slug = descricao.lower()[:30]
        slug = slug.replace(' ', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        nome_arquivo = f"{hoje}-{hora}-{slug}.md"

        # Tags
        tags = ['evento']
        if jogo: tags.append(f'jogo/{jogo}')
        tags += [f'tipo/{t.lower()}' for t in tipo]
        tags += [f'impacto/{i.lower()}' for i in impacto]
        tags_str = ', '.join(tags)

        conteudo = f"""---
tags: [{tags_str}]
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

| Dimensão   | Seleções |
|------------|----------|
| Tipo       | {', '.join(tipo)    or '—'} |
| Impacto    | {', '.join(impacto) or '—'} |
| Ameaça     | {', '.join(ameaca)  or '—'} |
| Personagens| {', '.join(pessoa)  or '—'} |

## Notas
_adicione observações no Obsidian_
"""
        EVENTOS.mkdir(parents=True, exist_ok=True)
        arquivo = EVENTOS / nome_arquivo
        arquivo.write_text(conteudo, encoding='utf-8')
        print(f"  ✅ Evento salvo: {nome_arquivo}")
        return {'ok': True, 'arquivo': nome_arquivo}


    def _salvar_consulta_cores(self, dados):
        """Salva resposta de LM com texto e imagens em consultas/."""
        import base64 as b64mod

        agora_dt   = datetime.now()
        timestamp  = agora_dt.strftime('%Y-%m-%d-%H%M')
        data_br    = agora_dt.strftime('%d/%m/%Y %H:%M')

        servico    = dados.get('servico', 'lm')
        resposta   = dados.get('resposta', '')
        imagens    = dados.get('imagens', [])   # [{base64, nome}]
        ref_evento = dados.get('ref_evento', '')
        descricao  = dados.get('descricao', '')
        jogo       = dados.get('jogo', '')
        jogo_nome  = JOGOS.get(jogo, '')

        consultas_dir = OBSIDIAN / 'consultas'
        assets_dir    = consultas_dir / 'assets'
        consultas_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Salva imagens e monta links markdown
        links_imagens = ''
        for img in imagens:
            try:
                nome    = img.get('nome', f'img-{timestamp}.png')
                b64data = img.get('base64', '')
                # Remove prefixo data:image/...;base64,
                if ',' in b64data:
                    b64data = b64data.split(',', 1)[1]
                caminho = assets_dir / nome
                caminho.write_bytes(b64mod.b64decode(b64data))
                links_imagens += f'\n![[assets/{nome}]]'
                print(f"  📷 Imagem salva: {nome}")
            except Exception as e:
                print(f"  ⚠ Erro ao salvar imagem: {e}")

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
        arquivo = consultas_dir / nome_arquivo
        arquivo.write_text(conteudo, encoding='utf-8')

        # Atualiza o evento original com link
        if ref_evento:
            evento_arquivo = EVENTOS / ref_evento
            if evento_arquivo.exists():
                texto = evento_arquivo.read_text(encoding='utf-8')
                link  = f"- [[consultas/{nome_arquivo}]] — {servico.title()} · {data_br}"
                if '## Consultas' in texto:
                    texto = texto.replace('## Consultas', '## Consultas\n' + link)
                else:
                    texto += f'\n\n## Consultas\n{link}\n'
                evento_arquivo.write_text(texto, encoding='utf-8')

        print(f"  ✅ Consulta salva: {nome_arquivo}")
        return {'ok': True, 'arquivo': nome_arquivo}


    def _buscar_conexoes(self, qs):
        """Busca conexões na base Obsidian para um evento."""
        jogo    = qs.get('jogo',    [''])[0]
        tipo    = [t for t in qs.get('tipo',    [''])[0].split(',') if t]
        impacto = [t for t in qs.get('impacto', [''])[0].split(',') if t]
        ameaca  = [t for t in qs.get('ameaca',  [''])[0].split(',') if t]

        resultado = {}

        # 1. Nota do jogo
        if jogo:
            jogo_num = jogo.zfill(2)
            jogos_dir = OBSIDIAN / 'jogos'
            if jogos_dir.exists():
                for f in jogos_dir.glob('*.md'):
                    if f.name.startswith(jogo_num):
                        conteudo = f.read_text(encoding='utf-8')
                        linhas = conteudo.splitlines()
                        titulo = next((l[2:].strip() for l in linhas if l.startswith('# ')), f.stem)
                        preview = ' '.join(l for l in linhas if l and not l.startswith('#') and not l.startswith('---') and not l.startswith('tags:'))[:200]
                        resultado['jogo_nota'] = {'arquivo': f.name, 'titulo': titulo, 'preview': preview}
                        break

        # 2. Fase atual (do status.json)
        if STATUS.exists():
            try:
                status = json.loads(STATUS.read_text(encoding='utf-8'))
                fase = status.get('fase', '')
                if fase:
                    fases_dir = OBSIDIAN / 'fases'
                    if fases_dir.exists():
                        for f in fases_dir.glob('*.md'):
                            if fase in f.name:
                                conteudo = f.read_text(encoding='utf-8')
                                linhas = conteudo.splitlines()
                                titulo = next((l[2:].strip() for l in linhas if l.startswith('# ')), f.stem)
                                preview = ' '.join(l for l in linhas if l and not l.startswith('#') and not l.startswith('---'))[:200]
                                resultado['fase_nota'] = {'arquivo': f.name, 'titulo': titulo, 'preview': preview}
                                break
            except Exception:
                pass

        # 3. Registros do Especificador com mesmo jogo ou classificações
        registros_dir = OBSIDIAN / 'registros'
        if registros_dir.exists():
            encontrados = []
            for f in sorted(registros_dir.glob('*.md'), reverse=True)[:50]:
                try:
                    conteudo = f.read_text(encoding='utf-8')
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ['titulo','jogo_ativo','fase','data','foco','agora']:
                            if linha.startswith(campo + ':'):
                                dados[campo] = linha.split(':',1)[1].strip()
                    # Match por jogo
                    match = jogo and dados.get('jogo_ativo','').startswith(jogo)
                    if match:
                        preview = (dados.get('agora','') or dados.get('foco',''))[:120]
                        encontrados.append({
                            'arquivo': f.name,
                            'titulo':  dados.get('titulo','') or dados.get('foco','') or f.stem,
                            'data':    dados.get('data',''),
                            'preview': preview
                        })
                        if len(encontrados) >= 3: break
                except Exception:
                    pass
            if encontrados:
                resultado['registros'] = encontrados

        # 4. Consultas com mesmo jogo
        consultas_dir = OBSIDIAN / 'consultas'
        if consultas_dir.exists():
            encontradas = []
            for f in sorted(consultas_dir.glob('*.md'), reverse=True)[:50]:
                try:
                    conteudo = f.read_text(encoding='utf-8')
                    dados = {}
                    for linha in conteudo.splitlines():
                        for campo in ['servico','jogo','data','titulo']:
                            if linha.startswith(campo + ':'):
                                dados[campo] = linha.split(':',1)[1].strip()
                    if not dados.get('titulo'):
                        for linha in conteudo.splitlines():
                            if linha.startswith('# '):
                                dados['titulo'] = linha[2:].strip(); break
                    # Extrai preview da resposta
                    em_resposta = False
                    linhas_resp = []
                    for linha in conteudo.splitlines():
                        if linha == '## Resposta': em_resposta = True; continue
                        if em_resposta and not linha.startswith('#') and not linha.startswith('---') and not linha.startswith('>'):
                            linhas_resp.append(linha)
                        if len(linhas_resp) > 3: break
                    preview = ' '.join(linhas_resp)[:120]

                    match = jogo and dados.get('jogo','').startswith(jogo)
                    if match:
                        encontradas.append({
                            'arquivo': f.name,
                            'titulo':  dados.get('titulo','Consulta'),
                            'servico': dados.get('servico',''),
                            'data':    dados.get('data',''),
                            'preview': preview
                        })
                        if len(encontradas) >= 3: break
                except Exception:
                    pass
            if encontradas:
                resultado['consultas'] = encontradas

        return resultado


# ---- EXECUÇÃO ----
print("=" * 50)
print("  Cores — Servidor Local")
print("=" * 50)
print(f"  Obsidian: {OBSIDIAN}")
print(f"  Eventos:  {EVENTOS}")
print(f"  HTML:     {HTML}")
print()

if not HTML.exists():
    print(f"  ⚠️  cores.html não encontrado em: {HTML}")
    print(f"  Salve o arquivo lá e reinicie.")
    print()

print(f"  Abrindo em http://localhost:{PORT}")
print("  Ctrl+C para parar.\n")

HTTPServer(('localhost', PORT), Handler).serve_forever()
