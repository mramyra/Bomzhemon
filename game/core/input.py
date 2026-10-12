import pygame

KEYMAP = {
    pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down",
    pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right",
    pygame.K_z: "ok", pygame.K_RETURN: "ok", pygame.K_SPACE: "ok",
    pygame.K_x: "back", pygame.K_BACKSPACE: "back", pygame.K_ESCAPE: "back",
}
DIRS = ("up", "down", "left", "right")


def key_action(event):
    """-> (action, is_down) или (None, False). Esc/Enter в мире ещё и открывают меню (см. WorldScene)."""
    if event.type in (pygame.KEYDOWN, pygame.KEYUP):
        return KEYMAP.get(event.key), event.type == pygame.KEYDOWN
    return None, False
