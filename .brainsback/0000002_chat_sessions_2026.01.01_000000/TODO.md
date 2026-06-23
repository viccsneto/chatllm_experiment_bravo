# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Hoje, a aplicação trabalha como se existisse apenas uma conversa. O usuário não consegue criar vários chats, trocar entre eles ou abrir novamente um histórico antigo pela interface.

O objetivo é permitir que cada usuário tenha várias conversas separadas. Essas conversas devem aparecer em uma barra lateral, parecida com a do ChatGPT ou Gemini.

Cada conversa precisa guardar somente as suas próprias mensagens. As mensagens de uma conversa não podem aparecer em outra e também não podem ser usadas como contexto em outro chat.

As conversas e mensagens devem ficar salvas no banco de dados. Assim, o histórico deve continuar disponível mesmo depois de atualizar a página, fechar a aplicação ou entrar novamente na conta.

Cada conversa deve pertencer ao usuário que a criou. Um usuário não pode ver nem acessar as conversas de outro usuário.

Quando uma nova conversa for criada, ela pode aparecer com um nome temporário, como "Nova conversa". Depois que o modelo terminar a primeira resposta, a aplicação deve criar automaticamente um título curto com base no assunto da conversa.

A solução deve manter o que já funciona hoje, como cadastro, login, logout, envio de mensagens, resposta por streaming e formatação das respostas.

A conversa do chat deve ser tratada de forma separada da sessão usada para manter o usuário conectado.

## Steps
- [ ] Ler e entender como funcionam o login, o envio de mensagens, o streaming e o salvamento das mensagens.
- [ ] Criar uma forma de representar cada conversa no banco de dados.
- [ ] Ligar cada conversa ao usuário que a criou.
- [ ] Ligar cada mensagem à conversa correta.
- [ ] Remover o uso de uma única conversa padrão para todas as mensagens.
- [ ] Garantir que cada conversa tenha seu próprio histórico.
- [ ] Garantir que o histórico seja carregado em ordem correta.
- [ ] Criar uma forma de o usuário iniciar uma nova conversa.
- [ ] Criar uma forma de listar todas as conversas do usuário.
- [ ] Criar uma forma de abrir uma conversa e carregar suas mensagens.
- [ ] Permitir que o usuário envie mensagens somente para a conversa selecionada.
- [ ] Usar apenas o histórico da conversa atual como contexto para o modelo.
- [ ] Salvar a mensagem do usuário na conversa correta.
- [ ] Salvar a resposta do assistente na mesma conversa.
- [ ] Manter o envio da resposta por streaming.
- [ ] Atualizar a conversa sempre que uma nova mensagem for concluída.
- [ ] Mostrar primeiro as conversas usadas mais recentemente.
- [ ] Mostrar um título temporário enquanto a conversa ainda não tiver um título automático.
- [ ] Criar o título automático depois que a primeira resposta terminar.
- [ ] Usar a primeira mensagem e a primeira resposta como contexto para o título.
- [ ] Salvar o título no banco de dados.
- [ ] Não trocar o título automaticamente depois das próximas mensagens.
- [ ] Criar um título simples com base na primeira mensagem caso a geração automática falhe.
- [ ] Garantir que uma falha no título não apague nem interrompa a resposta do chat.
- [ ] Criar uma barra lateral para mostrar as conversas.
- [ ] Destacar visualmente a conversa que está aberta.
- [ ] Permitir que o usuário troque de conversa pela barra lateral.
- [ ] Atualizar o título da conversa na barra lateral sem precisar recarregar a página.
- [ ] Tratar o carregamento da lista de conversas.
- [ ] Tratar o carregamento do histórico de uma conversa.
- [ ] Tratar conversas vazias.
- [ ] Tratar erros ao carregar ou enviar mensagens.
- [ ] Definir o que deve acontecer se o usuário tentar trocar de conversa durante uma resposta em andamento.
- [ ] Limpar os dados visuais do usuário anterior depois do logout.
- [ ] Carregar apenas as conversas do usuário atual depois do login.
- [ ] Criar testes para conversas, mensagens, títulos, histórico e segurança entre usuários.
- [ ] Confirmar que login, logout, streaming e envio de mensagens continuam funcionando.

## Success Looks Like
- [ ] O usuário consegue criar uma nova conversa pela barra lateral.
- [ ] A nova conversa é aberta automaticamente.
- [ ] A nova conversa começa sem mensagens antigas.
- [ ] O usuário consegue criar duas ou mais conversas.
- [ ] O usuário consegue trocar entre as conversas.
- [ ] Cada conversa mostra somente as suas próprias mensagens.
- [ ] Uma conversa não usa mensagens de outra como contexto.
- [ ] As mensagens continuam disponíveis depois de atualizar a página.
- [ ] As conversas continuam disponíveis depois de sair e entrar novamente na conta.
- [ ] Um usuário não consegue ver conversas de outro usuário.
- [ ] Um usuário não consegue abrir uma conversa de outro usuário usando seu identificador.
- [ ] A resposta do assistente continua aparecendo aos poucos por streaming.
- [ ] A primeira resposta gera automaticamente um título para a conversa.
- [ ] O título representa o assunto principal da conversa.
- [ ] O título é curto e fácil de ler na barra lateral.
- [ ] O título continua salvo depois de atualizar a página.
- [ ] As próximas mensagens não mudam o título automaticamente.
- [ ] Se a geração do título falhar, a conversa continua funcionando.
- [ ] Se a geração do título falhar, um título simples é criado com base na primeira mensagem.
- [ ] Uma falha no título não causa perda da resposta do assistente.
- [ ] A conversa usada mais recentemente aparece no topo da lista.
- [ ] A conversa aberta fica destacada na barra lateral.
- [ ] A mensagem é enviada somente para a conversa selecionada.
- [ ] A interface mostra quando as conversas estão sendo carregadas.
- [ ] A interface mostra quando o histórico está sendo carregado.
- [ ] A interface mostra uma mensagem clara quando ocorre um erro.
- [ ] A barra lateral continua utilizável em telas menores.
- [ ] Os testes automatizados são executados com sucesso.
- [ ] O cadastro, o login, o logout e o chat continuam funcionando como antes.

## Notes
- [ ] O banco de dados deve ser a principal fonte do histórico.
- [ ] Uma conversa sem título pode aparecer como "Nova conversa".
- [ ] O título automático deve ser criado apenas uma vez.
- [ ] O título alternativo pode usar uma parte da primeira mensagem.
- [ ] O título alternativo deve remover quebras de linha e ser limitado a um tamanho pequeno.
- [ ] Toda conversa deve ser verificada junto com o usuário autenticado.
- [ ] A aplicação deve impedir o acesso a conversas de outros usuários.
- [ ] Durante uma resposta em andamento, a troca de conversa deve ser bloqueada ou a resposta deve ser interrompida de forma segura.
- [ ] Excluir conversa não faz parte desta implementação.
- [ ] Renomear conversa manualmente não faz parte desta implementação.
- [ ] Buscar, compartilhar ou arquivar conversas não faz parte desta implementação.
- [ ] A prioridade é garantir conversas separadas, histórico salvo, segurança entre usuários e título automático.

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
