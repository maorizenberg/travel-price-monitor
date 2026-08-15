"""WhatsApp notification sender using Meta Cloud API."""

import logging
import os

import requests

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """Send WhatsApp messages via Meta Cloud API.
    
    Requires: FACEBOOK_ACCESS_TOKEN and WHATSAPP_PHONE_ID env vars.
    Get them at: https://developers.facebook.com → Create App → WhatsApp
    """
    
    API_URL = "https://graph.facebook.com/v22.0"
    
    def __init__(self):
        self.token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        self.phone_id = os.environ.get("WHATSAPP_PHONE_ID", "")
        
        if not self.token or not self.phone_id:
            logger.warning(
                "WhatsApp not configured. "
                "Set FACEBOOK_ACCESS_TOKEN and WHATSAPP_PHONE_ID env vars."
            )
    
    @property
    def configured(self) -> bool:
        return bool(self.token and self.phone_id)
    
    def send_text(self, to: str, message: str) -> dict:
        """Send a text message.
        
        Args:
            to: Recipient phone (e.g., "972507118144")
            message: Message text
            
        Returns:
            API response dict
        """
        if not self.configured:
            raise RuntimeError("WhatsApp not configured. Set FACEBOOK_ACCESS_TOKEN and WHATSAPP_PHONE_ID")
        
        url = f"{self.API_URL}/{self.phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        
        logger.info(f"Sending WhatsApp to {to}")
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()


def format_trip_message(trip_data: dict) -> str:
    """Format trip data into a WhatsApp message."""
    name = trip_data.get("trip_name", "Trip")
    depart = trip_data.get("departure_date", "N/A")
    ret = trip_data.get("return_date", "N/A")
    days = trip_data.get("duration_days", trip_data.get("duration_nights", "N/A"))
    price = trip_data.get("current_price", "N/A")
    currency = trip_data.get("currency", "EUR")
    board = trip_data.get("board_type", None)
    hotel = trip_data.get("hotel_name", None)
    guide = trip_data.get("guide", None)
    
    lines = [
        f"📌 {name}",
        "",
        f"📅 {depart} - {ret}",
        f"⏱️ {days} days",
        f"💰 {price} {currency}",
    ]
    
    if board:
        lines.append(f"🍽️ {board}")
    if hotel:
        lines.append(f"🏨 {hotel}")
    if guide:
        lines.append(f"👤 {guide}")
    
    return "\n".join(lines)


def send_trip_message(to: str, trip_data: dict) -> dict:
    """Send trip details via WhatsApp.
    
    Args:
        to: Phone number (e.g., "972507118144")
        trip_data: TripData dict
        
    Returns:
        API response
    """
    sender = WhatsAppSender()
    message = format_trip_message(trip_data)
    return sender.send_text(to, message)