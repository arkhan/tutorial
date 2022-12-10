#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unicodedata as uncd
from string import printable


def normalize(text_doc):
    remove = ["Mn", "Po", "Pc", "Pd", "Pf", "Pi", "Ps"]
    cstring = "".join(
        (c for c in uncd.normalize("NFD", text_doc) if uncd.category(c) not in remove)
    )
    return "".join(i for i in cstring if i in printable)
