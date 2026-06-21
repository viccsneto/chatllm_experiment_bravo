# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
O chat atual suporta apenas uma única conversa, fazendo com que o histórico seja perdido ou misturado a cada nova interação. O objetivo é implementar o suporte a múltiplas sessões de chat independentes, permitindo ao usuário criar, alternar e retomar conversas através de uma barra lateral. Cada sessão deve isolar seu próprio histórico de mensagens e possuir um título gerado automaticamente para identificação rápida, melhorando a experiência de uso e a organização do usuário.

## Steps
- [ ] Analisar o fluxo atual do chat para mapear onde o sistema armazena, exibe e assume uma única conversa.

- [ ] Definir a estrutura da sessão de chat e mapeie como ela vai se conectar com os usuários e com as mensagens.

- [ ] Planejar as operações necessárias para criar, listar, selecionar e carregar sessões separadas.

- [ ] Garantir que as novas mensagens enviadas sejam associadas à sessão que está aberta na tela.

- [ ] Definir uma interface com a nova barra lateral para permitir a criação de chats, a troca de contexto e a indicação visual de qual conversa está selecionada.

- [ ] Estabelecer uma regra para a criação do título automático e o comportamento quando ela falhar.

- [ ] Testar o isolamento dos históricos, o comportamento da troca rápida entre chats e se as informações continuam lá após atualizar a página.

## Success Looks Like
- [ ] Ao clicar no botão de nova conversa na barra lateral, uma sessão limpa é iniciada imediatamente na interface.

- [ ] A barra lateral lista todas as sessões criadas pelo usuário de forma organizada e atualizada.

- [ ] Ao clicar em uma sessão diferente na barra lateral, o histórico antigo desaparece e o histórico da nova sessão selecionada é carregado sem misturar mensagens de conversas diferentes.

- [ ] As mensagens enviadas dentro de uma sessão específica permanecem visíveis apenas dentro dela.

- [ ] Ao recarregar a página (F5), a barra lateral e a sessão que estava aberta continuam sendo exibidas exatamente no mesmo estado de antes.

- [ ] O título automático da sessão atualiza na barra lateral de forma consistente.

- [ ] Se o serviço de geração de título falhar, a interface exibe um título padrão legível (ex: "Conversa sem título") e o chat continua funcionando normalmente.

## Notes
- [ ] Sessões vazias: Decidir se aparecem na barra lateral antes da primeira mensagem.

- [ ] Falha no título: O chat deve continuar funcionando mesmo se o título falhar.

- [ ] Troca rápida: Evitar que o histórico de um chat apareça no outro por lentidão da API.

- [ ] Segurança: Validar o usuário autenticado em todas as requisições de sessão.

- [ ] Recarregamento: Definir se o F5 reabre o último chat ativo ou abre um padrão.

- [ ] Custo/Tempo: Gerar o título em segundo plano para não travar o chat.

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
