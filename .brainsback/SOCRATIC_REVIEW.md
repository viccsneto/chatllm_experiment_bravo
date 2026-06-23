# Socratic Review Record

## Question 1 — Cookie vs JWT storage

**Pergunta:** Por que você escolheu cookies HttpOnly para armazenar o token de sessão em vez de armazenar um JWT no localStorage? Que ameaça específica essa decisão mitiga?

**Resposta:** Escolhi cookies HttpOnly porque eles não podem ser lidos pelo JavaScript da página. Isso reduz o risco de roubo do token em caso de uma vulnerabilidade XSS, diferente de um JWT salvo no localStorage, que pode ser acessado por scripts maliciosos.

## Question 2 — CSRF protection

**Pergunta:** Como a proteção CSRF funciona nesta aplicação? O que impede um atacante de fazer um request malicioso contra a API usando o cookie de sessão da vítima?

**Resposta:** A proteção CSRF funciona em duas camadas. Primeiro, o cookie usa SameSite=Strict, então o navegador evita enviá-lo em requisições vindas de outro site. Além disso, a API exige o cabeçalho X-Requested-With: XMLHttpRequest nas ações que alteram dados. Como um site externo não consegue enviar esse cabeçalho sem passar pelas regras de CORS, a requisição maliciosa é bloqueada antes de usar a sessão da vítima.

## Question 3 — Password hashing

**Pergunta:** Como as senhas são armazenadas no banco de dados? O que acontece se dois usuários escolherem a mesma senha — os hashes serão iguais?

**Resposta:** As senhas são armazenadas usando bcrypt com um salt gerado automaticamente. Como o bcrypt.gensalt() gera um salt aleatório diferente para cada chamada, mesmo que dois usuários escolham a mesma senha, os hashes armazenados serão diferentes. Isso protege contra ataques de rainbow table.

## Question 4 — Session expiration

**Pergunta:** O que acontece quando uma sessão expira? Como o backend detecta isso e como o frontend reage?

**Resposta:** Cada sessão tem um campo expires_at. No get_current_user, o backend filtra as sessões cujo expires_at é maior que o momento atual. Se a sessão expirou, a consulta não retorna nenhum resultado e o backend devolve 401. No frontend, quando o usuário tenta acessar /api/auth/me e recebe 401, o App redireciona para a tela de login.

## Question 5 — Cookie attributes

**Pergunta:** O cookie de sessão usa o prefixo `__Host-`. O que esse prefixo garante? E qual o papel do atributo `SameSite=Strict`?

**Resposta:** O prefixo `__Host-` exige que o cookie seja enviado apenas por HTTPS, use `Path=/` e não tenha um domínio definido. Isso dificulta que outro subdomínio crie ou substitua o cookie de sessão. Já o `SameSite=Strict` impede que o navegador envie esse cookie em requisições iniciadas por outros sites, ajudando a proteger a aplicação contra ataques CSRF.

## Question 6 — Logout server-side

**Pergunta:** O que exatamente acontece no servidor quando o usuário clica em "Sair"? Por que não basta apenas apagar o cookie no frontend?

**Resposta:** A sessão é removida do banco de dados, então mesmo que o cookie ainda exista no navegador, ele não será mais aceito pelo backend. Apagar apenas o cookie no frontend deixaria a sessão ativa no servidor, permitindo que um atacante que tivesse capturado o token anteriormente ainda pudesse usá-lo.

## Question 7 — ChatSession vs auth Session

**Pergunta:** Por que existem duas entidades separadas — Session (autenticação) e ChatSession (conversa)? Elas não poderiam ser a mesma coisa?

**Resposta:** A Session de autenticação controla se o usuário está logado, enquanto a ChatSession representa uma conversa específica. Uma única sessão de login pode ter várias conversas, e uma conversa pode continuar existindo mesmo depois que o usuário faz login novamente. Misturar os dois conceitos dificultaria a separação de responsabilidades e tornaria o código mais confuso.

## Question 8 — Title generation failure

**Pergunta:** O que acontece com a resposta do chat se a geração do título automático falhar? E o que acontece com o título em si?

**Resposta:** A resposta do chat não é afetada pela falha do título. O título é gerado depois que a resposta já foi recebida e salva. Se a chamada ao OpenRouter para o título falhar, o serviço generate_title retorna um fallback baseado nos primeiros caracteres da primeira mensagem do usuário. A conversa continua funcionando normalmente.

## Question 9 — Session ownership

**Pergunta:** Como você garante que um usuário não consiga acessar as conversas de outro usuário? O que acontece se alguém tentar acessar /api/sessions/123/messages onde 123 é uma conversa de outro usuário?

**Resposta:** O backend verifica se a sessão pertence ao usuário autenticado antes de retornar qualquer dado. A consulta filtra tanto pelo id da conversa quanto pelo user_id do usuário atual. Se a conversa não pertencer ao usuário, a consulta não retorna nenhum resultado e o backend devolve 404, como se a conversa não existisse.

## Question 10 — Frontend session switching

**Pergunta:** O que acontece no frontend quando o usuário troca de conversa enquanto uma resposta ainda está sendo transmitida? Como você evita que a resposta apareça na conversa errada?

**Resposta:** Quando o usuário troca de conversa durante uma resposta, o frontend interrompe o AbortController atual, o que cancela a requisição de streaming. Depois disso, o histórico da nova conversa é carregado. Como a resposta foi interrompida, ela não aparece na conversa errada. Se a resposta já tiver sido concluída antes da troca, ela já foi salva na conversa correta pelo backend.

## Question 11 — Title one-shot

**Pergunta:** O título automático é gerado apenas uma vez. Por que essa decisão foi tomada? O que aconteceria se o título fosse atualizado a cada nova mensagem?

**Resposta:** O título é gerado apenas na primeira resposta para representar o assunto inicial da conversa. Se o título fosse atualizado a cada mensagem, ele poderia mudar completamente depois de algumas trocas, deixando o usuário confuso ao procurar uma conversa antiga. Além disso, cada chamada ao OpenRouter para gerar título tem custo e latência. Manter o título fixo após a primeira definição é mais estável e econômico.

## Question 12 — Session ordering

**Pergunta:** As sessões são ordenadas pela data da última atualização. Quando exatamente o updated_at é atualizado? E por que essa ordenação foi escolhida em vez de ordenar por created_at?

**Resposta:** O updated_at é atualizado sempre que uma nova mensagem é adicionada à conversa, tanto no endpoint de chat comum quanto no streaming. A ordenação por updated_at faz com que as conversas mais recentemente usadas apareçam no topo da lista, que é o comportamento esperado em aplicações como ChatGPT e Gemini. Ordenar por created_at manteria a conversa mais antiga sempre no topo, o que não reflete o uso real.

## Question 13 — Cross-task integration

**Pergunta:** Como a autenticação implementada na Task 1 se conecta com o sistema de sessões da Task 2? O que aconteceria se um endpoint de chat ou sessão não verificasse o usuário autenticado?

**Resposta:** A Task 1 forneceu o get_current_user, que é usado como dependência em todas as rotas da Task 2. Sem essa verificação, qualquer pessoa poderia listar, criar ou acessar conversas sem estar logada, e não haveria como associar uma conversa a um usuário específico. A integração entre as duas tarefas é feita através dessa dependência compartilhada.

---

## Veredito Final

O desenvolvedor demonstrou compreensão sólida de todas as implementações, incluindo as decisões de segurança, a separação de responsabilidades entre as camadas e o fluxo de integração entre as duas tarefas. A revisão socrática está concluída. ✅
