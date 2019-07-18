# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 09:17:10 2011

@author: Eric Burnett (ericburnett@gmail.com)
Released under the LGPL (or most other licenses on demand) - contact me if you
need appropriate headers stuck on.
"""
import copy
import math
import pygame
from pygame.locals import *  # Gives names like K_DOWN for key presses.
import sys
import time

# Global variables for tracking various counts.
numNodesConstructed=0
numAlreadyInCache=0
numNodeObjectsSaved=0

# Global cache for a spare node, to reduce object churn when looking up
# canonical nodes.
spare_node=None

class UsageError(RuntimeError):
  pass

################################################################################
class Node:
  """A Node represents a square 2^N x 2^N cluster of cells.

  The Node class is based on the description of the HashLife algorithm found
  at http://drdobbs.com/high-performance-computing/184406478. It is a hash tree
  with agressive caching and de-duplication. In particular:
  * Nodes are defined recursively, with _nw, _ne, _sw, and _se being Nodes
    representing the 2^(N-1) x 2^(N-1) cells in a particular corner ([0|1] at
    the leaves).
  * Nodes are immutable. Once a Node is returned from Node.CanonicalNode(), the
    cells represented are guaranteed not to change.
  * Nodes are unique. They are constructed in such a way that no two Node
    objects can represent the same configuration of cells. In particular, this
    means that Nodes can be compared by equality by doing id(a)==id(b). This
    means that most node hierarchies take far less than 2^(2N) space to store.
  * One key operation on a Node is to return the inner core 2^(N-1) x 2^(N-1)
    cells forward a number of generations (usually 2^(N-2)). This is cached
    wherever possible, and, along with identical nodes being shared due to their
    uniqueness, means calculating the future inner core of a Node is usually far
    cheaper than the worst case 2^(2N) operation.
    """
  @classmethod
  def CanonicalNode(cls, level, nw, ne, sw, se):
    """Returns a canonical version of a new node. Should always be used, never
    the base constructor."""
    global spare_node
    global numNodeObjectsSaved
    if spare_node is not None:
      spare_node._level = level
      spare_node._nw = nw
      spare_node._ne = ne
      spare_node._sw = sw
      spare_node._se = se
      assert spare_node._next is None
      assert spare_node._nextLevel is None
    else:
      spare_node = Node(level, nw, ne, sw, se, really_use_constructor=True)
    canonical = spare_node.Canonical()
    if id(spare_node) == id(canonical):
      spare_node = None
    else:
      numNodeObjectsSaved += 1
    return canonical

  def __init__(self, level, nw, ne, sw, se, really_use_constructor=False):
    if not really_use_constructor:
      raise UsageError("You should call Node.CanonicalNode rather than the "
                       "constructor directly. This breaks assumptions used "
                       "throughout the class and will slow down execution "
                       "enormously.")
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
      assert nw._level == ne._level == sw._level == se._level == level - 1
      pass

    # Recursive sub-nodes:
    self._nw = nw
    self._ne = ne
    self._sw = sw
    self._se = se

    # Cached values. _next and _nextLevel are the cached inner core and the
    # level at which exponential speedups were started (see Forward() for more
    # information about the level).
    self._next = None
    self._nextLevel = None

  def Canonical(self, cache_dont_touch={}):
    """Returns the canonical variant of a node, hopefully with a cached center.
    """
    cache = cache_dont_touch
    global numAlreadyInCache
    if self not in cache:
      cache[self] = self
    if id(cache[self]) != id(self):
      numAlreadyInCache += 1
    return cache[self]

  def IsCanonical(self):
    return id(self) == id(self.Canonical())

  def __hash__(self):
    # Hash is dependent on cells only, not e.g. _next.
    # Required for Canonical(), so cannot be simply the id of the current
    # object (which would otherwise work).
    return hash((id(self._nw), id(self._ne), id(self._sw), id(self._se)))

  def __eq__(self, other):
    """Are two nodes equal? Doesn't take caching _next into account."""
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
    """Returns a node tree of all zeroes at the specified level."""
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
    """Returns a node one level deeper, with the center being this node."""
    zero = Node.Zero(self._level - 1)
    nw = self.CanonicalNode(self._level, nw=zero, ne=zero, sw=zero, se=self._nw)
    ne = self.CanonicalNode(self._level, nw=zero, ne=zero, sw=self._ne, se=zero)
    sw = self.CanonicalNode(self._level, nw=zero, ne=self._sw, sw=zero, se=zero)
    se = self.CanonicalNode(self._level, nw=self._se, ne=zero, sw=zero, se=zero)
    return self.CanonicalNode(self._level + 1, nw=nw, ne=ne, sw=sw, se=se)

  def Compact(self):
    """Returns the smallest node (level >= 1) that will contain all the cells
    (without shifting the center).
    """
    if self._level == 1:
      return self
    cur = self
    zero = Node.Zero(cur._level - 2)
    while (
        cur._level >= 2 and
        cur._nw._nw == zero and cur._nw._ne == zero and cur._nw._sw == zero and
        cur._ne._nw == zero and cur._ne._ne == zero and cur._ne._se == zero and
        cur._sw._nw == zero and cur._sw._sw == zero and cur._sw._se == zero and
        cur._se._ne == zero and cur._se._sw == zero and cur._se._se == zero):
      cur = self.CanonicalNode(cur._level - 1, cur._nw._se, cur._ne._sw, cur._sw._ne,
                 cur._se._nw)
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
    """Returns the inner 2^(level-1) x 2^(level-1) core of this node, forward in
    time. The number of generations will be 2^(atLevel-2), by calling _Forward
    twice at every level <= atLevel, and once for higher levels. This causes the
    exponential speedup to start at the specified level, being linear up till
    that point.
    """
    if atLevel is None or atLevel > self._level:
      atLevel = self._level
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
    """Returns a Node pointer, representing these cells forward n generations.
    It will automatically expand to be big enough to fit all cells.
    The most compact node centered at the appropriate location that contains
    all the cells is returned.
    """
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
    """Simple string method for debugging purposes.
    """
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

  @classmethod
  def _OffsetBounds(cls, bounds, level, index):
    """Returns the input bounds offset to a particular quadrant (i.e. so the
    center of the new quadrant is still considered (0,0)), along with the
    opposing offset for tracking purposes.
    """
    size = 2**level
    assert size >= 4
    quarter_size = size >> 2
    if index == 0:
      ret = (bounds[0]+quarter_size, bounds[1]+quarter_size,
             bounds[2]-quarter_size, bounds[3]-quarter_size)
      offset = (-quarter_size, quarter_size)
    elif index == 1:
      ret = (bounds[0]-quarter_size, bounds[1]-quarter_size,
             bounds[2]-quarter_size, bounds[3]-quarter_size)
      offset = (quarter_size, quarter_size)
    elif index == 2:
      ret = (bounds[0]+quarter_size, bounds[1]+quarter_size,
             bounds[2]+quarter_size, bounds[3]+quarter_size)
      offset = (-quarter_size, -quarter_size)
    elif index == 3:
      ret = (bounds[0]-quarter_size, bounds[1]-quarter_size,
             bounds[2]+quarter_size, bounds[3]+quarter_size)
      offset = (quarter_size, -quarter_size)
    return (ret, offset)

  def Draw(self, bounds, draw_func, offset=(0,0)):
    """Draw the cells within this Node that fall within bounds. Before offset,
    the cell upper-right of center is 0,0. The offsetted coordinates of 'on'
    cells are passed to draw_func for the actual rendering.
    """
    if self.IsZero():
      return

    inner_size = 2**(self._level-1)
    if (bounds[1] < -inner_size or bounds[0] >= inner_size or
        bounds[3] < -inner_size or bounds[2] >= inner_size):
      return

    if self._level == 1:
      if self._nw and bounds[0] <= -1 and bounds[3] >= 0:
        draw_func(-1 + offset[0], 0 + offset[1])
      if self._ne and bounds[1] >= 0 and bounds[3] >= 0:
        draw_func(0 + offset[0], 0 + offset[1])
      if self._sw and bounds[0] <= -1 and bounds[2] <= -1:
        draw_func(-1 + offset[0], -1 + offset[1])
      if self._se and bounds[1] >= 0 and bounds[2] <= -1:
        draw_func(0 + offset[0], -1 + offset[1])
    else:
      directions = self._nw, self._ne, self._sw, self._se
      for i in range(4):
        new_bounds, new_offset = Node._OffsetBounds(bounds, self._level, i)
        self.Raw(i).Draw(new_bounds, draw_func,
                         (offset[0]+new_offset[0], offset[1]+new_offset[1]))


################################################################################
class World:
  """Manages the world of cells, infinite in size.

  Handles drawing, iteration, and tracking various statistics about what is
  happening.
  """

  def __init__(self, positions):
    """Initialize the world. Positions is a list of coordinates in the world
    that should be set to true, as (x,y) tuples."""
    self._root = World.FillNode(set(positions))
    self._view_center = [0, 0]
    self._view_size = 5  # How many pixels across is each cell?
    self._iteration_count = 0

  @classmethod
  def FillNode(cls, positions):
    """Turns a set of positions into a node hierarchy."""
    if not positions:
      return ([0,0], Node.Zero(1))

    min_x = min(map(lambda a: a[0], positions))
    max_x = max(map(lambda a: a[0], positions))
    min_y = min(map(lambda a: a[1], positions))
    max_y = max(map(lambda a: a[1], positions))
    center_x = (max_x + min_x) // 2
    center_y = (max_y + min_y) // 2
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    levels = int(math.log(max(width, height), 2)) + 1
    node_size = 2**levels
    bounds = (center_x - (node_size >> 1) + 1,
              center_x + (node_size >> 1),
              center_y - (node_size >> 1) + 1,
              center_y + (node_size >> 1))
    root = cls._NodeFromPositionsAndBounds(positions, levels, bounds)
    return root

  @classmethod
  def _NodeFromPositionsAndBounds(cls, positions, level, bounds):
    """Builds a Node at the specified level using the cells in positions that
    fall within the given bounds.
    """
    inner_size = 2**(level-1)
    assert bounds[0] + 2*inner_size - 1 == bounds[1]
    assert bounds[2] + 2*inner_size - 1 == bounds[3]
    if level == 1:
      return Node.CanonicalNode(
          1,
          1 if (bounds[0], bounds[3]) in positions else 0,
          1 if (bounds[1], bounds[3]) in positions else 0,
          1 if (bounds[0], bounds[2]) in positions else 0,
          1 if (bounds[1], bounds[2]) in positions else 0)
    else:
      return Node.CanonicalNode(
          level,
          cls._NodeFromPositionsAndBounds(positions, level-1,
                                          cls._InnerBounds(bounds, 0)),
          cls._NodeFromPositionsAndBounds(positions, level-1,
                                          cls._InnerBounds(bounds, 1)),
          cls._NodeFromPositionsAndBounds(positions, level-1,
                                          cls._InnerBounds(bounds, 2)),
          cls._NodeFromPositionsAndBounds(positions, level-1,
                                          cls._InnerBounds(bounds, 3)))

  @classmethod
  def _InnerBounds(self, bounds, index):
    """Helper method for NodeFromPositionsAndBounds - returns the quadrant of
    the bounds that corresponds to the given index. So for bounds [3, 6, 10, 13]
    the return values are 0:[3, 4, 12, 13], 1:[5, 6, 12, 13], 2:[3, 4, 10, 11],
      3:[5, 6, 10, 11].
    """
    size = bounds[1] - bounds[0] + 1
    assert bounds[2] + size - 1 == bounds[3]
    assert size > 1
    inner_size = size >> 1
    if index == 0:
      return (bounds[0], bounds[1]-inner_size,
              bounds[2]+inner_size, bounds[3])
    elif index == 1:
      return (bounds[0]+inner_size, bounds[1],
              bounds[2]+inner_size, bounds[3])
    elif index == 2:
      return (bounds[0], bounds[1]-inner_size,
              bounds[2], bounds[3]-inner_size)
    elif index == 3:
      return (bounds[0]+inner_size, bounds[1],
              bounds[2], bounds[3]-inner_size)
    else:
      assert False
      pass

  def Iterate(self, num_generations):
    """Updates the state of the current world by n generations."""
    self._root = self._root.ForwardN(num_generations)
    self._iteration_count += num_generations

  def ShiftView(self, direction, step_size):
    """Shifts the current view by a number of screen pixels."""
    # view_center is in terms of cells, so shift by the corresponding number of
    # cells instead.
    cells = step_size // self._view_size
    if direction == K_UP:
      self._view_center[1] -= cells
    elif direction == K_DOWN:
      self._view_center[1] += cells
    elif direction == K_RIGHT:
      self._view_center[0] += cells
    elif direction == K_LEFT:
      self._view_center[0] -= cells

  def ZoomOut(self):
    self._view_size = max(1, self._view_size - 1)

  def ZoomIn(self):
    self._view_size += 1

  def Draw(self, screen_width, screen_height, screen):
    """Draws the current world to the screen. Uses self._view_center and
    self._view_size to specify the location and zoom level.
    """
    # + 2 for rounding here and the // 2 that follows.
    view_width = screen_width // self._view_size + 2
    view_height = screen_height // self._view_size + 2
    view_bounds = (self._view_center[0] - (view_width // 2),
                   self._view_center[0] + (view_width // 2),
                   self._view_center[1] - (view_height // 2),
                   self._view_center[1] + (view_height // 2))
    def ToScreenSpace(x, y):
      """Helper method to convert a Node coordinate into a screen Rect."""
      pixels = self._view_size
      x = x - self._view_center[0]
      y = y - self._view_center[1]
      return pygame.Rect((screen_width // 2 + x*pixels,
                          screen_height // 2 + y*pixels,
                          pixels, pixels))
    def DrawCell(x, y):
      """Helper method to draw a cell in Node coordinates to the screen."""
      rect = ToScreenSpace(x, y)
      screen.fill((0,0,0), rect)

    # The bounds passed in assume the Node is rooted at 0,0. DrawCell will take
    # care of translating back to screen space and applying the view offsets.
    self._root.Draw(view_bounds, DrawCell)


################################################################################
class Game:
  def __init__(self, size, world):
    # Width and height of the main screen.
    (self._width, self._height) = size
    self._screen = pygame.display.set_mode(size)
    # Clock for tracking things that happen over time.
    self._clock = pygame.time.Clock()
    # How many ticks left until we iterate?
    self._ticks_per_update = 16
    # When we're iterating once per frame we can step more than one generation
    # (for running the iterations faster than our render loop).
    self._generations_per_update = 1
    # How long until the next draw? Started high to introduce a pause when the
    # program starts before the iterations kick off.
    self._ticks_till_next = 90
    self._paused = False
    # World to iterate.
    self._world = world

  def ProcessEvent(self, event):
    """Handle a single 'event' - like a key press, mouse click, etc."""
    if event.type == pygame.QUIT:
      sys.exit()
    elif event.type == pygame.KEYDOWN:
      if (event.key == K_DOWN or event.key == K_UP or
          event.key == K_LEFT or event.key == K_RIGHT):
        # Pan.
        self._world.ShiftView(event.key, max(self._width, self._height) // 20)
      elif event.key == K_MINUS or event.key == K_KP_MINUS:
        # Slow down.
        if (self._generations_per_update > 1):
          self._generations_per_update >>= 1
        else:
          self._ticks_per_update <<= 1
      elif event.key == K_EQUALS or event.key == K_KP_PLUS:
        # Speed up.
        if self._ticks_per_update > 1:
          self._ticks_per_update >>= 1
        else:
          self._generations_per_update <<= 1
      elif event.key == K_SPACE:
        # Pause.
        self._paused = not self._paused
      elif event.key == K_PAGEDOWN:
        # Zoom in.
        self._world.ZoomIn()
      elif event.key == K_PAGEUP:
        # Zoom out.
        self._world.ZoomOut()
      elif event.key == K_q and (pygame.key.get_mods() & KMOD_CTRL):
        # Quit.
        sys.exit()

  def Draw(self):
    self._screen.fill((255,255,255))  # White
    self._world.Draw(self._width, self._height, self._screen)
    pygame.display.flip()

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

      # Re-draw the screen.
      self.Draw()


def ParseFile(name):
  """Load a file. We support pretty lax syntax; ! or # start a comment, . on a
  line is a dead cell, anything else is live. Line lengths do not need to
  match. This can load basic .cells and .lif files, although nothing complicated
  is supported.
  """
  with open(name) as f:
    result = []

    row = 0
    for line in f:
      if not line or line[0] == '!' or line[0] == '#':
        continue

      col = 0
      for c in line:
        if c == '\r' or c == '\n':
          break
        if c != '.':
          result.append((row,col))
        col += 1
      row -= 1
    return result


def main():
  pygame.init()
  pygame.key.set_repeat(150, 50)
  size = (1200, 1000)

  if len(sys.argv) > 1:
    initial_state = ParseFile(sys.argv[1])
  else:
    # Infinite zig-zag
    initial_state = [(-2,-2), (-2,-1), (-2,2), (-1,-2), (-1,1), (0,-2), (0,1),
                     (0,2), (1,0), (2,-2), (2,0), (2,1), (2,2)]
  game = Game(size, World(initial_state))
  game.RunGameLoop()


if __name__ == "__main__":
  main()
