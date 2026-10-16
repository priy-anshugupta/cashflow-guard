"""
Join logic and indexed relational access for HackerRank Orchestrate (September 2026) - Buy or Wait?
Fast in-memory lookups linking requests to users, events, payment options, messages, and images.
"""

from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass

from data.models import (
    UserProfile, FinancialEvent, RequestItem,
    PaymentOption, MessageItem, ImageItem
)

@dataclass
class RequestContext:
    request: RequestItem
    user: UserProfile
    events: List[FinancialEvent]
    payment_options: List[PaymentOption]
    messages: List[MessageItem]
    images: List[ImageItem]

class DataRepository:
    def __init__(
        self,
        profiles: Dict[str, UserProfile],
        events: List[FinancialEvent],
        requests: List[RequestItem],
        payment_options: List[PaymentOption],
        messages: List[MessageItem],
        images: List[ImageItem]
    ):
        self.profiles = profiles
        self.requests = {r.request_id: r for r in requests}
        
        # User -> Events
        self.user_events: Dict[str, List[FinancialEvent]] = defaultdict(list)
        for e in events:
            self.user_events[e.user_id].append(e)
            
        # Request -> Payment Options
        self.request_options: Dict[str, List[PaymentOption]] = defaultdict(list)
        for opt in payment_options:
            self.request_options[opt.request_id].append(opt)
            
        # Message indexes
        self.event_messages: Dict[str, List[MessageItem]] = defaultdict(list)
        self.request_messages: Dict[str, List[MessageItem]] = defaultdict(list)
        self.user_messages: Dict[str, List[MessageItem]] = defaultdict(list)
        for m in messages:
            self.user_messages[m.user_id].append(m)
            if m.related_event_id:
                self.event_messages[m.related_event_id].append(m)
            if m.request_id:
                self.request_messages[m.request_id].append(m)
                
        # Image indexes
        self.event_images: Dict[str, List[ImageItem]] = defaultdict(list)
        self.request_images: Dict[str, List[ImageItem]] = defaultdict(list)
        self.user_images: Dict[str, List[ImageItem]] = defaultdict(list)
        for img in images:
            self.user_images[img.user_id].append(img)
            if img.related_event_id:
                self.event_images[img.related_event_id].append(img)
            if img.request_id:
                self.request_images[img.request_id].append(img)

    def get_context(self, request_id: str) -> RequestContext:
        req = self.requests[request_id]
        user = self.profiles[req.user_id]
        events = self.user_events[req.user_id]
        options = self.request_options[request_id]
        
        # Collect relevant messages for request & user
        req_msgs = list(self.request_messages.get(request_id, []))
        # Also include event-specific messages for user events
        for e in events:
            for em in self.event_messages.get(e.event_id, []):
                if em not in req_msgs:
                    req_msgs.append(em)
        # Also include user general messages
        for um in self.user_messages.get(req.user_id, []):
            if um not in req_msgs:
                req_msgs.append(um)
                
        # Collect relevant images
        req_imgs = list(self.request_images.get(request_id, []))
        for e in events:
            for ei in self.event_images.get(e.event_id, []):
                if ei not in req_imgs:
                    req_imgs.append(ei)
                    
        return RequestContext(
            request=req,
            user=user,
            events=events,
            payment_options=options,
            messages=req_msgs,
            images=req_imgs,
        )
