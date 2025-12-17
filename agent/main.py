from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    WorkerType,
    cli,
    function_tool,
    utils,
)
from livekit.plugins import xai
from xai_sdk import Client

load_dotenv(dotenv_path=".env.local")

logger = logging.getLogger("grok-playground")
logger.setLevel(logging.INFO)

# Suppress OpenTelemetry attribute warnings
logging.getLogger("opentelemetry.attributes").setLevel(logging.ERROR)


@dataclass
class SessionConfig:
    xai_api_key: str
    instructions: str
    model: str
    voice: str
    temperature: float
    max_response_output_tokens: str | int
    modalities: list[str]
    grok_image_enabled: bool = False

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if k != "xai_api_key"}

    @staticmethod
    def _modalities_from_string(
        modalities: str,
    ) -> list[str]:
        modalities_map: Dict[str, List[str]] = {
            "text_and_audio": ["text", "audio"],
            "text_only": ["text"],
            "audio_only": ["audio"],
        }
        return modalities_map.get(modalities, modalities_map["audio_only"])

    def __eq__(self, other) -> bool:
        return self.to_dict() == other.to_dict()


def parse_session_config(data: Dict[str, Any]) -> SessionConfig:
    # Parse grok_image_enabled - handle both boolean and string types
    grok_image_value = data.get("grok_image_enabled", False)
    if isinstance(grok_image_value, bool):
        grok_image_enabled = grok_image_value
    elif isinstance(grok_image_value, str):
        grok_image_enabled = grok_image_value.lower() == "true"
    else:
        grok_image_enabled = bool(grok_image_value)
    
    logger.debug(f"Parsing config - grok_image_enabled: {grok_image_value} (type: {type(grok_image_value).__name__}) -> {grok_image_enabled}")
    
    config = SessionConfig(
        xai_api_key=data.get("xai_api_key", ""),
        instructions=data.get("instructions", ""),
        model=data.get("model", "grok-1118"),
        voice=data.get("voice", "ara"),
        temperature=float(data.get("temperature", 0.8)),
        max_response_output_tokens=
            "inf" if data.get("max_output_tokens") == "inf"
            else int(data.get("max_output_tokens") or 2048),
        modalities=SessionConfig._modalities_from_string(
            data.get("modalities", "audio_only")
        ),
        grok_image_enabled=grok_image_enabled,
    )
    return config


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    
    # Parse metadata with error handling
    try:
        metadata = json.loads(participant.metadata) if participant.metadata else {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse participant metadata: {e}. Using default config.")
        metadata = {}
    
    config = parse_session_config(metadata)
    
    session_manager = SessionManager(config)
    await session_manager.start_session(ctx, participant)

    logger.info("agent started")


def create_generate_image_tool(session_manager):
    """Factory function to create the generate_image tool with access to session_manager"""

    raw_schema = {
        "type": "function",
        "name": "generate_image",
        "description": "Generate an image using Grok Image Generation and send it to the user",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Creative, detailed, and sophisticated description of the image to generate (e.g., 'a futuristic city with flying cars at sunset'), not simply a few words. Not a generic prompt such as 'image of a cat' or 'random image'."
                }
            },
            "required": [
                "prompt"
            ],
            "additionalProperties": False
        }
    }
    
    @function_tool(raw_schema=raw_schema)
    async def generate_image(raw_arguments: dict) -> str:
        # Extract prompt from raw_arguments when using raw_schema
        prompt = raw_arguments["prompt"]
        
        try:
            # Use xAI SDK for image generation
            client = Client(api_key=session_manager.current_config.xai_api_key)
            
            # Run synchronous image generation in a thread to avoid blocking event loop
            response = await asyncio.to_thread(
                lambda: client.image.sample(
                    model='grok-2-image',
                    prompt=prompt,
                    image_format="base64"
                )
            )
            
            # Get the image bytes from response
            image_bytes = response.image
            
            # Compress the image to reduce size
            img = Image.open(BytesIO(image_bytes))
            # Resize to max 512x512 to keep it small
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            # Save to bytes buffer
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=90, optimize=True)
            image_data = buffer.getvalue()
            
            # Send image to frontend using LiveKit's stream_bytes
            if session_manager.ctx and session_manager.participant:
                await session_manager.send_image_to_frontend(prompt, image_data)
            
            return "I've generated the image and sent it to your screen!"
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return f"Sorry, I couldn't generate that image. Error: {str(e)}"
    
    return generate_image


class PlaygroundAgent(Agent):
    """Custom agent class for the playground"""
    def __init__(self, instructions: str, tools=None, chat_ctx=None):
        if chat_ctx:
            super().__init__(instructions=instructions, tools=tools or [], chat_ctx=chat_ctx)
        else:
            super().__init__(instructions=instructions, tools=tools or [])
        self.session_manager = None


class SessionManager:
    def __init__(self, config: SessionConfig):
        self.current_session: AgentSession | None = None
        self.current_config: SessionConfig = config
        self.ctx: JobContext | None = None
        self.participant: rtc.RemoteParticipant | None = None
        self.current_agent: PlaygroundAgent | None = None

    def create_session(self, config: SessionConfig) -> AgentSession:
        """Create an AgentSession with the given configuration"""
        session = AgentSession(
            llm=xai.RealtimeModel(
                voice=config.voice,
                api_key=config.xai_api_key,
            )
        )
        return session

    async def start_session(self, ctx: JobContext, participant: rtc.RemoteParticipant):
        """Start the initial agent session"""
        self.ctx = ctx
        self.participant = participant
        
        # Conditionally add Grok image generation tool
        tools = []
        if self.current_config.grok_image_enabled:
            logger.info("Grok Image Generation tool enabled 🎨")
            tools.append(create_generate_image_tool(self))
        
        self.current_session = self.create_session(self.current_config)
        self.current_agent = PlaygroundAgent(
            instructions=self.current_config.instructions,
            tools=tools
        )
        
        await self.current_session.start(
            room=ctx.room,
            agent=self.current_agent,
        )
        
        # Greet the user
        await self.current_session.generate_reply(
            instructions="Please begin the interaction with the user in a manner consistent with your instructions."
        )

        # Register RPC method for config updates
        @ctx.room.local_participant.register_rpc_method("pg.updateConfig")
        async def update_config(data: rtc.rpc.RpcInvocationData):
            logger.info(f"update_config called by {data.caller_identity}: {data.payload}")
            if self.current_session is None or data.caller_identity != participant.identity:
                logger.info("update_config called by non-participant or no session")
                return json.dumps({"changed": False})

            new_config = parse_session_config(json.loads(data.payload))
            if self.current_config != new_config:
                logger.info(
                    f"config changed: {new_config.to_dict()}, participant: {participant.identity}"
                )
                # Pass old config before updating, so replace_session can detect what changed
                old_config = self.current_config
                self.current_config = new_config
                await self.replace_session(ctx, participant, new_config, old_config)
                return json.dumps({"changed": True})
            else:
                logger.info("config not changed at all")
                return json.dumps({"changed": False})

    async def send_image_to_frontend(self, prompt: str, image_data: bytes):
        if not self.ctx or not self.participant:
            logger.warning("Cannot send image: no context or participant")
            return

        try:
            # Stream the image using LiveKit's stream_bytes API with attributes
            writer = await self.ctx.room.local_participant.stream_bytes(
                name="generated_image.jpg",
                total_size=len(image_data),
                mime_type="image/jpeg",
                topic="grok_image",
                destination_identities=[self.participant.identity],
                attributes={"prompt": prompt, "type": "grok_image"},
            )
            
            # Write the image data and close the stream
            await writer.write(image_data)
            await writer.aclose()
            
            logger.info(f"Image streamed to frontend, prompt: {prompt}")
        except Exception as e:
            logger.error(f"Failed to send image to frontend: {e}")

    @utils.log_exceptions(logger=logger)
    async def replace_session(self, ctx: JobContext, participant: rtc.RemoteParticipant, config: SessionConfig, old_config: SessionConfig):
        """Replace the current session with a new one using updated config"""
        if self.current_session is None or self.current_agent is None:
            return
        
        # Try to preserve chat context from current agent
        chat_ctx = None
        try:
            if hasattr(self.current_agent, 'chat_ctx'):
                chat_ctx = self.current_agent.chat_ctx
        except Exception as e:
            logger.warning(f"Could not preserve chat context: {e}")
        
        # Track if Grok image is being newly enabled (compare old vs new config)
        was_grok_image_enabled = old_config.grok_image_enabled
        is_grok_image_enabled = config.grok_image_enabled
        grok_image_newly_enabled = not was_grok_image_enabled and is_grok_image_enabled
        
        logger.info(f"Image Generation status: was={was_grok_image_enabled}, now={is_grok_image_enabled}, newly_enabled={grok_image_newly_enabled}")
        
        # End current session
        await self.current_session.aclose()
        
        # Conditionally add Grok image generation tool
        tools = []
        if config.grok_image_enabled:
            tools.append(create_generate_image_tool(self))
        
        # Create new session with updated config
        self.current_session = self.create_session(config)
        
        # Create new agent, passing chat_ctx if available
        self.current_agent = PlaygroundAgent(
            instructions=config.instructions,
            tools=tools,
            chat_ctx=chat_ctx
        )
        
        await self.current_session.start(
            room=ctx.room,
            agent=self.current_agent,
        )
        
        # Notify user about the config change
        try:
            if grok_image_newly_enabled:
                logger.info("Grok Image Generation tool newly enabled")
                await self.current_session.generate_reply(
                    instructions="Briefly and enthusiastically announce: 'Grok Image Generation is now active! Feel free to ask me to generate an image and I can show you whatever you like!'",
                )
            else:
                logger.info("Session restarted with new config")
                await self.current_session.generate_reply(
                    instructions=is_grok_image_enabled and "Briefly acknowledge that your configuration has been updated and you're ready to continue and announce that you can also generate images now!" or "Briefly acknowledge that your configuration has been updated and you're ready to continue"
                )
        except Exception as e:
            logger.error(f"Failed to notify user about config change: {e}")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(agent_name='grok-playground', entrypoint_fnc=entrypoint, worker_type=WorkerType.ROOM))
