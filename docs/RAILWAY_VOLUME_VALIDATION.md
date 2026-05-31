# Railway Volume Validation

## Persistent Storage Configuration

Railway uses stateless containers by default. Because HFOS uses SQLite for state (users, portfolios, scores), persistent storage is mandatory.

### Volume Configuration
- **Mount Path:** `/app/database`
- **Verification:** The Dockerfile runs with `/app` as the working directory. If a Railway volume is attached to `/app/database`, the SQLite engine will write `hfos.db`, `hfos.db-wal`, and `hfos.db-shm` directly to the network storage.

### Checks
- **Automatic Database Creation:** If the volume is empty on first boot, HFOS's `initialize_schema()` will automatically provision the 37-table schema into the volume.
- **Read/Write Permissions:** Railway volumes run as `root` inside the container unless specified otherwise. The `Dockerfile` does not demote the user, ensuring full `rw` access to the volume.
- **Restart Persistence:** Because WAL mode splits data across `hfos.db` and `hfos.db-wal`, mounting the entire `/app/database` directory ensures that un-checkpointed WAL data survives container restarts.

## Conclusion
Railway Persistent Volumes are fully compatible with HFOS's SQLite WAL configuration. No further code changes are required.
