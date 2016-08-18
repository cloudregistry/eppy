#!/usr/bin/env python

import string
import random


CSET = string.lowercase + string.digits + string.uppercase


def randid(min=5, max=15):
    """
    Generate a random ID which size is at least <min> and
    at most <max> characters
    """
    if max <= min:
        max = min + 1
    return ''.join([random.choice(CSET) for i in range(min +
                                                       random.choice(range(max - min)))])
