# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 09:17:10 2011

@author: Eric Burnett (ericburnett@gmail.com)
"""
import copy
import pygame
from pygame.locals import *  # Gives names like K_DOWN for key presses.
import sys

numNodesConstructed=0
numAlreadyInCache=0
numNodeObjectsSaved=0
spare_node=None

class Node:
  # [ns][ew] are Node pointers for level > 1
  # [ns][ew] are [0|1] if level == 1
  def __init__(self, level, nw, ne, sw, se):
    global numNodesConstructed
    numNodesConstructed += 1
    self._level = level
    if (level == 1):
      assert nw is 1 or nw is 0
      assert ne is 1 or ne is 0
      assert sw is 1 or sw is 0
      assert se is 1 or se is 0
      pass
    else:
      assert nw._level == level - 1
      assert ne._level == level - 1
      assert sw._level == level - 1
      assert se._level == level - 1
      pass
    self._nw = nw
    self._ne = ne
    self._sw = sw
    self._se = se
    self._next = None
    self._nextLevel = None
    self._hash = None

  def Canonical(self, cache_dont_touch={}):
    # Returns the canonical variant of a node, hopefully with a cached center.
    cache = cache_dont_touch
    global numAlreadyInCache
    if self not in cache:
      cache[self] = self
    if id(cache[self]) != id(self):
      numAlreadyInCache+= 1
    return cache[self]

  def IsCanonical(self):
    return id(self) == id(self.Canonical())

  @classmethod
  def CanonicalNode(cls, level, nw, ne, sw, se):
    global spare_node
    global numNodeObjectsSaved
    if spare_node is not None:
      spare_node._level = level
      spare_node._nw = nw
      spare_node._ne = ne
      spare_node._sw = sw
      spare_node._se = se
      spare_node._hash = None
    else:
      spare_node = Node(level, nw, ne, sw, se)
    canonical = spare_node.Canonical()
    if id(spare_node) == id(canonical):
      spare_node = None
    else:
      numNodeObjectsSaved += 1
    return canonical

  def __hash__(self):
    # Hash is dependent on cells only, not e.g. _next.
    if not self._hash:
      self._hash = hash((self._level, self._nw, self._ne, self._sw, self._se))
    return self._hash

  def __eq__(self, other):
    # Are two nodes equal? Doesn't take caching _next into account.
    if id(self) == id(other):
      return True
    return (id(self._nw) == id(other._nw) and
            id(self._ne) == id(other._ne) and
            id(self._sw) == id(other._sw) and
            id(self._se) == id(other._se))
  def __ne__(self, other):
    return not self.__eq__(other)


  @classmethod
  def Zero(cls, level,
           cache_dont_touch=[]):
    # Returns a node tree of all zeroes at the specified level.
    cache = cache_dont_touch

    if level == 0:
      return 0
    n = len(cache)
    if n == 0:
      cache.append(Node.CanonicalNode(1, 0, 0, 0, 0))
      n += 1
    while n < level:
      back = cache[-1]
      cache.append(
          Node.CanonicalNode(back._level + 1, nw=back, ne=back, sw=back, se=back))
      n += 1

    ret = cache[level-1]
    assert ret._level == level
    return ret

  def IsZero(self):
    zero = Node.Zero(self._level)
    return zero == self

  def Expand(self):
    # Returns a node one level deeper, with the center being this node.
    zero = Node.Zero(self._level - 1)
    nw = self.CanonicalNode(self._level, nw=zero, ne=zero, sw=zero, se=self._nw)
    ne = self.CanonicalNode(self._level, nw=zero, ne=zero, sw=self._ne, se=zero)
    sw = self.CanonicalNode(self._level, nw=zero, ne=self._sw, sw=zero, se=zero)
    se = self.CanonicalNode(self._level, nw=self._se, ne=zero, sw=zero, se=zero)
    return self.CanonicalNode(self._level + 1, nw=nw, ne=ne, sw=sw, se=se)

  def Compact(self):
    # Returns the smallest node (level >= 1) that will contain all the cells.
    if self._level == 1:
      return self
    cur = self
    zero = Node.Zero(cur._level - 2)
    while (
        cur._nw._nw == zero and cur._nw._ne == zero and cur._nw._sw == zero and
        cur._ne._nw == zero and cur._ne._ne == zero and cur._ne._se == zero and
        cur._sw._nw == zero and cur._sw._sw == zero and cur._sw._se == zero and
        cur._se._ne == zero and cur._se._sw == zero and cur._se._se == zero):
      cur = self.CanonicalNode(cur._level - 1, cur._nw._se, cur._ne._sw, cur._sw._ne,
                 cur._se._nw)
      if cur._level == 1:
        break
      zero = Node.Zero(cur._level - 2)
    return cur

  @classmethod
  def MergeHorizontal(cls, l, r):
    assert l._level == r._level
    return cls.CanonicalNode(l._level, nw=l._ne, ne=r._nw, sw=l._se, se=r._sw)
  @classmethod
  def MergeVertical(cls, t, b):
    assert t._level == b._level
    return cls.CanonicalNode(t._level, nw=t._sw, ne=t._se, sw=b._nw, se=b._ne)
  @classmethod
  def MergeCenter(cls, nw, ne, sw, se):
    return cls.CanonicalNode(nw._level, nw._se, ne._sw, sw._ne, se._nw)

  def _Forward(self, atLevel=None):
    if atLevel is None or atLevel > self._level:
      atLevel = self._level

    # Returns a Node pointer, representing the center
    # 2^(level-1) x 2^(level-1) cells forward 2^(level-2) generations.
    assert self._level > 1
    if self._next and self._nextLevel != atLevel:
      # Wipe the cache for now.
      # TODO(ericburnett): Test cache array instead.
      self._next = None
      self._nextLevel = None
    if self._next:
      return self._next

    if self._level == 2:
      assert atLevel == 2
      countNW = (self._nw.Sum(3) + self._ne.SumLeft() + self._sw.SumTop() +
                 self._se._nw)
      countNE = (self._ne.Sum(2) + self._nw.SumRight() + self._se.SumTop() +
                 self._sw._ne)
      countSW = (self._sw.Sum(1) + self._se.SumLeft() + self._nw.SumBottom() +
                 self._ne._sw)
      countSE = (self._se.Sum(0) + self._sw.SumRight() + self._ne.SumBottom() +
                 self._nw._se)
      self._next = Node.CanonicalNode(
          1,
          (countNW == 3 or (countNW == 2 and self._nw._se)) and 1 or 0,
          (countNE == 3 or (countNE == 2 and self._ne._sw)) and 1 or 0,
          (countSW == 3 or (countSW == 2 and self._sw._ne)) and 1 or 0,
          (countSE == 3 or (countSE == 2 and self._se._nw)) and 1 or 0)
      self._nextLevel = atLevel
      return self._next
    else:
      n00 = self._nw._Forward(atLevel=atLevel)
      n01 = Node.MergeHorizontal(self._nw, self._ne)._Forward(atLevel=atLevel)
      n02 = self._ne._Forward(atLevel=atLevel)
      n10 = Node.MergeVertical(self._nw, self._sw)._Forward(atLevel=atLevel)
      n11 = Node.MergeCenter(self._nw, self._ne,
                             self._sw, self._se)._Forward(atLevel=atLevel)
      n12 = Node.MergeVertical(self._ne, self._se)._Forward(atLevel=atLevel)
      n20 = self._sw._Forward(atLevel=atLevel)
      n21 = Node.MergeHorizontal(self._sw, self._se)._Forward(atLevel=atLevel)
      n22 = self._se._Forward(atLevel=atLevel)
      if atLevel != self._level:
        # Just merge the result from the lower levels without adding another
        # Forward phase - this takes out a factor of two in the recursion and
        # allows us to step some number of generations forward < 2^(level-2).
        nw = Node.MergeCenter(n00, n01, n10, n11)
        ne = Node.MergeCenter(n01, n02, n11, n12)
        sw = Node.MergeCenter(n10, n11, n20, n21)
        se = Node.MergeCenter(n11, n12, n21, n22)
      else:
        nw = self.CanonicalNode(self._level-1, n00, n01, n10, n11)._Forward()
        ne = self.CanonicalNode(self._level-1, n01, n02, n11, n12)._Forward()
        sw = self.CanonicalNode(self._level-1, n10, n11, n20, n21)._Forward()
        se = self.CanonicalNode(self._level-1, n11, n12, n21, n22)._Forward()
      self._next = self.CanonicalNode(self._level-1, nw, ne, sw, se)
      self._nextLevel = atLevel
      return self._next

  def ForwardN(self, n):
    # Returns a Node pointer, representing these cells forward n generations.
    # It will automatically expand to be big enough to fit all cells.
    atLevel = 2
    cur = self
    while n > 0:
      if n & 1:
        while cur._level < atLevel - 2:
          cur = cur.Expand()
	# Expand twice extra to ensure the expanded cells will fit within the
	# center forward one.
        cur = cur.Expand().Expand()._Forward(atLevel=atLevel)
      n >>= 1
      atLevel += 1
    return cur.Compact()

  def __str__(self):
    return str((self._level, str(self._nw), str(self._ne), str(self._sw),
                str(self._se)))

  # Various sum functions, for counting portions of a level-1 node.
  def Sum(self, index):
    # index is the value to skip (i.e. count 3 of 4 cells).
    assert self._level == 1
    return self._nw + self._ne + self._sw + self._se - self.Raw(index)
  def SumLeft(self):
    assert self._level == 1
    return self._nw + self._sw
  def SumTop(self):
    assert self._level == 1
    return self._nw + self._ne
  def SumRight(self):
    assert self._level == 1
    return self._ne + self._se
  def SumBottom(self):
    assert self._level == 1
    return self._sw + self._se
  def Raw(self, index):
    if index == 0:
      return self._nw
    elif index == 1:
      return self._ne
    elif index == 2:
      return self._sw
    elif index == 3:
      return self._se
    else:
      assert False
      pass


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

  def Iterate(self, num_generations):
    if len(self._current) == 0:
      return

    for i in range(num_generations):
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

    pixels = max(min(screen_width // (width+1), screen_height // (height+1)),
                 1)

    for (x,y) in self._current:
      box = pygame.Rect((screen_width // 2 + (x - center_x)*pixels,
                         screen_height // 2 + (y - center_y)*pixels),
			(pixels, pixels))
      screen.fill((0,0,0), box)


class Game:
  def __init__(self, size, world):
    # Width and height of the main screen.
    (self._width, self._height) = size
    self._screen = pygame.display.set_mode(size)
    # Clock for tracking things that happen over time.
    self._clock = pygame.time.Clock()
    # How many ticks left until we iterate?
    self._ticks_per_update = 16
    self._generations_per_update = 1
    self._ticks_till_next = 90
    self._paused = False
    # World to iterate.
    self._world = world

  # Handle a single 'event' - like a key press, mouse click, etc.
  def ProcessEvent(self, event):
    if event.type == pygame.QUIT:
      sys.exit()
    elif event.type == pygame.KEYDOWN:
      if event.key == K_DOWN:
	if (self._generations_per_update > 1):
          self._generations_per_update >>= 1
	else:
          self._ticks_per_update <<= 1
      elif event.key == K_UP:
	if self._ticks_per_update > 1:
          self._ticks_per_update >>= 1
	else:
          self._generations_per_update <<= 1
      elif event.key == K_SPACE:
	self._paused = not self._paused
      elif event.key == K_q and (pygame.key.get_mods() & KMOD_CTRL):
	sys.exit()

  def Draw(self):
    self._screen.fill((255,255,255))  # White
    self._world.Draw(self._width, self._height, self._screen)

  def Tick(self):
    if self._paused:
      return
    if self._ticks_till_next > 1:
      self._ticks_till_next -= 1
    else:
      self._world.Iterate(self._generations_per_update)
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


def ParseFile(name):
  with open(name) as f:
    result = []

    row = 0
    for line in f:
      if not line or line[0] == '!':
	continue

      col = 0
      for c in line:
	if c != '.':
          result.append((row,col))
        col += 1
      row -= 1
    return result


def main():
  pygame.init()
  size = (800, 800)

  if len(sys.argv) > 1:
    initial_state = ParseFile(sys.argv[1])
  else:
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


if __name__ == "__main__":
  main()
