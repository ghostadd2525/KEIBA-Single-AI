# -*- coding: utf-8 -*-
"""Ticket Policy package — Policy Resolver (V109 C3)."""
from app.consumer.ticket.dto import TicketPlan, TICKET_SCHEMA
from app.consumer.ticket.market import DictMarketResolver, NullMarketResolver
from app.consumer.ticket.resolver import resolve_ticket
from app.consumer.ticket.templates import get_template, template_registry_meta

__all__ = [
    "TICKET_SCHEMA",
    "DictMarketResolver",
    "NullMarketResolver",
    "TicketPlan",
    "get_template",
    "resolve_ticket",
    "template_registry_meta",
]
