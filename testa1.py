
import math
import random
from bisect import bisect_right

import pygame
import customtkinter as ctk


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LARGURA = 1000
ALTURA = 700

COR_GRAMA = (35, 105, 57)
COR_PISTA = (65, 68, 73)
COR_JOGADOR = (230, 57, 70)

LARGURA_PISTA = 125
MEIO_COMP = 17
MEIA_LARG = 10

ACELERACAO = 0.16
VEL_MAX = 6
VEL_RE = -2.5
FREIO_MOTOR = 0.985
ADERENCIA = 0.80
PERDA_FORA_DA_PISTA = 0.94

MASSA = 1.0
INERCIA = MASSA * (
    (2 * MEIO_COMP) ** 2 + (2 * MEIA_LARG) ** 2
) / 12

RESTITUICAO = 0.35
GIRO_MAX = 0.08

SLOT_JOGADOR = 5

LANE_MIN = 0.86
LANE_MAX = 1.14

ALCANCE_DEFESA = 130
ALCANCE_ULTRAPASSAGEM = 90

NIVEIS_IA = {
    "Muito Fácil": (0.70, 0.10),
    "Fácil": (0.78, 0.25),
    "Médio": (0.86, 0.45),
    "Difícil": (0.92, 0.70),
    "Extremo": (1.00, 1.00),
}

CORRIDAS = [
    {
        "nome": "CORRIDA URBANA",
        "dificuldade": "Muito Fácil",
        "voltas": 3,
        "cor": (35, 100, 220),
    },
    {
        "nome": "DESERTO EXTREMO",
        "dificuldade": "Fácil",
        "voltas": 6,
        "cor": (210, 130, 40),
    },
    {
        "nome": "MONTANHAS",
        "dificuldade": "Médio",
        "voltas": 10,
        "cor": (40, 150, 100),
    },
    {
        "nome": "PISTA NOTURNA",
        "dificuldade": "Difícil",
        "voltas": 15,
        "cor": (120, 70, 200),
    },
    {
        "nome": "GRANDE PRÊMIO",
        "dificuldade": "Extremo",
        "voltas": 25,
        "cor": (190, 40, 40),
    },
]


# ============================================================
# CINCO CIRCUITOS PERSONALIZADOS
# ============================================================

CIRCUITOS = {
    "CORRIDA URBANA": [
        (170, 130), (350, 100), (550, 120), (800, 100),
        (890, 210), (850, 350), (900, 510), (700, 580),
        (490, 550), (300, 600), (130, 480), (110, 300),
    ],

    "DESERTO EXTREMO": [
        (160, 180), (300, 100), (470, 150), (650, 100),
        (850, 180), (900, 330), (800, 430), (880, 550),
        (650, 600), (480, 520), (300, 610), (120, 470),
        (170, 320),
    ],

    "MONTANHAS": [
        (150, 180), (330, 100), (500, 170), (650, 100),
        (850, 170), (900, 300), (760, 360), (880, 500),
        (700, 600), (520, 510), (350, 620), (130, 500),
        (220, 350),
    ],

    "PISTA NOTURNA": [
        (160, 150), (350, 100), (500, 150), (700, 100),
        (870, 190), (820, 300), (920, 430), (760, 570),
        (570, 530), (450, 610), (260, 550), (110, 420),
        (200, 300),
    ],

    "GRANDE PRÊMIO": [
        (150, 150), (350, 100), (550, 100), (800, 150),
        (900, 270), (820, 370), (900, 520), (700, 600),
        (500, 550), (350, 620), (150, 520), (100, 350),
        (220, 280),
    ],
}


# ============================================================
# SISTEMA DE PISTAS CURVAS
# ============================================================

PISTA = []
DISTANCIAS = []
COMPRIMENTO_PISTA = 1


def catmull_rom(p0, p1, p2, p3, t):
    """Calcula um ponto suave entre pontos de controle."""

    t2 = t * t
    t3 = t2 * t

    x = 0.5 * (
        2 * p1[0]
        + (-p0[0] + p2[0]) * t
        + (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2
        + (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3
    )

    y = 0.5 * (
        2 * p1[1]
        + (-p0[1] + p2[1]) * t
        + (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2
        + (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
    )

    return x, y


def gerar_pista(pontos_controle):
    """Transforma pontos de controle em uma pista curva."""

    pontos = []
    quantidade = 12
    total = len(pontos_controle)

    for i in range(total):
        p0 = pontos_controle[(i - 1) % total]
        p1 = pontos_controle[i]
        p2 = pontos_controle[(i + 1) % total]
        p3 = pontos_controle[(i + 2) % total]

        for j in range(quantidade):
            t = j / quantidade
            pontos.append(catmull_rom(p0, p1, p2, p3, t))

    distancias = [0.0]

    for i in range(len(pontos)):
        atual = pontos[i]
        proximo = pontos[(i + 1) % len(pontos)]

        distancia = math.hypot(
            proximo[0] - atual[0],
            proximo[1] - atual[1],
        )

        distancias.append(distancias[-1] + distancia)

    return pontos, distancias


def configurar_pista(nome_corrida):
    global PISTA, DISTANCIAS, COMPRIMENTO_PISTA

    pontos = CIRCUITOS.get(
        nome_corrida,
        CIRCUITOS["CORRIDA URBANA"],
    )

    PISTA, DISTANCIAS = gerar_pista(pontos)
    COMPRIMENTO_PISTA = DISTANCIAS[-1]


def ponto_pista(distancia, deslocamento=0):
    """
    Retorna uma posição da pista.
    deslocamento positivo = lado esquerdo da trajetória.
    """

    distancia %= COMPRIMENTO_PISTA

    indice = bisect_right(DISTANCIAS, distancia) - 1
    indice = max(0, min(indice, len(PISTA) - 1))

    proximo = (indice + 1) % len(PISTA)

    inicio = PISTA[indice]
    fim = PISTA[proximo]

    comprimento = DISTANCIAS[indice + 1] - DISTANCIAS[indice]

    if comprimento == 0:
        t = 0
    else:
        t = (
            distancia - DISTANCIAS[indice]
        ) / comprimento

    x = inicio[0] + (fim[0] - inicio[0]) * t
    y = inicio[1] + (fim[1] - inicio[1]) * t

    tx = fim[0] - inicio[0]
    ty = fim[1] - inicio[1]

    tamanho = math.hypot(tx, ty)

    if tamanho == 0:
        return x, y

    tx /= tamanho
    ty /= tamanho

    nx = -ty
    ny = tx

    return (
        x + nx * deslocamento,
        y + ny * deslocamento,
    )


def projetar_pista(x, y):
    """
    Encontra o ponto mais próximo da pista.

    Retorna:
    distância percorrida na pista e deslocamento lateral.
    """

    menor_distancia = float("inf")
    melhor_progresso = 0
    melhor_lateral = 0

    for i in range(len(PISTA)):
        a = PISTA[i]
        b = PISTA[(i + 1) % len(PISTA)]

        dx = b[0] - a[0]
        dy = b[1] - a[1]

        tamanho2 = dx * dx + dy * dy

        if tamanho2 == 0:
            continue

        t = (
            (x - a[0]) * dx + (y - a[1]) * dy
        ) / tamanho2

        t = max(0, min(1, t))

        px = a[0] + dx * t
        py = a[1] + dy * t

        distancia2 = (x - px) ** 2 + (y - py) ** 2

        if distancia2 < menor_distancia:
            menor_distancia = distancia2

            tamanho = math.sqrt(tamanho2)

            melhor_progresso = (
                DISTANCIAS[i] + tamanho * t
            )

            melhor_lateral = (
                dx * (y - py) - dy * (x - px)
            ) / tamanho

    return melhor_progresso, melhor_lateral


# ============================================================
# CARRO
# ============================================================

class Carro:

    def __init__(
        self,
        x,
        y,
        angulo,
        cor,
        vel_max=VEL_MAX,
        progresso_inicial=0,
    ):
        self.x = x
        self.y = y
        self.angulo = angulo

        self.vx = 0.0
        self.vy = 0.0
        self.giro = 0.0

        self.cor = cor
        self.vel_max = vel_max

        distancia, _ = projetar_pista(x, y)

        self.distancia_anterior = distancia
        self.progresso = progresso_inicial

        self.rho_ant = self.rho()

    def frente(self):
        return math.cos(self.angulo), math.sin(self.angulo)

    def velocidade_total(self):
        return math.hypot(self.vx, self.vy)

    def velocidade_frente(self):
        fx, fy = self.frente()
        return self.vx * fx + self.vy * fy

    def rho(self):
        _, lateral = projetar_pista(self.x, self.y)

        return 1.0 + lateral / (LARGURA_PISTA * 0.5)

    def atualizar(self, acelerar, direcao, dt):

        fx, fy = self.frente()
        rx, ry = -fy, fx

        v_f = self.vx * fx + self.vy * fy
        v_l = self.vx * rx + self.vy * ry

        if acelerar != 0:
            v_f += ACELERACAO * acelerar * dt
        else:
            v_f *= FREIO_MOTOR ** dt

        v_f = max(VEL_RE, min(v_f, self.vel_max))

        v_l *= ADERENCIA ** dt

        self.angulo += direcao * 0.045 * dt * (v_f / 3)

        fx, fy = self.frente()
        rx, ry = -fy, fx

        self.vx = fx * v_f + rx * v_l
        self.vy = fy * v_f + ry * v_l

        self.angulo += self.giro * dt
        self.giro *= 0.88 ** dt

        self.x += self.vx * dt
        self.y += self.vy * dt

        rho = self.rho()

        if rho < 0.78 or rho > 1.22:
            arrasto = PERDA_FORA_DA_PISTA ** dt
            self.vx *= arrasto
            self.vy *= arrasto

        velocidade = self.velocidade_total()
        limite = VEL_MAX * 1.25

        if velocidade > limite:
            self.vx *= limite / velocidade
            self.vy *= limite / velocidade

    def atualizar_progresso(self):

        distancia, _ = projetar_pista(self.x, self.y)

        diferenca = (
            distancia - self.distancia_anterior
            + COMPRIMENTO_PISTA / 2
        ) % COMPRIMENTO_PISTA - COMPRIMENTO_PISTA / 2

        if abs(diferenca) < 100:
            self.progresso += diferenca

        self.distancia_anterior = distancia


# ============================================================
# COLISÕES
# ============================================================

def cantos(carro):

    fx, fy = carro.frente()
    rx, ry = -fy, fx

    resultado = []

    for sc, sl in (
        (1, -1),
        (1, 1),
        (-1, 1),
        (-1, -1),
    ):
        resultado.append((
            carro.x + fx * sc * MEIO_COMP + rx * sl * MEIA_LARG,
            carro.y + fy * sc * MEIO_COMP + ry * sl * MEIA_LARG,
        ))

    return resultado


def ponto_dentro(carro, px, py):

    fx, fy = carro.frente()

    dx = px - carro.x
    dy = py - carro.y

    return (
        abs(dx * fx + dy * fy) <= MEIO_COMP + 0.5
        and abs(-dx * fy + dy * fx) <= MEIA_LARG + 0.5
    )


def detectar_colisao(a, b):

    dx = b.x - a.x
    dy = b.y - a.y

    if dx * dx + dy * dy > 40 * 40:
        return None

    cantos_a = cantos(a)
    cantos_b = cantos(b)

    eixos = []

    for carro in (a, b):
        fx, fy = carro.frente()
        eixos.append((fx, fy))
        eixos.append((-fy, fx))

    menor = None

    for ex, ey in eixos:

        pa = [x * ex + y * ey for x, y in cantos_a]
        pb = [x * ex + y * ey for x, y in cantos_b]

        sobreposicao = (
            min(max(pa), max(pb))
            - max(min(pa), min(pb))
        )

        if sobreposicao <= 0:
            return None

        if menor is None or sobreposicao < menor[0]:
            menor = (sobreposicao, ex, ey)

    penetracao, nx, ny = menor

    if nx * dx + ny * dy < 0:
        nx, ny = -nx, -ny

    pontos = (
        [p for p in cantos_a if ponto_dentro(b, *p)]
        + [p for p in cantos_b if ponto_dentro(a, *p)]
    )

    if pontos:
        px = sum(p[0] for p in pontos) / len(pontos)
        py = sum(p[1] for p in pontos) / len(pontos)
    else:
        px = (a.x + b.x) / 2
        py = (a.y + b.y) / 2

    return nx, ny, penetracao, px, py


def resolver_colisao(a, b):

    colisao = detectar_colisao(a, b)

    if colisao is None:
        return None

    nx, ny, penetracao, px, py = colisao

    recuo = penetracao / 2 + 0.01

    a.x -= nx * recuo
    a.y -= ny * recuo

    b.x += nx * recuo
    b.y += ny * recuo

    rax, ray = px - a.x, py - a.y
    rbx, rby = px - b.x, py - b.y

    vax = a.vx - a.giro * ray
    vay = a.vy + a.giro * rax

    vbx = b.vx - b.giro * rby
    vby = b.vy + b.giro * rbx

    vn = (vbx - vax) * nx + (vby - vay) * ny

    if vn >= 0:
        return 0.0, px, py

    ra_n = rax * ny - ray * nx
    rb_n = rbx * ny - rby * nx

    divisor = (
        2 / MASSA
        + (ra_n ** 2 + rb_n ** 2) / INERCIA
    )

    impulso = -(1 + RESTITUICAO) * vn / divisor

    ix = impulso * nx
    iy = impulso * ny

    a.vx -= ix / MASSA
    a.vy -= iy / MASSA

    b.vx += ix / MASSA
    b.vy += iy / MASSA

    a.giro -= (rax * iy - ray * ix) / INERCIA
    b.giro += (rbx * iy - rby * ix) / INERCIA

    a.giro = max(-GIRO_MAX, min(GIRO_MAX, a.giro))
    b.giro = max(-GIRO_MAX, min(GIRO_MAX, b.giro))

    return impulso, px, py


# ============================================================
# INTELIGÊNCIA ARTIFICIAL
# ============================================================

class PilotoIA:

    def __init__(self, carro, fator_vel, agressividade, lane_inicial):

        self.carro = carro
        self.agressividade = agressividade

        self.vel_base = (
            VEL_MAX * fator_vel * random.uniform(0.95, 1.0)
        )

        carro.vel_max = self.vel_base

        self.lane = lane_inicial
        self.lane_base = random.uniform(0.95, 1.05)

        self.antecipacao = 6 + 14 * agressividade
        self.lado = 0

    def vizinhos(self, todos):

        c = self.carro

        fx, fy = c.frente()
        rx, ry = -fy, fx

        atras = None
        frente = None

        for outro in todos:

            if outro is c:
                continue

            rel_x = outro.x - c.x
            rel_y = outro.y - c.y

            d_long = rel_x * fx + rel_y * fy
            d_lat = rel_x * rx + rel_y * ry

            if -ALCANCE_DEFESA <= d_long <= 8 and abs(d_lat) <= 70:

                if outro.velocidade_total() >= c.velocidade_total() - 0.6:
                    if atras is None or d_long > atras[1]:
                        atras = (outro, d_long, d_lat)

            elif 8 < d_long <= ALCANCE_ULTRAPASSAGEM and abs(d_lat) <= 28:

                if frente is None or d_long < frente[1]:
                    frente = (outro, d_long, d_lat)

        return atras, frente

    def controlar(self, todos, dt):

        c = self.carro

        atras, frente = self.vizinhos(todos)

        lane_alvo = self.lane_base
        vel_alvo = self.vel_base

        if frente is not None:

            outro, d_long, d_lat = frente

            if self.lado == 0:
                self.lado = -1 if outro.rho() >= 1.0 else 1

            lane_alvo = outro.rho() + self.lado * 0.15

            if d_long < 40 and abs(d_lat) < 22:
                vel_alvo = min(
                    vel_alvo,
                    outro.velocidade_total() * 0.98,
                )

        else:

            self.lado = 0

            if atras is not None:

                outro, d_long, d_lat = atras

                rho_outro = outro.rho()

                lane_alvo = (
                    rho_outro
                    + (rho_outro - outro.rho_ant) * self.antecipacao
                )

                if (
                    d_long > -26
                    and abs(d_lat) < 34
                    and self.agressividade < 0.7
                ):
                    lane_alvo = self.lane

        lane_alvo = max(LANE_MIN, min(LANE_MAX, lane_alvo))

        passo = (
            0.006 * (0.7 + 0.6 * self.agressividade) * dt
        )

        self.lane += max(
            -passo,
            min(passo, lane_alvo - self.lane),
        )

        # A IA procura um ponto à frente na pista personalizada.
        antecedencia = 65 + max(c.velocidade_frente(), 0) * 12

        deslocamento = (
            (self.lane - 1.0) * LARGURA_PISTA * 0.42
        )

        alvo_x, alvo_y = ponto_pista(
            c.progresso + antecedencia,
            deslocamento,
        )

        erro = (
            math.atan2(alvo_y - c.y, alvo_x - c.x)
            - c.angulo
            + math.pi
        ) % (2 * math.pi) - math.pi

        if abs(erro) > 1.2 and c.velocidade_total() < 2.5:

            c.angulo += max(-0.05, min(0.05, erro)) * dt
            acelerar = 1
            direcao = 0

        else:

            direcao = max(-1, min(1, erro * 2.2))

            velocidade = c.velocidade_frente()

            if velocidade < vel_alvo:
                acelerar = 1
            elif velocidade > vel_alvo + 0.4:
                acelerar = -1
            else:
                acelerar = 0

        c.atualizar(acelerar, direcao, dt)


# ============================================================
# GRADE DE LARGADA
# ============================================================

def criar_grade(corrida):

    fator_vel, agressividade = NIVEIS_IA.get(
        corrida["dificuldade"],
        (0.85, 0.5),
    )

    cores = [
        (30, 130, 255),
        (255, 190, 30),
        (30, 210, 120),
        (180, 70, 230),
        (240, 240, 240),
    ]

    jogador = None
    pilotos = []
    carros = []

    cor_ia = iter(cores)

    for slot in range(6):

        progresso_inicial = -slot * 48

        lane = 0.93 if slot % 2 == 0 else 1.07

        deslocamento = (
            (lane - 1.0) * LARGURA_PISTA * 0.42
        )

        x, y = ponto_pista(
            progresso_inicial,
            deslocamento,
        )

        proximo_x, proximo_y = ponto_pista(
            progresso_inicial + 5,
            deslocamento,
        )

        direcao = math.atan2(
            proximo_y - y,
            proximo_x - x,
        )

        if slot == SLOT_JOGADOR:

            jogador = Carro(
                x,
                y,
                direcao,
                COR_JOGADOR,
                progresso_inicial=progresso_inicial,
            )

            carros.append(jogador)

        else:

            carro = Carro(
                x,
                y,
                direcao,
                next(cor_ia),
                progresso_inicial=progresso_inicial,
            )

            piloto = PilotoIA(
                carro,
                fator_vel,
                agressividade,
                lane,
            )

            pilotos.append(piloto)
            carros.append(carro)

    return jogador, pilotos, carros


# ============================================================
# DESENHO DA PISTA
# ============================================================

def construir_contorno(deslocamento):

    pontos = [
        ponto_pista(
            DISTANCIAS[i],
            deslocamento,
        )
        for i in range(len(PISTA))
    ]

    return [(int(x), int(y)) for x, y in pontos]


def desenhar_pista(tela, corrida):

    tela.fill(COR_GRAMA)

    metade = LARGURA_PISTA / 2

    externo = construir_contorno(metade + 9)
    interno = construir_contorno(-metade - 9)

    externo_pista = construir_contorno(metade)
    interno_pista = construir_contorno(-metade)

    # Bordas externas
    pygame.draw.polygon(
        tela,
        (210, 210, 210),
        externo + list(reversed(interno)),
    )

    # Asfalto
    pygame.draw.polygon(
        tela,
        COR_PISTA,
        externo_pista + list(reversed(interno_pista)),
    )

    # Linhas laterais
    pygame.draw.lines(
        tela,
        (245, 245, 245),
        True,
        externo_pista,
        3,
    )

    pygame.draw.lines(
        tela,
        (245, 245, 245),
        True,
        interno_pista,
        3,
    )

    # Linha central tracejada
    passo = 35

    for distancia in range(0, int(COMPRIMENTO_PISTA), passo * 2):

        pontos = [
            ponto_pista(distancia + i, 0)
            for i in (0, passo)
        ]

        pygame.draw.line(
            tela,
            (220, 220, 100),
            pontos[0],
            pontos[1],
            2,
        )

    # Linha de largada
    inicio = ponto_pista(0, metade)
    fim = ponto_pista(0, -metade)

    pygame.draw.line(
        tela,
        (255, 255, 255),
        inicio,
        fim,
        6,
    )

    # Pequenos detalhes de pista
    for i in range(0, len(PISTA), 8):

        x, y = PISTA[i]

        pygame.draw.circle(
            tela,
            (45, 45, 45),
            (int(x), int(y)),
            3,
        )


# ============================================================
# DESENHO DOS CARROS E EFEITOS
# ============================================================

def desenhar_carro(tela, carro):

    corpo = pygame.Surface((38, 22), pygame.SRCALPHA)

    pygame.draw.rect(
        corpo,
        carro.cor,
        (3, 2, 32, 18),
        border_radius=5,
    )

    pygame.draw.rect(
        corpo,
        (25, 30, 35),
        (11, 4, 15, 14),
        border_radius=3,
    )

    pygame.draw.rect(
        corpo,
        (240, 240, 240),
        (31, 5, 4, 4),
    )

    pygame.draw.rect(
        corpo,
        (240, 240, 240),
        (31, 13, 4, 4),
    )

    imagem = pygame.transform.rotate(
        corpo,
        -math.degrees(carro.angulo),
    )

    retangulo = imagem.get_rect(
        center=(int(carro.x), int(carro.y))
    )

    tela.blit(imagem, retangulo)


def criar_faiscas(faiscas, x, y, intensidade):

    quantidade = 3 + int(min(intensidade, 2.0) * 5)

    for _ in range(quantidade):

        angulo = random.uniform(0, 2 * math.pi)
        velocidade = random.uniform(1.0, 4.0)

        faiscas.append([
            x,
            y,
            math.cos(angulo) * velocidade,
            math.sin(angulo) * velocidade,
            random.uniform(10, 22),
        ])


# ============================================================
# MOTOR DA CORRIDA
# ============================================================

def executar_corrida(corrida):

    # Cada corrida recebe sua própria pista.
    configurar_pista(corrida["nome"])

    pygame.init()

    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(
        f"Racing Legends - {corrida['nome']}"
    )

    relogio = pygame.time.Clock()

    fonte = pygame.font.SysFont("Arial", 22, bold=True)
    fonte_grande = pygame.font.SysFont("Arial", 45, bold=True)
    fonte_contagem = pygame.font.SysFont("Arial", 110, bold=True)

    voltas_maximas = corrida["voltas"]
    volta_total = voltas_maximas * COMPRIMENTO_PISTA

    jogador, pilotos, carros = criar_grade(corrida)

    adversarios = [p.carro for p in pilotos]

    faiscas = []

    contagem = 3.0
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
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    executando = False

        if not executando:
            break

        teclas = pygame.key.get_pressed()

        # ----------------------------------------------------
        # CONTAGEM REGRESSIVA
        # ----------------------------------------------------

        if contagem > 0:

            contagem -= dt / 60

            if contagem <= 0:
                tempo_inicio = pygame.time.get_ticks()

        # ----------------------------------------------------
        # SIMULAÇÃO
        # ----------------------------------------------------

        elif not finalizada:

            acelerar = 0

            if teclas[pygame.K_UP] or teclas[pygame.K_w]:
                acelerar = 1

            elif teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
                acelerar = -1

            direcao = (
                int(bool(
                    teclas[pygame.K_RIGHT]
                    or teclas[pygame.K_d]
                ))
                - int(bool(
                    teclas[pygame.K_LEFT]
                    or teclas[pygame.K_a]
                ))
            )

            jogador.atualizar(
                acelerar,
                direcao,
                dt,
            )

            # Inteligência artificial
            for piloto in pilotos:
                piloto.controlar(carros, dt)

            # Colisões entre os carros
            for _ in range(2):

                for i in range(len(carros)):

                    for j in range(i + 1, len(carros)):

                        batida = resolver_colisao(
                            carros[i],
                            carros[j],
                        )

                        if batida and batida[0] > 0.3:

                            criar_faiscas(
                                faiscas,
                                batida[1],
                                batida[2],
                                batida[0],
                            )

            # Atualização do progresso
            for carro in carros:

                carro.atualizar_progresso()
                carro.rho_ant = carro.rho()

            # Atualização das faíscas
            for faisca in faiscas:

                faisca[0] += faisca[2] * dt
                faisca[1] += faisca[3] * dt
                faisca[4] -= dt

            faiscas = [
                f for f in faiscas
                if f[4] > 0
            ]

            # Final da corrida
            if jogador.progresso >= volta_total:

                finalizada = True

                tempo_final = (
                    pygame.time.get_ticks() - tempo_inicio
                ) / 1000

                posicao_final = 1 + sum(
                    c.progresso > jogador.progresso
                    for c in adversarios
                )

        # ----------------------------------------------------
        # DESENHAR PISTA E CARROS
        # ----------------------------------------------------

        desenhar_pista(tela, corrida)

        for carro in adversarios:
            desenhar_carro(tela, carro)

        desenhar_carro(tela, jogador)

        for x, y, vx, vy, vida in faiscas:

            cor = (
                255,
                150 + int(min(vida, 20) * 5),
                60,
            )

            pygame.draw.line(
                tela,
                cor,
                (int(x), int(y)),
                (int(x - vx * 1.5), int(y - vy * 1.5)),
                2,
            )

        # ----------------------------------------------------
        # PAINEL DE INFORMAÇÕES
        # ----------------------------------------------------

        if finalizada:
            tempo = tempo_final

        elif tempo_inicio is not None:
            tempo = (
                pygame.time.get_ticks() - tempo_inicio
            ) / 1000

        else:
            tempo = 0.0

        volta = max(
            1,
            min(
                int(max(jogador.progresso, 0)
                    // COMPRIMENTO_PISTA) + 1,
                voltas_maximas,
            ),
        )

        pygame.draw.rect(
            tela,
            (15, 20, 28),
            (15, 15, 300, 130),
            border_radius=10,
        )

        textos = [
            corrida["nome"],
            f"Velocidade: {int(jogador.velocidade_total() * 30)} km/h",
            f"Volta: {volta} / {voltas_maximas}",
            f"Tempo: {tempo:.1f}s",
        ]

        for i, texto in enumerate(textos):

            imagem = fonte.render(
                texto,
                True,
                (255, 255, 255),
            )

            tela.blit(
                imagem,
                (30, 23 + i * 27),
            )

        # Posição
        posicao = (
            posicao_final
            if finalizada
            else 1 + sum(
                c.progresso > jogador.progresso
                for c in adversarios
            )
        )

        posicao_img = fonte.render(
            f"POSIÇÃO: {posicao}º / {len(carros)}",
            True,
            (255, 220, 50),
        )

        tela.blit(
            posicao_img,
            (LARGURA - 250, 25),
        )

        # ----------------------------------------------------
        # CONTAGEM REGRESSIVA
        # ----------------------------------------------------

        if contagem > 0:

            numero = fonte_contagem.render(
                str(math.ceil(contagem)),
                True,
                (255, 220, 50),
            )

            tela.blit(
                numero,
                numero.get_rect(
                    center=(LARGURA // 2, ALTURA // 2)
                ),
            )

        elif (
            tempo_inicio is not None
            and not finalizada
            and pygame.time.get_ticks() - tempo_inicio < 800
        ):

            vai = fonte_contagem.render(
                "VAI!",
                True,
                (60, 230, 120),
            )

            tela.blit(
                vai,
                vai.get_rect(
                    center=(LARGURA // 2, ALTURA // 2)
                ),
            )

        # ----------------------------------------------------
        # TELA DE RESULTADO
        # ----------------------------------------------------

        if finalizada:

            pygame.draw.rect(
                tela,
                (15, 20, 28),
                (230, 235, 540, 220),
                border_radius=20,
            )

            titulo = fonte_grande.render(
                "CORRIDA CONCLUÍDA!",
                True,
                (230, 57, 70),
            )

            tela.blit(
                titulo,
                titulo.get_rect(center=(500, 285)),
            )

            resultado = fonte.render(
                f"Tempo: {tempo_final:.1f}s",
                True,
                (255, 255, 255),
            )

            tela.blit(
                resultado,
                resultado.get_rect(center=(500, 345)),
            )

            colocacao = fonte.render(
                f"Posição final: {posicao_final}º / {len(carros)}",
                True,
                (255, 220, 50),
            )

            tela.blit(
                colocacao,
                colocacao.get_rect(center=(500, 380)),
            )

            instrucoes = fonte.render(
                "ENTER para voltar ao menu",
                True,
                (190, 190, 190),
            )

            tela.blit(
                instrucoes,
                instrucoes.get_rect(center=(500, 425)),
            )

        pygame.display.flip()

    pygame.quit()


# ============================================================
# MENU PRINCIPAL
# ============================================================

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
            self,
            fg_color="transparent",
        )

        container.pack(expand=True)

        ctk.CTkLabel(
            container,
            text="RACING LEGENDS",
            font=("Arial", 46, "bold"),
        ).pack(pady=15)

        ctk.CTkLabel(
            container,
            text="Prepare-se para acelerar!",
            font=("Arial", 17),
            text_color="#AAB7C4",
        ).pack(pady=15)

        ctk.CTkButton(
            container,
            text="JOGAR",
            width=280,
            height=55,
            fg_color="#E63946",
            hover_color="#C92F3B",
            font=("Arial", 18, "bold"),
            command=self.selecao_corridas,
        ).pack(pady=12)

        ctk.CTkButton(
            container,
            text="CONFIGURAÇÕES",
            width=280,
            height=55,
            fg_color="#263746",
            command=self.configuracoes,
        ).pack(pady=12)

        ctk.CTkButton(
            container,
            text="SAIR",
            width=280,
            height=55,
            fg_color="transparent",
            border_width=1,
            command=self.destroy,
        ).pack(pady=12)

    # --------------------------------------------------------
    # SELEÇÃO DAS CORRIDAS
    # --------------------------------------------------------

    def selecao_corridas(self):

        self.limpar()

        ctk.CTkLabel(
            self,
            text="SELECIONE SUA CORRIDA",
            font=("Arial", 32, "bold"),
        ).pack(pady=20)

        area = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )

        area.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10,
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
                border_color=(
                    "#E63946"
                    if i == self.selecionada
                    else "#354B5E"
                ),
            )

            card.grid(
                row=i // 3,
                column=i % 3,
                padx=10,
                pady=10,
                sticky="nsew",
            )

            ctk.CTkLabel(
                card,
                text="🏁",
                font=("Arial", 40),
            ).pack(pady=8)

            ctk.CTkLabel(
                card,
                text=corrida["nome"],
                font=("Arial", 16, "bold"),
            ).pack(pady=5)

            ctk.CTkLabel(
                card,
                text=f'Dificuldade: {corrida["dificuldade"]}',
            ).pack(pady=5)

            ctk.CTkLabel(
                card,
                text=f'Voltas: {corrida["voltas"]}',
            ).pack(pady=5)

            botao = ctk.CTkButton(
                card,
                text=(
                    "SELECIONADA"
                    if i == self.selecionada
                    else "SELECIONAR"
                ),
                fg_color=(
                    "#E63946"
                    if i == self.selecionada
                    else "#354B5E"
                ),
                command=lambda indice=i: self.selecionar(indice),
            )

            botao.pack(
                fill="x",
                padx=15,
                pady=12,
            )

            self.botoes_corrida.append((card, botao))

        botoes = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        botoes.pack(pady=15)

        ctk.CTkButton(
            botoes,
            text="VOLTAR",
            width=160,
            height=45,
            command=self.menu_principal,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes,
            text="INICIAR CORRIDA",
            width=220,
            height=45,
            fg_color="#E63946",
            hover_color="#C92F3B",
            command=self.iniciar_corrida,
        ).pack(side="left", padx=10)

    def selecionar(self, indice):

        self.selecionada = indice

        for i, (card, botao) in enumerate(self.botoes_corrida):

            selecionada = i == indice

            card.configure(
                border_color=(
                    "#E63946"
                    if selecionada
                    else "#354B5E"
                ),
            )

            botao.configure(
                text=(
                    "SELECIONADA"
                    if selecionada
                    else "SELECIONAR"
                ),
                fg_color=(
                    "#E63946"
                    if selecionada
                    else "#354B5E"
                ),
            )

    # --------------------------------------------------------
    # INICIAR CORRIDA
    # --------------------------------------------------------

    def iniciar_corrida(self):

        corrida = CORRIDAS[self.selecionada]

        self.withdraw()

        try:
            executar_corrida(corrida)

        finally:
            if self.winfo_exists():
                self.deiconify()

    # --------------------------------------------------------
    # CONFIGURAÇÕES
    # --------------------------------------------------------

    def configuracoes(self):

        self.limpar()

        container = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        container.pack(expand=True)

        ctk.CTkLabel(
            container,
            text="CONFIGURAÇÕES",
            font=("Arial", 36, "bold"),
        ).pack(pady=20)

        ctk.CTkLabel(
            container,
            text="Modo de aparência",
        ).pack(pady=10)

        aparencia = ctk.CTkSegmentedButton(
            container,
            values=["Escuro", "Claro", "Sistema"],
            command=lambda escolha: ctk.set_appearance_mode(
                {
                    "Escuro": "dark",
                    "Claro": "light",
                    "Sistema": "system",
                }[escolha]
            ),
        )

        aparencia.set("Escuro")
        aparencia.pack(pady=10)

        ctk.CTkButton(
            container,
            text="VOLTAR",
            width=220,
            height=45,
            command=self.menu_principal,
        ).pack(pady=25)


# ============================================================
# EXECUTAR APLICAÇÃO
# ============================================================

if __name__ == "__main__":

    jogo = RacingMenu()
    jogo.mainloop()
