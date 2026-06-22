# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
O sistema atual opera com um chat de sessão única e volátil. Para aproximar a experiência do usuário aos padrões de mercado e permitir a retenção de conhecimento, precisamos transformar o chat em um sistema multi-sessão persistente. O principal desafio arquitetural é isolar o histórico de mensagens por contexto de sessão e automatizar a criação de títulos amigáveis usando o próprio modelo de linguagem (LLM), evitando que o usuário precise nomear o chat manualmente e reduzindo a fricção na primeira interação.

## Steps
- [ ] Modelagem e Persistência de Sessões: Criar a estrutura de dados para ChatSession (ID, título, ID do usuário, timestamps) no banco de dados, estabelecendo um relacionamento de um para muitos com as mensagens existentes.
- [ ] Isolamento de Contexto no Backend: Modificar o motor do chat para receber um identificador de sessão (session_id) nas requisições. O backend deve carregar apenas o histórico específico daquela sessão antes de enviar o prompt ao LLM.
- [ ] Geração Assíncrona/Condicional de Título: Implementar uma regra de negócio que detecta se a sessão possui um título genérico/padrão. Se for a primeira resposta da inteligência artificial, disparar uma chamada em segundo plano (ou encadeada) para o LLM resumir o contexto inicial em uma string de até 4-5 palavras.
- [ ] Interface de Navegação Lateral: Desenvolver o componente de barra lateral (sidebar) para listar as sessões do usuário de forma cronológica (Ex: Hoje, Ontem, Últimos 7 dias).


## Success Looks Like
- [ ] O usuário clica em "Novo Chat", uma nova sessão limpa é criada no banco e a URL ou estado visual é atualizado.
- [ ] Ao enviar a primeira mensagem em um chat novo, o título da barra lateral muda automaticamente de "Nova conversa" (ou similar) para um resumo curto baseado na conversa, sem exigir recarregamento manual da página.
- [ ] Alternar entre diferentes sessões na barra lateral carrega instantaneamente (ou exibe um loading adequado) o histórico de mensagens correspondente a cada uma delas.


## Notes
- [ ] Pitfall (Latência): A geração do título automático não deve travar a resposta principal do chat para o usuário. Idealmente, deve rodar após a primeira resposta ser concluída ou em uma tarefa de background.

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
