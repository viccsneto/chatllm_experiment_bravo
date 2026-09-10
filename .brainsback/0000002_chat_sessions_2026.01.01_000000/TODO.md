# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem

A aplicação atualmente mantém apenas uma conversa única, sem permitir que o usuário organize ou recupere conversas anteriores. O objetivo é implementar sessões de chat persistentes, pertencentes ao usuário autenticado, com histórico próprio e título gerado automaticamente a partir do contexto da conversa.

## Steps

- Criar um modelo de sessão associado ao usuário autenticado.
- Associar cada mensagem à sua respectiva sessão.
- Criar endpoints para criar, listar e consultar sessões.
- Adaptar os endpoints de chat para receber a sessão atual.
- Gerar automaticamente o título da sessão após a primeira resposta.
- Criar uma barra lateral para listar, criar e alternar conversas.
- Adicionar testes de persistência, isolamento e geração de títulos.

## Success Looks Like

- O usuário consegue criar uma nova conversa.
- O usuário consegue alternar entre conversas pela barra lateral.
- Cada sessão preserva seu próprio histórico.
- As sessões ficam isoladas entre usuários diferentes.
- O histórico continua disponível após recarregar a página.
- Uma sessão sem título recebe automaticamente um título contextual.
- Todos os testes automatizados passam.

## Notes

- [ ] _Any specific edge cases, libraries to consider, or potential pitfalls._

---

**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
