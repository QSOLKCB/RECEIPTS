# Contributing

Preserve the difference between observations, calculations, and inferences.
Changes to claim rules need both a case they should accept and a case they should
reject. Include cases where strong evidence warrants a positive conclusion.

Use original synthetic fixtures or reviewed public evidence with receipts and
rights information. Keep expected labels out of model inputs. Document changes
to cases, prompts, scoring, model settings and data inclusion rules. Never silently
rewrite historical evaluation artifacts or present mocks as inference results.

Run `PYTHONPATH=src python -m unittest discover -s tests -v` before submitting code.
Run a dry evaluation after changing prompt or fixture formats. Genuine model
evaluation uses a provider credential and incurs usage; it is a separate check.

Contributions intentionally submitted for inclusion are under Apache-2.0 unless
explicitly stated otherwise, consistent with that license. Preserve third-party
notices and clearly identify modifications to distributed files.
