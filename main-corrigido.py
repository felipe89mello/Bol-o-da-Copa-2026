"""
╔══════════════════════════════════════════╗
║       BOLÃO DA COPA - BACKEND API        ║
║   Feito com FastAPI + SQLite em Python   ║
╚══════════════════════════════════════════╝

COMO FUNCIONA:
  Este arquivo é o "cérebro" do app.
  Ele recebe as requisições do frontend (celular dos participantes),
  salva os dados no banco e retorna as respostas em JSON.

ESTRUTURA:
  /register   → Cadastro de usuário
  /login      → Login
  /jogos      → Lista de jogos disponíveis para palpite
  /palpite    → Enviar palpite de um jogo
  /ranking    → Placar geral do bolão
  /resultado  → (admin) Registrar resultado real de um jogo
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import sqlite3
import hashlib
from jose import jwt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

# ─────────────────────────────────────────
# CONFIGURAÇÕES GERAIS
# ─────────────────────────────────────────

app = FastAPI(title="Bolão da Copa API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Permite que o frontend (celular) se comunique com o backend
# Em produção, troque "*" pelo seu domínio real
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "bolao-copa-secret-2026")  # Troque em produção!
DB_PATH = "bolao.db"
security = HTTPBearer()


# ─────────────────────────────────────────
# BANCO DE DADOS (SQLite)
# SQLite é um arquivo .db local — simples e sem configuração
# ─────────────────────────────────────────

def get_db():
    """Abre conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Retorna dicionários em vez de tuplas
    return conn


def criar_tabelas():
    """
    Cria as tabelas do banco se ainda não existirem.
    Chamado automaticamente ao iniciar o servidor.
    """
    conn = get_db()
    conn.executescript("""
        -- Tabela de usuários (participantes do bolão)
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            senha_hash  TEXT NOT NULL,
            is_admin    INTEGER DEFAULT 0,  -- 1 = administrador
            criado_em   TEXT DEFAULT (datetime('now'))
        );

        -- Tabela de jogos da copa
        CREATE TABLE IF NOT EXISTS jogos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            time_casa    TEXT NOT NULL,
            time_fora    TEXT NOT NULL,
            data_jogo    TEXT NOT NULL,        -- formato: "2026-06-15 18:00"
            fase         TEXT DEFAULT 'Grupos', -- Grupos, Oitavas, Quartas, Semi, Final
            gols_casa    INTEGER DEFAULT NULL,  -- NULL = ainda não aconteceu
            gols_fora    INTEGER DEFAULT NULL,
            encerrado    INTEGER DEFAULT 0      -- 0 = aberto para palpites, 1 = encerrado
        );

        -- Tabela de palpites dos participantes
        CREATE TABLE IF NOT EXISTS palpites (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id   INTEGER NOT NULL,
            jogo_id      INTEGER NOT NULL,
            palpite_casa INTEGER NOT NULL,
            palpite_fora INTEGER NOT NULL,
            pontos       INTEGER DEFAULT 0,    -- calculado após o resultado
            criado_em    TEXT DEFAULT (datetime('now')),
            UNIQUE(usuario_id, jogo_id),       -- apenas 1 palpite por jogo por usuário
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (jogo_id) REFERENCES jogos(id)
        );
    """)
    conn.commit()

    # Inserir jogos de exemplo se o banco estiver vazio
    count = conn.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
    if count == 0:
        jogos_exemplo = [
            ("Brasil", "Argentina", "2026-06-15 21:00", "Grupos"),
            ("França", "Alemanha", "2026-06-16 18:00", "Grupos"),
            ("Espanha", "Portugal", "2026-06-17 15:00", "Grupos"),
            ("Inglaterra", "Itália", "2026-06-18 21:00", "Grupos"),
            ("Japão", "Coreia do Sul", "2026-06-19 12:00", "Grupos"),
        ]
        conn.executemany(
            "INSERT INTO jogos (time_casa, time_fora, data_jogo, fase) VALUES (?, ?, ?, ?)",
            jogos_exemplo
        )
        conn.commit()

    conn.close()


# Cria as tabelas ao iniciar
criar_tabelas()


# ─────────────────────────────────────────
# AUTENTICAÇÃO COM JWT
# JWT = Token seguro que identifica o usuário logado
# O frontend guarda esse token e envia em cada requisição
# ─────────────────────────────────────────

def hash_senha(senha: str) -> str:
    """Converte a senha em um hash seguro (nunca salve senhas em texto puro!)."""
    return hashlib.sha256(senha.encode()).hexdigest()


def criar_token(usuario_id: int, email: str) -> str:
    """Gera um token JWT válido por 7 dias."""
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Middleware de autenticação.
    Verifica se o token enviado pelo frontend é válido.
    Usado em rotas que exigem login.
    """
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado. Faça login novamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")


# ─────────────────────────────────────────
# MODELOS (formato dos dados recebidos)
# Pydantic valida automaticamente os dados
# ─────────────────────────────────────────

class RegistroInput(BaseModel):
    nome: str
    email: str
    senha: str

class LoginInput(BaseModel):
    email: str
    senha: str

class PalpiteInput(BaseModel):
    jogo_id: int
    palpite_casa: int
    palpite_fora: int

class ResultadoInput(BaseModel):
    jogo_id: int
    gols_casa: int
    gols_fora: int

class JogoInput(BaseModel):
    time_casa: str
    time_fora: str
    data_jogo: str
    fase: str

# ─────────────────────────────────────────
# SISTEMA DE PONTUAÇÃO
# Regras clássicas de bolão
# ─────────────────────────────────────────

def calcular_pontos(
    palpite_casa: int, palpite_fora: int,
    real_casa: int, real_fora: int
) -> int:
    """
    Regras de pontuação:
      10 pts → Placar exato (ex: palpitou 2x1, resultado foi 2x1)
       5 pts → Acertou o vencedor E a diferença de gols
       3 pts → Acertou apenas o vencedor (ou empate)
       0 pts → Errou tudo
    """
    if palpite_casa == real_casa and palpite_fora == real_fora:
        return 10  # Placar exato!

    diff_palpite = palpite_casa - palpite_fora
    diff_real = real_casa - real_fora

    if diff_palpite == diff_real:
        return 5   # Acertou vencedor e diferença

    vencedor_palpite = (
        "casa" if palpite_casa > palpite_fora
        else "fora" if palpite_fora > palpite_casa
        else "empate"
    )
    vencedor_real = (
        "casa" if real_casa > real_fora
        else "fora" if real_fora > real_casa
        else "empate"
    )

    if vencedor_palpite == vencedor_real:
        return 3   # Acertou só o vencedor

    return 0       # Errou tudo


# ─────────────────────────────────────────
# ROTAS DA API
# ─────────────────────────────────────────



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse("templates/index-ajustado.html")


@app.post("/register")
def registrar(dados: RegistroInput):
    """
    Cadastra um novo participante.
    Recebe: nome, email, senha
    Retorna: token JWT para login automático
    """
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
            (dados.nome, dados.email, hash_senha(dados.senha))
        )
        conn.commit()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (dados.email,)
        ).fetchone()
        token = criar_token(usuario["id"], usuario["email"])
        return {
    "token": token,
    "nome": usuario["nome"],
    "id": usuario["id"],
    "is_admin": bool(usuario["is_admin"])
}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")
    finally:
        conn.close()


@app.post("/login")
def login(dados: LoginInput):
    """
    Autentica um participante.
    Recebe: email, senha
    Retorna: token JWT
    """
    conn = get_db()
    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE email = ? AND senha_hash = ?",
        (dados.email, hash_senha(dados.senha))
    ).fetchone()
    conn.close()

    if not usuario:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    token = criar_token(usuario["id"], usuario["email"])
    return {
    "token": token,
    "nome": usuario["nome"],
    "id": usuario["id"],
    "is_admin": bool(usuario["is_admin"])
}


@app.get("/jogos")
def listar_jogos(usuario=Depends(verificar_token)):
    """
    Lista todos os jogos com os palpites do usuário logado.
    Requer autenticação (token JWT no header).
    """
    conn = get_db()
    jogos = conn.execute("SELECT * FROM jogos ORDER BY data_jogo").fetchall()

    resultado = []
    for jogo in jogos:
        # Busca o palpite deste usuário neste jogo (se existir)
        palpite = conn.execute(
            "SELECT * FROM palpites WHERE usuario_id = ? AND jogo_id = ?",
            (usuario["sub"], jogo["id"])
        ).fetchone()

        resultado.append({
            "id": jogo["id"],
            "time_casa": jogo["time_casa"],
            "time_fora": jogo["time_fora"],
            "data_jogo": jogo["data_jogo"],
            "fase": jogo["fase"],
            "encerrado": bool(jogo["encerrado"]),
            "gols_casa": jogo["gols_casa"],
            "gols_fora": jogo["gols_fora"],
            "meu_palpite": {
                "casa": palpite["palpite_casa"],
                "fora": palpite["palpite_fora"],
                "pontos": palpite["pontos"],
            } if palpite else None
        })

    conn.close()
    return resultado


@app.post("/palpite")
def enviar_palpite(dados: PalpiteInput, usuario=Depends(verificar_token)):
    """
    Registra ou atualiza o palpite de um usuário em um jogo.
    Só permite palpite se o jogo ainda não foi encerrado.
    """
    conn = get_db()

    jogo = conn.execute(
        "SELECT * FROM jogos WHERE id = ?",
        (dados.jogo_id,)
    ).fetchone()

    if not jogo:
        raise HTTPException(
            status_code=404,
            detail="Jogo não encontrado."
        )

    # Bloqueio manual
    if jogo["encerrado"]:
        raise HTTPException(
            status_code=400,
            detail="Este jogo já foi encerrado."
        )

    # Bloqueio automático por horário
    data_jogo = datetime.strptime(
        jogo["data_jogo"],
        "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/Sao_Paulo"))

    horario_limite = data_jogo - timedelta(minutes=5)

    if datetime.now(ZoneInfo("America/Sao_Paulo")) >= horario_limite:
        raise HTTPException(
            status_code=400,
            detail="Palpites encerrados 5 minutos antes do jogo!"
        )

    # Salvar palpite
    conn.execute("""
        INSERT INTO palpites (
            usuario_id,
            jogo_id,
            palpite_casa,
            palpite_fora
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(usuario_id, jogo_id)
        DO UPDATE SET
            palpite_casa = excluded.palpite_casa,
            palpite_fora = excluded.palpite_fora
    """, (
        usuario["sub"],
        dados.jogo_id,
        dados.palpite_casa,
        dados.palpite_fora
    ))

    conn.commit()
    conn.close()

    return {
        "mensagem": "✅ Palpite registrado com sucesso!"
    }

@app.post("/jogo")
def criar_jogo(
    dados: JogoInput,
    usuario=Depends(verificar_token)
):
    conn = get_db()

    # Verifica admin
    user = conn.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (usuario["sub"],)
    ).fetchone()

    if not user["is_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Apenas admins podem criar jogos."
        )

    conn.execute("""
        INSERT INTO jogos (
            time_casa,
            time_fora,
            data_jogo,
            fase
        )
        VALUES (?, ?, ?, ?)
    """, (
        dados.time_casa,
        dados.time_fora,
        dados.data_jogo,
        dados.fase
    ))

    conn.commit()
    conn.close()

    return {
        "mensagem": "✅ Jogo criado com sucesso!"
    }

@app.post("/resultado")
def registrar_resultado(dados: ResultadoInput, usuario=Depends(verificar_token)):
    """
    (ADMIN) Registra o resultado real de um jogo e calcula pontos de todos.
    Apenas administradores podem usar esta rota.
    """
    conn = get_db()

    # Verifica se é admin
    user = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario["sub"],)).fetchone()
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Apenas administradores podem registrar resultados.")

    jogo = conn.execute("SELECT * FROM jogos WHERE id = ?", (dados.jogo_id,)).fetchone()
    if not jogo:
        raise HTTPException(status_code=404, detail="Jogo não encontrado.")

    # Salva o resultado e encerra o jogo
    conn.execute("""
        UPDATE jogos SET gols_casa = ?, gols_fora = ?, encerrado = 1
        WHERE id = ?
    """, (dados.gols_casa, dados.gols_fora, dados.jogo_id))

    # Calcula os pontos de cada palpite deste jogo
    palpites = conn.execute(
        "SELECT * FROM palpites WHERE jogo_id = ?", (dados.jogo_id,)
    ).fetchall()

    for palpite in palpites:
        pontos = calcular_pontos(
            palpite["palpite_casa"], palpite["palpite_fora"],
            dados.gols_casa, dados.gols_fora
        )
        conn.execute(
            "UPDATE palpites SET pontos = ? WHERE id = ?",
            (pontos, palpite["id"])
        )

    conn.commit()
    conn.close()
    return {"mensagem": f"✅ Resultado registrado! Pontos calculados para {len(palpites)} palpites."}


@app.get("/ranking")
def ranking(usuario=Depends(verificar_token)):
    """
    Retorna o ranking geral do bolão.
    Ordena por total de pontos (decrescente).
    """
    conn = get_db()
    ranking = conn.execute("""
        SELECT
            u.nome,
            u.id,
            COALESCE(SUM(p.pontos), 0) AS total_pontos,
            COUNT(p.id) AS total_palpites,
            COUNT(CASE WHEN p.pontos = 10 THEN 1 END) AS placares_exatos
        FROM usuarios u
        LEFT JOIN palpites p ON u.id = p.usuario_id
        GROUP BY u.id
        ORDER BY total_pontos DESC, placares_exatos DESC
    """).fetchall()

    resultado = []

    for i, row in enumerate(ranking, start=1):
        resultado.append({
            "id": row["id"],  # ← IMPORTANTE
            "posicao": i,
            "nome": row["nome"],
            "total_pontos": row["total_pontos"],
            "total_palpites": row["total_palpites"],
            "placares_exatos": row["placares_exatos"],
            "sou_eu": row["id"] == int(usuario["sub"])
        })

    conn.close()
    return resultado


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main-corrigido:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )

@app.get("/usuario/{usuario_id}/palpites")
def ver_palpites_usuario(
    usuario_id: int,
    usuario=Depends(verificar_token)
):
    conn = get_db()

    user = conn.execute("""
        SELECT id, nome
        FROM usuarios
        WHERE id = ?
    """, (usuario_id,)).fetchone()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuário não encontrado."
        )

    palpites = conn.execute("""
        SELECT
            j.time_casa,
            j.time_fora,
            j.gols_casa,
            j.gols_fora,
            j.encerrado,
            p.palpite_casa,
            p.palpite_fora,
            p.pontos,
            j.fase,
            j.data_jogo
        FROM palpites p
        JOIN jogos j ON j.id = p.jogo_id
        WHERE p.usuario_id = ?
        ORDER BY j.data_jogo
    """, (usuario_id,)).fetchall()

    resultado = []

    for p in palpites:
        resultado.append({
            "time_casa": p["time_casa"],
            "time_fora": p["time_fora"],
            "gols_casa": p["gols_casa"],
            "gols_fora": p["gols_fora"],
            "palpite_casa": p["palpite_casa"],
            "palpite_fora": p["palpite_fora"],
            "pontos": p["pontos"],
            "fase": p["fase"],
            "encerrado": bool(p["encerrado"]),
            "data_jogo": p["data_jogo"]
        })

    conn.close()

    return {
        "usuario": user["nome"],
        "palpites": resultado
    }