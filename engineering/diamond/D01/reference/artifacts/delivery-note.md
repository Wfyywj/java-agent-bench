Durable per-region migration controller, stable entry identity, dual writes, bounded backfill, exact key/amount gate, fencing and rollback reverse-copy check.
Limitations: No real source DB, two shard databases, asynchronous CDC, concurrent thread scheduling, crash between two independent DB commits or scale test.
Recovery: retain state.properties and audit.log; invoke only fenced documented commands. Never delete unknown effects to retry. Real deployment needs separate infrastructure review and trials.
