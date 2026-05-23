"""Infrastructure for agent recovery and re-instantiation."""

from __future__ import annotations

from typing import Any, Callable, Dict

from debate_sdk.shared.logger import setup_logger

logger = setup_logger("recovery")


class RecoveryManager:
    """
    Orchestrates the re-spawning of agents after a failure.

    Attributes:
        factories (Dict[str, Callable[..., Any]]): Map of agent types to spawn functions.
    """

    def __init__(self) -> None:
        """Initialize the RecoveryManager."""
        self.factories: Dict[str, Callable[..., Any]] = {}

    def register_factory(self, agent_type: str, factory: Callable[..., Any]) -> None:
        """
        Register a factory function for a specific agent type.

        Args:
            agent_type (str): Type identifier (e.g., 'pro', 'con').
            factory (Callable): Function that creates and starts the agent.
        """
        self.factories[agent_type] = factory
        logger.info(f"Registered recovery factory for agent type '{agent_type}'")

    def recover(self, agent_id: str, agent_type: str, state: Dict[str, Any]) -> Any:
        """
        Re-spawn an agent and inject its prior state.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_type (str): Type of agent to spawn.
            state (Dict[str, Any]): Historical context to inject.

        Returns:
            Any: The newly spawned agent instance.
        """
        factory = self.factories.get(agent_type)
        if not factory:
            logger.error(f"No factory registered for agent type '{agent_type}'")
            return None

        logger.info(f"Recovering agent '{agent_id}' of type '{agent_type}'...")
        try:
            return factory(agent_id=agent_id, state=state)
        except Exception as exc:
            logger.error(f"Failed to recover agent '{agent_id}': {exc}")
            return None
