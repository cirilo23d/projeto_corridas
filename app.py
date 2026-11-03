import math
import random

import pygame
import customtkinter as ctk


# ==========================================
# CONFIGURAÇÕES DO JOGO
# ==========================================

LARGURA = 1000
ALTURA = 700

COR_FUNDO = (16, 24, 32)
COR_PISTA = (65, 68, 73)
COR_GRAMA = (35, 105, 57)
COR_LINHA = (255, 255, 255)
COR_JOGADOR = (230, 57, 70)

CORRIDAS = [
    {"nome": "CORRIDA URBANA", "dificuldade": "Muito Fácil",
     "voltas": 3, "cor": (35, 100, 220)},
    {"nome": "DESERTO EXTREMO", "dificuldade": "Fácil",
     "voltas": 6, "cor": (210, 130, 40)},
    {"nome": "MONTANHAS", "dificuldade": "Médio",
     "voltas": 10, "cor": (40, 150, 100)},
    {"nome": "PISTA NOTURNA", "dificuldade": "Difícil",
     "voltas": 15, "cor": (120, 70, 200)},
    {"nome": "GRANDE PRÊMIO", "dificuldade": "Extremo",
     "voltas": 25, "cor": (190, 40, 40)}
]

# Geometria da pista (elipse)
CX = LARGURA // 2
CY = ALTURA // 2
RAIO_X = 340
RAIO_Y = 235
LARGURA_PISTA = 125

# Física dos carros
ACELERACAO = 0.16
VEL_MAX = 6
VEL_RE = -2.5
FREIO_MOTOR = 0.985          # perda de velocidade ao soltar o acelerador
ADERENCIA = 0.80             # fração da velocidade lateral que sobra por frame
PERDA_FORA_DA_PISTA = 0.94   # arrasto na grama

# Colisões (caixa retangular orientada de cada carro)
MEIO_COMP = 17
MEIA_LARG = 10
MASSA = 1.0
INERCIA = MASSA * ((2 * MEIO_COMP) ** 2 + (2 * MEIA_LARG) ** 2) / 12
RESTITUICAO = 0.35           # 0 = batida "mole", 1 = elástica
GIRO_MAX = 0.08              # rotação máxima causada por uma batida (rad/frame)

# Inteligência artificial
# dificuldade: (fração da velocidade do jogador, agressividade de 0 a 1)
NIVEIS_IA = {
    "Muito Fácil": (0.70, 0.10),
    "Fácil": (0.78, 0.25),
    "Médio": (0.86, 0.45),
    "Difícil": (0.92, 0.70),
    "Extremo": (1.00, 1.00),
}
LANE_MIN = 0.86              # faixas de trajetória permitidas à IA
LANE_MAX = 1.14              # (1.0 = linha central da pista)
ALCANCE_DEFESA = 130         # distância atrás na qual a IA passa a defender
ALCANCE_ULTRAPASSAGEM = 90   # distância à frente na qual a IA tenta ultrapassar

SLOT_JOGADOR = 5             # 0 = pole position; 5 = último da fila


# ==========================================
# CARRO (FÍSICA)
# ==========================================

class Carro:

    def __init__(self, x, y, angulo, cor, vel_max=VEL_MAX):
        self.x = x
        self.y = y
        self.angulo = angulo
        self.vx = 0.0
        self.vy = 0.0
        self.giro = 0.0          # rotação causada por batidas
        self.cor = cor
        self.vel_max = vel_max

        self.theta_anterior = self.theta()
        self.rho_ant = self.rho()

        # Progresso em radianos a partir da linha de largada
        # (negativo para quem larga atrás dela)
        self.progresso = (
            self.theta_anterior + math.pi / 2 + math.pi
        ) % (2 * math.pi) - math.pi

    # --- geometria -----------------------------------------------------

    def frente(self):
        return math.cos(self.angulo), math.sin(self.angulo)

    def theta(self):
        return math.atan2((self.y - CY) / RAIO_Y, (self.x - CX) / RAIO_X)

    def rho(self):
        """Distância normalizada ao centro da pista (1.0 = linha central)."""
        dx = (self.x - CX) / RAIO_X
        dy = (self.y - CY) / RAIO_Y
        return math.sqrt(dx * dx + dy * dy)

    def velocidade_total(self):
        return math.hypot(self.vx, self.vy)

    def velocidade_frente(self):
        fx, fy = self.frente()
        return self.vx * fx + self.vy * fy

    # --- movimento -----------------------------------------------------

    def atualizar(self, acelerar, direcao, dt):
        """
        acelerar: 1 acelera, -1 freia/ré, 0 solta o pedal
        direcao: -1 esquerda ... +1 direita
        """
        fx, fy = self.frente()
        rx, ry = -fy, fx

        v_f = self.vx * fx + self.vy * fy
        v_l = self.vx * rx + self.vy * ry

        if acelerar != 0:
            v_f += ACELERACAO * acelerar * dt
        else:
            v_f *= FREIO_MOTOR ** dt

        v_f = max(VEL_RE, min(v_f, self.vel_max))

        # Os pneus "seguram" o carro: a parte lateral da velocidade some
        v_l *= ADERENCIA ** dt

        # Direção
        self.angulo += direcao * 0.045 * dt * (v_f / 3)

        fx, fy = self.frente()
        rx, ry = -fy, fx
        self.vx = fx * v_f + rx * v_l
        self.vy = fy * v_f + ry * v_l

        # Rotação vinda de batidas (não gira o vetor velocidade, então o
        # carro "derrapa" até as rodas realinharem)
        self.angulo += self.giro * dt
        self.giro *= 0.88 ** dt

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Fora da pista
        rho = self.rho()
        if rho < 0.78 or rho > 1.22:
            arrasto = PERDA_FORA_DA_PISTA ** dt
            self.vx *= arrasto
            self.vy *= arrasto

        # Evita velocidades absurdas depois de batidas
        v = self.velocidade_total()
        limite = VEL_MAX * 1.25
        if v > limite:
            self.vx *= limite / v
            self.vy *= limite / v

    def atualizar_progresso(self):
        t = self.theta()
        dif = (t - self.theta_anterior + math.pi) % (2 * math.pi) - math.pi

        if abs(dif) < 0.25:
            self.progresso += dif   # anda pra trás = perde progresso

        self.theta_anterior = t


# ==========================================
# COLISÕES (SAT + IMPULSO COM ROTAÇÃO)
# ==========================================

def _cantos(c):
    fx, fy = c.frente()
    rx, ry = -fy, fx
    cantos = []

    for sc, sl in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
        cantos.append((
            c.x + fx * sc * MEIO_COMP + rx * sl * MEIA_LARG,
            c.y + fy * sc * MEIO_COMP + ry * sl * MEIA_LARG
        ))

    return cantos


def _ponto_dentro(c, px, py):
    fx, fy = c.frente()
    dx, dy = px - c.x, py - c.y

    return (
        abs(dx * fx + dy * fy) <= MEIO_COMP + 0.5
        and abs(-dx * fy + dy * fx) <= MEIA_LARG + 0.5
    )


def detectar_colisao(a, b):
    """
    Teste dos eixos separadores entre dois retângulos orientados.
    Retorna (nx, ny, penetração, px, py) com a normal apontando de a para b,
    ou None se os carros não se tocam.
    """
    dx, dy = b.x - a.x, b.y - a.y

    # Descarte rápido: longe demais para encostar
    if dx * dx + dy * dy > 40 * 40:
        return None

    cantos_a = _cantos(a)
    cantos_b = _cantos(b)

    eixos = []
    for c in (a, b):
        fx, fy = c.frente()
        eixos.append((fx, fy))
        eixos.append((-fy, fx))

    menor = None

    for ex, ey in eixos:
        pa = [px * ex + py * ey for px, py in cantos_a]
        pb = [px * ex + py * ey for px, py in cantos_b]

        sobreposicao = min(max(pa), max(pb)) - max(min(pa), min(pb))

        if sobreposicao <= 0:
            return None

        if menor is None or sobreposicao < menor[0]:
            menor = (sobreposicao, ex, ey)

    penetracao, nx, ny = menor

    if nx * dx + ny * dy < 0:
        nx, ny = -nx, -ny

    # Ponto de contato: média dos cantos de um carro que entraram no outro
    pontos = (
        [p for p in cantos_a if _ponto_dentro(b, *p)]
        + [p for p in cantos_b if _ponto_dentro(a, *p)]
    )

    if pontos:
        px = sum(p[0] for p in pontos) / len(pontos)
        py = sum(p[1] for p in pontos) / len(pontos)
    else:
        px, py = (a.x + b.x) / 2, (a.y + b.y) / 2

    return nx, ny, penetracao, px, py


def resolver_colisao(a, b):
    """
    Separa os carros e troca impulso entre eles (com giro).
    Retorna (intensidade, x, y) da batida ou None se não houve contato.
    """
    colisao = detectar_colisao(a, b)

    if colisao is None:
        return None

    nx, ny, penetracao, px, py = colisao

    # Separação (massas iguais: cada um recua metade)
    recuo = penetracao / 2 + 0.01
    a.x -= nx * recuo
    a.y -= ny * recuo
    b.x += nx * recuo
    b.y += ny * recuo

    # Braços de alavanca do ponto de contato
    rax, ray = px - a.x, py - a.y
    rbx, rby = px - b.x, py - b.y

    # Velocidade de cada carro exatamente no ponto de contato
    vax = a.vx - a.giro * ray
    vay = a.vy + a.giro * rax
    vbx = b.vx - b.giro * rby
    vby = b.vy + b.giro * rbx

    vn = (vbx - vax) * nx + (vby - vay) * ny

    if vn >= 0:
        return 0.0, px, py   # já estão se afastando

    ra_n = rax * ny - ray * nx
    rb_n = rbx * ny - rby * nx

    divisor = 2 / MASSA + (ra_n ** 2 + rb_n ** 2) / INERCIA
    j = -(1 + RESTITUICAO) * vn / divisor

    ix, iy = j * nx, j * ny

    a.vx -= ix / MASSA
    a.vy -= iy / MASSA
    b.vx += ix / MASSA
    b.vy += iy / MASSA

    a.giro -= (rax * iy - ray * ix) / INERCIA
    b.giro += (rbx * iy - rby * ix) / INERCIA

    a.giro = max(-GIRO_MAX, min(GIRO_MAX, a.giro))
    b.giro = max(-GIRO_MAX, min(GIRO_MAX, b.giro))

    return j, px, py


# ==========================================
# INTELIGÊNCIA ARTIFICIAL
# ==========================================

class PilotoIA:
    """
    Segue a pista com uma "perseguição de ponto" (pure pursuit) e decide
    sua faixa de trajetória olhando os carros próximos:

    - carro atrás, perto e chegando  -> copia a faixa dele para fechar a
      ultrapassagem (com antecipação do movimento lateral dele);
    - carro lento à frente           -> escolhe um lado e tenta passar;
    - ninguém por perto              -> volta para a sua faixa preferida.

    Pilotos pouco agressivos não "fecham a porta" quando o rival já está
    ao lado; os agressivos sim, e é aí que as batidas acontecem.
    """

    def __init__(self, carro, fator_vel, agressividade, lane_inicial):
        self.carro = carro
        self.agressividade = agressividade

        self.vel_base = VEL_MAX * fator_vel * random.uniform(0.95, 1.0)
        carro.vel_max = self.vel_base

        self.lane = lane_inicial
        self.lane_base = random.uniform(0.95, 1.05)
        self.antecipacao = 6 + 14 * agressividade
        self.lado = 0   # lado escolhido para ultrapassar (-1 dentro, +1 fora)

    def _vizinhos(self, todos):
        c = self.carro
        fx, fy = c.frente()
        rx, ry = -fy, fx

        atras = None
        frente = None

        for o in todos:
            if o is c:
                continue

            rel_x = o.x - c.x
            rel_y = o.y - c.y

            d_long = rel_x * fx + rel_y * fy
            d_lat = rel_x * rx + rel_y * ry

            if -ALCANCE_DEFESA <= d_long <= 8 and abs(d_lat) <= 70:
                # Só vira ameaça quem não está bem mais lento que eu
                if o.velocidade_total() >= c.velocidade_total() - 0.6:
                    if atras is None or d_long > atras[1]:
                        atras = (o, d_long, d_lat)

            elif 8 < d_long <= ALCANCE_ULTRAPASSAGEM and abs(d_lat) <= 28:
                if frente is None or d_long < frente[1]:
                    frente = (o, d_long, d_lat)

        return atras, frente

    def controlar(self, todos, dt):
        c = self.carro
        atras, frente = self._vizinhos(todos)

        lane_alvo = self.lane_base
        vel_alvo = self.vel_base

        if frente is not None:
            o, d_long, d_lat = frente

            if self.lado == 0:
                self.lado = -1 if o.rho() >= 1.0 else 1

            lane_alvo = o.rho() + self.lado * 0.15

            if d_long < 40 and abs(d_lat) < 22:
                vel_alvo = min(vel_alvo, o.velocidade_total() * 0.98)

        else:
            self.lado = 0

            if atras is not None:
                o, d_long, d_lat = atras

                rho_o = o.rho()
                lane_alvo = rho_o + (rho_o - o.rho_ant) * self.antecipacao

                # Rival já ao lado: os "limpos" não esmagam o adversário
                if (d_long > -26 and abs(d_lat) < 34
                        and self.agressividade < 0.7):
                    lane_alvo = self.lane

        lane_alvo = max(LANE_MIN, min(LANE_MAX, lane_alvo))

        # Mudança de faixa limitada: dá para enganar a IA com fintas
        passo = 0.006 * (0.7 + 0.6 * self.agressividade) * dt
        self.lane += max(-passo, min(passo, lane_alvo - self.lane))

        # Ponto da pista que o carro persegue
        theta = c.theta()
        v_f = c.velocidade_frente()
        antecedencia = 0.14 + 0.03 * max(v_f, 0)

        alvo_x = CX + RAIO_X * self.lane * math.cos(theta + antecedencia)
        alvo_y = CY + RAIO_Y * self.lane * math.sin(theta + antecedencia)

        erro = (
            math.atan2(alvo_y - c.y, alvo_x - c.x) - c.angulo + math.pi
        ) % (2 * math.pi) - math.pi

        if abs(erro) > 1.2 and c.velocidade_total() < 2.5:
            # Rodou e ficou travado de lado/de ré: gira no lugar
            c.angulo += max(-0.05, min(0.05, erro)) * dt
            acelerar, direcao = 1, 0
        else:
            direcao = max(-1, min(1, erro * 2.2))

            if v_f < vel_alvo:
                acelerar = 1
            elif v_f > vel_alvo + 0.4:
                acelerar = -1
            else:
                acelerar = 0

        c.atualizar(acelerar, direcao, dt)


def criar_grade(corrida):
    """Monta a grade de largada em duas filas alternadas."""

    fator_vel, agressividade = NIVEIS_IA.get(
        corrida["dificuldade"], (0.85, 0.5)
    )

    cores = [
        (30, 130, 255),
        (255, 190, 30),
        (30, 210, 120),
        (180, 70, 230),
        (240, 240, 240)
    ]

    jogador = None
    pilotos = []
    carros = []
    cor_ia = iter(cores)

    for slot in range(6):

        theta = -math.pi / 2 - slot * 0.15
        lane = 0.93 if slot % 2 == 0 else 1.07

        x = CX + RAIO_X * lane * math.cos(theta)
        y = CY + RAIO_Y * lane * math.sin(theta)

        direcao = math.atan2(
            RAIO_Y * math.cos(theta),
            -RAIO_X * math.sin(theta)
        )

        if slot == SLOT_JOGADOR:
            jogador = Carro(x, y, direcao, COR_JOGADOR)
            carros.append(jogador)

        else:
            carro = Carro(x, y, direcao, next(cor_ia))
            pilotos.append(
                PilotoIA(carro, fator_vel, agressividade, lane)
            )
            carros.append(carro)

    return jogador, pilotos, carros


# ==========================================
# DESENHO
# ==========================================

def desenhar_carro(tela, carro):

    corpo = pygame.Surface((38, 22), pygame.SRCALPHA)

    pygame.draw.rect(
        corpo, carro.cor, (3, 2, 32, 18), border_radius=5
    )

    pygame.draw.rect(
        corpo, (25, 30, 35), (11, 4, 15, 14), border_radius=3
    )

    pygame.draw.rect(
        corpo, (240, 240, 240), (31, 5, 4, 4)
    )

    pygame.draw.rect(
        corpo, (240, 240, 240), (31, 13, 4, 4)
    )

    imagem = pygame.transform.rotate(
        corpo, -math.degrees(carro.angulo)
    )

    retangulo = imagem.get_rect(center=(int(carro.x), int(carro.y)))

    tela.blit(imagem, retangulo)


def desenhar_pista(tela):

    tela.fill(COR_GRAMA)

    # Parte externa da pista
    pygame.draw.ellipse(
        tela,
        (210, 210, 210),
        (
            CX - RAIO_X - LARGURA_PISTA // 2,
            CY - RAIO_Y - LARGURA_PISTA // 2,
            2 * RAIO_X + LARGURA_PISTA,
            2 * RAIO_Y + LARGURA_PISTA
        )
    )

    pygame.draw.ellipse(
        tela,
        COR_PISTA,
        (
            CX - RAIO_X + LARGURA_PISTA // 2,
            CY - RAIO_Y + LARGURA_PISTA // 2,
            2 * RAIO_X - LARGURA_PISTA,
            2 * RAIO_Y - LARGURA_PISTA
        )
    )

    # Área interna da pista
    pygame.draw.ellipse(
        tela,
        COR_GRAMA,
        (
            CX - RAIO_X + LARGURA_PISTA,
            CY - RAIO_Y + LARGURA_PISTA,
            2 * RAIO_X - 2 * LARGURA_PISTA,
            2 * RAIO_Y - 2 * LARGURA_PISTA
        )
    )

    # Linha central tracejada
    pygame.draw.ellipse(
        tela,
        (220, 220, 100),
        (
            CX - RAIO_X,
            CY - RAIO_Y,
            RAIO_X * 2,
            RAIO_Y * 2
        ),
        2
    )

    # Linha de largada
    pygame.draw.line(
        tela,
        (255, 255, 255),
        (CX, CY - RAIO_Y - 60),
        (CX, CY - RAIO_Y + 60),
        5
    )


def criar_faiscas(faiscas, x, y, intensidade):

    quantidade = 3 + int(min(intensidade, 2.0) * 5)

    for _ in range(quantidade):
        ang = random.uniform(0, 2 * math.pi)
        vel = random.uniform(1.0, 4.0)

        # [x, y, vx, vy, vida]
        faiscas.append([
            x, y,
            math.cos(ang) * vel,
            math.sin(ang) * vel,
            random.uniform(10, 22)
        ])


# ==========================================
# MOTOR DA CORRIDA
# ==========================================

def executar_corrida(corrida):

    pygame.init()

    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Racing Legends")

    relogio = pygame.time.Clock()

    fonte = pygame.font.SysFont("Arial", 22, bold=True)
    fonte_grande = pygame.font.SysFont("Arial", 45, bold=True)
    fonte_contagem = pygame.font.SysFont("Arial", 110, bold=True)

    voltas_maximas = corrida["voltas"]
    volta_total = voltas_maximas * 2 * math.pi

    jogador, pilotos, carros = criar_grade(corrida)
    adversarios = [p.carro for p in pilotos]

    faiscas = []

    contagem = 3.0          # segundos até a largada
    tempo_inicio = None
    tempo_final = 0.0
    posicao_final = len(carros)

    executando = True
    finalizada = False

    while executando:

        dt = min(relogio.tick(60) / 16.67, 2)

        for evento in pygame.event.get():

            if evento.type == pygame.QUIT:
                executando = False

            if evento.type == pygame.KEYDOWN:

                if evento.key == pygame.K_ESCAPE:
                    executando = False

                if finalizada and evento.key in (
                    pygame.K_RETURN, pygame.K_SPACE
                ):
                    executando = False

        if not executando:
            break

        teclas = pygame.key.get_pressed()

        # ==================================
        # LARGADA
        # ==================================

        if contagem > 0:

            contagem -= dt / 60

            if contagem <= 0:
                tempo_inicio = pygame.time.get_ticks()

        # ==================================
        # SIMULAÇÃO
        # ==================================

        elif not finalizada:

            # Jogador
            acelerar = 0

            if teclas[pygame.K_UP] or teclas[pygame.K_w]:
                acelerar = 1
            elif teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
                acelerar = -1

            direcao = (
                int(bool(teclas[pygame.K_RIGHT] or teclas[pygame.K_d]))
                - int(bool(teclas[pygame.K_LEFT] or teclas[pygame.K_a]))
            )

            jogador.atualizar(acelerar, direcao, dt)

            # Adversários
            for piloto in pilotos:
                piloto.controlar(carros, dt)

            # Colisões entre todos os pares (2 passadas deixam as pilhas
            # de carros mais estáveis)
            for _ in range(2):
                for i in range(len(carros)):
                    for j in range(i + 1, len(carros)):

                        batida = resolver_colisao(carros[i], carros[j])

                        if batida and batida[0] > 0.3:
                            criar_faiscas(
                                faiscas, batida[1], batida[2], batida[0]
                            )

            for carro in carros:
                carro.atualizar_progresso()
                carro.rho_ant = carro.rho()

            # Faíscas
            for f in faiscas:
                f[0] += f[2] * dt
                f[1] += f[3] * dt
                f[4] -= dt

            faiscas = [f for f in faiscas if f[4] > 0]

            if jogador.progresso >= volta_total:
                finalizada = True
                tempo_final = (
                    pygame.time.get_ticks() - tempo_inicio
                ) / 1000
                posicao_final = 1 + sum(
                    c.progresso > jogador.progresso for c in adversarios
                )

        # ==================================
        # DESENHAR O JOGO
        # ==================================

        desenhar_pista(tela)

        for carro in adversarios:
            desenhar_carro(tela, carro)

        desenhar_carro(tela, jogador)

        for x, y, vx, vy, vida in faiscas:
            cor = (255, 150 + int(min(vida, 20) * 5), 60)
            pygame.draw.line(
                tela, cor, (x, y), (x - vx * 1.5, y - vy * 1.5), 2
            )

        # ==================================
        # PAINEL DE INFORMAÇÕES
        # ==================================

        if finalizada:
            tempo = tempo_final
        elif tempo_inicio is not None:
            tempo = (pygame.time.get_ticks() - tempo_inicio) / 1000
        else:
            tempo = 0.0

        volta = max(
            1,
            min(int(jogador.progresso // (2 * math.pi)) + 1, voltas_maximas)
        )

        pygame.draw.rect(
            tela,
            (15, 20, 28),
            (15, 15, 280, 125),
            border_radius=10
        )

        textos = [
            corrida["nome"],
            f"Velocidade: {int(jogador.velocidade_total() * 30)} km/h",
            f"Volta: {volta} / {voltas_maximas}",
            f"Tempo: {tempo:.1f}s"
        ]

        for i, texto in enumerate(textos):

            imagem = fonte.render(
                texto, True, (255, 255, 255)
            )

            tela.blit(imagem, (30, 23 + i * 27))

        # Posição na corrida
        posicao = (
            posicao_final if finalizada
            else 1 + sum(c.progresso > jogador.progresso for c in adversarios)
        )

        posicao_img = fonte.render(
            f"POSIÇÃO: {posicao}º / {len(carros)}",
            True,
            (255, 220, 50)
        )

        tela.blit(posicao_img, (LARGURA - 220, 25))

        # ==================================
        # CONTAGEM REGRESSIVA
        # ==================================

        if contagem > 0:

            numero = fonte_contagem.render(
                str(math.ceil(contagem)), True, (255, 220, 50)
            )

            tela.blit(
                numero,
                numero.get_rect(center=(LARGURA // 2, ALTURA // 2))
            )

        elif (tempo_inicio is not None and not finalizada
                and pygame.time.get_ticks() - tempo_inicio < 800):

            vai = fonte_contagem.render("VAI!", True, (60, 230, 120))

            tela.blit(
                vai,
                vai.get_rect(center=(LARGURA // 2, ALTURA // 2))
            )

        # ==================================
        # TELA DE RESULTADO
        # ==================================

        if finalizada:

            pygame.draw.rect(
                tela,
                (15, 20, 28),
                (230, 235, 540, 220),
                border_radius=20
            )

            titulo = fonte_grande.render(
                "CORRIDA CONCLUÍDA!",
                True,
                (230, 57, 70)
            )

            tela.blit(
                titulo,
                titulo.get_rect(center=(500, 285))
            )

            resultado = fonte.render(
                f"Tempo: {tempo_final:.1f}s",
                True,
                (255, 255, 255)
            )

            tela.blit(
                resultado,
                resultado.get_rect(center=(500, 345))
            )

            colocacao = fonte.render(
                f"Posição final: {posicao_final}º / {len(carros)}",
                True,
                (255, 220, 50)
            )

            tela.blit(
                colocacao,
                colocacao.get_rect(center=(500, 380))
            )

            instrucoes = fonte.render(
                "ENTER para voltar ao menu",
                True,
                (190, 190, 190)
            )

            tela.blit(
                instrucoes,
                instrucoes.get_rect(center=(500, 425))
            )

        pygame.display.flip()

    pygame.quit()


# ==========================================
# MENU PRINCIPAL
# ==========================================

class RacingMenu(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Racing Legends")
        self.geometry("1000x700")
        self.minsize(850, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color="#101820")

        self.selecionada = 0

        self.menu_principal()

    def limpar(self):

        for widget in self.winfo_children():
            widget.destroy()

    def menu_principal(self):

        self.limpar()

        container = ctk.CTkFrame(
            self, fg_color="transparent"
        )

        container.pack(expand=True)

        ctk.CTkLabel(
            container,
            text="RACING LEGENDS",
            font=("Arial", 46, "bold")
        ).pack(pady=15)

        ctk.CTkLabel(
            container,
            text="Prepare-se para acelerar!",
            font=("Arial", 17),
            text_color="#AAB7C4"
        ).pack(pady=15)

        ctk.CTkButton(
            container,
            text="JOGAR",
            width=280,
            height=55,
            fg_color="#E63946",
            hover_color="#C92F3B",
            font=("Arial", 18, "bold"),
            command=self.selecao_corridas
        ).pack(pady=12)

        ctk.CTkButton(
            container,
            text="CONFIGURAÇÕES",
            width=280,
            height=55,
            fg_color="#263746",
            command=self.configuracoes
        ).pack(pady=12)

        ctk.CTkButton(
            container,
            text="SAIR",
            width=280,
            height=55,
            fg_color="transparent",
            border_width=1,
            command=self.destroy
        ).pack(pady=12)

    # ======================================
    # SELEÇÃO DAS CORRIDAS
    # ======================================

    def selecao_corridas(self):

        self.limpar()

        ctk.CTkLabel(
            self,
            text="SELECIONE SUA CORRIDA",
            font=("Arial", 32, "bold")
        ).pack(pady=20)

        area = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        for coluna in range(3):
            area.grid_columnconfigure(coluna, weight=1)

        self.botoes_corrida = []

        for i, corrida in enumerate(CORRIDAS):

            card = ctk.CTkFrame(
                area,
                fg_color="#1C2A38",
                corner_radius=15,
                border_width=2,
                border_color="#E63946" if i == self.selecionada else "#354B5E"
            )

            card.grid(
                row=i // 3,
                column=i % 3,
                padx=10,
                pady=10,
                sticky="nsew"
            )

            ctk.CTkLabel(
                card,
                text="🏁",
                font=("Arial", 40)
            ).pack(pady=8)

            ctk.CTkLabel(
                card,
                text=corrida["nome"],
                font=("Arial", 16, "bold")
            ).pack(pady=5)

            ctk.CTkLabel(
                card,
                text=f'Dificuldade: {corrida["dificuldade"]}'
            ).pack(pady=5)

            ctk.CTkLabel(
                card,
                text=f'Voltas: {corrida["voltas"]}'
            ).pack(pady=5)

            botao = ctk.CTkButton(
                card,
                text="SELECIONADA" if i == self.selecionada else "SELECIONAR",
                fg_color="#E63946" if i == self.selecionada else "#354B5E",
                command=lambda indice=i: self.selecionar(indice)
            )

            botao.pack(
                fill="x",
                padx=15,
                pady=12
            )

            self.botoes_corrida.append((card, botao))

        botoes = ctk.CTkFrame(
            self, fg_color="transparent"
        )

        botoes.pack(pady=15)

        ctk.CTkButton(
            botoes,
            text="VOLTAR",
            width=160,
            height=45,
            command=self.menu_principal
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes,
            text="INICIAR CORRIDA",
            width=220,
            height=45,
            fg_color="#E63946",
            hover_color="#C92F3B",
            command=self.iniciar_corrida
        ).pack(side="left", padx=10)

    def selecionar(self, indice):

        self.selecionada = indice

        for i, (card, botao) in enumerate(self.botoes_corrida):

            selecionada = i == indice

            card.configure(
                border_color="#E63946" if selecionada else "#354B5E"
            )

            botao.configure(
                text="SELECIONADA" if selecionada else "SELECIONAR",
                fg_color="#E63946" if selecionada else "#354B5E"
            )

    # ======================================
    # INICIAR O GAMEPLAY
    # ======================================

    def iniciar_corrida(self):

        corrida = CORRIDAS[self.selecionada]

        self.withdraw()

        try:
            executar_corrida(corrida)

        finally:
            if self.winfo_exists():
                self.deiconify()

    # ======================================
    # CONFIGURAÇÕES
    # ======================================

    def configuracoes(self):

        self.limpar()

        container = ctk.CTkFrame(
            self, fg_color="transparent"
        )

        container.pack(expand=True)

        ctk.CTkLabel(
            container,
            text="CONFIGURAÇÕES",
            font=("Arial", 36, "bold")
        ).pack(pady=20)

        ctk.CTkLabel(
            container,
            text="Modo de aparência"
        ).pack(pady=10)

        aparencia = ctk.CTkSegmentedButton(
            container,
            values=["Escuro", "Claro", "Sistema"],
            command=lambda escolha: ctk.set_appearance_mode(
                {"Escuro": "dark", "Claro": "light", "Sistema": "system"}[escolha]
            )
        )

        aparencia.set("Escuro")
        aparencia.pack(pady=10)

        ctk.CTkButton(
            container,
            text="VOLTAR",
            width=220,
            height=45,
            command=self.menu_principal
        ).pack(pady=25)


# ==========================================
# EXECUTAR APLICAÇÃO
# ==========================================

if __name__ == "__main__":

    jogo = RacingMenu()
    jogo.mainloop()