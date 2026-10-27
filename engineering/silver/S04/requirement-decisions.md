# Frozen synthetic fixture decisions

Whole batch succeeds or fails. Ship/cancel lock the same batch row before checking/updating; shipped order blocks all cancellation. Repeated cancel returns duplicate with no inventory delta. Transaction entry owns connection and commit.

Pending: H2 is not PostgreSQL. JDK Proxy is not Spring AOP: Spring self-invocation, propagation configuration and connection-pool exhaustion remain unmeasured. One fixture batch; no production lock/load calibration.
