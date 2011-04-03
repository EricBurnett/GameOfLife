# -*- coding: utf-8 -*-
"""
Created on Sat Apr 2 14:05:10 2011

@author: Eric Burnett (ericburnett@gmail.com)
Released under the LGPL (or most other licenses on demand) - contact me if you
need appropriate headers stuck on.
"""

import sys
from life import *

def TestNoNodeConstructor():
  try:
    n = Node(1, 1, 1, 1, 1)
  except UsageError, e:
    return True
  else:
    assert "Constructor should have thrown!"

def BasicTests():
  box = Node.CanonicalNode(1, 1, 1, 1, 1)
  print "box", box
  exp = box.Expand()
  print "exp", exp
  exp2 = exp._Forward()
  print "exp2", exp2
  expexp = exp.Expand()
  print "expexp", expexp
  expexp2 = expexp._Forward()
  print "expexp2", expexp2
  assert expexp2 == box.Expand()
  expexp3 = expexp2._Forward()
  print "expexp3", expexp3
  assert expexp3 == box
  assert expexp3.Canonical() == box.Canonical()
  return True


def TestFillNode():
  box = Node.CanonicalNode(1, 1, 1, 1, 1)
  box2 = World.FillNode(((5, 5), (5, 6), (6, 5), (6, 6)))
  assert box.Expand() == box2

  blink = Node.CanonicalNode(
      2,
      Node.Zero(1), Node.Zero(1),
      Node.CanonicalNode(1, 1, 1, 0, 0),
      Node.CanonicalNode(1, 1, 0, 0, 0))
  blink2 = World.FillNode(((0,0), (1, 0), (2, 0)))
  assert blink == blink2
  return True

def TestInnerBounds():
  bounds = (1, 4, 3, 6)
  assert World._InnerBounds(bounds, 0) == (1, 2, 5, 6)
  assert World._InnerBounds(bounds, 1) == (3, 4, 5, 6)
  assert World._InnerBounds(bounds, 2) == (1, 2, 3, 4)
  assert World._InnerBounds(bounds, 3) == (3, 4, 3, 4)
  return True

def TestBlinker():
  # Blinker run to 2^32+1 generations
  b = Node.CanonicalNode(
       2,
       Node.CanonicalNode(1, 0, 0, 1, 1),
       Node.CanonicalNode(1, 0, 0, 1, 0),
       Node.Zero(1), Node.Zero(1))
  b_1 = b.ForwardN(1)
  b_2 = b.ForwardN(2)
  assert b.IsCanonical()
  assert b_1.IsCanonical()
  assert b_2.IsCanonical()
  b_1f = b_1.ForwardN(1)
  assert b_1f.IsCanonical()
  assert b_1f == b_2
  assert b != b_1
  assert b_1 != b_2
  assert b == b_2
  b_lots = b.ForwardN(2**32+1)
  assert b_lots == b_1
  return True

def TestPerformance():
  initial_state = [(-2,-2), (-2,-1), (-2,2), (-1,-2), (-1,1), (0,-2), (0,1),
                     (0,2), (1,0), (2,-2), (2,0), (2,1), (2,2)]
  n = World.FillNode(initial_state)
  n.ForwardN(1000000)
  return True


if __name__ == "__main__":
  if (TestNoNodeConstructor() and
      BasicTests() and
      TestFillNode() and
      TestInnerBounds() and
      TestBlinker() and
      TestPerformance()):
    print "All Tests Passed"
    sys.exit(0)
  else:
    print "Test failed!"
    sys.exit(1)
