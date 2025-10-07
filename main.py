import sys
import pygame
from util import set_window_icon_title
from game import main_menu, run_demo_level

WINDOW_W, WINDOW_H = 1280, 720
VERSION = ""  # لا نعرض أي إصدار

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    set_window_icon_title("Zombie Shooter")
    clock = pygame.time.Clock()

    while True:
        act = main_menu(screen, clock, VERSION)  
        if act is None:
            break
        if act == "start":
            back = run_demo_level(screen, clock, version=VERSION)  
            if back is None:
                break  # window closed -> exit

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
