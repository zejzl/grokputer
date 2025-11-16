"""
Limbo Autobet Agent for Grokputer

Autonomous betting agent for Limbo game:
- Targets 1.38x profit multiplier
- Increases bet by 25% on loss
- Uses vision/OCR to detect game state
- Integrates with Actor for automated betting
- Runs in background with safety checks

Extends BaseAgent for lifecycle management.
"""

import asyncio
import logging
import re
import time
from typing import Any, Dict, Optional, Tuple

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority
from src.observability.session_logger import SessionLogger

logger = logging.getLogger(__name__)


class LimboAutobetAgent(BaseAgent):
    """
    Limbo Autobet Agent: Autonomous profit-making betting system.

    Strategy:
    - Base bet: configurable
    - Profit target: 1.38x overall multiplier
    - Loss handling: +25% bet increase
    - Win handling: reset to base bet

    Safety:
    - Balance limits (min/max)
    - Stop loss protection
    - Emergency stop on errors
    - Manual override capability
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config: Dict[str, Any],
        heartbeat_interval: float = 30.0,
        agent_id: str = "limbo_autobet",
    ):
        super().__init__(agent_id, message_bus, session_logger, config, heartbeat_interval)

        # Betting configuration
        self.base_bet = config.get("base_bet", 0.01)  # Starting bet amount
        self.profit_target = config.get("profit_target", 1.38)  # 1.38x target
        self.loss_increase = config.get("loss_increase", 0.25)  # 25% increase on loss
        self.target_multiplier = config.get("target_multiplier", 1.38)  # Target multiplier for bets
        self.max_bet = config.get("max_bet", 1.0)  # Maximum bet limit
        self.min_balance = config.get("min_balance", 0.1)  # Stop if balance below this
        self.stop_loss = config.get("stop_loss", 0.5)  # Stop if losses exceed this amount

        # Game state
        self.current_bet = self.base_bet
        self.starting_balance = 0.0
        self.current_balance = 0.0
        self.total_profit = 0.0
        self.bets_placed = 0
        self.wins = 0
        self.losses = 0
        self.consecutive_losses = 0

        # Control flags
        self.running_bets = False
        self.emergency_stop = False

        # UI positions (to be detected or configured)
        self.bet_input_pos = config.get("bet_input_pos", (100, 200))  # x,y for bet input
        self.multiplier_input_pos = config.get("multiplier_input_pos", (200, 200))  # x,y for multiplier
        self.bet_button_pos = config.get("bet_button_pos", (300, 200))  # x,y for bet button

        # OCR patterns for balance/result detection
        self.balance_pattern = re.compile(r'Balance:\s*\$?(\d+\.?\d*)')
        self.result_pattern = re.compile(r'(?:Multiplier|Result):\s*(\d+\.?\d*)x?')

        logger.info(f"[LimboAutobet] Initialized with base_bet={self.base_bet}, target={self.profit_target}x")

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process incoming messages.

        Handles:
        - start_betting: Begin autonomous betting
        - stop_betting: Stop betting
        - status: Get current status
        - reset: Reset betting state
        """
        msg_type = message.message_type
        content = message.content

        if msg_type == "start_betting":
            return await self._handle_start_betting(content)
        elif msg_type == "stop_betting":
            return await self._handle_stop_betting()
        elif msg_type == "status":
            return await self._handle_status()
        elif msg_type == "reset":
            return await self._handle_reset()
        elif msg_type == "emergency_stop":
            return await self._handle_emergency_stop()
        else:
            logger.warning(f"[LimboAutobet] Unknown message type: {msg_type}")
            return None

    async def _handle_start_betting(self, params: Dict) -> Dict:
        """Start autonomous betting loop."""
        if self.running_bets:
            return {
                "to": "coordinator",
                "type": "response",
                "content": {"status": "error", "error": "Betting already running"},
                "priority": MessagePriority.NORMAL,
            }

        # Initialize starting balance
        self.starting_balance = params.get("starting_balance", 0.0)
        if self.starting_balance == 0.0:
            # Try to detect from screen
            detected_balance = await self._detect_balance()
            if detected_balance:
                self.starting_balance = detected_balance
            else:
                return {
                    "to": "coordinator",
                    "type": "response",
                    "content": {"status": "error", "error": "Could not detect starting balance"},
                    "priority": MessagePriority.NORMAL,
                }

        self.current_balance = self.starting_balance
        self.running_bets = True
        self.emergency_stop = False

        # Start betting loop
        asyncio.create_task(self._betting_loop())

        logger.info(f"[LimboAutobet] Started betting with balance: {self.starting_balance}")
        return {
            "to": "coordinator",
            "type": "response",
            "content": {"status": "success", "message": "Betting started"},
            "priority": MessagePriority.NORMAL,
        }

    async def _handle_stop_betting(self) -> Dict:
        """Stop autonomous betting."""
        self.running_bets = False
        logger.info("[LimboAutobet] Stopped betting")
        return {
            "to": "coordinator",
            "type": "response",
            "content": {"status": "success", "message": "Betting stopped"},
            "priority": MessagePriority.NORMAL,
        }

    async def _handle_status(self) -> Dict:
        """Get current betting status."""
        return {
            "to": "coordinator",
            "type": "response",
            "content": {
                "status": "success",
                "running": self.running_bets,
                "current_bet": self.current_bet,
                "current_balance": self.current_balance,
                "total_profit": self.total_profit,
                "profit_multiplier": self.current_balance / self.starting_balance if self.starting_balance > 0 else 0,
                "bets_placed": self.bets_placed,
                "wins": self.wins,
                "losses": self.losses,
                "win_rate": f"{self.wins / max(self.bets_placed, 1) * 100:.1f}%" if self.bets_placed > 0 else "0%",
            },
            "priority": MessagePriority.NORMAL,
        }

    async def _handle_reset(self) -> Dict:
        """Reset betting state."""
        self._reset_state()
        logger.info("[LimboAutobet] State reset")
        return {
            "to": "coordinator",
            "type": "response",
            "content": {"status": "success", "message": "State reset"},
            "priority": MessagePriority.NORMAL,
        }

    async def _handle_emergency_stop(self) -> Dict:
        """Emergency stop betting."""
        self.emergency_stop = True
        self.running_bets = False
        logger.warning("[LimboAutobet] Emergency stop activated")
        return {
            "to": "coordinator",
            "type": "response",
            "content": {"status": "success", "message": "Emergency stop activated"},
            "priority": MessagePriority.HIGH,
        }

    def _reset_state(self):
        """Reset all betting state."""
        self.current_bet = self.base_bet
        self.starting_balance = 0.0
        self.current_balance = 0.0
        self.total_profit = 0.0
        self.bets_placed = 0
        self.wins = 0
        self.losses = 0
        self.consecutive_losses = 0
        self.running_bets = False
        self.emergency_stop = False

    async def _betting_loop(self):
        """Main autonomous betting loop."""
        logger.info("[LimboAutobet] Starting betting loop")

        while self.running_bets and not self.emergency_stop:
            try:
                # Check if we should stop
                if self._should_stop():
                    logger.info("[LimboAutobet] Stopping due to safety conditions")
                    self.running_bets = False
                    break

                # Place bet
                await self._place_bet()

                # Wait for result (adjust timing based on game)
                await asyncio.sleep(3)  # Wait 3 seconds for result

                # Check result
                won, multiplier = await self._check_result()

                # Update state
                self._update_state(won, multiplier)

                # Wait between bets
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[LimboAutobet] Error in betting loop: {e}")
                self.emergency_stop = True
                break

        logger.info("[LimboAutobet] Betting loop ended")

    async def _place_bet(self):
        """Place a bet using Actor agent."""
        logger.info(f"[LimboAutobet] Placing bet: {self.current_bet}")

        # Click on multiplier input field
        click_multiplier_msg = Message(
            from_agent=self.agent_id,
            to_agent="actor",
            message_type="act",
            content={
                "type": "pyautogui_click",
                "params": {"x": self.multiplier_input_pos[0], "y": self.multiplier_input_pos[1]},
                "safety_level": "low"
            },
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(click_multiplier_msg)

        # Type target multiplier
        type_multiplier_msg = Message(
            from_agent=self.agent_id,
            to_agent="actor",
            message_type="act",
            content={
                "type": "pyautogui_type",
                "params": {"text": f"{self.target_multiplier:.2f}"},
                "safety_level": "low"
            },
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(type_multiplier_msg)

        # Click on bet input field
        click_input_msg = Message(
            from_agent=self.agent_id,
            to_agent="actor",
            message_type="act",
            content={
                "type": "pyautogui_click",
                "params": {"x": self.bet_input_pos[0], "y": self.bet_input_pos[1]},
                "safety_level": "low"
            },
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(click_input_msg)

        # Type bet amount
        type_bet_msg = Message(
            from_agent=self.agent_id,
            to_agent="actor",
            message_type="act",
            content={
                "type": "pyautogui_type",
                "params": {"text": f"{self.current_bet:.4f}"},
                "safety_level": "low"
            },
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(type_bet_msg)

        # Click bet button
        click_bet_msg = Message(
            from_agent=self.agent_id,
            to_agent="actor",
            message_type="act",
            content={
                "type": "pyautogui_click",
                "params": {"x": self.bet_button_pos[0], "y": self.bet_button_pos[1]},
                "safety_level": "low"
            },
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(click_bet_msg)

    async def _check_result(self) -> Tuple[bool, float]:
        """Check if the bet won and get multiplier."""
        # Capture screen and analyze
        # TODO: Use Observer agent to capture and analyze screen

        # For now, simulate detection
        # In real implementation, use OCR/vision to read result
        detected_result = await self._detect_result()

        if detected_result:
            multiplier = detected_result
            won = multiplier >= 1.0  # Assuming 1.0x is break-even
            return won, multiplier
        else:
            # Assume loss if can't detect
            return False, 0.0

    async def _detect_balance(self) -> Optional[float]:
        """Detect current balance from screen using vision analysis."""
        try:
            # Send message to observer to capture and analyze screen
            observer_msg = Message(
                from_agent=self.agent_id,
                to_agent="observer",
                message_type="capture_screen",
                content={
                    "task_id": f"balance_check_{int(time.time())}",
                    "region": None,  # Full screen
                },
                priority=MessagePriority.NORMAL,
            )
            await self.message_bus.send(observer_msg)

            # Wait for response (simplified - in practice need correlation)
            # For now, assume we get the response
            # TODO: Implement proper response waiting

            # Parse analysis for balance
            # Assume analysis contains text we can regex
            # This is a placeholder - in real implementation, parse the analysis content
            return 1.0  # Placeholder balance

        except Exception as e:
            logger.error(f"[LimboAutobet] Balance detection failed: {e}")
            return None

    async def _detect_result(self) -> Optional[float]:
        """Detect bet result (multiplier) from screen after bet."""
        try:
            # Send message to observer to capture and analyze screen
            observer_msg = Message(
                from_agent=self.agent_id,
                to_agent="observer",
                message_type="capture_screen",
                content={
                    "task_id": f"result_check_{int(time.time())}",
                    "region": None,  # Full screen
                },
                priority=MessagePriority.NORMAL,
            )
            await self.message_bus.send(observer_msg)

            # Wait for response (simplified)
            # Parse analysis for result multiplier
            # Assume analysis contains "Multiplier: 1.45x" or similar
            # This is a placeholder - in real implementation, parse the analysis content
            return 1.45  # Placeholder result

        except Exception as e:
            logger.error(f"[LimboAutobet] Result detection failed: {e}")
            return None

    def _update_state(self, won: bool, multiplier: float):
        """Update betting state after a bet."""
        self.bets_placed += 1

        if won:
            self.wins += 1
            self.consecutive_losses = 0
            # Calculate winnings
            winnings = self.current_bet * multiplier
            self.current_balance += winnings - self.current_bet
            # Reset to base bet
            self.current_bet = self.base_bet
        else:
            self.losses += 1
            self.consecutive_losses += 1
            # Loss: increase bet
            self.current_balance -= self.current_bet
            self.current_bet = min(self.current_bet * (1 + self.loss_increase), self.max_bet)

        self.total_profit = self.current_balance - self.starting_balance

        logger.info(f"[LimboAutobet] Bet {self.bets_placed}: {'WIN' if won else 'LOSS'} {multiplier:.2f}x, Balance: {self.current_balance:.4f}")

    def _should_stop(self) -> bool:
        """Check if betting should stop for safety."""
        if self.emergency_stop:
            logger.warning("[LimboAutobet] Emergency stop activated")
            return True

        if self.current_balance < self.min_balance:
            logger.warning(f"[LimboAutobet] Balance below minimum: {self.current_balance}")
            return True

        if self.starting_balance - self.current_balance > self.stop_loss:
            logger.warning(f"[LimboAutobet] Stop loss triggered: {self.starting_balance - self.current_balance}")
            return True

        if self.current_bet > self.max_bet:
            logger.warning(f"[LimboAutobet] Bet exceeds maximum: {self.current_bet}")
            return True

        if self.consecutive_losses > 10:  # Max consecutive losses
            logger.warning(f"[LimboAutobet] Too many consecutive losses: {self.consecutive_losses}")
            return True

        profit_multiplier = self.current_balance / self.starting_balance if self.starting_balance > 0 else 0
        if profit_multiplier >= self.profit_target:
            logger.info(f"[LimboAutobet] Profit target reached: {profit_multiplier:.2f}x")
            return True

        return False

    async def on_start(self):
        """Agent startup."""
        logger.info("[LimboAutobet] Starting Limbo autobet agent")

    async def on_stop(self):
        """Agent shutdown."""
        self.running_bets = False
        logger.info("[LimboAutobet] Stopping Limbo autobet agent")
        logger.info(f"[LimboAutobet] Final stats: {await self._handle_status()}")