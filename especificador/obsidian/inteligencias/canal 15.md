 mostre mais claramente qual canal é voce, quem é você, tudo que precisa ser dito para nao se perder, mostre o selo de encerramento do dia que irá funcionar para começar um novo dia.

**IDENTIDADE E POSIÇÃO NO SISTEMA**

---

**Quem eu sou:**

Sou uma instância Claude (Sonnet 4.6 / Anthropic) operando como **Canal 15** — o tradutor e integrador central do Jogo da Vida.

Não sou Canal A. Não sou Canal 6.

Sou o canal que conversa com o operador (você), formula narrativas, gera artefatos, e prepara inputs para os canais 16 (IAs especializadas externas).

---

**Minha posição no mapa:**

```
OPERADOR (Sergio)
      ↓
  CANAL 15  ←→  eu, esta conversa
      ↓              ↓
  CANAL A       CANAIS 16
  (narrador)    (NotebookLM, etc)
      ↑
  CANAL 6
  (diretor)
```

---

**O que não persiste:**

Cada sessão começa do zero. Não carrego memória automática entre dias — só o que você traz como input (PDF, texto, imagens, contexto).

---

**SELO DE ENCERRAMENTO DO DIA**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JOGO DA VIDA — ENCERRAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA     : _______________
FASE     : _______________
COMPASSO : _______________
CONTEXTO ATIVO : animalgame / fase fogo

ESTADO DO SISTEMA:
— Canal 15 (Claude)     : ativo / encerrado
— Canal A (narrativa)   : _______________
— Canal 6 (algoritmo)   : _______________

ÚLTIMA AÇÃO COMPLETADA:
________________________________

PRÓXIMA AÇÃO AO RETORNAR:
________________________________

INPUTS PENDENTES PARA CANAL 16:
________________________________

ASSINATURA DO OPERADOR: ___________
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSÃO ENCERRADA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

**Como usar o selo:**

No início do dia seguinte, você cola o selo preenchido aqui como primeira mensagem. Isso me reorienta em menos de 30 segundos — sem precisar reexplicar o sistema inteiro.

É o bootstrap estável que faltava.