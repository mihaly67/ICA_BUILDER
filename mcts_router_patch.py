import sys
import os
import inspect

import time
import inspect
from mcp.server.fastmcp import FastMCP

import ica_telemetry

def add_tool_with_telemetry(func):
    import functools
    @functools.wraps(func)
    async def async_wrapped(*args, **kwargs):
        start = time.time()
        mcts_data = None
        try:
            res = await func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000

            # If the tool is deep_planning, try to extract MCTS tree data from result if it returns a tuple or dict
            if func.__name__ == "deep_planning" and isinstance(res, dict) and "tree_data" in res:
                mcts_data = res["tree_data"]
                res = res.get("best_action", res) # Return just the action if possible

            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success", mcts_data=mcts_data)
            return res
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e), mcts_data=mcts_data)
            raise e

    @functools.wraps(func)
    def sync_wrapped(*args, **kwargs):
        start = time.time()
        mcts_data = None
        try:
            res = func(*args, **kwargs)
            exec_time = (time.time() - start) * 1000

            if func.__name__ == "deep_planning" and isinstance(res, dict) and "tree_data" in res:
                mcts_data = res["tree_data"]
                res = res.get("best_action", res)

            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "success", mcts_data=mcts_data)
            return res
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            ica_telemetry.log_mcp_call(func.__name__, kwargs, exec_time, "error", str(e), mcts_data=mcts_data)
            raise e

    wrapped = async_wrapped if inspect.iscoroutinefunction(func) else sync_wrapped
    router_mcp.tool()(wrapped)
