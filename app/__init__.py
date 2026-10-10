"""Intelligent Product Returns & Recovery Engine - Backend Application."""
__version__ = "1.0.0"

# Re-export Flask app and internal helpers from root app.py to support test suite and legacy runners
try:
    import importlib.util
    import os
    _root_app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    if os.path.exists(_root_app_path):
        _spec = importlib.util.spec_from_file_location("_flask_root_app", _root_app_path)
        if _spec and _spec.loader:
            _flask_module = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_flask_module)
            app = getattr(_flask_module, "app", None)
            _build_demo_returns = getattr(_flask_module, "_build_demo_returns", None)
            _run_authenticity_check = getattr(_flask_module, "_run_authenticity_check", None)
            _run_condition_score = getattr(_flask_module, "_run_condition_score", None)
            _run_warranty_verification = getattr(_flask_module, "_run_warranty_verification", None)
except Exception:
    pass

