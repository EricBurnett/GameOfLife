# -*- coding: utf-8 -*-
"""
Created on Sat Apr 2 14:05:10 2011

@author: Eric Burnett (ericburnett@gmail.com)
"""

import sys
from life import Node


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


def TestBlinker():
  # Blinker run to 2^32+1 generations
  b = Node.CanonicalNode(2,
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


if __name__ == "__main__":
  if BasicTests() and TestBlinker():
    print "All Tests Passed"
    sys.exit(0)
  else:
    print "Test failed!"
    sys.exit(1)
