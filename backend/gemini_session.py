"""Gemini Live API session manager using google-genai SDK directly."""

import asyncio
import json
import logging
from typing import Any, Callable

from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI doorbell assistant for {owner_name}'s home. You can see \
visitors through the doorbell camera and have natural voice conversations with them.

## Your Responsibilities
1. Greet every visitor politely
2. Identify who they are and what they want through natural conversation
3. Use your tools to verify information:
   - Delivery? → check_gmail_orders to match with expected packages
   - Says a name? → check_known_faces + check_calendar
   - Can't verify? → ask follow-up questions, capture photo
4. Send appropriate alerts to the homeowner via send_telegram_alert
5. Handle the situation based on verification result:
   - Verified delivery: Thank them, instruct door placement
   - Known person + appointment: Greet warmly, notify owner, await instruction
   - Unknown but cooperative: Ask details, notify owner
   - Cannot verify + evasive: Stay polite, don't reveal info, capture photo, high-urgency alert

## House Rules
- Owner: {owner_name}
- Language: {language}
- Delivery instructions: {delivery_instructions}
- Personality: Friendly and warm, like a helpful building concierge

## Critical Behaviors
- You can be interrupted — handle it gracefully
- Keep responses concise (1-2 sentences)
- Never reveal you are AI unless directly asked
- Never reveal personal information about the homeowner
- Always call send_telegram_alert for every visitor
- For suspicious visitors: be polite but firm, capture photo, alert owner immediately
- When owner sends a command via Telegram, relay it naturally to the visitor
"""

TOOL_DECLARATIONS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="check_gmail_orders",
                description=(
                    "Check Gmail for recent online orders and delivery notifications. "
                    "Call when a delivery person arrives to match the package with an expected order."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "keywords": types.Schema(
                            type=types.Type.STRING,
                            description="Search keywords like carrier name or description",
                        )
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="check_calendar",
                description=(
                    "Check Google Calendar for today's appointments. "
                    "Call when a visitor claims to have an appointment or gives a name."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "visitor_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the visitor",
                        )
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="check_known_faces",
                description=(
                    "Check if the visitor is a registered known person. "
                    "Call when a visitor gives their name."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the visitor",
                        )
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="send_telegram_alert",
                description=(
                    "Send alert to homeowner via Telegram. Call for every visitor interaction."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "urgency": types.Schema(
                            type=types.Type.STRING,
                            enum=["low", "medium", "high"],
                            description="low=delivery/known, medium=unknown cooperative, high=suspicious/unverified",
                        ),
                        "visitor_type": types.Schema(
                            type=types.Type.STRING,
                            enum=["delivery", "known_person", "unknown", "suspicious"],
                        ),
                        "summary": types.Schema(
                            type=types.Type.STRING,
                            description="Brief summary for the homeowner",
                        ),
                        "capture_photo": types.Schema(
                            type=types.Type.BOOLEAN,
                            description="Whether to capture and attach photo. Always true for suspicious visitors.",
                        ),
                    },
                    required=["urgency", "visitor_type", "summary", "capture_photo"],
                ),
            ),
            types.FunctionDeclaration(
                name="capture_screenshot",
                description=(
                    "Capture current camera frame and save to storage. "
                    "Call immediately when encountering suspicious visitors."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={},
                ),
            ),
        ]
    )
]


class GeminiSession:
    """Manages a Gemini Live API session with tool calling and session resumption."""

    def __init__(self, tool_handlers: dict[str, Callable] | None = None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.tool_handlers = tool_handlers or {}
        self.session = None
        self._resumption_handle: str = ""
        self._last_video_frame: bytes | None = None
        self._running = False
        self._receive_task: asyncio.Task | None = None

        # Callbacks for forwarding data to the WebSocket client
        self.on_audio: Callable[[bytes], Any] | None = None
        self.on_subtitle: Callable[[str, str], Any] | None = None
        self.on_tool_call_start: Callable[[str], Any] | None = None
        self.on_interrupted: Callable[[], Any] | None = None

    def _build_config(self) -> types.LiveConnectConfig:
        system_prompt = SYSTEM_PROMPT.format(
            owner_name=settings.OWNER_NAME,
            language=settings.LANGUAGE,
            delivery_instructions=settings.DELIVERY_INSTRUCTIONS,
        )

        return types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=types.Content(
                parts=[types.Part(text=system_prompt)]
            ),
            tools=TOOL_DECLARATIONS,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=100000,
                sliding_window=types.SlidingWindow(target_tokens=50000),
            ),
            session_resumption=types.SessionResumptionConfig(
                handle=self._resumption_handle
            ),
        )

    async def connect(self):
        """Establish a Gemini Live API session."""
        config = self._build_config()
        self.session = await self.client.aio.live.connect(
            model=settings.GEMINI_MODEL,
            config=config,
        ).__aenter__()
        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.info("Gemini session connected")

    async def disconnect(self):
        """Gracefully close the Gemini session."""
        self._running = False
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None
        logger.info("Gemini session disconnected")

    async def send_audio(self, audio_data: bytes):
        """Send audio PCM data to Gemini. Use audio key, NOT media."""
        if not self.session:
            return
        await self.session.send_realtime_input(
            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
        )

    async def send_video(self, jpeg_frame: bytes):
        """Send a JPEG video frame to Gemini. Use video key, NOT media."""
        if not self.session:
            return
        self._last_video_frame = jpeg_frame
        await self.session.send_realtime_input(
            video=types.Blob(data=jpeg_frame, mime_type="image/jpeg")
        )

    async def send_audio_stream_end(self):
        """Send audioStreamEnd to flush cached audio when mic is paused."""
        if not self.session:
            return
        await self.session.send_realtime_input(audio_stream_end=True)

    async def inject_text(self, text: str):
        """Inject text input (e.g., Telegram owner command) into the session."""
        if not self.session:
            return
        await self.session.send_realtime_input(text=text)

    def get_last_frame(self) -> bytes | None:
        """Get the most recent video frame for screenshot capture."""
        return self._last_video_frame

    async def _receive_loop(self):
        """Main loop to receive and process messages from Gemini."""
        try:
            while self._running and self.session:
                async for response in self.session.receive():
                    if not self._running:
                        break
                    await self._handle_response(response)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Gemini receive loop error: %s", e)
            await self._attempt_resumption()

    async def _handle_response(self, response):
        """Process a single response from Gemini."""
        server_content = getattr(response, "server_content", None)
        tool_call = getattr(response, "tool_call", None)
        session_resumption_update = getattr(
            response, "session_resumption_update", None
        )
        go_away = getattr(response, "go_away", None)

        # Audio response
        if server_content and server_content.model_turn:
            for part in server_content.model_turn.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                    if self.on_audio:
                        await self._call(self.on_audio, part.inline_data.data)

        # Input transcription (visitor subtitle)
        if server_content and hasattr(server_content, "input_transcription"):
            transcript = server_content.input_transcription
            if transcript and transcript.text:
                if self.on_subtitle:
                    await self._call(self.on_subtitle, transcript.text, "visitor")

        # Output transcription (AI subtitle)
        if server_content and hasattr(server_content, "output_transcription"):
            transcript = server_content.output_transcription
            if transcript and transcript.text:
                if self.on_subtitle:
                    await self._call(self.on_subtitle, transcript.text, "ai")

        # Interrupted
        if server_content and getattr(server_content, "interrupted", False):
            if self.on_interrupted:
                await self._call(self.on_interrupted)

        # Tool calls
        if tool_call and tool_call.function_calls:
            await self._handle_tool_calls(tool_call.function_calls)

        # Session resumption update — store handle for reconnection
        if session_resumption_update:
            new_handle = getattr(session_resumption_update, "handle", "")
            if new_handle:
                self._resumption_handle = new_handle
                logger.info("Session resumption handle updated")

        # GoAway signal — proactively reconnect
        if go_away:
            logger.warning("Received GoAway signal, triggering session resumption")
            await self._attempt_resumption()

    async def _handle_tool_calls(self, function_calls):
        """Dispatch tool calls and return results to Gemini."""
        responses = []
        for fc in function_calls:
            handler = self.tool_handlers.get(fc.name)
            if handler:
                if self.on_tool_call_start:
                    await self._call(self.on_tool_call_start, fc.name)
                try:
                    args = dict(fc.args) if fc.args else {}
                    result = await handler(**args)
                    responses.append(
                        types.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                except Exception as e:
                    logger.error("Tool %s failed: %s", fc.name, e)
                    responses.append(
                        types.FunctionResponse(
                            name=fc.name,
                            response={"error": str(e)},
                        )
                    )
            else:
                logger.warning("Unknown tool: %s", fc.name)
                responses.append(
                    types.FunctionResponse(
                        name=fc.name,
                        response={"error": f"Unknown tool: {fc.name}"},
                    )
                )

        if responses and self.session:
            await self.session.send_tool_response(responses)

    async def _attempt_resumption(self):
        """Attempt session resumption with stored handle."""
        if not self._resumption_handle:
            logger.error("No resumption handle available, cannot resume session")
            return

        logger.info("Attempting session resumption...")
        max_retries = 3
        backoff = 1

        for attempt in range(max_retries):
            try:
                if self.session:
                    try:
                        await self.session.__aexit__(None, None, None)
                    except Exception:
                        pass

                config = self._build_config()
                self.session = await self.client.aio.live.connect(
                    model=settings.GEMINI_MODEL,
                    config=config,
                ).__aenter__()
                logger.info("Session resumed successfully on attempt %d", attempt + 1)
                return
            except Exception as e:
                logger.error(
                    "Resumption attempt %d failed: %s", attempt + 1, e
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2

        logger.error("All resumption attempts failed")

    @staticmethod
    async def _call(callback, *args):
        """Call a callback, handling both sync and async."""
        result = callback(*args)
        if asyncio.iscoroutine(result):
            await result
