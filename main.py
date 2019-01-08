import os
import subprocess
from time import sleep, time
import threading
from sys import argv

import ruamel.yaml
import contextlib
with contextlib.redirect_stdout(None):  # removes terminal output
    import pygame
    from pygame.locals import *

color_theme = ["#0e2431", "#fc3a52", "#f9b248", "#e8d5b7"]
# color_theme = ["#2a363b", "#e84a5f", "#ff847c", "#fecea8"]
# color_theme = ["#0f1021", "#d01257", "#fb90b7", "#ffcee4"]
# color_theme = ["#2c2d34", "#e94822", "#f2910a", "#efd510"]

yaml = ruamel.yaml.YAML()

with open("settings.yaml", "r") as f:
    settings = yaml.load(f)

if len(argv) == 2:
    file_path = argv[1]
elif "file_path" in list(settings) and settings["file_path"]:
    file_path = settings["file_path"]

else:
    import glob
    files = glob.glob("*.yaml") + glob.glob("*.yml")
    possible_files = [f for f in files if f != "settings.yaml"]
    if len(possible_files) == 1:
        file_path = possible_files[0]


SCALE = settings["scale"]
REST = settings["rest_time"]

SCREEN = (int(800 * SCALE), int(450 * SCALE))
EPS = .3
LINE = SCALE * 50
REST -= .001
LEFT_MARGIN = 50 * SCALE

FONT = "ProstoOne-Regular.ttf"

BACKGROUND = pygame.Color(color_theme[0])
GENERAL = pygame.Color(color_theme[1])
MAIN_INFO = pygame.Color(color_theme[2])
ATTENTION = pygame.Color(color_theme[3])


def get(key, dct):
    try:
        value = dct[key]
        if key == "time":
            value = str(value)
            if ":" in value:
                value = value.split(":")
                value = int(value[0]) * 60 + int(value[1])
            else:
                value = int(value) * 60

        return value

    except KeyError:
        if key == "bpm":
            return 60
        elif key == "rate":
            return 0
        elif key == "time":
            return 5
        elif key == "bar":
            return 4
        else:
            raise KeyError("Key '%s' does not exist" % key)


MARGIN = 150
NORMAL_LINES = 4
LARGE_LINES = 1


class Prac(object):
    def __init__(self, plan=None):
        if plan is None:
            with open(file_path, "r") as f:
                self.plan = yaml.load(f)
            self.save = True
        else:
            self.plan = plan
            self.save = False
            # REST = 2 # TODO: fix
            self.update_screen = self.minimal_update_screen

        self.time_left_lock = threading.Lock()
        self.set_time_left(REST)

        pygame.init()
        pygame.key.set_repeat(500, 100)
        self.icon_surface = pygame.image.load('icon_64.png')
        pygame.display.set_icon(self.icon_surface)
        pygame.display.set_caption('Woodpecker')
        self.font = pygame.font.Font(FONT, int(48 * SCALE))
        self.large_font = pygame.font.Font(FONT, int(64 * SCALE))
        self.spacing = self.font.size("|")[1], self.large_font.size("|")[1]

        maximum_width = 0
        for p in self.plan:
            maximum_width = max(maximum_width, self.font.size(p)[0])
        # TODO: make it smarter, for short practice names
        maximum_width = max(maximum_width, 800)

        height = NORMAL_LINES * self.spacing[0] + \
            LARGE_LINES * self.spacing[1] + \
            MARGIN * SCALE
        height = int(height)
        width = maximum_width + MARGIN * SCALE
        width = int(width)
        self.screen = pygame.display.set_mode((width, height))

        self.number_of_practices = len(self.plan)

        self.running = True
        self.paused = False
        self.count_down = False
        self.practice_name = "Loading ..."
        self.bpm = 0
        self.skipped = False
        self.FNULL = open(os.devnull, 'w')
        self.terminated_metronome = False
        self.prac_index = 0
        self.volume = 100

        self.update_practice()
        self.face()

        while self.running:

            self.start_practice()
            if not self.running:
                break

            if self.skipped:
                self.skipped = False
            else:
                subprocess.call(['paplay', '--volume=%i' % self._volume, 'end.ogg'],
                                stdout=self.FNULL, stderr=subprocess.STDOUT)
                if self.bpm > 0:
                    rate = get("rate", self.plan[self.practice_name])
                    duration = get("time", self.plan[self.practice_name])
                    increment_value = rate * duration / 60.
                    self.plan[self.practice_name]["bpm"] += increment_value
                self.update_practice(1)
                if self.prac_index == 0:
                    self.paused = True

        self.terminated_metronome = True
        self.face_thrd.join()

    @property
    def volume(self):
        return self.volume_percent

    @volume.setter
    def volume(self, value):
        self.volume_percent = min(max(0, value), 100)
        self._volume = min(int(655 * self.volume_percent), 65536)

    def set_time_left(self, value):
        with self.time_left_lock:
            self.time_left = value

    def update_practice(self, step=0):
        self.prac_index = (self.prac_index + step) % self.number_of_practices
        self.practice_name = list(self.plan)[self.prac_index]
        bpm = int(get("bpm", self.plan[self.practice_name]))
        self.update_bpm(bpm)
        total_time = 0
        for p in list(self.plan)[self.prac_index + 1:]:
            total_time += self.plan[p]["time"]
        total_time *= 60
        self.total_time = [total_time // 60, total_time % 60]

    def update_plan_file(self):
        with open(file_path, "w") as f:
            yaml.dump(self.plan, f)

    def _clean_bpm(self, value):
        return max(0, value)

    def update_bpm(self, value):
        self.bpm = self._clean_bpm(value)
        self.plan[self.practice_name]["bpm"] = self.bpm
        if self.bpm > 0:
            self.lapse = 60.0 / self.bpm
            self.lapse_2 = min(self.lapse, EPS)
            self.lapse_1 = self.lapse - self.lapse_2
            self.sleep_time = min(1, max(0, self.lapse - EPS))
            self.next_click_time = time() + .2
        else:
            self.sleep_time = 1

    def start_practice(self):
        self.count_down = True
        self.set_time_left(REST)
        while not self.skipped and self.time_left > 0:
            sleep(.1)

        if self.skipped or not self.running:
            return

        self.count_down = False

        self.set_time_left(get("time", self.plan[self.practice_name]))
        self.next_click_time = time()

        while not self.skipped and self.time_left > 0:
            self.next_click_time += self.lapse_1
            while time() < self.next_click_time:
                sleep(.01)
            self.next_click_time += self.lapse_2
            # sleep(self.sleep_time)  # TODO: maybe put this in a loop
            if not self.paused and self.bpm:
                while time() < self.next_click_time:
                    pass
                subprocess.call(['paplay', '--volume=%i' % self._volume, 'tic.ogg'],
                                stdout=self.FNULL, stderr=subprocess.STDOUT)
                # print(time())

    def update_screen(self):
        self.screen.fill(BACKGROUND)

        minutes = self.time_left // 60
        seconds = self.time_left % 60

        line = LINE * .5
        text = self.font.render(self.practice_name, 1, GENERAL)
        self.screen.blit(text, (LEFT_MARGIN, line))

        line += self.spacing[0]
        text = self.font.render("Tempo: %i" % self.bpm, 1, GENERAL)
        self.screen.blit(text, (LEFT_MARGIN, line))

        line += self.spacing[0]
        if self.count_down:
            text = self.large_font.render("Starting in %i" % (self.time_left + 1),
                                          1, MAIN_INFO)
        else:
            text = self.large_font.render("%i:%02i" % (minutes, seconds),
                                          1, MAIN_INFO)
        self.screen.blit(text, (LEFT_MARGIN, line))

        line += self.spacing[1]
        if self.paused:
            text = self.font.render("Paused!", 1, ATTENTION)
            self.screen.blit(text, (LEFT_MARGIN, line))

        line += self.spacing[0] * 2
        text = self.font.render("Remaining: %i:%02i" % (self.total_time[0], self.total_time[1]),
                                1, GENERAL)
        self.screen.blit(text, (LEFT_MARGIN, line))

        pygame.display.update()

    def minimal_update_screen(self):
        self.screen.fill(BACKGROUND)

        line = LINE * .5
        text = self.font.render(self.practice_name, 1, GENERAL)
        self.screen.blit(text, (LEFT_MARGIN, line))

        line += self.spacing[0] * 2
        text = self.font.render("Tempo: %i" % self.bpm, 1, MAIN_INFO)
        self.screen.blit(text, (LEFT_MARGIN, line))

        line += self.spacing[0] * 2
        if self.paused:
            text = self.font.render("Paused!", 1, ATTENTION)
            self.screen.blit(text, (LEFT_MARGIN, line))

        pygame.display.update()

    def close(self):
        self.running = False
        self.paused = True
        self.next_click_time = time()
        self.set_time_left(0)
        while not self.terminated_metronome:
            sleep(.05)
        if self.save:
            self.update_plan_file()
        pygame.quit()

    def face(self):
        self.face_thrd = threading.Thread(target=self._face)
        self.face_thrd.daemon = True
        self.face_thrd.start()

    def _face(self):
        running = True
        prev_time = time()
        while running:
            if not self.paused:
                self.set_time_left(
                    max(0, self.time_left - (time() - prev_time)))
            prev_time = time()
            self.update_screen()
            sleep(.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        running = False
                    elif event.key == K_UP:
                        if pygame.key.get_mods() & KMOD_CTRL:
                            self.update_bpm(self.bpm + 5)
                        else:
                            self.update_bpm(self.bpm + 1)
                    elif event.key == K_DOWN:
                        if pygame.key.get_mods() & KMOD_CTRL:
                            self.update_bpm(self.bpm - 5)
                        else:
                            self.update_bpm(self.bpm - 1)
                    elif event.key == K_RIGHT:
                        self.skipped = True
                        self.update_practice(1)
                    elif event.key == K_LEFT:
                        self.skipped = True
                        self.update_practice(-1)
                    elif event.key == K_SPACE:
                        if not self.paused:
                            self.paused = True
                        else:
                            self.paused = False
                    elif event.key == K_EQUALS:
                        self.volume = self.volume + 5
                    elif event.key == K_MINUS:
                        self.volume = self.volume - 5

        self.close()


if len(argv) > 1:
    if argv[1] == "dry":
        Prac({"Dry Practice": {"time": 60}})
else:
    Prac()
