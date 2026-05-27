# SimplePod Failproof Plan

## Problem
Streamlit reruns the Python script on every interaction. Starting a background API server thread inside Streamlit is fragile because:
- The thread can die silently on exception
- `st.session_state` persists, so we don't retry startup
- Port conflicts cause immediate crash

## Solution
**Separate process architecture.** `run.py` starts the API server as a subprocess, then starts Streamlit. Streamlit NEVER tries to start the API server.

## Steps
1. **Clean slate** — kill all streamlit, python processes related to simplepod
2. **Fix app.py** — remove ALL API server startup code. Just use the API at localhost:58091
3. **Fix client.py** — add retry logic and connection-lost error handling
4. **Fix run.py** — robust launcher: start API → health check → start Streamlit
5. **Test** — run `python run.py`, verify API + Streamlit both respond
6. **Commit**

## Rollback strategy
If Streamlit fails, fall back to: API server only + curl-based demo.
