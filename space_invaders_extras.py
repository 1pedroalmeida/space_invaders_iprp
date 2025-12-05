import turtle
import random
import time
import os
import sys

# =========================
# Parâmetros / Constantes
# =========================
LARGURA, ALTURA = 600, 700
BORDA_X = (LARGURA // 2) - 20
BORDA_Y = (ALTURA // 2) - 10

PLAYER_SPEED = 20
PLAYER_BULLET_SPEED = 16

ENEMY_ROWS = 3
ENEMY_COLS = 10
ENEMY_SPACING_X = 60
ENEMY_SPACING_Y = 50
ENEMY_SIZE = 32
ENEMY_START_Y = BORDA_Y - ENEMY_SIZE    # topo visível
ENEMY_FALL_SPEED = 0.5
ENEMY_DRIFT_STEP = 2
ENEMY_FIRE_PROB = 0.006
ENEMY_BULLET_SPEED = 8
ENEMY_INVERT_CHANCE = 0.05
ENEMY_DRIFT_CHANCE = 0.5

COLLISION_RADIUS = 10
HIGHSCORES_FILE = "highscores.txt"
SAVE_FILE = "savegame.txt"
TOP_N = 10

STATE = None  # usado apenas para callbacks do teclado

# =========================
# Top Resultados (Highscores)
# =========================
def ler_highscores(filename):
    with open(filename, "r") as f:
        linhas = f.readlines()
        f.seek(0)

        if ":" not in f.read():
            return []

        nomes = [l[:l.index(":")] for l in linhas]
        scores = [l[l.index(":")+1:-1] for l in linhas]

    return nomes, scores

def ordenar_highscores(highscores, novo_score, nome):
    nomes = highscores[0]
    scores = highscores[1]

    for i in range(len(scores)):
        score = int(scores[i])

        if len(scores) == TOP_N:
            dif = -1
        else:
            dif = len(scores)

        if novo_score > score:
            
            scores = scores[:i] + [novo_score] + scores[i:dif]
            nomes = nomes[:i] + [nome] + nomes[i:dif]

            return nomes, scores
        elif novo_score == score:
            for n in range(len(scores)-1, -1, -1):
                score = int(scores[n])

                if novo_score == score:
                    scores = scores[:i] + [novo_score] + scores[i:dif]
                    nomes = nomes[:i] + [nome] + nomes[i:dif]

                    return nomes, scores
    if len(scores) < TOP_N:
        scores.append(novo_score)
        nomes.append(nome)

    return nomes, scores

def atualizar_highscores(filename, score):
    highscores = ler_highscores(filename)
    linhas = []
    
    if len(highscores) == 0:
        nome = input(f"\nNovo highscore ({score})! Nome do utilizador: ")

        highscores.append([nome])
        highscores.append([score])

    elif len(highscores[1]) < TOP_N:
        nome = input(f"\nNovo highscore ({score})! Nome do utilizador: ")

        highscores = ordenar_highscores(ler_highscores(filename), score, nome)
    elif score > int(highscores[1][-1]):
        nome = input(f"\nNovo highscore ({score})! Nome do utilizador: ")

        highscores = ordenar_highscores(ler_highscores(filename), score, nome)

    for i in range(len(highscores[0])):
        linhas.append(f"{highscores[0][i]}:{highscores[1][i]}\n")

    with open(filename, "w") as f:
        f.writelines(linhas)

def atualizar_score(x, y, t, score):
    t.penup()
    t.clear()
    t.goto(x, y)
    t.color("WHITE")
    t.pendown()
    t.write(f"SCORE: {score}", align="center", font=("Arial", 12, "bold"))

# =========================
# Guardar / Carregar estado (texto)
# =========================
def guardar_estado_txt(filename, state):
    # ==== savegame.txt ==== 
    # player:x,y
    # enemies:x,y;x,y;x,y;...
    # enemy_moves:1;-1;-1;1;...
    # player_bullets:x,y;x,y;x,y;...
    # enemy_bullets:x,y;x,y;x,y;...
    # score:n
    estado_guardado = ""

    estado_guardado += f'player:{state["player"].position()[0]},{state["player"].position()[1]}'

    estado_guardado += "\nenemies:"
    for enemy in state["enemies"]:
        estado_guardado += f'{enemy.position()[0]},{enemy.position()[1]};'

    estado_guardado += "\nenemy_moves:"
    for enemy_move in state["enemy_moves"]:
        estado_guardado += f'{enemy_move};'

    estado_guardado += "\nplayer_bullets:"
    for bullet in state["player_bullets"]:
        estado_guardado += f'{bullet.position()[0]},{bullet.position()[1]};'

    estado_guardado += "\nenemy_bullets:"
    for bullet in state["enemy_bullets"]:
        estado_guardado += f'{bullet.position()[0]},{bullet.position()[1]};'

    estado_guardado += f'\nscore:{state["score"]}'

    with open(filename, "w") as f:
        f.write(estado_guardado)

def carregar_estado_txt(filename):
    try:
        estado_carregado = {
                "player": [],
                "enemies": [],
                "enemy_moves": [],
                "player_bullets": [],
                "enemy_bullets": [],
                "score": []
                }

        with open(filename, "r") as f:
            linhas = f.readlines()

            for l in range(len(linhas)):
                linha = linhas[l].replace("\n", "")
                chave = linha[:linha.index(":")]
                valor = linha[linha.index(":")+1:].split(";")
                
                if valor[-1] == '':
                    valor.pop()

                estado_carregado[chave] = valor

        return estado_carregado

    except FileNotFoundError:
        return None

# =========================
# Criação de entidades (jogador, inimigo e balas)
# =========================
def criar_entidade(x,y, tipo="enemy"):
    t = turtle.Turtle(visible=False)
    if tipo == "player":
        t.shape("player.gif")
    else:
        t.shape("enemy.gif")

    t.penup()
    t.goto(x, y)
    t.showturtle()
    return t 

def criar_bala(x, y, tipo):
    t = turtle.Turtle(visible=False)
    if tipo == "player":
        t.fillcolor("YELLOW")
    else:
        t.fillcolor("RED")

    t.penup()
    t.goto(x, y)
    t.begin_fill()
    t.shapesize(stretch_wid=0.5, stretch_len=0.2)
    t.shape("square")
    t.end_fill()
    t.showturtle()
    return t

def spawn_inimigos_em_grelha(state, posicoes_existentes, dirs_existentes=None):
    if posicoes_existentes == None:
        for i in range(ENEMY_ROWS):
            for j in range(ENEMY_COLS):
                state["enemies"].append(criar_entidade(-BORDA_X+j*ENEMY_SPACING_X, ENEMY_START_Y-ENEMY_SPACING_Y*i, "enemy"))
    else:
        for pos in posicoes_existentes:
            ent = criar_entidade(float(pos.split(",")[0]), float(pos.split(",")[1]), "enemy")

            state["enemies"].append(ent)

def restaurar_balas(state, lista_pos, tipo):
    for p in lista_pos:
        pos = p.split(",")

        state[f"{tipo}_bullets"].append(criar_bala(float(pos[0]), float(pos[1]), tipo))

# =========================
# Handlers de tecla 
# =========================
def mover_esquerda_handler():
    global STATE

    if STATE == None:
        return 

    if STATE["player"].position()[0] > -BORDA_X:
        STATE["player"].goto(STATE["player"].position()[0] - PLAYER_SPEED, -300)

def mover_direita_handler():
    global STATE

    if STATE == None:
        return

    if STATE["player"].position()[0] < BORDA_X:
        STATE["player"].goto(STATE["player"].position()[0]+PLAYER_SPEED, -300)

def disparar_handler():
    global STATE

    if STATE == None:
        return

    STATE["player_bullets"].append(criar_bala(STATE["player"].position()[0], STATE["player"].position()[1]+PLAYER_BULLET_SPEED, "player"))

def gravar_handler():
    global STATE

    if STATE == None:
        return

    guardar_estado_txt(STATE["files"]["save"], STATE)

# ADICIONADO: ECRÃ DE FIM DE JOGO; (funcionalidade) REINICIAR JOGO
def terminar_handler():
    global STATE
    global REINICIAR

    if STATE == None:
        return

    t = turtle.Turtle(visible=False)

    t.penup()
    t.goto(0,0)
    t.color("WHITE")
    t.pendown()

    t.write(f'SCORE: {STATE["score"]}', align="center", font=("Arial", 24, "bold"))
    t.penup()
    t.goto(0, -30)

    if len(STATE["enemies"]) == 0:
        t.color("YELLOW")
        t.pendown()
        t.write("VITÓRIA", align="center", font=("Arial", 15, "bold"))
    else:
        t.color("RED")
        t.pendown()
        t.write("DERROTA", align="center", font=("Arial", 15, "bold"))

    atualizar_highscores(HIGHSCORES_FILE, STATE["score"])
    nomes, scores = ler_highscores(HIGHSCORES_FILE)

    print("\n================\n|| HIGHSCORES ||\n================")
    for i, (n, s) in enumerate(zip(nomes, scores), start=1):
        print(f"{i}. {n}: {s}")
    print("================\n")

    reiniciar_inp = input("Recomeçar jogo [S/N]: ")
    if reiniciar_inp.lower() == "n":
        STATE["screen"].bye()
        os._exit(0)
    
    STATE["screen"].clear()
    REINICIAR = True

# =========================
# Atualizações e colisões
# =========================
def atualizar_balas_player(state):
    for bullet in state["player_bullets"]:
        bullet.goto(bullet.position()[0], bullet.position()[1]+PLAYER_BULLET_SPEED)

        if bullet.position()[1] >= BORDA_Y:
            bullet.hideturtle()
            state["player_bullets"].remove(bullet)

def atualizar_balas_inimigos(state):
    for bullet in state["enemy_bullets"]:
        bullet.goto(bullet.position()[0], bullet.position()[1]-ENEMY_BULLET_SPEED)

        if bullet.position()[1] <= -BORDA_Y:
            bullet.hideturtle()
            state["enemy_bullets"].remove(bullet)

def atualizar_inimigos(state):
    # direcao = -1

    for enemy in state["enemies"]:
        i = state["enemies"].index(enemy)

        if len(state["enemy_moves"]) < (i+1):
            direcao = -1
        else:
            direcao = state["enemy_moves"][i]

        enemy.goto(enemy.position()[0], enemy.position()[1]-ENEMY_FALL_SPEED)

        drift_random = random.random()
        invert_random = random.random()
        limite_X = BORDA_X+ENEMY_DRIFT_STEP

        if invert_random <= ENEMY_INVERT_CHANCE:
            direcao *= -1

        if drift_random <= ENEMY_DRIFT_CHANCE:
            if (enemy.position()[0] <= -limite_X and direcao == -1) or (enemy.position()[0] >= limite_X and direcao == 1):
                direcao *= -1
            else:
                enemy.goto(enemy.position()[0] + direcao*ENEMY_DRIFT_STEP, enemy.position()[1])

        if len(state["enemy_moves"]) < (i+1):
            state["enemy_moves"].append(direcao)
        else:
            state["enemy_moves"][i] = direcao

def inimigos_disparam(state):
    for enemy in state["enemies"]:
        disparam_random = random.random()

        if disparam_random <= ENEMY_FIRE_PROB:
            state["enemy_bullets"].append(criar_bala(enemy.position()[0], enemy.position()[1]-10, "enemy"))

def verificar_colisoes_player_bullets(state):
    for bullet in state["player_bullets"]:
        for enemy in state["enemies"]:
            distancia_bala_inimigo_Y = enemy.position()[1] - ENEMY_SIZE/2 - bullet.position()[1]
            distancia_bala_inimigo_X = abs(enemy.position()[0] - bullet.position()[0])

            if (distancia_bala_inimigo_Y <= COLLISION_RADIUS) and (distancia_bala_inimigo_X <= ENEMY_SIZE/2):
                bullet.hideturtle()
                state["player_bullets"].remove(bullet)
                enemy.hideturtle()
                state["enemy_moves"].remove(state["enemy_moves"][state["enemies"].index(enemy)]) #ALTERADO
                state["enemies"].remove(enemy)

                # AUMENTAR SCORE
                state["score"] += 1
                atualizar_score(0, 310, score_t, state["score"])
                break

def verificar_colisoes_enemy_bullets(state):
    for bullet in state["enemy_bullets"]:
        distancia_bala_player_Y = abs(bullet.position()[1] - state["player"].position()[1])
        distancia_bala_player_X = abs(state["player"].position()[0] - bullet.position()[0])

        if (distancia_bala_player_Y <= COLLISION_RADIUS) and (distancia_bala_player_X <= 4):
            state["player"].hideturtle()

            # PERDEU
            return True

def inimigo_chegou_ao_fundo(state):
    for enemy in state["enemies"]:
        if enemy.position()[1] <= -BORDA_Y:
            enemy.hideturtle()
            state["enemies"].remove(enemy)

            # PERDEU
            return True

def verificar_colisao_player_com_inimigos(state):
    for enemy in state["enemies"]:
        distancia_player_inimigo_Y = enemy.position()[1] - state["player"].position()[1]
        distancia_player_inimigo_X = abs(state["player"].position()[0] - enemy.position()[0])

        if (distancia_player_inimigo_Y <= (COLLISION_RADIUS)) and (distancia_player_inimigo_X <= ENEMY_SIZE/2):
            state["player"].hideturtle()
            enemy.hideturtle()

            # PERDEU
            return True

# =========================
# Execução principal
# =========================
if __name__ == "__main__":
    while True:
        REINICIAR = False

        # Pergunta inicial: carregar?
        filename = input("Carregar jogo? Se sim, escreva nome do ficheiro, senão carregue Return: ").strip()
        loaded = carregar_estado_txt(filename)

        # Ecrã
        screen = turtle.Screen()
        screen.title("Space Invaders IPRP")
        screen.bgcolor("black")
        screen.setup(width=LARGURA, height=ALTURA)
        screen.tracer(0)

        # Imagens obrigatórias
        for img in ["player.gif", "enemy.gif"]:
            if not os.path.exists(img):
                print("ERRO: imagem '" + img + "' não encontrada.")
                sys.exit(1)
            screen.addshape(img)

        # Estado base
        state = {
                "screen": screen,
                "player": None,
                "enemies": [],
                "enemy_moves": [],          
                "player_bullets": [],
                "enemy_bullets": [],
                "score": 0,
                "frame": 0,
                "files": {"highscores": HIGHSCORES_FILE, "save": SAVE_FILE},
                }

        # Construção inicial
        if loaded == None and len(filename) != 0:
            print("FileNotFoundError: ficheiro '" + filename + "' não encontrado.")
            sys.exit(1)
        elif loaded:
            print("Loaded game!")
            time.sleep(2.5)

            player_pos = loaded["player"][0].split(",")
            state["player"] = criar_entidade(int(player_pos[0]), int(player_pos[1]), "player")
            spawn_inimigos_em_grelha(state, loaded["enemies"], None)
            restaurar_balas(state, loaded["player_bullets"], "player")
            restaurar_balas(state, loaded["enemy_bullets"], "enemy")
            state["enemy_moves"] = [int(enemy_move) for enemy_move in loaded["enemy_moves"]]
            state["score"] = int(loaded["score"][0])

            score_t = turtle.Turtle(visible=False)
            atualizar_score(0, 310, score_t, state["score"])
        else:
            print("New game!")
            state["player"] = criar_entidade(0, -300, "player")
            spawn_inimigos_em_grelha(state, None, None)

            score_t = turtle.Turtle(visible=False)
            atualizar_score(0, 310, score_t, 0)

        # Variavel global para os keyboard key handlers
        STATE = state

        # Teclas
        screen.listen()
        screen.onkeypress(mover_esquerda_handler, "Left")
        screen.onkeypress(mover_direita_handler, "Right")
        screen.onkeypress(disparar_handler, "space")
        screen.onkeypress(gravar_handler, "g")
        screen.onkeypress(terminar_handler, "Escape")

        # Loop principal
        while not REINICIAR:
            atualizar_balas_player(STATE)
            atualizar_inimigos(STATE)
            inimigos_disparam(STATE)
            atualizar_balas_inimigos(STATE)
            verificar_colisoes_player_bullets(STATE)

            if verificar_colisao_player_com_inimigos(STATE):
                print("Colisão direta com inimigo! Game Over")
                terminar_handler()
                break

            if verificar_colisoes_enemy_bullets(STATE):
                print("Atingido por inimigo! Game Over")
                terminar_handler()
                break

            if inimigo_chegou_ao_fundo(STATE):
                print("Um inimigo chegou ao fundo! Game Over")
                terminar_handler()
                break

            if len(STATE["enemies"]) == 0:
                print("Vitória! Todos os inimigos foram destruídos.")
                terminar_handler()
                break

            STATE["frame"] += 1
            screen.update()
            time.sleep(0.016)
