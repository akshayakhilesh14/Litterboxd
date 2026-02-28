"""
Webhook system for Litterboxd low supply alerts.
Handles notifications to facilities when bathrooms have ratings below 4.0/10
"""
import asyncio
import httpx
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Webhook configuration
WEBHOOK_TIMEOUT = 10  # seconds
WEBHOOK_RETRY_COUNT = 3
WEBHOOK_RETRY_DELAY = 5  # seconds


class WebhookPayload:
    """Represents a webhook notification payload"""
    def __init__(
        self,
        bathroom_id: int,
        building: str,
        floor: int,
        gender: str,
        avg_rating: float,
        alert_type: str = "low_supply"
    ):
        self.bathroom_id = bathroom_id
        self.building = building
        self.floor = floor
        self.gender = gender
        self.avg_rating = avg_rating
        self.alert_type = alert_type
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "bathroom_id": self.bathroom_id,
            "building": self.building,
            "floor": self.floor,
            "gender": self.gender,
            "avg_rating": self.avg_rating,
            "alert_type": self.alert_type,
            "timestamp": self.timestamp
        }


async def send_webhook(
    webhook_url: str,
    payload: WebhookPayload,
    retry_count: int = WEBHOOK_RETRY_COUNT
) -> bool:
    """
    Send webhook notification to external service.
    Returns True if successful, False otherwise.
    """
    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
        for attempt in range(retry_count):
            try:
                response = await client.post(
                    webhook_url,
                    json=payload.to_dict(),
                    headers={
                        "Content-Type": "application/json",
                        "X-Litterboxd-Signature": "sha256=webhook_signature_here"
                    }
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(
                        f"Webhook sent successfully to {webhook_url} for bathroom {payload.bathroom_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook failed with status {response.status_code}: {response.text}"
                    )
                    if attempt < retry_count - 1:
                        await asyncio.sleep(WEBHOOK_RETRY_DELAY)
                        continue
                    return False
                    
            except httpx.TimeoutException:
                logger.error(
                    f"Webhook timeout on attempt {attempt + 1}/{retry_count}"
                )
                if attempt < retry_count - 1:
                    await asyncio.sleep(WEBHOOK_RETRY_DELAY)
                    continue
                return False
                
            except Exception as e:
                logger.error(
                    f"Error sending webhook: {str(e)}"
                )
                if attempt < retry_count - 1:
                    await asyncio.sleep(WEBHOOK_RETRY_DELAY)
                    continue
                return False
    
    return False


async def notify_low_supply(
    bathroom_id: int,
    building: str,
    floor: int,
    gender: str,
    avg_rating: float,
    webhook_urls: List[str]
) -> dict:
    """
    Send low supply notifications to all registered webhook endpoints.
    Returns a dictionary with notification results.
    """
    payload = WebhookPayload(
        bathroom_id=bathroom_id,
        building=building,
        floor=floor,
        gender=gender,
        avg_rating=avg_rating,
        alert_type="low_supply"
    )
    
    results = {
        "bathroom_id": bathroom_id,
        "total_endpoints": len(webhook_urls),
        "successful": 0,
        "failed": 0,
        "endpoints": []
    }
    
    for webhook_url in webhook_urls:
        success = await send_webhook(webhook_url, payload)
        results["endpoints"].append({
            "url": webhook_url,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if success:
            results["successful"] += 1
        else:
            results["failed"] += 1
    
    logger.info(
        f"Low supply notification sent for bathroom {bathroom_id}: "
        f"{results['successful']}/{results['total_endpoints']} successful"
    )
    
    return results

