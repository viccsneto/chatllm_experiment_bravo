# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Gostaria de implementar sessões de chats, estilo chatGPT com histórico das perguntas e respostas, cada mensagem deve ser associada a uma sessão. Estas sessões serão apresentadas ao usuário numa barra lateral do chat com as sessões existentes, cada qual com um título associado, quando uma sessão nova é iniciada ela recebe um título baseado na primeira mensagem, enquanto isso um título default é utilizado ("New chat"). As sessões podem ser alternadas clicando na sessão desejada na barra lateral. As sessões de um usuário não pode ser acessada por outros usuários, então é necessário a autentificação do usuário, para que apenas suas sessões sejam retornadas.

## Steps
- [ criar schemas para sessão, mensagens ]
- [ no model da mensagem deve ter um campo de timestamp para garantia do histórico ]
- [ gerar autentificação no acesso às sessões ]
- [ criar um router para as sessões ]
- [ garantir persistência no db ]
- [ criar barra lateral para acesso/visualização às sessões ] 
- [ criar gerador de título a partir da primeira mensagem ]
- [ atualizar o operouter para gerar um título ]
- [ gerar testes para garantir que um usuário não acesse sessões de outros usuários ]
- [ gerar testes pra criação automática de título ]
- [ gerar testes para o histórico ]
## Success Looks Like
- [ Ser possível o acesso apenas às sessões do usuário ao realizar o login, quando o usuário realizar o logout, não deve mais ser permitido o acesso às sessões ]
- [ Quando uma sessão for acessada o seu histórico de mensagens deve vir junto ]
- [ Uma barra lateral com sessões for mostrada após o login ]
- [ Um título provisório for mostrado quando uma nova sessão iniciar ]
- [ Após a primeira mensagem numa sessão nova, um título for gerado com base nesssa mensagem ]
- [ Os testes não falharem ] 

## Notes
- [ Cada sessão deve ser associada a um usuário ] 

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
