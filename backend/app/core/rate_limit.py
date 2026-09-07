"""Rate limiting for sensitive endpoints (auth), via slowapi/limits. Keyed by client
IP. In-memory backend — resets on restart and is per-process, which is an accepted
limitation for this single-process development deployment (see docs/LIMITATIONS.md);
a shared backend (e.g. Redis) would be needed for a multi-process production deploy."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
