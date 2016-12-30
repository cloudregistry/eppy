#!/usr/bin/env python

import string
import random

CSET = string.ascii_letters + string.digits

def randid(mini=5, maxi=15):
    """
    Generate a random ID which size is at least <mini> and
    at most <maxi> characters
    """
    if maxi <= mini:
        maxi = mini + 1
    return ''.join([random.choice(CSET) for i in range(mini +
                                                       random.choice(range(maxi - mini)))])
