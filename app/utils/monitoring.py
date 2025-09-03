import functools
import time
from typing import Callable, Any, Dict

def monitor_node(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        node_name = func.__name__
        print(f"\n🔄 Executing node: {node_name}")
        print("-" * 30)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            print(f"✅ Node {node_name} completed in {execution_time:.2f}s")
            print(f"Output state: {result.get('status', 'unknown')}")
            
            if result.get('errors'):
                print(f"⚠️ Errors: {result['errors']}")
                
            return result
            
        except Exception as e:
            print(f"❌ Error in {node_name}: {str(e)}")
            raise
            
    return wrapper

# Apply the monitor decorator to all nodes
def apply_monitoring(module):
    for attr_name in dir(module):
        if attr_name.startswith('__'):
            continue
            
        attr = getattr(module, attr_name)
        if callable(attr):
            setattr(module, attr_name, monitor_node(attr))
            
# Example usage in each node file:
"""
from .monitoring import monitor_node

@monitor_node
def your_node_function(state: Dict[str, Any]) -> Dict[str, Any]:
    # Your node logic here
    pass
"""
