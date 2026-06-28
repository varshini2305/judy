"""Preference-conditioned judging: learn a user's evaluation preferences and
feed them to the judge as context (scoped observations + retrieved ICL examples).

This is the personalization track (layered on the objective judge). Evaluation
uses simulated users with known hidden policies so preference-learning is
falsifiable. See docs/EXPERIMENT_PLAN.md.
"""
