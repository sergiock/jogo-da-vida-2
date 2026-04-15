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
Próximo passo: implementar commit automático + campo autor + estrutura de pastas.

---

## Estado ao fechar

- Servidor rodando em localhost:8080
- canal17/ com 3 posts de síntese
- GitHub atualizado
- Arquitetura multi-colaborador: definida, não implementada
