"""Engine context guard utilities."""

from __future__ import annotations

from typing import Any


class GuardedContext(dict[str, Any]):
    def __init__(
        self,
        *args: Any,
        protected_keys: set[str] | None = None,
        allowed_root_keys: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._protected_keys = set(protected_keys or set())
        self._allowed_root_keys = set(
            allowed_root_keys or {"input", "signals", "families", "areas", "metrics", "modules", "meta"}
        )
        self._mutation_log: list[str] = []
        self._active_module: str | None = None
        self._allowed_path_prefix: str | None = None
        self._read_rules: dict[str, set[str]] = {}
        self._deny_reads: set[str] = set()

    @property
    def mutation_log(self) -> list[str]:
        return list(self._mutation_log)

    def allow(self, module: str, path: str) -> None:
        self._active_module = module
        self._allowed_path_prefix = path

    def clear_allow(self) -> None:
        self._active_module = None
        self._allowed_path_prefix = None

    def allow_read(self, module: str, path: str) -> None:
        self._read_rules.setdefault(module, set()).add(path)

    def deny_read(self, path: str) -> None:
        self._deny_reads.add(path)

    def check_read(self, module: str, path: str) -> None:
        def _match(pattern: str, value: str) -> bool:
            if pattern.endswith(".*"):
                root = pattern[:-2]
                return value == root or value.startswith(root + ".")
            if pattern.endswith("*"):
                return value.startswith(pattern[:-1])
            return value == pattern

        if path in self._deny_reads:
            raise ValueError(f"engine_context_read_denied:{module}:{path}")
        allowed = self._read_rules.get(module)
        if allowed and not any(_match(p, path) for p in allowed):
            raise ValueError(f"engine_context_read_scope_violation:{module}:{path}")

    def __getitem__(self, key: str) -> Any:
        if self._active_module is not None:
            self.check_read(self._active_module, str(key))
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        if self._active_module is not None:
            self.check_read(self._active_module, str(key))
        return super().get(key, default)

    def set_module_slot(self, module: str, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError(f"module_payload_invalid_type:{module}")
        modules = dict(self.get("modules") or {})
        modules[module] = payload
        super().__setitem__("modules", modules)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self._protected_keys:
            self._mutation_log.append(f"blocked_mutation:{key}")
            raise ValueError(f"engine_context_readonly_mutation_blocked:{key}")
        if key not in self._allowed_root_keys:
            self._mutation_log.append(f"blocked_root_write:{key}")
            raise ValueError(f"engine_context_root_write_blocked:{key}")
        if self._active_module is not None and key != "modules":
            self._mutation_log.append(f"blocked_module_write:{self._active_module}:{key}")
            raise ValueError(f"engine_context_module_scope_violation:{self._active_module}:{key}")
        super().__setitem__(key, value)

