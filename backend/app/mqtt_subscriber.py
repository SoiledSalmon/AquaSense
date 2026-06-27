"""MQTT Subscriber Service.

Subscribes to ThingSpeak MQTT broker to receive live water quality readings,
validates them, inserts them into the PostgreSQL readings table, and handles
reconnections with exponential backoff and REST API catch-up.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Set, Dict

import httpx
import structlog
from pydantic import BaseModel, Field

import aiomqtt
from app.core.config import get_settings
from app.repositories.readings_repository import ReadingsRepository
from app.services.ml_pipeline import ml_pipeline

logger = structlog.get_logger()


class ReadingInsert(BaseModel):
    """Pydantic model for validation of readings before DB insertion."""
    timestamp: datetime
    user_id: str
    ph: Optional[float] = Field(None, ge=0.0, le=14.0)
    tds: Optional[float] = Field(None, ge=0.0, le=5000.0)
    turbidity: Optional[float] = Field(None, ge=0.0, le=5000.0)
    wqi_score: Optional[float] = None
    label: Optional[str] = None


def parse_float(val: Optional[str]) -> Optional[float]:
    """Safely parse string values from ThingSpeak payload to floats."""
    if val is None:
        return None
    val_str = str(val).strip()
    if val_str == "" or val_str.lower() in ("nan", "null", "none"):
        return None
    try:
        return float(val_str)
    except ValueError:
        return None


# Global registry of subscriptions to avoid duplicate subscriptions
_subscribed_channels: Set[str] = set()
_channel_to_user_map: Dict[str, dict] = {}


async def get_active_users(supabase_admin) -> list[dict]:
    """Fetch all users who have a channel_id configured."""
    try:
        response = (
            supabase_admin.table("users")
            .select("id, channel_id, ts_api_key")
            .not_.is_("channel_id", "null")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error("mqtt_get_active_users_error", error=str(e))
        return []


async def catch_up_user(user: dict, supabase_admin, settings, repo: ReadingsRepository):
    """Fetch missed readings from ThingSpeak REST API for the user's channel."""
    user_id = user["id"]
    channel_id = user["channel_id"]
    ts_api_key = user.get("ts_api_key") or settings.THINGSPEAK_REST_API_KEY

    # 1. Query the latest reading's timestamp from our DB
    last_ts = await repo.get_latest_reading_timestamp(user_id)

    # 2. Set start time (either last stored timestamp or default to 24h ago)
    if last_ts:
        # Use UTC timestamp string format for ThingSpeak GET (YYYY-MM-DD HH:MM:SS)
        # Convert timezone-aware datetime to UTC first
        last_ts_utc = last_ts.astimezone(timezone.utc)
        start_str = last_ts_utc.strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    logger.info("mqtt_catch_up_start", user_id=user_id, channel_id=channel_id, start_time=start_str)

    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
    params = {"start": start_str}
    if ts_api_key:
        params["api_key"] = ts_api_key

    async with httpx.AsyncClient() as http_client:
        try:
            response = await http_client.get(url, params=params, timeout=10.0)
            if response.status_code != 200:
                logger.error("mqtt_catch_up_api_failed", user_id=user_id, status_code=response.status_code)
                return

            data = response.json()
            feeds = data.get("feeds", [])
            logger.info("mqtt_catch_up_fetched", user_id=user_id, count=len(feeds))

            inserted_count = 0
            for feed in feeds:
                feed_created_at = feed.get("created_at")
                if not feed_created_at:
                    continue

                feed_ts = datetime.fromisoformat(feed_created_at.replace("Z", "+00:00"))
                # Skip duplicate readings
                if last_ts and feed_ts <= last_ts:
                    continue

                ph = parse_float(feed.get("field1"))
                tds = parse_float(feed.get("field2"))
                turbidity = parse_float(feed.get("field3"))

                try:
                    reading_obj = ReadingInsert(
                        timestamp=feed_ts,
                        user_id=user_id,
                        ph=ph,
                        tds=tds,
                        turbidity=turbidity
                    )
                except Exception as ve:
                    logger.warning("mqtt_catch_up_validation_error", user_id=user_id, feed=feed, error=str(ve))
                    continue

                try:
                    inserted = await repo.insert_reading(reading_obj.model_dump())
                    await ml_pipeline.process(inserted, repo)
                    inserted_count += 1
                except Exception as ie:
                    logger.error("mqtt_catch_up_insert_error", user_id=user_id, error=str(ie))

            logger.info("mqtt_catch_up_completed", user_id=user_id, inserted=inserted_count)

        except Exception as e:
            logger.error("mqtt_catch_up_failed", user_id=user_id, error=str(e))


async def handle_mqtt_message(message, repo: ReadingsRepository, sse_manager=None):
    """Process and store a live MQTT reading message."""
    topic = str(message.topic)
    payload_str = message.payload.decode("utf-8")

    logger.info("mqtt_msg_received", topic=topic, payload=payload_str)

    try:
        parts = topic.split('/')
        if len(parts) < 2:
            logger.warning("mqtt_invalid_topic", topic=topic)
            return

        channel_id = parts[1]
        user_info = _channel_to_user_map.get(channel_id)
        if not user_info:
            logger.warning("mqtt_unmapped_channel", channel_id=channel_id)
            return

        user_id = user_info["id"]
        data = json.loads(payload_str)

        created_at_str = data.get("created_at")
        if created_at_str:
            timestamp = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)

        ph = parse_float(data.get("field1"))
        tds = parse_float(data.get("field2"))
        turbidity = parse_float(data.get("field3"))

        try:
            reading_obj = ReadingInsert(
                timestamp=timestamp,
                user_id=user_id,
                ph=ph,
                tds=tds,
                turbidity=turbidity
            )
        except Exception as ve:
            logger.warning("mqtt_msg_validation_error", user_id=user_id, error=str(ve))
            return

        inserted = await repo.insert_reading(reading_obj.model_dump())
        logger.info("mqtt_msg_inserted", reading_id=inserted.get("id"), user_id=user_id)

        processed = await ml_pipeline.process(inserted, repo)
        
        if sse_manager:
            # Serialise datetime fields for JSON transmission
            serializable = {}
            for k, v in processed.items():
                if isinstance(v, datetime):
                    serializable[k] = v.isoformat()
                else:
                    serializable[k] = v
            await sse_manager.send_event(user_id, "reading_update", serializable)
            
            # Send new alert event over SSE if generated
            new_alert = processed.get("new_alert")
            if new_alert:
                alert_serializable = {}
                for k, v in new_alert.items():
                    if isinstance(v, datetime):
                        alert_serializable[k] = v.isoformat()
                    else:
                        alert_serializable[k] = v
                await sse_manager.send_event(user_id, "alert_new", alert_serializable)

    except json.JSONDecodeError:
        logger.error("mqtt_invalid_json", payload=payload_str)
    except Exception as e:
        logger.error("mqtt_processing_error", error=str(e))


async def poll_new_channels_loop(client, supabase_admin, repo: ReadingsRepository, settings):
    """Background loop checking for newly registered channels and subscribing to them."""
    while True:
        try:
            await asyncio.sleep(60.0)
            users = await get_active_users(supabase_admin)
            for user in users:
                ch_id = user["channel_id"]
                if ch_id not in _subscribed_channels:
                    _channel_to_user_map[ch_id] = user
                    await catch_up_user(user, supabase_admin, settings, repo)

                    topic = f"channels/{ch_id}/subscribe/feeds"
                    await client.subscribe(topic)
                    _subscribed_channels.add(ch_id)
                    logger.info("mqtt_subscribed_to_new_channel", channel_id=ch_id)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("mqtt_poll_loop_error", error=str(e))


async def run_mqtt_subscriber(app):
    """FastAPI lifespan background coroutine that handles the MQTT connection lifecycle."""
    # Add a short delay to let FastAPI startup complete
    await asyncio.sleep(2.0)
    logger.info("mqtt_subscriber_starting")
    app.state.mqtt_status = "starting"

    settings = get_settings()
    supabase_admin = app.state.supabase_admin
    repo = ReadingsRepository(supabase_admin)

    reconnect_delay = 1.0
    max_reconnect_delay = 60.0

    while True:
        try:
            async with aiomqtt.Client(
                hostname="mqtt3.thingspeak.com",
                port=1883,
                username=settings.THINGSPEAK_MQTT_USER,
                password=settings.THINGSPEAK_MQTT_API_KEY,
                timeout=15.0,
            ) as client:
                logger.info("mqtt_connected")
                app.state.mqtt_status = "connected"
                reconnect_delay = 1.0

                # Clear and reload local maps
                _subscribed_channels.clear()
                _channel_to_user_map.clear()

                users = await get_active_users(supabase_admin)
                for user in users:
                    ch_id = user["channel_id"]
                    _channel_to_user_map[ch_id] = user

                    # Catch up missed readings
                    await catch_up_user(user, supabase_admin, settings, repo)

                    # Subscribe to ThingSpeak feeds
                    topic = f"channels/{ch_id}/subscribe/feeds"
                    await client.subscribe(topic)
                    _subscribed_channels.add(ch_id)
                    logger.info("mqtt_subscribed", channel_id=ch_id)

                # Start the dynamic channel polling loop as a concurrent task
                poll_task = asyncio.create_task(
                    poll_new_channels_loop(client, supabase_admin, repo, settings)
                )

                try:
                    async for message in client.messages:
                        await handle_mqtt_message(message, repo, app.state.sse_manager)
                finally:
                    poll_task.cancel()

        except aiomqtt.MqttError as me:
            logger.warning("mqtt_connection_error", error=str(me), retry_in=reconnect_delay)
            app.state.mqtt_status = "reconnecting"
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        except asyncio.CancelledError:
            logger.info("mqtt_subscriber_shutdown")
            app.state.mqtt_status = "stopped"
            break
        except Exception as e:
            logger.error("mqtt_unexpected_error", error=str(e), retry_in=reconnect_delay)
            app.state.mqtt_status = "error"
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

