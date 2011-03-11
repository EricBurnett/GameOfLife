# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 09:17:10 2011

@author: Eric Burnett (ericburnett@gmail.com)
"""
import copy
import pygame
from pygame.locals import *  # Gives things names like K_DOWN for key presses.
import sys

class World:
    """Manages the world of cells, infinite in size.
    
    Handles drawing, iteration, and tracking various statistics about what is
    happening.
    """
    
    def __init__(self, positions):
        """Initialize the world. Positions is a list of coordinates in the world
        that should be set to true, as (x,y) tuples."""
        self._current = set(positions)
        self._last = set()
        self._iteration_count = 0
        self._min_x = 9999999
        self._max_x = -9999999
        self._min_y = 9999999
        self._max_y = -9999999
        self.UpdateBounds()
        self._center_x = 0
        self._center_y = 0
    
    def Iterate(self):
        if len(self._current) == 0:
            return
        
        self._iteration_count += 1
        self._last = copy.copy(self._current)
        candidates = self.Expand(self._current)
        self._current = set()
        for c in candidates:
            if self.ValidNext(c, self._last):
                self._current.add(c)
        self.UpdateBounds()
                
    def UpdateBounds(self):
        if len(self._current) == 0:
            return
        
        # Todo: ignore gliders in this
        min_x = min(map(lambda a: a[0], self._current))
        max_x = max(map(lambda a: a[0], self._current))
        min_y = min(map(lambda a: a[1], self._current))
        max_y = max(map(lambda a: a[1], self._current))
        self._min_x = min(self._min_x, min_x)
        self._max_x = max(self._max_x, max_x)
        self._min_y = min(self._min_y, min_y)
        self._max_y = max(self._max_y, max_y)
    
    def Expand(self, positions):
        """From a set of positions, expand to include all adjacent positions
        not included."""
        new_positions = set()
        for p in positions:
            new_positions.update(self.ExpandOne(p))
        return new_positions
        
    def ExpandOne(self, position):
        """Expand one position to the set of positions in a 3x3 grid."""
        x,y = position
        return set([(a,b) for a in (x-1,x,x+1) for b in (y-1,y,y+1)])
        
    def ValidNext(self, position, current_positions):
        """Checks if a position should be live next round."""
        neighbors = self.ExpandOne(position)
        neighbors.remove(position)
        neighbors.intersection_update(current_positions)
        
        return (len(neighbors) == 3 or 
                (len(neighbors) == 2 and position in current_positions))
                
    def Draw(self, screen_width, screen_height, screen):
        min_dimension = 50
        width = self._max_x - self._min_x + 1
        height = self._max_y - self._min_y + 1
        center_x = (self._min_x + self._max_x) // 2
        center_y = (self._min_y + self._max_y) // 2
        # Artifically expand maximums so we get less bouncing around in the
        # early game
        if width < min_dimension or height < min_dimension:
            self._min_x = min(self._min_x, center_x - min_dimension // 2)
            self._max_x = max(self._max_x, center_x + min_dimension // 2)
            self._min_y = min(self._min_y, center_y - min_dimension // 2)
            self._max_y = max(self._max_y, center_y + min_dimension // 2)
        
        pixels = min(screen_width // (width+1), screen_height // (height+1))
        
        for (x,y) in self._current:
            box = pygame.Rect((screen_width // 2 + (x - center_x)*pixels,
                               screen_height // 2 + (y - center_y)*pixels),
                              (pixels, pixels))
            screen.fill((0,0,0), box)


class Game:
    # Construct the Game object here. Called once to set up the initial data we
    # need.
    def __init__(self, size, world):
        # Width and height of the main screen.
        (self._width, self._height) = size
        self._screen = pygame.display.set_mode(size)
        # Clock for tracking things that happen over time.
        self._clock = pygame.time.Clock()
        # How many ticks left until we iterate?
        self._ticks_per_update = 15
        self._ticks_till_next = 90
        # World to iterate.
        self._world = world

    # Handle a single 'event' - like a key press, mouse click, etc.
    def ProcessEvent(self, event):
        if event.type == pygame.QUIT:
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == K_DOWN:
                self._ticks_per_update += 1
            elif event.key == K_UP:
                self._ticks_per_update = max(1, self._ticks_per_update-1)
            elif event.key == K_q and (pygame.key.get_mods() & KMOD_CTRL):
                sys.exit()

    def Draw(self):
        self._screen.fill((255,255,255))  # White
        self._world.Draw(self._width, self._height, self._screen)

    def Tick(self):
        if self._ticks_till_next:
            self._ticks_till_next -= 1
        else:
            self._world.Iterate()
            self._ticks_till_next = self._ticks_per_update

    def RunGameLoop(self):
        while True:
            # Process any pending events.
            for event in pygame.event.get():
                self.ProcessEvent(event)
            
            # Update anything that happens over time. The first call waits until
            # it has been a 30th of a second since the last tick, then the
            # second call updates the program.
            self._clock.tick(30)
            self.Tick()
                
            # Re-draw the screen
            self.Draw()
            
            # Switch the current screen image for the one we just prepared.
            pygame.display.flip()


def main():
    pygame.init()
    size = (800, 800)
    # Blinker
    # initial_state = [(0,-1),(0,0),(0,1)]
    # R-pentomino
    # initial_state = [(-1,0), (0,-1), (0,0), (0,1), (1, -1)]
    # Diehard
    # initial_state = [(0,0), (1,0), (1,1), (5,1), (6,-1), (6,1), (7,1)]
    # Acorn
    # initial_state = [(0,1), (1,-1), (1,1), (3,0), (4,1), (5,1), (6,1)]
    # Infinite zig-zag
    initial_state = [(-2,-2), (-2,-1), (-2,2), (-1,-2), (-1,1), (0,-2), (0,1),
                     (0,2), (1,0), (2,-2), (2,0), (2,1), (2,2)]
    game = Game(size, World(initial_state))
    game.RunGameLoop()

main()
