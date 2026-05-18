
/* ══════════════════════════════════════════
   CONFIGURAÇÃO
   ⚠️ Troque a URL abaixo pela URL do seu backend hospedado
   Durante desenvolvimento local: http://localhost:8000
   Em produção: https://seu-app.railway.app
══════════════════════════════════════════ */
const API = "http://127.0.0.1:8000"; // ajuste automático para produção

/* ══════════════════════════════════════════
   ESTADO DA APLICAÇÃO
   Guarda dados do usuário logado em memória
══════════════════════════════════════════ */
let token = localStorage.getItem("bolao_token");
let usuario = JSON.parse(localStorage.getItem("bolao_usuario") || "null");

/* ══════════════════════════════════════════
   INICIALIZAÇÃO
   Verifica se já tem sessão salva ao abrir o app
══════════════════════════════════════════ */
window.onload = () => {
  if (token && usuario) mostrarApp();
};

/* ══════════════════════════════════════════
   AUTENTICAÇÃO
══════════════════════════════════════════ */

function alternarAuth(modo, btn) {
  document.getElementById("form-login").style.display = modo === "login" ? "block" : "none";
  document.getElementById("form-cadastro").style.display = modo === "cadastro" ? "block" : "none";
  document.querySelectorAll(".tabs-auth button").forEach(b => b.classList.remove("ativa"));
  btn.classList.add("ativa");
}

async function fazerLogin() {
  const email = document.getElementById("login-email").value.trim();
  const senha = document.getElementById("login-senha").value;
  const erroEl = document.getElementById("erro-login");
  erroEl.textContent = "";

  console.log("1. Tentando login com:", email);

  if (!email || !senha) { erroEl.textContent = "Preencha todos os campos."; return; }

  try {
    console.log("2. Enviando requisição...");
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha })
    });
    console.log("3. Resposta recebida, status:", res.status);
    const data = await res.json();
    console.log("4. Dados:", data);
    if (!res.ok) throw new Error(data.detail);

    console.log("5. Salvando sessão...");
    salvarSessao(data);
    console.log("6. Chamando mostrarApp...");
    mostrarApp();
    console.log("7. mostrarApp executado!");
  } catch (e) {
    console.error("ERRO:", e);
    erroEl.textContent = e.message;
  }
}

async function fazerCadastro() {
  const nome = document.getElementById("cad-nome").value.trim();
  const email = document.getElementById("cad-email").value.trim();
  const senha = document.getElementById("cad-senha").value;
  const erroEl = document.getElementById("erro-cadastro");
  erroEl.textContent = "";

  if (!nome || !email || !senha) { erroEl.textContent = "Preencha todos os campos."; return; }
  if (senha.length < 6) { erroEl.textContent = "A senha deve ter pelo menos 6 caracteres."; return; }

  try {
    const res = await fetch(`${API}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, email, senha })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    salvarSessao(data);
    mostrarApp();
  } catch (e) {
    erroEl.textContent = e.message;
  }
}

function salvarSessao(data) {
  token = data.token;
  usuario = {
  nome: data.nome,
  id: data.id,
  is_admin: data.is_admin
};
  localStorage.setItem("bolao_token", token);
  localStorage.setItem("bolao_usuario", JSON.stringify(usuario));
}

function logout() {
  localStorage.removeItem("bolao_token");
  localStorage.removeItem("bolao_usuario");
  token = null; usuario = null;
  document.getElementById("tela-auth").style.display = "block";
  document.getElementById("conteudo").style.display = "none";
  document.getElementById("nav").style.display = "none";
  document.getElementById("btn-logout").style.display = "none";
}

/* ══════════════════════════════════════════
   MOSTRAR APP APÓS LOGIN
══════════════════════════════════════════ */
function mostrarApp() {
  document.getElementById("tela-auth").style.display = "none";
  document.getElementById("conteudo").style.display = "block";
  document.getElementById("conteudo").classList.remove("oculto");
  document.getElementById("nav").classList.add("visivel");
  document.getElementById("btn-logout").style.display = "block";
  if (usuario.is_admin) {
  document.getElementById("btn-nav-admin").style.display = "block";
} else {
  document.getElementById("btn-nav-admin").style.display = "none";
}
  document.getElementById("nome-usuario").textContent = `Olá, ${usuario.nome}! 👋`;
  carregarJogos();
}

/* ══════════════════════════════════════════
   NAVEGAÇÃO POR ABAS
══════════════════════════════════════════ */
function mostrarAba(aba, btn) {
  ["jogos", "ranking", "admin"].forEach(a => {
    document.getElementById(`aba-${a}`).style.display = a === aba ? "block" : "none";
  });
  document.querySelectorAll("nav button").forEach(b => b.classList.remove("ativa"));
  btn.classList.add("ativa");

  if (aba === "ranking") carregarRanking();
  if (aba === "admin") carregarJogosAdmin();
}

let subAbaAtual = "futuros";

function trocarSubAba(tipo, btn) {

  subAbaAtual = tipo;

  document
    .querySelectorAll(".subtab")
    .forEach(b => b.classList.remove("ativa"));

  btn.classList.add("ativa");

  carregarJogos();
}

/* ══════════════════════════════════════════
   CARREGAR E RENDERIZAR JOGOS
══════════════════════════════════════════ */
async function carregarJogos() {
  const container = document.getElementById("lista-jogos");
  container.innerHTML = '<div class="loading"><div class="spinner"></div>Carregando jogos...</div>';

  try {
    const res = await fetch(`${API}/jogos`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (res.status === 401) { logout(); return; }
    const jogos = await res.json();
    renderizarJogos(jogos);
  } catch {
    container.innerHTML = '<p class="erro">Erro ao carregar jogos. Verifique sua conexão.</p>';
  }
}

// Emojis de bandeira por país (simplificado)
const bandeiras = {
  "Brasil": "🇧🇷", "Argentina": "🇦🇷", "França": "🇫🇷", "Alemanha": "🇩🇪",
  "Espanha": "🇪🇸", "Portugal": "🇵🇹", "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Itália": "🇮🇹",
  "Japão": "🇯🇵", "Coreia do Sul": "🇰🇷", "México": "🇲🇽", "EUA": "🇺🇸",
  "Canadá": "🇨🇦", "Uruguai": "🇺🇾", "Colômbia": "🇨🇴", "Holanda": "🇳🇱",
  "Bélgica": "🇧🇪", "Croácia": "🇭🇷", "Senegal": "🇸🇳", "Marrocos": "🇲🇦",
};

function bandeira(pais) {
  return bandeiras[pais] || "🏳️";
}

function renderizarJogos(jogos) {

  const container = document.getElementById("lista-jogos");

  if (!jogos.length) {
    container.innerHTML = `
      <p style="color:var(--text2);text-align:center;padding:40px">
        Nenhum jogo cadastrado.
      </p>
    `;
    return;
  }

  let jogosFiltrados = [];

  if (subAbaAtual === "futuros") {
    jogosFiltrados = jogos.filter(j => !j.encerrado);
  } else {
    jogosFiltrados = jogos.filter(j => j.encerrado);
  }

  if (!jogosFiltrados.length) {
    container.innerHTML = `
      <p style="color:var(--text2);text-align:center;padding:40px">
        Nenhum jogo nesta categoria.
      </p>
    `;
    return;
  }

  // AGRUPAR POR FASE
  const fases = {};

  jogosFiltrados.forEach(j => {
    if (!fases[j.fase]) {
      fases[j.fase] = [];
    }

    fases[j.fase].push(j);
  });

  container.innerHTML = Object.entries(fases)
    .map(([fase, lista]) => `
      <p class="secao-titulo" style="margin-top:16px">
        ${fase}
      </p>

      ${lista.map(jogo => renderizarJogo(jogo)).join("")}
    `)
    .join("");
}

function renderizarJogo(jogo) {
  const temPalpite = jogo.meu_palpite !== null;
  const encerrado = jogo.encerrado;
  const agora = new Date();
  const horarioJogo = new Date(jogo.data_jogo.replace(" ", "T")
);

// bloqueia 5 minutos antes
const horarioLimite = new Date(
  horarioJogo.getTime() - (5 * 60 * 1000)
);
  const diferenca = horarioLimite - agora;

  const horas = Math.floor(diferenca / (1000 * 60 * 60));
  const minutos = Math.floor((diferenca % (1000 * 60 * 60)) / (1000 * 60));
  const bloqueado = diferenca <= 0;

  const countdown =
    !bloqueado
      ? `⏳ Fecha em ${horas}h ${minutos}min`
      : "⛔ Palpites encerrados";

  

  const placarCentro = encerrado
    ? `<div class="placar-real"><div class="nums">${jogo.gols_casa} × ${jogo.gols_fora}</div><div style="font-size:10px;color:var(--text2);margin-top:2px">Resultado</div></div>`
    : `<div class="placar-real"><div class="vs">VS</div></div>`;

  const inputsOuPlacar =
  encerrado
    ? (
        temPalpite
          ? `
            <div style="text-align:center">
              <div style="font-size:13px;color:var(--text2)">
                Seu palpite:
                <strong>
                  ${jogo.meu_palpite.casa} × ${jogo.meu_palpite.fora}
                </strong>
              </div>

              <span class="pontos-badge">
                +${jogo.meu_palpite.pontos} pts
              </span>
            </div>
          `
          : `
            <p style="font-size:13px;color:var(--text2);text-align:center">
              Você não fez palpite neste jogo.
            </p>
          `
      )

    : bloqueado
      ? ``

      : `
          <div class="palpite-label" style="text-align:center">
            Seu palpite
          </div>

          <div class="palpite-inputs">
            <input
              class="input-placar"
              type="number"
              min="0"
              max="20"
              value="${temPalpite ? jogo.meu_palpite.casa : 0}"
              id="casa-${jogo.id}"
            />

            <span class="x-palpite">×</span>

            <input
              class="input-placar"
              type="number"
              min="0"
              max="20"
              value="${temPalpite ? jogo.meu_palpite.fora : 0}"
              id="fora-${jogo.id}"
            />
          </div>

          <button
            class="btn-palpitar ${temPalpite ? 'salvo' : ''}"
            id="btn-${jogo.id}"
            onclick="enviarPalpite(${jogo.id})"
            style="margin-top:12px"
          >
            ${temPalpite
              ? '✅ Palpite salvo — alterar'
              : '🎯 Salvar palpite'}
          </button>
        `;

  return `
  <div class="jogo-card ${temPalpite ? 'com-palpite' : ''} ${encerrado ? 'encerrado' : ''}" id="card-${jogo.id}">
    
    <div class="jogo-fase">
      ${jogo.fase} ${encerrado ? '• Encerrado' : ''}
    </div>

    <div class="jogo-data">
      📅 ${jogo.data_jogo}
    </div>

    <div class="countdown">
      ${countdown}
    </div>

    <div class="jogo-times">
      <div class="time">
        <span class="time-emoji">${bandeira(jogo.time_casa)}</span>
        <div class="time-nome">${jogo.time_casa}</div>
      </div>

      ${placarCentro}

      <div class="time">
        <span class="time-emoji">${bandeira(jogo.time_fora)}</span>
        <div class="time-nome">${jogo.time_fora}</div>
      </div>
    </div>

    ${inputsOuPlacar}

  </div>
`;
}
/* ══════════════════════════════════════════
   ENVIAR PALPITE
══════════════════════════════════════════ */
async function enviarPalpite(jogoId) {
  const casa = parseInt(document.getElementById(`casa-${jogoId}`).value);
  const fora = parseInt(document.getElementById(`fora-${jogoId}`).value);
  const btn = document.getElementById(`btn-${jogoId}`);

  if (isNaN(casa) || isNaN(fora) || casa < 0 || fora < 0) {
    mostrarToast("Placar inválido!", true); return;
  }

  btn.disabled = true;
  btn.textContent = "Salvando...";

  try {
    const res = await fetch(`${API}/palpite`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ jogo_id: jogoId, palpite_casa: casa, palpite_fora: fora })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    btn.textContent = "✅ Palpite salvo — alterar";
    btn.classList.add("salvo");
    document.getElementById(`card-${jogoId}`).classList.add("com-palpite");
    mostrarToast("Palpite salvo! ✅");
  } catch (e) {
    mostrarToast(e.message, true);
    btn.textContent = "🎯 Salvar palpite";
  } finally {
    btn.disabled = false;
  }
}

/* ══════════════════════════════════════════
   RANKING
══════════════════════════════════════════ */
async function carregarRanking() {
  const container = document.getElementById("lista-ranking");
  container.innerHTML = '<div class="loading"><div class="spinner"></div>Carregando...</div>';

  try {
    const res = await fetch(`${API}/ranking`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const ranking = await res.json();

    container.innerHTML = ranking.map(p => `
      <div class="ranking-card ${p.sou_eu ? 'sou-eu' : ''}"
  onclick="abrirPalpitesUsuario(${p.id})"
>
        <div class="posicao ${p.posicao <= 3 ? 'top' + p.posicao : ''}">
          ${p.posicao === 1 ? '🥇' : p.posicao === 2 ? '🥈' : p.posicao === 3 ? '🥉' : p.posicao + 'º'}
        </div>
        <div class="ranking-info">
          <div class="ranking-nome">${p.nome} ${p.sou_eu ? '(você)' : ''}</div>
          <div class="ranking-stats">${p.total_palpites} palpites • ${p.placares_exatos} exatos 🎯</div>
        </div>
        <div class="ranking-pontos">${p.total_pontos}</div>
      </div>
    `).join("");
  } catch {
    container.innerHTML = '<p class="erro">Erro ao carregar ranking.</p>';
  }
}

/* ══════════════════════════════════════════
   ADMIN: REGISTRAR RESULTADO
══════════════════════════════════════════ */
async function carregarJogosAdmin() {
  try {
    const res = await fetch(`${API}/jogos`, { headers: { "Authorization": `Bearer ${token}` } });
    const jogos = await res.json();
    const select = document.getElementById("admin-jogo");
    select.innerHTML = jogos
      .filter(j => !j.encerrado)
      .map(j => `<option value="${j.id}" data-casa="${j.time_casa}" data-fora="${j.time_fora}">
        ${j.time_casa} × ${j.time_fora} (${j.fase})
      </option>`).join("");

    // Atualiza labels com os times ao trocar
    select.onchange = () => {
      const opt = select.options[select.selectedIndex];
      document.getElementById("label-casa").textContent = `Gols ${opt.dataset.casa}`;
      document.getElementById("label-fora").textContent = `Gols ${opt.dataset.fora}`;
    };
    select.dispatchEvent(new Event("change"));

    document.getElementById("btn-nav-admin").style.display = "block";
  } catch {}
}

async function registrarResultado() {
  const jogoId = document.getElementById("admin-jogo").value;
  const casa = parseInt(document.getElementById("admin-gols-casa").value);
  const fora = parseInt(document.getElementById("admin-gols-fora").value);

  try {
    const res = await fetch(`${API}/resultado`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ jogo_id: parseInt(jogoId), gols_casa: casa, gols_fora: fora })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    mostrarToast("Resultado registrado! ✅");
    carregarJogosAdmin();
    carregarJogos();
  } catch (e) {
    mostrarToast(e.message, true);
  }
}

/* ══════════════════════════════════════════
   TOAST (NOTIFICAÇÃO FLUTUANTE)
══════════════════════════════════════════ */
function mostrarToast(msg, erro = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = erro ? "erro visivel" : "visivel";
  setTimeout(() => t.classList.remove("visivel"), 2800);
}

async function criarJogo() {

  const time_casa =
    document.getElementById("novo-time-casa").value;

  const time_fora =
    document.getElementById("novo-time-fora").value;

  const dataInput =
    document.getElementById("novo-data-jogo").value;

  const fase =
    document.getElementById("nova-fase").value;

  if (!time_casa || !time_fora || !dataInput) {
    mostrarToast("Preencha todos os campos", true);
    return;
  }

  // converte para formato do backend
  const data_jogo =
    dataInput.replace("T", " ");

  try {

    const resposta = await fetch(`${API}/jogo`, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },

      body: JSON.stringify({
        time_casa,
        time_fora,
        data_jogo,
        fase
      })
    });

    const dados = await resposta.json();

    if (!resposta.ok) {
      throw new Error(dados.detail);
    }

    mostrarToast("✅ Jogo criado!");

    carregarJogos();

    // limpa formulário
    document.getElementById("novo-time-casa").value = "";
    document.getElementById("novo-time-fora").value = "";
    document.getElementById("novo-data-jogo").value = "";

  } catch (erro) {

    mostrarToast(erro.message, true);

  }
}

async function abrirPalpitesUsuario(usuarioId) {

  try {

    const res = await fetch(
      `${API}/usuario/${usuarioId}/palpites`,
      {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      }
    );

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail);
    }

    const html = data.palpites.map(p => {

      if (p.bloqueado) {

        return `
          <div class="palpite-card bloqueado">

            <div>
              ${p.time_casa} × ${p.time_fora}
            </div>

            <div style="margin-top:8px;color:#999">
              🔒 Palpite oculto até o encerramento
            </div>

          </div>
    `;
  }

 return `
  <div class="palpite-card">

    <div class="palpite-topo">
      <span class="fase-badge">
        ${p.fase}
      </span>

      ${
        p.encerrado
          ? `<span class="status encerrado">Encerrado</span>`
          : `<span class="status aberto">Aberto</span>`
      }
    </div>

    <div class="jogo-nome">
      ${p.time_casa} × ${p.time_fora}
    </div>

    <div class="linha-info">
      🎯 Seu palpite:
      <strong>
        ${p.palpite_casa} × ${p.palpite_fora}
      </strong>
    </div>

    ${
      p.encerrado
        ? `
          <div class="linha-info">
            ⚽ Resultado:
            <strong>
              ${p.gols_casa} × ${p.gols_fora}
            </strong>
          </div>

          <div class="pontos-pill">
            +${p.pontos} pts
          </div>
        `
        : ""
    }

  </div>
`;

}).join("");

    document.getElementById("modal-conteudo").innerHTML = `
      <h2 style="margin-bottom:20px">
        Palpites de ${data.usuario}
      </h2>

      ${html}
    `;

    document.getElementById("modal").style.display = "flex";

  } catch (e) {

    mostrarToast(e.message, true);

  }
}