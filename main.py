"""
╔══════════════════════════════════════════╗
║       BOLÃO DA COPA - BACKEND API        ║
║  Feito com FastAPI + PostgreSQL (Supabase)║
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
 
VARIÁVEIS DE AMBIENTE NECESSÁRIAS (configurar no Render):
  DATABASE_URL → URL de conexão do PostgreSQL (ex: do Supabase)
  SECRET_KEY   → Chave secreta para JWT
"""
 
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import psycopg2
import psycopg2.extras
import hashlib
from jose import jwt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
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
    allow_origins=["https://bolao-copa-43bn.onrender.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
SECRET_KEY = os.getenv("SECRET_KEY", "bolao-copa-secret-2026")  # Troque em produção!
DATABASE_URL = os.getenv("DATABASE_URL")  # Configurar no painel do Render
security = HTTPBearer()
 
 
# ─────────────────────────────────────────
# BANCO DE DADOS (PostgreSQL)
# Conecta ao banco via URL de ambiente
# ─────────────────────────────────────────
 
def get_db():
    """Abre conexão com o banco PostgreSQL."""
    conn = psycopg2.connect(
    DATABASE_URL,
    sslmode="require"
)
    conn.cursor_factory = psycopg2.extras.RealDictCursor  # Retorna dicionários
    return conn
 
 
def criar_tabelas():
    """
    Cria as tabelas do banco se ainda não existirem.
    Chamado automaticamente ao iniciar o servidor.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        -- Tabela de usuários (participantes do bolão)
        CREATE TABLE IF NOT EXISTS usuarios (
            id          SERIAL PRIMARY KEY,
            nome        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            senha_hash  TEXT NOT NULL,
            is_admin    INTEGER DEFAULT 0,
            codigo_reset TEXT DEFAULT NULL,
            criado_em   TEXT DEFAULT (NOW()::text)
        );
 
        -- Tabela de jogos da copa
        CREATE TABLE IF NOT EXISTS jogos (
            id           SERIAL PRIMARY KEY,
            time_casa    TEXT NOT NULL,
            time_fora    TEXT NOT NULL,
            data_jogo    TEXT NOT NULL,
            fase         TEXT DEFAULT 'Grupos',
            gols_casa    INTEGER DEFAULT NULL,
            gols_fora    INTEGER DEFAULT NULL,
            encerrado    INTEGER DEFAULT 0
        );
 
        -- Tabela de palpites dos participantes
        CREATE TABLE IF NOT EXISTS palpites (
            id           SERIAL PRIMARY KEY,
            usuario_id   INTEGER NOT NULL,
            jogo_id      INTEGER NOT NULL,
            palpite_casa INTEGER NOT NULL,
            palpite_fora INTEGER NOT NULL,
            pontos       INTEGER DEFAULT 0,
            criado_em    TEXT DEFAULT (NOW()::text),
            UNIQUE(usuario_id, jogo_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (jogo_id) REFERENCES jogos(id)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
 
 
# Cria as tabelas ao iniciar
criar_tabelas()
 
 
# ─────────────────────────────────────────
# AUTENTICAÇÃO COM JWT
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
 
class EditarJogoInput(BaseModel):
    time_casa: str
    time_fora: str
    data_jogo: str
    fase: str
 
 
# ─────────────────────────────────────────
# SISTEMA DE PONTUAÇÃO
# ─────────────────────────────────────────
 
def calcular_pontos(
    palpite_casa: int, palpite_fora: int,
    real_casa: int, real_fora: int
) -> int:

    # 10 pontos → placar exato
    if palpite_casa == real_casa and palpite_fora == real_fora:
        return 10

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

    # 5 pontos → acertou vencedor E diferença de gols
    # MAS não pode ser empate
    diff_palpite = palpite_casa - palpite_fora
    diff_real = real_casa - real_fora

    if (
        vencedor_real != "empate"
        and vencedor_palpite == vencedor_real
        and diff_palpite == diff_real
    ):
        return 5

    # 3 pontos → acertou vencedor ou empate
    if vencedor_palpite == vencedor_real:
        return 3

    return 0
 
 
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
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (%s, %s, %s)",
            (dados.nome, dados.email, hash_senha(dados.senha))
        )
        conn.commit()
        cur.execute(
            "SELECT * FROM usuarios WHERE email = %s", (dados.email,)
        )
        usuario = cur.fetchone()
        token = criar_token(usuario["id"], usuario["email"])
        return {
            "token": token,
            "nome": usuario["nome"],
            "id": usuario["id"],
            "is_admin": bool(usuario["is_admin"])
        }
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")
    finally:
        cur.close()
        conn.close()
 
 
@app.post("/login")
def login(dados: LoginInput):
    """
    Autentica um participante.
    Recebe: email, senha
    Retorna: token JWT
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM usuarios WHERE email = %s AND senha_hash = %s",
        (dados.email, hash_senha(dados.senha))
    )
    usuario = cur.fetchone()
    cur.close()
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
 
 
@app.post("/tornar-admin")
def tornar_admin(email: str):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("""
        UPDATE usuarios
        SET is_admin = 1
        WHERE email = %s
    """, (email,))
 
    conn.commit()
    rowcount = cur.rowcount
    cur.close()
    conn.close()
 
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
 
    return {
        "ok": True,
        "mensagem": f"{email} agora é admin"
    }
 
 
@app.post("/recuperar-senha")
def recuperar_senha(email: str):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cur.fetchone()
 
    if not usuario:
        cur.close()
        conn.close()
        return {"ok": True}
 
    codigo = str(random.randint(100000, 999999))
 
    cur.execute("""
        UPDATE usuarios
        SET codigo_reset = %s
        WHERE id = %s
    """, (codigo, usuario["id"]))
 
    conn.commit()
    cur.close()
    conn.close()
 
    print("Código de recuperação:", codigo)
 
    return {"ok": True}
 
 
@app.post("/nova-senha")
def nova_senha(
    email: str,
    codigo: str,
    nova_senha: str
):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("""
        SELECT *
        FROM usuarios
        WHERE email = %s
        AND codigo_reset = %s
    """, (email, codigo))
    usuario = cur.fetchone()
 
    if not usuario:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Código inválido")
 
    cur.execute("""
        UPDATE usuarios
        SET senha_hash = %s,
            codigo_reset = NULL
        WHERE id = %s
    """, (hash_senha(nova_senha), usuario["id"]))
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"ok": True}
 
 
@app.delete("/usuario/{usuario_id}")
def deletar_usuario(
    usuario_id: int,
    usuario=Depends(verificar_token)
):
    conn = get_db()
    cur = conn.cursor()
 
    # Verifica admin
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario["sub"],))
    admin = cur.fetchone()
 
    if not admin["is_admin"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas admins podem deletar usuários.")
 
    # Impede deletar a si mesmo
    if int(usuario["sub"]) == usuario_id:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta.")
 
    # Remove palpites do usuário
    cur.execute("DELETE FROM palpites WHERE usuario_id = %s", (usuario_id,))
 
    # Remove usuário
    cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
    rowcount = cur.rowcount
 
    conn.commit()
    cur.close()
    conn.close()
 
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
 
    return {"mensagem": "🗑️ Usuário deletado com sucesso!"}
 
 
@app.get("/jogos")
def listar_jogos(usuario=Depends(verificar_token)):
    """
    Lista todos os jogos com os palpites do usuário logado.
    """
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM jogos ORDER BY data_jogo")
    jogos = cur.fetchall()
 
    resultado = []
    for jogo in jogos:
        cur.execute(
            "SELECT * FROM palpites WHERE usuario_id = %s AND jogo_id = %s",
            (usuario["sub"], jogo["id"])
        )
        palpite = cur.fetchone()
 
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
 
    cur.close()
    conn.close()
    return resultado
 
 
@app.post("/palpite")
def enviar_palpite(dados: PalpiteInput, usuario=Depends(verificar_token)):
    """
    Registra ou atualiza o palpite de um usuário em um jogo.
    Só permite palpite se o jogo ainda não foi encerrado.
    """
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM jogos WHERE id = %s", (dados.jogo_id,))
    jogo = cur.fetchone()
 
    if not jogo:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Jogo não encontrado.")
 
    # Bloqueio manual
    if jogo["encerrado"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Este jogo já foi encerrado.")
 
    # Bloqueio automático por horário
    data_jogo = datetime.strptime(
        jogo["data_jogo"], "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
 
    horario_limite = data_jogo - timedelta(minutes=5)
 
    if datetime.now(ZoneInfo("America/Sao_Paulo")) >= horario_limite:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Palpites encerrados 5 minutos antes do jogo!")
 
    # Salvar palpite (INSERT ou UPDATE se já existe)
    cur.execute("""
        INSERT INTO palpites (usuario_id, jogo_id, palpite_casa, palpite_fora)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (usuario_id, jogo_id)
        DO UPDATE SET
            palpite_casa = EXCLUDED.palpite_casa,
            palpite_fora = EXCLUDED.palpite_fora
    """, (usuario["sub"], dados.jogo_id, dados.palpite_casa, dados.palpite_fora))
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"mensagem": "✅ Palpite registrado com sucesso!"}
 
 
@app.post("/jogo")
def criar_jogo(
    dados: JogoInput,
    usuario=Depends(verificar_token)
):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario["sub"],))
    user = cur.fetchone()
 
    if not user["is_admin"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas admins podem criar jogos.")
 
    cur.execute("""
        INSERT INTO jogos (time_casa, time_fora, data_jogo, fase)
        VALUES (%s, %s, %s, %s)
    """, (dados.time_casa, dados.time_fora, dados.data_jogo, dados.fase))
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"mensagem": "✅ Jogo criado com sucesso!"}
 
 
@app.put("/jogo/{jogo_id}")
def editar_jogo(
    jogo_id: int,
    dados: EditarJogoInput,
    usuario=Depends(verificar_token)
):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario["sub"],))
    user = cur.fetchone()
 
    if not user["is_admin"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas admins podem editar jogos.")
 
    cur.execute("SELECT * FROM jogos WHERE id = %s", (jogo_id,))
    jogo = cur.fetchone()
 
    if not jogo:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Jogo não encontrado.")
 
    cur.execute("""
        UPDATE jogos
        SET time_casa = %s,
            time_fora = %s,
            data_jogo = %s,
            fase = %s
        WHERE id = %s
    """, (dados.time_casa, dados.time_fora, dados.data_jogo, dados.fase, jogo_id))
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"mensagem": "✅ Jogo atualizado!"}
 
 
@app.delete("/jogo/{jogo_id}")
def deletar_jogo(
    jogo_id: int,
    usuario=Depends(verificar_token)
):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario["sub"],))
    user = cur.fetchone()
 
    if not user["is_admin"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas admins podem deletar jogos.")
 
    cur.execute("DELETE FROM palpites WHERE jogo_id = %s", (jogo_id,))
    cur.execute("DELETE FROM jogos WHERE id = %s", (jogo_id,))
    rowcount = cur.rowcount
 
    conn.commit()
    cur.close()
    conn.close()
 
    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Jogo não encontrado.")
 
    return {"mensagem": "🗑️ Jogo deletado!"}
 
 
@app.post("/resultado")
def registrar_resultado(dados: ResultadoInput, usuario=Depends(verificar_token)):
    """
    (ADMIN) Registra o resultado real de um jogo e calcula pontos de todos.
    """
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario["sub"],))
    user = cur.fetchone()
 
    if not user["is_admin"]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas administradores podem registrar resultados.")
 
    cur.execute("SELECT * FROM jogos WHERE id = %s", (dados.jogo_id,))
    jogo = cur.fetchone()
 
    if not jogo:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Jogo não encontrado.")
 
    # Salva resultado e encerra o jogo
    cur.execute("""
        UPDATE jogos SET gols_casa = %s, gols_fora = %s, encerrado = 1
        WHERE id = %s
    """, (dados.gols_casa, dados.gols_fora, dados.jogo_id))
 
    # Busca todos os palpites deste jogo
    cur.execute("SELECT * FROM palpites WHERE jogo_id = %s", (dados.jogo_id,))
    palpites = cur.fetchall()
 
    # Calcula e atualiza os pontos de cada palpite
    for palpite in palpites:
        pontos = calcular_pontos(
            palpite["palpite_casa"], palpite["palpite_fora"],
            dados.gols_casa, dados.gols_fora
        )
        cur.execute(
            "UPDATE palpites SET pontos = %s WHERE id = %s",
            (pontos, palpite["id"])
        )
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"mensagem": f"✅ Resultado registrado! Pontos calculados para {len(palpites)} palpites."}
 
 
@app.get("/ranking")
def ranking(usuario=Depends(verificar_token)):
    """
    Retorna o ranking geral do bolão.
    Ordena por total de pontos (decrescente).
    """
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("""
        SELECT
            u.nome,
            u.id,
            COALESCE(SUM(p.pontos), 0) AS total_pontos,
            COUNT(p.id) AS total_palpites,
            COUNT(CASE WHEN p.pontos = 10 THEN 1 END) AS placares_exatos
        FROM usuarios u
        LEFT JOIN palpites p ON u.id = p.usuario_id
        GROUP BY u.id, u.nome
        ORDER BY total_pontos DESC, placares_exatos DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
 
    resultado = []
    for i, row in enumerate(rows, start=1):
        resultado.append({
            "id": row["id"],
            "posicao": i,
            "nome": row["nome"],
            "total_pontos": row["total_pontos"],
            "total_palpites": row["total_palpites"],
            "placares_exatos": row["placares_exatos"],
            "sou_eu": row["id"] == int(usuario["sub"])
        })
 
    return resultado
 
 
@app.get("/usuario/{usuario_id}/palpites")
def ver_palpites_usuario(
    usuario_id: int,
    usuario=Depends(verificar_token)
):
    conn = get_db()
    cur = conn.cursor()
 
    cur.execute("SELECT id, nome FROM usuarios WHERE id = %s", (usuario_id,))
    user = cur.fetchone()
 
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
 
    cur.execute("""
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
        WHERE p.usuario_id = %s
        ORDER BY j.data_jogo
    """, (usuario_id,))
    palpites = cur.fetchall()
    cur.close()
    conn.close()
 
    resultado = []
 
    for p in palpites:
        data_jogo = datetime.strptime(
            p["data_jogo"], "%Y-%m-%d %H:%M"
        ).replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
 
        horario_limite = data_jogo - timedelta(minutes=5)
 
        palpites_abertos = (
            datetime.now(ZoneInfo("America/Sao_Paulo")) < horario_limite
        )
 
        # Só mostra jogos já iniciados/encerrados
        if palpites_abertos:
            continue
 
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
 
    return {
        "usuario": user["nome"],
        "palpites": resultado
    }
 
 