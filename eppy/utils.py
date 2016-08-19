from random import choice


TRID_CSET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


def gen_trid(length=12):
    return ''.join(choice(TRID_CSET) for _i in range(length))
