import pygame
import sys
import random
import array
import os

# ---- RUTA BASE (funciona en Python normal y empaquetado con PyInstaller) ----
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(os.path.join(BASE_DIR, "assets"))

pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
pygame.init()

# ---- CONFIGURACIÓN DE PANTALLA (debe ir antes de cargar imágenes) ----
WIDTH, HEIGHT = 1200, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("UmaRacing")
clock = pygame.time.Clock()
fullscreen = True

def toggle_fullscreen():
    global screen, fullscreen
    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

# ---- SONIDO SINTÉTICO (pop de navegación) ----
def make_pop(volume=0.35):
    sample_rate = 44100
    n = int(sample_rate * 0.06)
    samples = array.array('h', [0] * (n * 2))  # estéreo: 2 canales
    for i in range(n):
        fade = max(0.0, 1.0 - i / n) ** 2
        val = int(volume * fade * 32767 * (random.random() * 2 - 1))
        val = max(-32768, min(32767, val))
        samples[i * 2]     = val
        samples[i * 2 + 1] = val
    return pygame.sndarray.make_sound(samples)

def load_sound(filename):
    try:
        return pygame.mixer.Sound(filename)
    except Exception as e:
        print(f"No se pudo cargar {filename}: {e}")
        return None

# Todos los audios como Sound (music.load no soporta estos MP3)
snd_elegir    = load_sound("Elegir.mp3")
snd_seleccion = load_sound("Seleccionar.mp3")
snd_321       = load_sound("321.mp3")
snd_menu      = load_sound("MenuSong.mp3")
snd_carrera1  = load_sound("Carrera1.mp3")
snd_carrera2  = load_sound("Carrera2.mp3")
snd_c1final   = load_sound("Carrera1Final.mp3")
snd_c2final   = load_sound("Carrera2Final.mp3")

# Volúmenes
if snd_elegir:    snd_elegir.set_volume(0.50)
if snd_seleccion: snd_seleccion.set_volume(0.50)
if snd_321:       snd_321.set_volume(0.20)
if snd_menu:      snd_menu.set_volume(1.0)

try:
    snd_pop = make_pop()
except Exception:
    snd_pop = None

current_carrera = None  # rastrea cuál tema de carrera está sonando


# Fuente estilo pixel art (Press Start 2P si está disponible, si no fallback a monospace)
def load_pixel_font(size):
    try:
        return pygame.font.SysFont("Press Start 2P", size)
    except:
        pass
    for name in ["Courier New", "Lucida Console", "monospace", "couriernew"]:
        try:
            f = pygame.font.SysFont(name, size)
            return f
        except:
            pass
    return pygame.font.SysFont(None, size)

font_big   = load_pixel_font(52)
font_med   = load_pixel_font(26)
font_small = load_pixel_font(16)
font_tiny  = load_pixel_font(13)

# ---- PALETA DE COLORES (temática naturaleza/montaña) ----
COL_SKY        = (135, 196, 224)
COL_GRASS      = ( 72, 140,  73)
COL_DARK_GREEN = ( 34,  85,  34)
COL_GOLD       = (220, 175,  50)
COL_CREAM      = (245, 235, 200)
COL_BROWN      = (110,  70,  30)
COL_LAKE       = ( 60, 130, 180)
COL_WHITE      = (255, 255, 255)
COL_BLACK      = (  0,   0,   0)
COL_P1         = ( 80, 200, 100)
COL_P2         = ( 80, 140, 220)
COL_P1_DARK    = ( 30, 120,  50)
COL_P2_DARK    = ( 20,  70, 150)
COL_SHADOW     = (  0,   0,   0, 120)

# ---- IMÁGENES ESTÁTICAS ----
background = pygame.image.load("escenario/fondo.png").convert()
bg_target_height = HEIGHT - 175
scale    = bg_target_height / background.get_height()
bg_width = int(background.get_width() * scale)
background = pygame.transform.scale(background, (bg_width, bg_target_height))

# ---- NUEVAS IMÁGENES ----
fondo_selection = pygame.transform.scale(pygame.image.load("menu/FondoSelection.png").convert(), (WIDTH, HEIGHT))

# Banners de selección: SelectionMS y Controls (mismo tamaño, se alternan con crossfade)
_sel_ms_raw      = pygame.image.load("menu/SelectionMS.png").convert_alpha()
selection_ms_img = pygame.transform.scale(_sel_ms_raw, (600, 120))

_controls_raw = pygame.image.load("menu/Controls.png").convert_alpha()
controls_img  = pygame.transform.scale(_controls_raw, (600, 120))

# P1Win / P2Win: 2000x933 → escalar a 700x327 (aparece arriba sin tapar la pista)
_p1win_raw = pygame.image.load("menu/P1Win.png").convert_alpha()
_p2win_raw = pygame.image.load("menu/P2Win.png").convert_alpha()
p1win_img  = pygame.transform.scale(_p1win_raw, (700, 327))
p2win_img  = pygame.transform.scale(_p2win_raw, (700, 327))

# Botones: proporciones originales, tamaño razonable para el menú
_correr_raw      = pygame.image.load("menu/CorrerButton.png").convert_alpha()
_personajes_raw  = pygame.image.load("menu/PersonajesButton.png").convert_alpha()
correr_button_img     = pygame.transform.scale(_correr_raw,     (220, 118))
personajes_button_img = pygame.transform.scale(_personajes_raw, (220, 126))

moving_img  = pygame.transform.scale(pygame.image.load("escenario/umas/calle.png").convert_alpha(),  (1200, 200))
moving_img2 = pygame.transform.scale(pygame.image.load("escenario/umas/calle2.png").convert_alpha(), (1200, 200))
img_width   = 1200
my          = HEIGHT - 200

meta_img = pygame.transform.scale(pygame.image.load("escenario/meta.png").convert_alpha(), (175, 250))
META_Y   = 400

SPRITE_SIZE = (int(125 * 1.2), int(150 * 1.2))

# ---- CARGAR SPRITES ----
def cargar_sprites(carpeta, prefijo, run_n, static_n, cry_n, win_n):
    def load(name):
        return pygame.transform.scale(
            pygame.image.load(f"corredoras/{carpeta}/{name}").convert_alpha(), SPRITE_SIZE)
    run    = [load(f"{prefijo}Run{i}.png")    for i in range(1, run_n    + 1)]
    static = [load(f"{prefijo}Static{i}.png") for i in range(1, static_n + 1)]
    cry    = [load(f"{prefijo}Cry{i}.png")    for i in range(1, cry_n    + 1)]
    win    = [load(f"{prefijo}Win{i}.png")    for i in range(1, win_n    + 1)]
    return run, static, cry, win

run_gold,   static_gold,   cry_gold,   win_gold   = cargar_sprites("goldship",     "Gold",   6, 3, 4, 7)
run_oguri,  static_oguri,  cry_oguri,  win_oguri  = cargar_sprites("oguricap",     "Oguri",  6, 3, 5, 3)
run_condor, static_condor, cry_condor, win_condor = cargar_sprites("elcondorpasa", "Condor", 6, 3, 4, 3)
run_jungle, static_jungle, cry_jungle, win_jungle = cargar_sprites("junglepocket", "Jungle", 6, 3, 6, 3)

# Imágenes de selección: originales 1273x2000 (portrait), escalar a 170x268
SELECT_IMG_SIZE = (170, 268)
CHAR_DATA = [
    {"name": "Gold Ship",  "img": pygame.transform.scale(pygame.image.load("menu/GoldSelect.png").convert_alpha(),   SELECT_IMG_SIZE),
     "sprites": (run_gold,   static_gold,   cry_gold,   win_gold)},
    {"name": "Oguri Cap",  "img": pygame.transform.scale(pygame.image.load("menu/OguriSelect.png").convert_alpha(),  SELECT_IMG_SIZE),
     "sprites": (run_oguri,  static_oguri,  cry_oguri,  win_oguri)},
    {"name": "Condor",     "img": pygame.transform.scale(pygame.image.load("menu/CondorSelect.png").convert_alpha(), SELECT_IMG_SIZE),
     "sprites": (run_condor, static_condor, cry_condor, win_condor)},
    {"name": "Jungle",     "img": pygame.transform.scale(pygame.image.load("menu/JungleSelect.png").convert_alpha(), SELECT_IMG_SIZE),
     "sprites": (run_jungle, static_jungle, cry_jungle, win_jungle)},
]

# Índices de personajes en CHAR_DATA
IDX_GOLD   = 0
IDX_OGURI  = 1
IDX_CONDOR = 2
IDX_JUNGLE = 3

# ---- FLECHAS QUE APUNTAN HACIA ABAJO (para pantalla de selección) ----
def make_down_arrow(color, size=36):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(surf, color, [(0, 0), (size, 0), (size // 2, size)])
    pygame.draw.polygon(surf, COL_BLACK, [(0, 0), (size, 0), (size // 2, size)], 2)
    return surf

arrow_p1 = make_down_arrow(COL_P1)
arrow_p2 = make_down_arrow(COL_P2)

# ---- CARGAR SPRITES DE NPCs ----
TWIN_SIZE      = (int(125 * 1.35), int(150 * 1.35))
NPC_SIZE       = (int(125 * 1.28), int(150 * 1.28))
AGNES_SIZE     = (int(125 * 1.28), int(150 * 1.28))

def cargar_npc(prefijo, cantidad, size=None):
    if size is None:
        size = NPC_SIZE
    frames = []
    for i in range(1, cantidad + 1):
        img = pygame.image.load(f"escenario/umas/{prefijo}{i}.png").convert_alpha()
        img = pygame.transform.scale(img, size)
        frames.append(img)
    return frames

twin_frames     = cargar_npc("Twin",     6, size=TWIN_SIZE)
matikane_frames = cargar_npc("Matikane", 6)
agnes_frames    = cargar_npc("Agnes",    4, size=AGNES_SIZE)
haru_frames     = cargar_npc("Haru",     6)

AGNES_Y = my - AGNES_SIZE[1] + 5

NPC_CATALOG = [
    {"nombre": "Twin",     "frames": twin_frames},
    {"nombre": "Matikane", "frames": matikane_frames},
    {"nombre": "Haru",     "frames": haru_frames, "walk_left": True},
]

PLAYER_Y_EXCLUSION = [265, 345]
EXCLUSION_MARGIN   = 45

def y_is_safe(y):
    for py in PLAYER_Y_EXCLUSION:
        if abs(y - py) < EXCLUSION_MARGIN:
            return False
    return True

NPC_Y_MAX     = HEIGHT - max(TWIN_SIZE[1], NPC_SIZE[1])
NPC_Y_OPTIONS = [my + offset for offset in range(-120, 160, 20) if my + offset <= NPC_Y_MAX]
SAFE_NPC_Y    = [y for y in NPC_Y_OPTIONS if y_is_safe(y)]
if not SAFE_NPC_Y:
    SAFE_NPC_Y = [min(my - 130, NPC_Y_MAX), min(my + 80, NPC_Y_MAX)]

HARU_WALK_SPEED = 0.8

def generar_npcs():
    pool = NPC_CATALOG.copy()
    random.shuffle(pool)
    npcs     = []
    x_actual = WIDTH + 200
    y_prev   = None
    for i, npc_def in enumerate(pool):
        if i > 0:
            x_actual += WIDTH + random.randint(200, 1400)
        y_choices = SAFE_NPC_Y.copy()
        if y_prev is not None and len(y_choices) > 1:
            y_choices = [y for y in y_choices if abs(y - y_prev) > 30]
        y = random.choice(y_choices)
        y_prev = y
        npc = {
            "x_mundo":  x_actual,
            "x":        x_actual,
            "y":        y,
            "frames":   npc_def["frames"],
            "anim_idx": 0.0,
            "walk_left": npc_def.get("walk_left", False),
        }
        npcs.append(npc)
    return npcs

# ---- HELPER: dibujar panel con bordes estilo pixel ----
def draw_pixel_panel(surface, rect, bg_color, border_color, border_w=3):
    pygame.draw.rect(surface, bg_color, rect, border_radius=0)
    pygame.draw.rect(surface, border_color, rect, border_w, border_radius=0)
    x, y, w, h = rect
    pygame.draw.rect(surface, COL_BLACK, (x, y, border_w+2, border_w+2))
    pygame.draw.rect(surface, COL_BLACK, (x+w-border_w-2, y, border_w+2, border_w+2))
    pygame.draw.rect(surface, COL_BLACK, (x, y+h-border_w-2, border_w+2, border_w+2))
    pygame.draw.rect(surface, COL_BLACK, (x+w-border_w-2, y+h-border_w-2, border_w+2, border_w+2))

# ---- HELPER: dibujar botón con imagen ----
def draw_image_button(surface, rect, img, highlighted=False):
    x, y, w, h = rect
    scaled = pygame.transform.scale(img, (w, h))
    if highlighted:
        bright = pygame.Surface((w, h), pygame.SRCALPHA)
        bright.fill((255, 255, 255, 40))
        surface.blit(scaled, (x, y))
        surface.blit(bright, (x, y))
    else:
        surface.blit(scaled, (x, y))

# ---- HELPER: dibujar botón estilo pixel art ----
def draw_button(rect, color, dark_color, label, highlighted=False):
    x, y, w, h = rect
    shadow_rect = pygame.Rect(x+4, y+4, w, h)
    pygame.draw.rect(screen, COL_BLACK, shadow_rect)
    bg = tuple(min(c + 40, 255) for c in color) if highlighted else color
    pygame.draw.rect(screen, bg, rect)
    border = COL_GOLD if highlighted else COL_CREAM
    pygame.draw.rect(screen, border, rect, 3)
    highlight_col = tuple(min(c + 60, 255) for c in bg)
    pygame.draw.line(screen, highlight_col, (x+3, y+3), (x+w-4, y+3), 2)
    pygame.draw.line(screen, highlight_col, (x+3, y+3), (x+3, y+h-4), 2)
    txt = font_tiny.render(label, True, COL_WHITE)
    if txt.get_width() > w - 10:
        tiny = load_pixel_font(11)
        txt = tiny.render(label, True, COL_WHITE)
    shadow_txt = font_tiny.render(label, True, COL_BLACK) if txt.get_width() <= w - 10 else txt
    tx = x + (w - txt.get_width()) // 2
    ty = y + (h - txt.get_height()) // 2
    screen.blit(shadow_txt, (tx+1, ty+1))
    screen.blit(txt, (tx, ty))

# ---- HELPER: texto con sombra ----
def draw_text_shadow(surface, font, text, color, x, y, shadow_col=COL_BLACK, offset=2, center=False):
    txt = font.render(text, True, color)
    shd = font.render(text, True, shadow_col)
    if center:
        x = x - txt.get_width() // 2
    surface.blit(shd, (x + offset, y + offset))
    surface.blit(txt, (x, y))

# ===============================================================
#  ESTADO GLOBAL
# ===============================================================
go_to_select = True
sel_p1, sel_p2 = 0, 1
run_p1 = static_p1 = cry_p1 = win_p1 = None
run_p2 = static_p2 = cry_p2 = win_p2 = None

# ================================================================
#  BUCLE EXTERNO
# ================================================================
while True:

    # =================== PANTALLA DE SELECCIÓN ===================
    if go_to_select:
        confirm_p1 = confirm_p2 = False
        sel_p1, sel_p2 = 0, 1
        arrow_bob    = 0.0
        blink_tick   = 0
        banner_tick  = 0        # contador para alternar banners
        banner_fade  = 0.0      # 0.0 = SelectionMS puro, 1.0 = Controls puro
        banner_show_controls = False  # cuál banner está "saliendo"

        # Música del menú de selección
        if snd_menu:
            pygame.mixer.stop()
            snd_menu.play(-1)

        CHARS_PER_PAGE = 2
        num_chars = len(CHAR_DATA)

        while not (confirm_p1 and confirm_p2):
            arrow_bob   += 0.08
            blink_tick  += 1
            banner_tick += 1
            arrow_offset = int(abs(pygame.math.Vector2(0, 6).rotate(arrow_bob * 57.3).y))

            # ---- Lógica de crossfade entre banners ----
            # Cada banner se muestra 4 seg (240 frames) y el fade dura 0.5 seg (30 frames)
            BANNER_HOLD  = 240
            BANNER_FADE  = 30
            BANNER_CYCLE = BANNER_HOLD + BANNER_FADE   # 270 frames por banner

            cycle_pos = banner_tick % (BANNER_CYCLE * 2)
            if cycle_pos < BANNER_HOLD:
                # SelectionMS visible, sin fade
                banner_show_controls = False
                banner_fade = 0.0
            elif cycle_pos < BANNER_HOLD + BANNER_FADE:
                # Fade SelectionMS → Controls
                banner_show_controls = False
                banner_fade = (cycle_pos - BANNER_HOLD) / BANNER_FADE
            elif cycle_pos < BANNER_CYCLE + BANNER_HOLD:
                # Controls visible, sin fade
                banner_show_controls = True
                banner_fade = 0.0
            else:
                # Fade Controls → SelectionMS
                banner_show_controls = True
                banner_fade = (cycle_pos - BANNER_CYCLE - BANNER_HOLD) / BANNER_FADE

            # Fondo de selección con imagen
            screen.blit(fondo_selection, (0, 0))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                    if not confirm_p1:
                        if event.key == pygame.K_a:
                            sel_p1 = (sel_p1 - 1) % num_chars
                            if snd_elegir: snd_elegir.play()
                            else:
                                if snd_pop: snd_pop.play()
                        if event.key == pygame.K_d:
                            sel_p1 = (sel_p1 + 1) % num_chars
                            if snd_elegir: snd_elegir.play()
                            else:
                                if snd_pop: snd_pop.play()
                        if event.key == pygame.K_w:
                            confirm_p1 = True
                            if snd_seleccion: snd_seleccion.play()
                    if not confirm_p2:
                        if event.key == pygame.K_LEFT:
                            sel_p2 = (sel_p2 - 1) % num_chars
                            if snd_elegir: snd_elegir.play()
                            else:
                                if snd_pop: snd_pop.play()
                        if event.key == pygame.K_RIGHT:
                            sel_p2 = (sel_p2 + 1) % num_chars
                            if snd_elegir: snd_elegir.play()
                            else:
                                if snd_pop: snd_pop.play()
                        if event.key == pygame.K_UP:
                            confirm_p2 = True
                            if snd_seleccion: snd_seleccion.play()

            # ---- Dibujar banner con crossfade ----
            ms_x = WIDTH // 2 - selection_ms_img.get_width() // 2

            if not banner_show_controls:
                img_out = selection_ms_img
                img_in  = controls_img
            else:
                img_out = controls_img
                img_in  = selection_ms_img

            alpha_out = int((1.0 - banner_fade) * 255)
            alpha_in  = int(banner_fade * 255)

            img_out_copy = img_out.copy()
            img_out_copy.set_alpha(alpha_out)
            screen.blit(img_out_copy, (ms_x, 14))

            if alpha_in > 0:
                img_in_copy = img_in.copy()
                img_in_copy.set_alpha(alpha_in)
                screen.blit(img_in_copy, (ms_x, 14))

            card_w, card_h = 200, 300
            total_cards = num_chars
            spacing = WIDTH // (total_cards + 1)

            # Tamaños de imagen: normal, hover (flecha encima), confirmado
            IMG_NORMAL  = (170, 268)
            IMG_HOVERED = (200, 315)

            # Parpadeo blanco: visible cada 8 ticks durante 4 ticks (≈ 7 Hz a 60 fps)
            blink_visible = (blink_tick % 8) < 4

            for i, ch in enumerate(CHAR_DATA):
                cx = spacing * (i + 1)
                card_y = HEIGHT // 2 - card_h // 2 - 10

                is_sel_p1  = (sel_p1 == i)
                is_sel_p2  = (sel_p2 == i)
                is_conf_p1 = (confirm_p1 and i == sel_p1)
                is_conf_p2 = (confirm_p2 and i == sel_p2)

                hovered   = (is_sel_p1 and not confirm_p1) or (is_sel_p2 and not confirm_p2)
                confirmed = is_conf_p1 or is_conf_p2

                iw, ih = IMG_HOVERED if (confirmed or hovered) else IMG_NORMAL

                scaled_img = pygame.transform.scale(ch["img"], (iw, ih))
                img_x = cx - iw // 2
                img_y = HEIGHT // 2 - ih // 2 - 10
                screen.blit(scaled_img, (img_x, img_y))

                # Parpadeo blanco semitransparente sobre la imagen al confirmar
                if confirmed and blink_visible:
                    blink_surf = pygame.Surface((iw, ih), pygame.SRCALPHA)
                    blink_surf.fill((255, 255, 255, 110))
                    screen.blit(blink_surf, (img_x, img_y))

                if confirmed:
                    conf_col = COL_P1 if is_conf_p1 else COL_P2
                    ready_surf = pygame.Surface((80, 24), pygame.SRCALPHA)
                    ready_surf.fill((*conf_col, 200))
                    screen.blit(ready_surf, (cx - 40, img_y + ih + 4))
                    draw_text_shadow(screen, font_tiny, "LISTO!", conf_col,
                                     cx, img_y + ih + 6, offset=1, center=True)

            for player_sel, arrow_img, confirmed in [
                    (sel_p1, arrow_p1, confirm_p1),
                    (sel_p2, arrow_p2, confirm_p2)]:
                if not confirmed:
                    cx = spacing * (player_sel + 1)
                    card_y = HEIGHT // 2 - card_h // 2 - 20
                    arrow_x = cx - arrow_img.get_width() // 2
                    arrow_y = card_y - arrow_img.get_height() - 6 + arrow_offset
                    screen.blit(arrow_img, (arrow_x, arrow_y))

            inst_bg = pygame.Surface((WIDTH, 52), pygame.SRCALPHA)
            inst_bg.fill((0, 0, 0, 140))
            screen.blit(inst_bg, (0, HEIGHT - 52))
            draw_text_shadow(screen, font_tiny, "J1: A/D mover  W confirmar",
                             COL_P1, WIDTH // 2 - 10, HEIGHT - 44, offset=1, center=True)
            draw_text_shadow(screen, font_tiny, "J2: FLECHAS mover  ARRIBA confirmar",
                             COL_P2, WIDTH // 2 - 10, HEIGHT - 26, offset=1, center=True)

            pygame.display.flip()
            clock.tick(60)

        run_p1, static_p1, cry_p1, win_p1 = CHAR_DATA[sel_p1]["sprites"]
        run_p2, static_p2, cry_p2, win_p2 = CHAR_DATA[sel_p2]["sprites"]
        go_to_select = False

    # ====================== VARIABLES DE CARRERA ======================
    char_p1 = sel_p1
    char_p2 = sel_p2

    bg1, bg2     = 0, bg_width
    bg_speed     = 0.05
    mx1, mx2     = 0, img_width
    track_speed  = 3
    meta_x       = WIDTH
    meta_speed   = 1.5

    anim_speed   = 0.25
    static_speed = 0.08
    cry_speed    = 0.06
    win_speed    = 0.10

    win_speed_slow      = 0.035
    win_speed_very_slow = 0.018
    GOLD_WIN_DRIFT = 0.4

    fi_p1 = random.uniform(0, len(static_p1) - 1) if static_p1 else 0.0
    fi_p2 = random.uniform(0, len(static_p2) - 1) if static_p2 else 0.0
    cry_done_p1 = cry_done_p2 = False
    cry_idx_p1  = cry_idx_p2  = 0.0
    cry_loop_f1 = [len(cry_p1) - 2, len(cry_p1) - 1]
    cry_loop_f2 = [len(cry_p2) - 2, len(cry_p2) - 1]
    cry_li_p1   = cry_li_p2   = 0.0
    win_idx_p1  = win_idx_p2  = 0.0

    win_intro_done_p1 = False
    win_intro_done_p2 = False

    x1, y1 = 175, 265
    x2, y2 = 175, 345
    sp1 = sp2 = 0
    lk1 = lk2 = None
    finish_trigger = 900
    game_over  = False
    winner     = None
    game_state = "countdown"

    npcs = generar_npcs()
    world_offset = 0

    agnes = {
        "x_mundo":  WIDTH + random.randint(800, 1600),
        "x":        0,
        "y":        AGNES_Y,
        "anim_idx": 0.0,
        "reaccionó": False,
    }
    agnes["x"] = agnes["x_mundo"]

    btn_w, btn_h = 220, 126
    btn_restart = pygame.Rect(WIDTH // 2 - btn_w - 20, HEIGHT // 2 + 10, btn_w, 118)
    btn_select  = pygame.Rect(WIDTH // 2 + 20,          HEIGHT // 2 + 10, btn_w, btn_h)
    menu_opt    = 0

    # ====================== COUNTDOWN ======================
    pygame.mixer.stop()
    if snd_321:
        snd_321.play()

    for count in ["3", "2", "1", "GO!"]:
        for _ in range(30):
            screen.blit(background, (0, 0))
            screen.blit(moving_img,  (mx1, my)); screen.blit(moving_img,  (mx2, my))
            screen.blit(meta_img,    (meta_x + 120, META_Y))
            screen.blit(moving_img2, (mx1, my)); screen.blit(moving_img2, (mx2, my))

            fi_p1 += static_speed; fi_p2 += static_speed
            if fi_p1 >= len(static_p1): fi_p1 = 0
            if fi_p2 >= len(static_p2): fi_p2 = 0
            screen.blit(static_p1[int(fi_p1)], (x1, y1))
            screen.blit(static_p2[int(fi_p2)], (x2, y2))

            ct_shd = font_big.render(count, True, (0, 0, 0))
            ct     = font_big.render(count, True, (255, 220, 0))
            cx = WIDTH // 2 - ct.get_width() // 2
            cy = HEIGHT // 2 - ct.get_height() // 2
            screen.blit(ct_shd, (cx + 4, cy + 4))
            screen.blit(ct, (cx, cy))

            pygame.display.flip()
            clock.tick(30)

    # Elegir música de carrera aleatoriamente y arrancarla
    current_carrera = random.choice([1, 2])
    carrera_snd = snd_carrera1 if current_carrera == 1 else snd_carrera2
    pygame.mixer.stop()
    if carrera_snd:
        carrera_snd.play(-1)

    fi_p1 = fi_p2 = 0.0
    game_state = "race"
    post_action = None

    # ====================== LOOP DE CARRERA ======================
    while post_action is None:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                if not game_over:
                    if   event.key == pygame.K_a     and lk1 != pygame.K_a:     sp1 += 1; lk1 = pygame.K_a
                    elif event.key == pygame.K_d     and lk1 != pygame.K_d:     sp1 += 1; lk1 = pygame.K_d
                    if   event.key == pygame.K_LEFT  and lk2 != pygame.K_LEFT:  sp2 += 1; lk2 = pygame.K_LEFT
                    elif event.key == pygame.K_RIGHT and lk2 != pygame.K_RIGHT: sp2 += 1; lk2 = pygame.K_RIGHT
                else:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        menu_opt = 0
                        if snd_elegir: snd_elegir.play()
                    if event.key in (pygame.K_RIGHT, pygame.K_d):
                        menu_opt = 1
                        if snd_elegir: snd_elegir.play()
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        if snd_seleccion: snd_seleccion.play()
                        post_action = "restart" if menu_opt == 0 else "select"

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_a, pygame.K_d):          lk1 = None
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):   lk2 = None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game_over:
                if btn_restart.collidepoint(mouse_pos):
                    if snd_seleccion: snd_seleccion.play()
                    post_action = "restart"
                if btn_select.collidepoint(mouse_pos):
                    if snd_seleccion: snd_seleccion.play()
                    post_action = "select"

        # ---- Movimiento ----
        if not game_over:
            sp1 *= 0.90; sp2 *= 0.90
            delta_track = track_speed

            x1  += sp1 * 0.4; x2 += sp2 * 0.4
            bg1 -= bg_speed; bg2 -= bg_speed
            if bg1 <= -bg_width: bg1 = bg2 + bg_width
            if bg2 <= -bg_width: bg2 = bg1 + bg_width
            mx1 -= delta_track; mx2 -= delta_track
            if mx1 <= -img_width: mx1 = mx2 + img_width
            if mx2 <= -img_width: mx2 = mx1 + img_width
            if x1 > finish_trigger or x2 > finish_trigger:
                meta_x -= meta_speed

            world_offset += delta_track

            for npc in npcs:
                if not npc.get("walk_left"):
                    npc["x"] = npc["x_mundo"] - world_offset

            agnes["x"] = agnes["x_mundo"] - world_offset

            if not agnes["reaccionó"]:
                if x1 >= agnes["x"] or x2 >= agnes["x"]:
                    agnes["reaccionó"] = True
                    agnes["anim_idx"]  = 2.0

        # Haru sigue caminando incluso después de terminar la carrera
        for npc in npcs:
            if npc.get("walk_left"):
                npc["x_mundo"] -= HARU_WALK_SPEED
                npc["x"] = npc["x_mundo"] - world_offset

        # ---- Gold retrocede lentamente en su animación de victoria ----
        if game_over and game_state == "finish":
            if winner == "Jugador 1" and char_p1 == IDX_GOLD:
                x1 -= GOLD_WIN_DRIFT
            if winner == "Jugador 2" and char_p2 == IDX_GOLD:
                x2 -= GOLD_WIN_DRIFT

        meta_right = meta_x + meta_img.get_width()
        if not game_over:
            if   x1 > meta_right: winner = "Jugador 1"; game_over = True; game_state = "finish"
            elif x2 > meta_right: winner = "Jugador 2"; game_over = True; game_state = "finish"
            if game_over:
                pygame.mixer.stop()
                final_snd = snd_c1final if current_carrera == 1 else snd_c2final
                if final_snd:
                    final_snd.play()

        # ======================================================
        # CAPAS DE DIBUJO
        # ======================================================
        screen.blit(background, (bg1, 0)); screen.blit(background, (bg2, 0))
        screen.blit(moving_img, (mx1, my)); screen.blit(moving_img, (mx2, my))
        screen.blit(meta_img, (meta_x + 120, META_Y))

        for npc in npcs:
            npc_w = npc["frames"][0].get_width()
            if -npc_w < npc["x"] < WIDTH:
                npc["anim_idx"] += 0.15
                if npc["anim_idx"] >= len(npc["frames"]):
                    npc["anim_idx"] = 0.0

        if -AGNES_SIZE[0] < agnes["x"] < WIDTH:
            if not agnes["reaccionó"]:
                agnes["anim_idx"] += 0.08
                if agnes["anim_idx"] >= 2.0:
                    agnes["anim_idx"] = 0.0
            else:
                agnes["anim_idx"] += 0.08
                if agnes["anim_idx"] >= 4.0:
                    agnes["anim_idx"] = 2.0

        def get_player1_frame():
            if game_state == "race":
                return run_p1[int(fi_p1)]
            elif winner == "Jugador 1":
                return win_p1[min(int(win_idx_p1), len(win_p1) - 1)]
            else:
                if char_p1 == IDX_JUNGLE:
                    return cry_p1[int(cry_idx_p1) % len(cry_p1)]
                else:
                    idx = int(cry_idx_p1) if not cry_done_p1 else cry_loop_f1[int(cry_li_p1) % len(cry_loop_f1)]
                    return cry_p1[idx]

        def get_player2_frame():
            if game_state == "race":
                return run_p2[int(fi_p2)]
            elif winner == "Jugador 2":
                return win_p2[min(int(win_idx_p2), len(win_p2) - 1)]
            else:
                if char_p2 == IDX_JUNGLE:
                    return cry_p2[int(cry_idx_p2) % len(cry_p2)]
                else:
                    idx = int(cry_idx_p2) if not cry_done_p2 else cry_loop_f2[int(cry_li_p2) % len(cry_loop_f2)]
                    return cry_p2[idx]

        # ---- Z-ORDER POR Y ----
        drawables_bajo  = []
        drawables_sobre = []

        drawables_bajo.append({"x": x1, "y": y1, "frame": get_player1_frame()})
        drawables_bajo.append({"x": x2, "y": y2, "frame": get_player2_frame()})

        for npc in npcs:
            npc_w = npc["frames"][0].get_width()
            if -npc_w < npc["x"] < WIDTH:
                entry = {"x": npc["x"], "y": npc["y"], "frame": npc["frames"][int(npc["anim_idx"])]}
                if npc["y"] > 375:
                    drawables_sobre.append(entry)
                else:
                    drawables_bajo.append(entry)

        if -AGNES_SIZE[0] < agnes["x"] < WIDTH:
            ag_frame_raw = agnes_frames[int(agnes["anim_idx"])]
            ag_frame = pygame.transform.flip(ag_frame_raw, True, False) if agnes["reaccionó"] else ag_frame_raw
            ag_entry = {"x": agnes["x"], "y": agnes["y"], "frame": ag_frame}
            if agnes["y"] > 375:
                drawables_sobre.append(ag_entry)
            else:
                drawables_bajo.append(ag_entry)

        drawables_bajo.sort(key=lambda e: e["y"])
        for e in drawables_bajo:
            screen.blit(e["frame"], (e["x"], e["y"]))

        screen.blit(moving_img2, (mx1, my)); screen.blit(moving_img2, (mx2, my))

        drawables_sobre.sort(key=lambda e: e["y"])
        for e in drawables_sobre:
            screen.blit(e["frame"], (e["x"], e["y"]))

        # ---- Actualizar animaciones jugadores ----
        if game_state == "race":
            fi_p1 += anim_speed; fi_p2 += anim_speed
            if fi_p1 >= len(run_p1): fi_p1 = 0
            if fi_p2 >= len(run_p2): fi_p2 = 0

        elif game_state == "finish":
            # ===== JUGADOR 1 =====
            if winner == "Jugador 1":
                if char_p1 == IDX_JUNGLE:
                    if not win_intro_done_p1:
                        win_idx_p1 += win_speed_slow
                        if win_idx_p1 >= 3.0:
                            win_idx_p1 = float(len(win_p1) - 2)
                            win_intro_done_p1 = True
                    else:
                        win_idx_p1 += win_speed_very_slow
                        if win_idx_p1 >= len(win_p1):
                            win_idx_p1 = float(len(win_p1) - 2)
                elif char_p1 == IDX_CONDOR:
                    if not win_intro_done_p1:
                        win_idx_p1 += win_speed
                        if win_idx_p1 >= len(win_p1):
                            win_idx_p1 = float(len(win_p1) - 2)
                            win_intro_done_p1 = True
                    else:
                        win_idx_p1 += win_speed_very_slow
                        if win_idx_p1 >= len(win_p1):
                            win_idx_p1 = float(len(win_p1) - 2)
                else:
                    win_idx_p1 += win_speed
                    if win_idx_p1 >= len(win_p1): win_idx_p1 = 0.0
            else:
                if char_p1 == IDX_JUNGLE:
                    cry_idx_p1 += cry_speed
                    if cry_idx_p1 >= len(cry_p1):
                        cry_idx_p1 = 0.0
                else:
                    if not cry_done_p1:
                        cry_idx_p1 += cry_speed
                        if cry_idx_p1 >= len(cry_p1):
                            cry_idx_p1 = len(cry_p1) - 1; cry_done_p1 = True; cry_li_p1 = 0.0
                    else:
                        cry_li_p1 += cry_speed

            # ===== JUGADOR 2 =====
            if winner == "Jugador 2":
                if char_p2 == IDX_JUNGLE:
                    if not win_intro_done_p2:
                        win_idx_p2 += win_speed_slow
                        if win_idx_p2 >= 3.0:
                            win_idx_p2 = float(len(win_p2) - 2)
                            win_intro_done_p2 = True
                    else:
                        win_idx_p2 += win_speed_very_slow
                        if win_idx_p2 >= len(win_p2):
                            win_idx_p2 = float(len(win_p2) - 2)
                elif char_p2 == IDX_CONDOR:
                    if not win_intro_done_p2:
                        win_idx_p2 += win_speed
                        if win_idx_p2 >= len(win_p2):
                            win_idx_p2 = float(len(win_p2) - 2)
                            win_intro_done_p2 = True
                    else:
                        win_idx_p2 += win_speed_very_slow
                        if win_idx_p2 >= len(win_p2):
                            win_idx_p2 = float(len(win_p2) - 2)
                else:
                    win_idx_p2 += win_speed
                    if win_idx_p2 >= len(win_p2): win_idx_p2 = 0.0
            else:
                if char_p2 == IDX_JUNGLE:
                    cry_idx_p2 += cry_speed
                    if cry_idx_p2 >= len(cry_p2):
                        cry_idx_p2 = 0.0
                else:
                    if not cry_done_p2:
                        cry_idx_p2 += cry_speed
                        if cry_idx_p2 >= len(cry_p2):
                            cry_idx_p2 = len(cry_p2) - 1; cry_done_p2 = True; cry_li_p2 = 0.0
                    else:
                        cry_li_p2 += cry_speed

        # ---- Menú de fin ----
        if game_over:
            win_img = p1win_img if winner == "Jugador 1" else p2win_img
            win_x = WIDTH // 2 - win_img.get_width() // 2
            screen.blit(win_img, (win_x, 8))

            hl_r = (menu_opt == 0) or btn_restart.collidepoint(mouse_pos)
            hl_s = (menu_opt == 1) or btn_select.collidepoint(mouse_pos)

            bx_r, by_r, bw_r, bh_r = btn_restart
            bx_s, by_s, bw_s, bh_s = btn_select
            SCALE_UP = 1.12

            if hl_r:
                sw = int(bw_r * SCALE_UP); sh = int(bh_r * SCALE_UP)
                img_r = pygame.transform.scale(correr_button_img, (sw, sh))
                screen.blit(img_r, (bx_r - (sw - bw_r) // 2, by_r - (sh - bh_r) // 2))
            else:
                screen.blit(correr_button_img, (bx_r, by_r))

            if hl_s:
                sw = int(bw_s * SCALE_UP); sh = int(bh_s * SCALE_UP)
                img_s = pygame.transform.scale(personajes_button_img, (sw, sh))
                screen.blit(img_s, (bx_s - (sw - bw_s) // 2, by_s - (sh - bh_s) // 2))
            else:
                screen.blit(personajes_button_img, (bx_s, by_s))

        pygame.display.flip()

    # ====================== DECISIÓN POST-CARRERA ======================
    if post_action == "restart":
        go_to_select = False
    else:
        go_to_select = True