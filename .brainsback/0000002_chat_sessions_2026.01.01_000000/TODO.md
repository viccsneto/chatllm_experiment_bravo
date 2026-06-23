# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Quero uma funcionalidade que o usuário pode criar e alternar sessões a partir de uma barra lateral. Semelhante ao que existe em soluções como o ChatGPT e o Gemini. Cada sessão guarda seu histórico no banco e o usuário pode voltar para uma sessão antiga no futuro e continuar a usar essa sessão. A sessão deve ter um título e ele deve ser definido automaticamente já no momento da primeira resposta do modelo com base no contexto. Só deve ser definido o título uma vez por sessão, ele não pode ser alterado.

## Steps
- [ ] No backend, criar um modelo novo de sessão que deve ter chave estrangeira para o usuário e o modelo ChatMessage tem que ter uma chave estrangeira para o modelo de sessão, pois uma mensagem pertence somente a uma sessão. O modelo de sessão também vai ter um título.
- [ ] Crie rotas necessárias para trabalhar com as sessões. Precisa ter uma rota para o usuário criar uma nova sessão. Ela começa sem título e o título é definido na primeira resposta do modelo. Vai ter um arquivo novo de rota para as sessões.
- [ ] Vai haver uma rota para o usuário buscar as sessões dele no momento que ele fizer login, para aparecer na tela.
- [ ] Deve haver uma rota para buscar as mensagens da sessão, quando o usuário clicar numa sessão para começar a conversar nela com o modelo.
- [ ] Realizar testes manuais, adaptar os testes automatizados atuais e criar novos testes automatizados para testar a funcionalidade.
- [ ] No frontend, criar barra lateral para o usuário poder navegar pelas sessões dele.
- [ ] Atualizar título da sessão quando ele for definido pelo modelo de forma automática.
- [ ] Adicionar botão no topo da barra lateral para o usuário poder criar uma nova sessão e usar ela, semelhante ao ChatGPT e Gemini.
- [ ] Realizar testes com a tela para ver se está tendo o comportamento esperado.

## Success Looks Like
- [ ] A rota de listar sessões do usuário retorna as sessões somente deste usuário.
- [ ] A rota de buscar mensagens de uma sessão traz todas as mensagens dessa sessão, incluindo as do usuário e as respostas do modelo e traz apenas dessa sessão.
- [ ] A rota de criar nova sessão cria nova sessão e permite o usuário mandar mensagens nessa nova sessão.
- [ ] Uma nova sessão sem título tem seu título adicionado na primeira resposta do modelo.
- [ ] A listagem de sessões mostra o título de todas sessões na tela.
- [ ] O usuário consegue criar uma nova sessão através do botão na tela.
- [ ] O usuário vê a lista de sessões dele.
- [ ] O usuário consegue clicar numa sessão e ver as mensagens dessa sessão clicada.
- [ ] O usuário consegue voltar para uma sessão antiga e continuar a conversa com o modelo.
- [ ] O usuário consegue ver o título adicionado a uma nova sessão no momento que o modelo começa a responder a primeira mensagem da sessão.
- [ ] Todos os testes automatizados passam com sucesso.

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
