import sys
import pygame
from util import set_window_icon_title
from game import main_menu, run_game

WINDOW_W, WINDOW_H = 1280, 720
VERSION = ""  # لا نعرض إصدار

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    set_window_icon_title("Zombie Shooter")
    clock = pygame.time.Clock()
    if not pygame.mixer.get_init(): pygame.mixer.init()

    while True:
        act = main_menu(screen, clock, VERSION)
        if act is None:
            break
        if act == "start":
            back = run_game(screen, clock, version=VERSION)
            if back is None:
                break

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()