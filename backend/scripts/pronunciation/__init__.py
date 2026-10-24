"""Offline pronunciation dataset/training/evaluation tooling (plan §P5).

Nothing here runs at inference time and nothing here is imported by
``app/``: the runtime engine never depends on training code. No raw learner
audio or downloaded public corpus may be committed into this repository.
"""
