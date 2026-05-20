# Connection: GreenAPI (WhatsApp)

## What it is
WhatsApp automation API — sends automated messages to clients.

## Status
PLANNED — not yet integrated. Currently using click-to-send WhatsApp links (zero cost, manual).

## When to use (once integrated)
- Auto-send appointment confirmation to client after dispatch
- Morning briefing digest to coordinator
- Tech status updates to clients

## Key details
- Provider: GreenAPI (https://green-api.com)
- Cost: ~$20/month
- Account: will be under infomaslul@gmail.com
- Trigger: after `findBestSlot()` confirms a dispatch (feature flag `whatsapp_enabled: true`)

## Current workaround
WhatsApp click-to-send button appears after dispatch — coordinator clicks it to open a pre-written WhatsApp message. No API cost, no automation.

## Roadmap note
This is listed in the May 2026 roadmap. Integrate after Railway Hobby upgrade is done.

## Secrets (future)
GREENAPI_INSTANCE_ID and GREENAPI_TOKEN — will go in `.env` when integrated
