import logging
from typing import Set, Dict
from backend.orchestrator.models import WorkflowState
from backend.orchestrator.exceptions import InvalidStateTransitionError

logger = logging.getLogger("codex_os.orchestrator.state_machine")

class WorkflowStateMachine:
    """
    Explicit state machine governing autonomous engineering run progression.
    Validates all state transitions and forbids illegal jumps.
    """

    # Explicit mapping of allowed target states for every workflow state
    _ALLOWED_TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
        WorkflowState.PENDING: {
            WorkflowState.ARCHITECTING,
            WorkflowState.BUILDING,
            WorkflowState.CANCELLED,
        },
        WorkflowState.ARCHITECTING: {
            WorkflowState.BUILDING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.BUILDING: {
            WorkflowState.TESTING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.TESTING: {
            WorkflowState.BREAKING,
            WorkflowState.DECIDING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.BREAKING: {
            WorkflowState.SECURITY_SCANNING,
            WorkflowState.DECIDING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.SECURITY_SCANNING: {
            WorkflowState.DECIDING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.DECIDING: {
            WorkflowState.ITERATING,
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.ITERATING: {
            WorkflowState.BUILDING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.PAUSED,
        },
        WorkflowState.PAUSED: {
            WorkflowState.ARCHITECTING,
            WorkflowState.BUILDING,
            WorkflowState.TESTING,
            WorkflowState.BREAKING,
            WorkflowState.SECURITY_SCANNING,
            WorkflowState.DECIDING,
            WorkflowState.ITERATING,
            WorkflowState.CANCELLED,
        },
        # Terminal states: no transitions out
        WorkflowState.COMPLETED: set(),
        WorkflowState.FAILED: set(),
        WorkflowState.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, from_state: WorkflowState | str, to_state: WorkflowState | str) -> bool:
        """Check if transition from from_state to to_state is valid."""
        try:
            curr = WorkflowState(from_state) if isinstance(from_state, str) else from_state
            target = WorkflowState(to_state) if isinstance(to_state, str) else to_state
        except ValueError:
            return False

        if curr == target:
            return True

        allowed = cls._ALLOWED_TRANSITIONS.get(curr, set())
        return target in allowed

    @classmethod
    def transition(cls, current_state: WorkflowState | str, target_state: WorkflowState | str) -> WorkflowState:
        """
        Validate and return the new state.
        Raises InvalidStateTransitionError if the transition is illegal.
        """
        try:
            curr = WorkflowState(current_state) if isinstance(current_state, str) else current_state
        except ValueError:
            raise InvalidStateTransitionError(str(current_state), str(target_state), "Unknown source state")

        try:
            target = WorkflowState(target_state) if isinstance(target_state, str) else target_state
        except ValueError:
            raise InvalidStateTransitionError(str(current_state), str(target_state), "Unknown target state")

        if not cls.can_transition(curr, target):
            msg = f"Cannot transition from {curr.value} to {target.value}"
            logger.warning(msg)
            raise InvalidStateTransitionError(curr.value, target.value, msg)

        logger.debug(f"State transition: {curr.value} -> {target.value}")
        return target

    @classmethod
    def is_terminal(cls, state: WorkflowState | str) -> bool:
        """Returns True if the state is terminal (COMPLETED, FAILED, CANCELLED)."""
        val = state.value if isinstance(state, WorkflowState) else state
        return val in (WorkflowState.COMPLETED.value, WorkflowState.FAILED.value, WorkflowState.CANCELLED.value)
