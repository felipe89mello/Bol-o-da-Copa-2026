🏆 Bolão da Copa 2026

Sistema completo de bolão da Copa do Mundo feito com:

⚡ FastAPI
🐘 PostgreSQL (Supabase)
🌐 Frontend Web (HTML + CSS + JavaScript)
🔐 Autenticação JWT
☁️ Deploy no Render
📸 Preview

O sistema permite:

✅ Cadastro e login de usuários
✅ Palpites em jogos da Copa
✅ Ranking em tempo real
✅ Sistema automático de pontuação
✅ Painel administrativo
✅ Cadastro/edição/exclusão de jogos
✅ Encerramento automático de palpites
✅ Visualização de palpites dos participantes

🚀 Tecnologias Utilizadas
Backend
Python
FastAPI
Psycopg2
PostgreSQL
JWT Authentication
Frontend
HTML5
CSS3
JavaScript Vanilla
Infraestrutura
Render
Supabase PostgreSQL
⚙️ Funcionalidades
👤 Usuários
Cadastro
Login
Sessão persistente
Recuperação de senha
Ranking geral
Histórico de palpites
⚽ Jogos
Listagem de jogos
Organização por fase
Ordenação por data/hora
Bloqueio automático 5 minutos antes do jogo
Cadastro de jogos
Edição de jogos
Exclusão de jogos
🎯 Sistema de Pontuação
Acerto	Pontos
Placar exato	10 pts
Vencedor + saldo de gols	5 pts
Apenas vencedor/empate	3 pts
Errou tudo	0 pts
🔐 Autenticação

O sistema utiliza JWT Token Authentication.

Todas as rotas privadas exigem:

Authorization: Bearer TOKEN
📦 Instalação Local
1. Clone o projeto
git clone https://github.com/seuusuario/bolao-copa.git
cd bolao-copa
2. Crie ambiente virtual
Windows
python -m venv venv
venv\Scripts\activate
Linux/Mac
python3 -m venv venv
source venv/bin/activate
3. Instale dependências
pip install -r requirements.txt
🐘 Banco de Dados

Configure PostgreSQL no Supabase.

Crie as variáveis de ambiente:

DATABASE_URL=postgresql://...
SECRET_KEY=sua-chave-secreta
▶️ Rodando o Backend
uvicorn main:app --reload

Servidor:

http://localhost:8000
🌐 Deploy no Render
Backend
Crie um Web Service
Conecte o GitHub
Configure:
Build Command
pip install -r requirements.txt
Start Command
uvicorn main:app --host 0.0.0.0 --port $PORT
Variáveis de Ambiente
DATABASE_URL=postgresql://...
SECRET_KEY=sua-chave
📁 Estrutura do Projeto
bolao-copa/
│
├── main.py
├── requirements.txt
├── static/
│   ├── app.js
│   ├── style.css
│
├── templates/
│   └── index-ajustado.html
│
└── README.md
📡 Rotas da API
🔑 Auth
Método	Rota	Descrição
POST	/register	Cadastro
POST	/login	Login
POST	/recuperar-senha	Recuperar senha
POST	/nova-senha	Definir nova senha
⚽ Jogos
Método	Rota	Descrição
GET	/jogos	Lista jogos
POST	/palpite	Envia palpite
GET	/ranking	Ranking geral
DELETE	/jogo/{id}	Excluir jogo
👑 Admin
Método	Rota	Descrição
POST	/jogo	Criar jogo
PUT	/jogo/{id}	Editar jogo
DELETE	/jogo/{id}	Deletar jogo
POST	/resultado	Registrar resultado
🧠 Regras do Bolão
Palpites podem ser alterados até 5 minutos antes do jogo
Após isso o sistema bloqueia automaticamente
Ranking atualizado em tempo real
Critérios de desempate:
Pontos totais
Placares exatos
🔒 Segurança
Senhas criptografadas com SHA256
JWT Authentication
Rotas protegidas
Controle de administrador
CORS configurado
📈 Melhorias Futuras
📧 Envio real de e-mail para recuperação de senha
🔔 Notificações
📱 PWA / App Mobile
🏆 Estatísticas avançadas
🌙 Dark mode
📊 Dashboard admin
👨‍💻 Autor

Projeto desenvolvido por Felipe Santana Mello ⚽🔥

📜 Licença

Este projeto é open-source e pode ser utilizado livremente.