import importlib
from typing import Any, Callable, Dict, Optional

from langchain_core._api import warn_deprecated

from langchain._api.interactive_env import is_interactive_env

ALLOWED_TOP_LEVEL_PKGS = {
    "langchain_community",
    "langchain_core",
    "langchain",
}


# For 0.1 releases keep this here
# Remove for 0.2 release so that deprecation warnings will
# be raised for all the new namespaces.
_NAMESPACES_WITH_DEPRECATION_WARNINGS_IN_0_1 = {
    "langchain",
    "langchain.adapters.openai",
    "langchain.agents.agent_toolkits",
    "langchain.callbacks",
    "langchain.chat_models",
    "langchain.docstore",
    "langchain.document_loaders",
    "langchain.document_transformers",
    "langchain.embeddings",
    "langchain.llms",
    "langchain.memory.chat_message_histories",
    "langchain.storage",
    "langchain.tools",
    "langchain.utilities",
    "langchain.vectorstores",
}


def _should_deprecate_for_package(package: str) -> bool:
    """Should deprecate for this package?"""
    return bool(package in _NAMESPACES_WITH_DEPRECATION_WARNINGS_IN_0_1)


def create_importer(
    package: str,
    *,
    module_lookup: Optional[Dict[str, str]] = None,
    deprecated_lookups: Optional[Dict[str, str]] = None,
    fallback_module: Optional[str] = None,
) -> Callable[[str], Any]:
    """Create a function that helps retrieve objects from their new locations.

    The goal of this function is to help users transition from deprecated
    imports to new imports.

    The function will raise deprecation warning on loops using
    deprecated_lookups or fallback_module.

    Module lookups will import without deprecation warnings (used to speed
    up imports from large namespaces like llms or chat models).

    This function should ideally only be used with deprecated imports not with
    existing imports that are valid, as in addition to raising deprecation warnings
    the dynamic imports can create other issues for developers (e.g.,
    loss of type information, IDE support for going to definition etc).

    Args:
        package: current package. Use __package__
        module_lookup: maps name of object to the module where it is defined.
            e.g.,
            {
                "MyDocumentLoader": (
                    "langchain_community.document_loaders.my_document_loader"
                )
            }
        deprecated_lookups: same as module look up, but will raise
            deprecation warnings.
        fallback_module: module to import from if the object is not found in
            module_lookup or if module_lookup is not provided.

    Returns:
        A function that imports objects from the specified modules.
    """
    all_module_lookup = {**(deprecated_lookups or {}), **(module_lookup or {})}

    def import_by_name(name: str) -> Any:
        """Import stores from langchain_community."""
        # If not in interactive env, raise warning.
        if all_module_lookup and name in all_module_lookup:
            new_module = all_module_lookup[name]
            if new_module.split(".")[0] not in ALLOWED_TOP_LEVEL_PKGS:
                raise AssertionError(
                    f"Importing from {new_module} is not allowed. "
                    f"Allowed top-level packages are: {ALLOWED_TOP_LEVEL_PKGS}"
                )

            try:
                module = importlib.import_module(new_module)
            except ModuleNotFoundError as e:
                if new_module.startswith("langchain_community"):
                    raise ModuleNotFoundError(
                        f"Module {new_module} not found. "
                        "Please install langchain-community to access this module. "
                        "You can install it using `pip install -U langchain-community`"
                    ) from e
                raise

            try:
                result = getattr(module, name)
                if (
                    not is_interactive_env()
                    and deprecated_lookups
                    and name in deprecated_lookups
                    and _should_deprecate_for_package(package)
                ):
                    warn_deprecated(
                        since="0.1",
                        pending=False,
                        removal="0.4",
                        message=(
                            f"Importing {name} from {package} is deprecated."
                            f"Please replace imports that look like:"
                            f"`from {package} import {name}`\n"
                            "with the following:\n "
                            f"from {new_module} import {name}"
                        ),
                    )
                return result
            except Exception as e:
                raise AttributeError(
                    f"module {new_module} has no attribute {name}"
                ) from e

        if fallback_module:
            try:
                module = importlib.import_module(fallback_module)
                result = getattr(module, name)
                if not is_interactive_env() and _should_deprecate_for_package(package):
                    warn_deprecated(
                        since="0.1",
                        pending=False,
                        removal="0.4",
                        message=(
                            f"Importing {name} from {package} is deprecated."
                            f"Please replace imports that look like:"
                            f"`from {package} import {name}`\n"
                            "with the following:\n "
                            f"from {fallback_module} import {name}"
                        ),
                    )
                return result

            except Exception as e:
                raise AttributeError(
                    f"module {fallback_module} has no attribute {name}"
                ) from e

        raise AttributeError(f"module {package} has no attribute {name}")

    return import_by_name