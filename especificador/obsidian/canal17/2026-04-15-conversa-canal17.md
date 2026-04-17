---
tags: [canal17, sessao, conversa]
data: 2026-04-15
---

# Conversa Canal 17 — 13 a 15/04/2026

---

## Bootstrap

Retomada do Canal 17 após intervalo.
Estado: 3 commits no main, servidor em 8080, 2 sessões exportadas no vault.

Diagnóstico das linhas abertas:
- Prioridade A: fechar backlog (filename dos registros, múltiplas consultas por registro)
- Prioridade B: documentação do processo
- Prioridade C: site cores com eventos — salto de fase maior

---

## Correção: títulos dos registros

Registros novos tinham filename só com data (`2026-04-13.md`).
No Obsidian, o arquivo aparecia sem título identificável.

**Fix aplicado em `servidor_unico.py`:**
Filename agora inclui hora + slug do título:
`2026-04-13-1021-as-imagens-entram-em-campo.md`

Alinhado com o formato histórico dos registros mais antigos.

---

## Registro: as imagens entram em campo

`[[registros/2026-04-13-1021-as-imagens-entram-em-campo]]`

Marca a transição da fase 1 (criador isolado) para a fase 2 (jogo coletivo).
9 anexos: partituras, tetraedros, mapa, corpo, PDFs.

Post canal17 gerado: `[[canal17/2026-04-13-as-imagens-entram-em-campo]]`

Subtítulo adicionado pelo autor:
> *assumindo protagonismos em jogadas transparentes*

Leitura operacional: três linhas em aberto —
custo de processamento, canal de saída para o mundo externo, artefatos como unidade de troca.

---

## Registro: convergência — o padrão Karpathy

`[[registros/2026-04-13-1229-o-que-podemos-aprender-com-essa-experiên]]`

Referência: gist de Andrej Karpathy sobre LLM Wiki.

Observação do autor: *"parece que todas as inteligências tendem à convergência."*

**Padrão LLM Wiki:**
- Fontes brutas (imutáveis) + Wiki (markdown sintetizado pela IA) + Schema (configuração)
- Operações: Ingest, Query, Lint
- Princípio: a parte tediosa não é pensar — é a escrituração. LLMs fazem a escrituração.

**Mapeamento para o Jogo da Vida:**

| Karpathy | Jogo da Vida |
|---|---|
| Fontes brutas | registros/ |
| Wiki | canal17/, sessões exportadas |
| Schema | sistema de canais (6, 15, 16, 17) |

O que falta: ingest automático (registro salvo → síntese gerada), lint periódico, query com arquivamento.

Post canal17 gerado: `[[canal17/2026-04-13-convergencia-llm-wiki]]`

---

## Commit

Publicado no GitHub `sergiock/jogo-da-vida-2`:
36 arquivos, 977 inserções — fase 2 no repositório.

---

## Expandindo o alcance — colaboradores não-programadores

**Tema:** ampliar a plataforma para além do perfil programador.
O vault abre áreas temáticas que pedem aprofundamento e discussão com outros tipos de colaboradores.

**Foco definido:** contribuição de conteúdo.

**Arquitetura atual vs. necessária:**

Hoje: `máquina local → servidor local → vault local → git manual`

Para múltiplos colaboradores: `servidor hospedado → vault compartilhado → git automático`

**Decisão central: controle editorial**

- **Curadoria** — contribuições em branch separada, merge manual por Sergio
- **Vault aberto** — cada colaborador numa pasta própria, síntese periódica

**Proposta mínima viável:**
1. Deploy do servidor (Railway ou Render)
2. Campo `autor` nos registros
3. Pasta por colaborador: `colaboradores/{nome}/registros/`
4. Commit automático a cada save (item crítico — ainda não existe)

**Decisão:** vault aberto.

Cada colaborador numa pasta própria. Síntese periódica por Sergio.

---

## Implementação: commit automático + campo autor

**Mudanças em `servidor_unico.py`:**

- Função `_git_commit(arquivos, mensagem)` — git add + commit + push automático
- Função `_pasta_colaborador(autor)` — retorna `registros/` para Sergio, `colaboradores/{autor}/registros/` para outros
- Campo `autor` nos registros — tag `autor/{nome}` no frontmatter
- `_salvar_registro` e `_salvar_consulta` chamam `_git_commit` após cada save

**Quando `GITHUB_TOKEN` disponível:** push automático para `main` após cada commit.

---

## Preparação para deploy

**Mudanças para produção:**
- `BASE` via `APP_BASE` (env var) — configurável sem alterar código
- `PORT` via `PORT` (env var) — Railway injeta automaticamente
- Bind em `0.0.0.0` quando `APP_BASE` definido (necessário em cloud)
- `Procfile` criado: `web: python3 dev/python/servidor_unico.py`

**Fluxo em produção:**
```
colaborador → servidor Railway → git commit → git push → GitHub → Sergio faz pull
```

**Variáveis de ambiente necessárias no Railway:**
- `APP_BASE` = `/app`
- `GITHUB_TOKEN` = Personal Access Token (scope: repo)
- `GIT_USER_NAME` = `Canal 17`
- `GIT_USER_EMAIL` = `canal17@jogo-da-vida.app`

**Commit publicado:** `7308f66` — `sergiock/jogo-da-vida-2`

**Próximo passo:** deploy no Railway (conectar repo → definir variáveis → URL pública).

---

## Estado ao fechar (15/04)

- Servidor rodando em localhost:8080 (commit automático ativo, push local sem token)
- canal17/ com 3 posts de síntese + este log
- GitHub atualizado (commit `7308f66`)
- Arquitetura multi-colaborador: implementada localmente, aguardando deploy

---

## Deploy Railway — 16/04

Deploy online em `jogo-da-vida-2.up.railway.app`.

**Problemas encontrados e resolvidos:**

1. **Railpack não detectou Python** → adicionado `requirements.txt` e `runtime.txt`
2. **Variáveis de ambiente** — configuradas no Railway (Variables → service level):
   `APP_BASE=/app`, `GITHUB_TOKEN`, `GIT_USER_NAME`, `GIT_USER_EMAIL`
3. **Anexos não persistiam** → `_upload_anexo` agora chama `_git_commit` após salvar binário
4. **Colaboradores A1/A2/A3** chegaram ao GitHub mas não apareciam no Obsidian local → resolvido com `git pull`; pasta `colaboradores/` presente no vault
5. **Repositório errado** — diretório local `/actualsc/jogo-da-vida` apontava para repo `jogo-da-vida` (3 commits, sem o projeto). Projeto real está em `jogo-da-vida-2`, clonado para `/actualsc/jogo-da-vida-2`
6. **BASE hardcoded** → corrigido para `Path(__file__).resolve().parents[2]` — detecta automaticamente independente do path local ou Railway
7. **Commit Railway sobrepôs HTML** — commit `2b66757` (feito pelo servidor Railway) truncou `especificador.html` de 2793 para 752 linhas, removendo autor, anexos e resto da interface → restaurado a partir do commit `f03b8bc`
8. **Cache do browser** — após restauração, browser servia versão antiga → solução: aba anônima (Cmd+Shift+N) ou hard refresh (Cmd+Shift+R)

**Estado atual:**
- Servidor local: `python3 /Users/sergio/Documents/actualsc/jogo-da-vida-2/dev/python/servidor_unico.py`
- localhost:8080 funcionando com HTML completo (autor + anexos)
- Railway online com redeploy automático a cada push
- Colaboradores salvam em `colaboradores/{autor}/registros/` com commit+push automático
