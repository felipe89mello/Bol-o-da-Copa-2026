# 🏆 Bolão da Copa 2026

Sistema completo de bolão da Copa do Mundo desenvolvido com:

- ⚡ FastAPI
- 🐘 PostgreSQL (Supabase)
- 🌐 HTML + CSS + JavaScript
- 🔐 Autenticação JWT
- ☁️ Deploy no Render

---

# 📸 Funcionalidades

O sistema permite:

- ✅ Cadastro e login de usuários
- ✅ Palpites em jogos da Copa
- ✅ Ranking em tempo real
- ✅ Sistema automático de pontuação
- ✅ Painel administrativo
- ✅ Cadastro, edição e exclusão de jogos
- ✅ Encerramento automático de palpites
- ✅ Visualização de palpites dos participantes

---

# 🚀 Tecnologias Utilizadas

## Backend
- Python
- FastAPI
- Psycopg2
- PostgreSQL
- JWT Authentication

## Frontend
- HTML5
- CSS3
- JavaScript Vanilla

## Infraestrutura
- Render
- Supabase PostgreSQL

---

# ⚙️ Funcionalidades

## 👤 Usuários
- Cadastro
- Login
- Sessão persistente
- Recuperação de senha
- Ranking geral
- Histórico de palpites

## ⚽ Jogos
- Listagem de jogos
- Organização por fase
- Ordenação por data/hora
- Bloqueio automático 5 minutos antes do jogo
- Cadastro de jogos
- Edição de jogos
- Exclusão de jogos

## 🎯 Sistema de Pontuação

| Acerto | Pontos |
|---|---|
| Placar exato | 10 pts |
| Vencedor + saldo de gols | 5 pts |
| Apenas vencedor/empate | 3 pts |
| Errou tudo | 0 pts |

---

# 🔐 Autenticação

O sistema utiliza JWT Token Authentication.

Todas as rotas privadas exigem:

```http
Authorization: Bearer TOKEN
