"""Receipt-driven Corruption connector; inventory and delivery share one owner."""
from __future__ import annotations

import asyncio
import logging
import uuid

from randovania.game_connection.connector.prime3_wii_tracker_connector import Prime3WiiTrackerConnector
from randovania.game_connection.connector.remote_connector import PlayerLocationEvent
from randovania.game_connection.prime3_wii_tracker_protocol import Snapshot
from randovania.game_description.resources.inventory import Inventory, InventoryItem
from randovania.game_description.resources.pickup_index import PickupIndex
from randovania.games.prime3.multiworld.ledger import DeliveryLedger
from randovania.games.prime3.multiworld.manifest import remote_pickup_key


class Prime3MultiworldConnector(Prime3WiiTrackerConnector):
    def __init__(self, client, ledger_path):
        super().__init__(client)
        self._layout_uuid = uuid.UUID(client.manifest["world_uuid"])
        self.ledger = DeliveryLedger(ledger_path, client.manifest)
        self._has_incoming_history = self.ledger.data["incoming_synchronized"]
        self._update_lock = asyncio.Lock()
        self._status = None
        self._reported_checks = set()

    def inventory(self, snapshot):
        result = super().inventory(snapshot)
        if self._status is None or not self._status.generation:
            return Inventory.empty()
        values = (self._status.launcher_bits & 1, (self._status.launcher_bits >> 1) & 1,
                  self._status.locked_missiles, self._status.locked_ship_missiles)
        for name, value in zip(("MissileLauncher", "ShipMissileLauncher", "TemporaryMissile", "TemporaryShipMissile"),
                               values, strict=True):
            result[self.game.resource_database.get_item(name)] = InventoryItem(value, value)
        return result

    def description(self):
        return "Prime 3 CP3W multiworld"

    async def set_remote_pickups(self, remote_pickups):
        async with self._update_lock:
            if self._disconnected:
                return
            try:
                self.ledger.accept_incoming([
                    remote_pickup_key(self.ledger.manifest, pickup.pickup_entry, self.game.resource_database,
                                      pickup.provider_name) for pickup in remote_pickups
                ])
                self._has_incoming_history = True
            except (OSError, ValueError) as error:
                await self._stop(error)

    async def acknowledge_uploaded_locations(self, locations):
        async with self._update_lock:
            if self._disconnected:
                return
            try:
                self.ledger.collect(locations)
                self.ledger.mark_uploaded(locations)
            except (OSError, ValueError) as error:
                await self._stop(error)

    async def _stop(self, error):
        if self._disconnected:
            return
        self.last_error = str(error)
        logging.getLogger(__name__).warning("Corruption multiworld stopped: %s", error)
        await self.force_finish()
        self.InventoryUpdated.emit(Inventory.empty())
        self.PlayerLocationChanged.emit(PlayerLocationEvent(None, None))
        self.ConnectionLost.emit(str(error))

    async def update(self):
        if self._disconnected or self._update_lock.locked():
            return
        async with self._update_lock:
            try:
                status = await self.client.status()
                self._status = status
                self.ledger.collect(status.locations)
                for index in self.ledger.data["collected"]:
                    if index not in self._reported_checks:
                        self.PickupIndexCollected.emit(PickupIndex(index))
                        self._reported_checks.add(index)
                delivery = self.ledger.reconcile(status) if self._has_incoming_history else None
                if delivery is not None:
                    result = await self.client.deliver(status, *delivery)
                    self.ledger.reconcile(result)
                    status = result
                snapshot = await self.client.snapshot()
                after = await self.client.status()
                # Inventory pages and virtual launcher/receipt state must belong
                # to the same owner. A normal death/load/delivery between reads
                # produces an unavailable sample, not a stale mixed inventory.
                self._status = after
                if self._has_incoming_history:
                    self.ledger.reconcile(after)
                self._publish_snapshot(snapshot if after == status else Snapshot(False))
            except TimeoutError as error:
                # Keep the durable queue and session. The next update reads
                # status before reconciling any possibly applied delivery.
                self._status = None
                self._telemetry_unavailable(error)
            except (OSError, ValueError) as error:
                await self._stop(error)
