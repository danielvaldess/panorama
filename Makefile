.PHONY: load-snapshot export-snapshot test accept

# Construye la DB operativa desde el snapshot congelado (verifica SHA-256).
load-snapshot:
	python -m pipeline.snapshot_io --load

# Regenera el snapshot + manifest desde la DB operativa.
export-snapshot:
	python -m pipeline.snapshot_io --export

test:
	python -m pytest tests -q

accept:
	python -m eval.acceptance
