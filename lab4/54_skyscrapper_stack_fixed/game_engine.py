import random
import pygame
from game.block import Block


class Debris:

    def __init__(self, x, y, width, height, color):
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.height = float(height)
        self.color = color
        self.vy = -2.0  # slight pop up before falling
        self.vx = random.choice([-1.5, 1.5])
        self.angle = 0.0
        self.spin = random.uniform(-6, 6)
        self.alive = True

        # Pre-render the block as a surface so we can rotate it
        self.surface = pygame.Surface(
            (max(1, int(width)), max(1, int(height))),
            pygame.SRCALPHA
        )
        pygame.draw.rect(
            self.surface, color,
            (0, 0, max(1, int(width)), max(1, int(height))),
            border_radius=4
        )
        pygame.draw.rect(
            self.surface, (245, 245, 250),
            (0, 0, max(1, int(width)), max(1, int(height))),
            width=2, border_radius=4
        )

    def update(self, screen_height):
        self.vy += 0.4  # gravity
        self.x += self.vx
        self.y += self.vy
        self.angle += self.spin

        if self.y > screen_height + 50:
            self.alive = False

    def render(self, surface):
        rotated = pygame.transform.rotate(self.surface, self.angle)
        rect = rotated.get_rect(
            center=(
                int(self.x + self.width / 2),
                int(self.y + self.height / 2)
            )
        )
        surface.blit(rotated, rect)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.block_height = 28
        self.base_width = 180

        self.font_title = pygame.font.SysFont(None, 38)
        self.font_hud = pygame.font.SysFont(None, 28)
        self.font_big = pygame.font.SysFont(None, 46)

        self.reset()

    def get_color(self, index):
        palette = [
            (230, 75, 75),   # Crimson
            (240, 140, 45),  # Orange
            (245, 210, 50),  # Gold
            (60, 195, 110),  # Green
            (50, 150, 240),  # Blue
            (165, 80, 225),  # Purple
        ]
        return palette[index % len(palette)]

    def get_sky_colors(self):
        stops = [
            (0,   (24, 27, 36),    (60, 70, 100)),
            (15,  (70, 100, 140),  (140, 180, 220)),
            (35,  (120, 170, 220), (200, 230, 250)),
            (60,  (180, 140, 180), (90, 130, 200)),
            (90,  (60, 50, 120),   (20, 20, 60)),
            (130, (10, 10, 30),    (0, 0, 10)),
        ]

        h = self.score

        if h <= stops[0][0]:
            return stops[0][1], stops[0][2]
        if h >= stops[-1][0]:
            return stops[-1][1], stops[-1][2]

        for i in range(len(stops) - 1):
            h0, bot0, top0 = stops[i]
            h1, bot1, top1 = stops[i + 1]

            if h0 <= h <= h1:
                t = (h - h0) / (h1 - h0)
                bot = tuple(
                    int(bot0[c] + (bot1[c] - bot0[c]) * t)
                    for c in range(3)
                )
                top = tuple(
                    int(top0[c] + (top1[c] - top0[c]) * t)
                    for c in range(3)
                )
                return bot, top

        return stops[-1][1], stops[-1][2]

    def draw_sky(self, screen):
        bot_color, top_color = self.get_sky_colors()

        for y in range(self.height):
            t = y / self.height
            r = int(top_color[0] + (bot_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bot_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bot_color[2] - top_color[2]) * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (self.width, y))

    def reset(self):
        self.score = 0
        self.game_over = False
        self.perfect_streak = 0
        self.perfect_flash_timer = 0
        self.debris = []

        base_x = (self.width - self.base_width) // 2
        base_y = self.height - 60
        base_block = Block(
            base_x, base_y, self.base_width,
            self.block_height, self.get_color(0), speed=0
        )
        self.stack = [base_block]

        self.spawn_active_block()

    def spawn_active_block(self):
        top_block = self.stack[-1]
        next_y = top_block.y - self.block_height - 4
        speed = min(10.0, 4.5 + (len(self.stack) * 0.35))
        color = self.get_color(len(self.stack))

        start_x = (
            25 if random.choice([True, False])
            else self.width - 25 - top_block.width
        )
        self.active_block = Block(
            start_x, next_y, top_block.width,
            self.block_height, color, speed=speed
        )

    def drop_block(self):
        if self.game_over:
            return

        top_block = self.stack[-1]
        act = self.active_block

        left = max(act.x, top_block.x)
        right = min(act.x + act.width, top_block.x + top_block.width)
        overlap = right - left

        if overlap <= 0:
            self.game_over = True
            return

        PERFECT_THRESHOLD = 4.0
        offset = abs(act.x - top_block.x)

        if offset <= PERFECT_THRESHOLD:
            new_x = top_block.x
            new_width = top_block.width
            self.perfect_streak += 1
            self.score += 3
            self.perfect_flash_timer = 45

            if self.perfect_streak >= 2:
                restored = min(self.base_width, new_width + 6)
                new_x = top_block.x - (restored - new_width) / 2
                new_width = restored

        else:
            new_x = left
            new_width = overlap
            self.perfect_streak = 0
            self.score += 1

            if act.x < top_block.x:
                cut_width = top_block.x - act.x
                if cut_width > 2:
                    self.debris.append(
                        Debris(
                            act.x, act.y, cut_width,
                            self.block_height, act.color
                        )
                    )

            if act.x + act.width > top_block.x + top_block.width:
                cut_width = (
                    act.x + act.width
                ) - (top_block.x + top_block.width)

                if cut_width > 2:
                    cut_x = top_block.x + top_block.width
                    self.debris.append(
                        Debris(
                            cut_x, act.y, cut_width,
                            self.block_height, act.color
                        )
                    )

        new_block = Block(
            new_x, act.y, new_width,
            self.block_height, act.color, speed=0
        )
        self.stack.append(new_block)

        if new_block.y < 180:
            shift_amount = self.block_height + 4
            for b in self.stack:
                b.y += shift_amount

        self.spawn_active_block()

    def handle_event(self, event):
        if self.game_over:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_r) or \
               (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                self.reset()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.drop_block()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drop_block()

    def update(self):
        if not self.game_over:
            self.active_block.update(self.width)

        if self.perfect_flash_timer > 0:
            self.perfect_flash_timer -= 1

        for d in self.debris:
            d.update(self.height)

        self.debris = [d for d in self.debris if d.alive]

    def render(self, screen):
        self.draw_sky(screen)

        title_surf = self.font_title.render(
            "Skyscraper Stack", True, (245, 245, 245)
        )
        screen.blit(
            title_surf,
            (self.width // 2 - title_surf.get_width() // 2, 16)
        )

        score_surf = self.font_hud.render(
            f"Height: {self.score}", True, (255, 220, 80)
        )
        screen.blit(
            score_surf,
            (self.width // 2 - score_surf.get_width() // 2, 54)
        )

        for b in self.stack:
            b.render(screen)

        for d in self.debris:
            d.render(screen)

        if not self.game_over:
            self.active_block.render(screen)

        if self.perfect_flash_timer > 0 and not self.game_over:
            perfect_surf = self.font_big.render(
                "PERFECT!", True, (255, 230, 80)
            )
            x = self.width // 2 - perfect_surf.get_width() // 2
            y = 95
            screen.blit(perfect_surf, (x, y))

        if self.game_over:
            overlay = pygame.Surface(
                (self.width, self.height), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 195))
            screen.blit(overlay, (0, 0))

            over_surf = self.font_big.render(
                "TOWER COLLAPSED!", True, (240, 75, 75)
            )
            screen.blit(
                over_surf,
                (
                    self.width // 2 - over_surf.get_width() // 2,
                    self.height // 2 - 40
                )
            )

            final_surf = self.font_hud.render(
                f"Final Height: {self.score}", True, (255, 255, 255)
            )
            screen.blit(
                final_surf,
                (
                    self.width // 2 - final_surf.get_width() // 2,
                    self.height // 2 + 10
                )
            )

            restart_surf = self.font_hud.render(
                "Press [Space] or [R] to Play Again",
                True, (200, 200, 200)
            )
            screen.blit(
                restart_surf,
                (
                    self.width // 2 - restart_surf.get_width() // 2,
                    self.height // 2 + 50
                )
            )