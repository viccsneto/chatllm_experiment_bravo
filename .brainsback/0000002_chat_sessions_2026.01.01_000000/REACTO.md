# Proof of Mastery (REACTO)

> Explain it to prove you own it.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## R — Repeat (The Problem)
O problema era que o nosso chat era esquecido: o usuário só podia ter uma única conversa por vez e, se atualizasse a página, perdia tudo. Precisávamos criar um sistema de conversas salvas (estilo ChatGPT), onde o usuário consegue criar vários chats, alternar entre eles por uma barra lateral e excluir o que não quiser mais. De quebra, o sistema precisa ser inteligente o suficiente para ler as primeiras mensagens e dar um título automático para o chat sozinho, sem o usuário precisar digitar um nome para a conversa.

## E — Examples
_Provide concrete inputs and expected outputs that demonstrate the correctness. Base them on observable behavior._

- **Happy Path Input**: ...
  Usuário clica em "Novo Chat", a sidebar mostra "Nova conversa".

  Ele envia: "Como fazer um bolo de cenoura fofinho?"

  Output esperado: O chat responde a receita normalmente. Em background, a sidebar atualiza sozinha o título de "Nova conversa" para "Receita de Bolo de Cenoura".

- **Edge Case Input**: ...
  O usuário abre um chat novo e manda só um "Oi" ou um emoji.

  Output esperado: O chat responde o cumprimento. O LLM tenta gerar um título, mas por falta de contexto, o sistema aciona o fallback e mantém o nome como "Nova conversa", sem quebrar o código ou dar erro na tela.

## A — Approach
A estratégia de solução foi dividida em três pilares principais que conectam o banco de dados à interface. Primeiro, criamos a tabela de sessões de chat e alteramos as mensagens para que fiquem atreladas a um identificador único de sessão via chave estrangeira, limpando o banco antigo para evitar conflitos de estrutura. Segundo, para resolver o problema do título sem prejudicar o tempo de resposta, adotamos uma abordagem totalmente assíncrona no backend, onde a rota principal salva a mensagem e delega a geração do título para uma tarefa em segundo plano que roda em paralelo. Terceiro, no frontend, redesenhamos o layout para incluir uma barra lateral que agrupa os chats por períodos cronológicos e centraliza o ID do chat ativo, forçando a tela a limpar o estado e carregar o histórico correto sempre que o usuário alterna entre as conversas.

## C — Code
Os pontos mais críticos do código estão concentrados no gerenciamento de estado do frontend e no assincronismo do backend. No servidor, o destaque é a função que lida com o título automático em background usando a criação de tarefas assíncronas do Python; ela aguarda um breve instante para garantir que a mensagem foi salva, consome o histórico inicial e faz uma requisição direta e enxuta para a API do OpenRouter, limitando a resposta a no máximo cinco palavras. No cliente, a lógica principal reside no componente central da aplicação, que gerencia os estados da sessão ativa e da lista de chats, disparando chamadas de atualização de histórico toda vez que o usuário interage com a barra lateral ou quando uma nova resposta do modelo é finalizada.

## T — Tests
A validação de toda essa arquitetura foi feita de forma automatizada com a criação de 12 novos cenários de testes focados especificamente no comportamento das sessões. Esses testes cobrem desde a criação e listagem básica até regras críticas de segurança, como garantir que um usuário nunca consiga visualizar as conversas de outro e que a exclusão de um chat limpe corretamente todas as mensagens vinculadas a ele em cascata no banco de dados. Complementando a suíte que agora conta com mais de sessenta testes bem-sucedidos, realizamos testes manuais no ambiente local rodando na porta padrão para confirmar visualmente que a alternância de abas é imediata e que a barra lateral atualiza os títulos de forma dinâmica.

## O — Optimize
Em termos de complexidade e performance, a solução é eficiente porque a busca de mensagens no banco utiliza índices na foreign key, tornando o carregamento do histórico muito rápido