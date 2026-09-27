"""Run programs on a SPIKE Prime hub from VS Code - over Bluetooth, or USB as a fallback.

Bluetooth speaks LEGO's published SPIKE Prime BLE protocol
(https://lego.github.io/spike-prime-docs/) - the same one the SPIKE app uses. A
program is uploaded into one of the hub's 20 slots and started there, and the
hub streams `print()` output back. Because the delivery path is identical to the
app's, a program that works here is exactly what you would paste into the app.

    spike discover                     # every hub in range: BLE address, USB serial
    spike session                      # connect once, stay connected, run files repeatedly
    spike send run programs\\x.py       # hand a file to the open session (the VS Code Run button)
    spike run programs\\hello_hub.py    # one-shot: upload to a slot, start, stream output
    spike bundle programs\\x.py         # write build\\x.py: the program with robot.py copied in, for the SPIKE app
    spike stop                         # stop whatever is running
    spike usb run programs\\x.py        # the same program over the USB cable instead
    spike usb repl                     # interactive MicroPython prompt (USB only)

Which robot? hubs.json (in the project root) names each robot with its Bluetooth
address and USB serial. Without --hub, Bluetooth connects to whichever hub is
advertising and USB uses the one hub plugged in. With `--hub robot2` you get
that robot specifically, even if both are switched on:

    spike session --hub robot2
    spike usb repl --hub robot1

The hub advertises over Bluetooth only while powered on, not connected to
anything (the SPIKE app included) and not running a program - blinking light.

A program may `from robot import ...` another file in programs/. The hub takes
one file per slot, so every send path copies that file in first (tools/bundle.py).

Needs `bleak` (Bluetooth) and `mpremote` (USB); setup.ps1 installs both into
.venv. Framing (COBS + XOR + 0x02 delimiter) and message layouts follow LEGO's
reference implementation; this file is self-contained on purpose.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import struct
import subprocess
import sys
import threading
import time
from binascii import crc32
from pathlib import Path

from bundle import BundleError, bundle_source  # tools/bundle.py, next to this file

try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # pragma: no cover
    sys.exit(
        "bleak is not installed. Run setup.ps1, or:\n"
        "  .venv\\Scripts\\python -m pip install -r requirements.txt"
    )

ROOT = Path(__file__).resolve().parent.parent
HUBS_FILE = ROOT / "hubs.json"

SERVICE = "0000fd02-0000-1000-8000-00805f9b34fb"
RX_CHAR = "0000fd02-0001-1000-8000-00805f9b34fb"  # hub receives on this
TX_CHAR = "0000fd02-0002-1000-8000-00805f9b34fb"  # hub transmits on this
LEGO_USB_VID = 0x0694

SCAN_SECONDS = 10.0
RESPONSE_TIMEOUT = 10.0
DEFAULT_SLOT = 0

# ---------------------------------------------------------------------------
# hubs.json - which robot is which
# ---------------------------------------------------------------------------


def load_hubs() -> dict[str, dict]:
    if not HUBS_FILE.exists():
        return {}
    try:
        data = json.loads(HUBS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{HUBS_FILE} is not valid JSON: {e}") from e
    return data.get("hubs", {})


def hub_config(name: str | None) -> dict | None:
    """The hubs.json entry for a named robot, or None when no name was given."""
    if name is None:
        return None
    hubs = load_hubs()
    if name not in hubs:
        known = ", ".join(sorted(hubs)) or "(none - is hubs.json missing?)"
        raise RuntimeError(f"unknown hub {name!r}. Known hubs: {known}")
    return hubs[name]


# ---------------------------------------------------------------------------
# Framing: COBS with 0x02 as delimiter, then XOR 3, then trailing 0x02.
# ---------------------------------------------------------------------------

_DELIM = 0x02
_NO_DELIM = 0xFF
_MAX_BLOCK = 84
_XOR = 3


def _cobs_encode(data: bytes) -> bytearray:
    out = bytearray()
    code_index = 0
    block = 0

    def begin_block() -> None:
        nonlocal code_index, block
        code_index = len(out)
        out.append(_NO_DELIM)
        block = 1

    begin_block()
    for byte in data:
        if byte > _DELIM:
            out.append(byte)
            block += 1
        if byte <= _DELIM or block > _MAX_BLOCK:
            if byte <= _DELIM:
                out[code_index] = byte * _MAX_BLOCK + block + _DELIM
            begin_block()
    out[code_index] = block + _DELIM
    return out


def _cobs_decode(data: bytes) -> bytearray:
    out = bytearray()

    def unescape(code: int):
        if code == _NO_DELIM:
            return None, _MAX_BLOCK + 1
        value, block = divmod(code - _DELIM, _MAX_BLOCK)
        if block == 0:
            block = _MAX_BLOCK
            value -= 1
        return value, block

    value, block = unescape(data[0])
    for byte in data[1:]:
        block -= 1
        if block > 0:
            out.append(byte)
            continue
        if value is not None:
            out.append(value)
        value, block = unescape(byte)
    return out


def pack(payload: bytes) -> bytes:
    buf = _cobs_encode(payload)
    for i in range(len(buf)):
        buf[i] ^= _XOR
    buf.append(_DELIM)
    return bytes(buf)


def unpack(frame: bytes) -> bytes:
    start = 1 if frame and frame[0] == 0x01 else 0  # optional priority byte
    body = bytes(b ^ _XOR for b in frame[start:])
    return bytes(_cobs_decode(body))


def crc(data: bytes, seed: int = 0, align: int = 4) -> int:
    rem = len(data) % align
    if rem:
        data += b"\x00" * (align - rem)
    return crc32(data, seed)


# ---------------------------------------------------------------------------
# Messages - only the subset this tool needs.
# ---------------------------------------------------------------------------

INFO_REQ, INFO_RESP = 0x00, 0x01
START_UPLOAD_REQ, START_UPLOAD_RESP = 0x0C, 0x0D
CHUNK_REQ, CHUNK_RESP = 0x10, 0x11
FLOW_REQ, FLOW_RESP, FLOW_NOTIFY = 0x1E, 0x1F, 0x20
CONSOLE_NOTIFY = 0x21
DEVICE_NOTIFY_REQ, DEVICE_NOTIFY_RESP = 0x28, 0x29
DEVICE_NOTIFY = 0x3C
CLEAR_SLOT_REQ, CLEAR_SLOT_RESP = 0x46, 0x47


def msg_info_request() -> bytes:
    return bytes([INFO_REQ])


def msg_clear_slot(slot: int) -> bytes:
    return struct.pack("<BB", CLEAR_SLOT_REQ, slot)


def msg_start_upload(name: str, slot: int, file_crc: int) -> bytes:
    enc = name.encode("utf8")
    if len(enc) > 31:
        raise ValueError(f"file name too long for the hub ({len(enc)} bytes, max 31)")
    return struct.pack(f"<B{len(enc) + 1}sBI", START_UPLOAD_REQ, enc, slot, file_crc)


def msg_chunk(running_crc: int, chunk: bytes) -> bytes:
    return struct.pack(f"<BIH{len(chunk)}s", CHUNK_REQ, running_crc, len(chunk), chunk)


def msg_program_flow(stop: bool, slot: int) -> bytes:
    return struct.pack("<BBB", FLOW_REQ, int(stop), slot)


class Info:
    def __init__(self, data: bytes):
        (
            _,
            self.rpc_major, self.rpc_minor, self.rpc_build,
            self.fw_major, self.fw_minor, self.fw_build,
            self.max_packet, self.max_message, self.max_chunk,
            self.product_group,
        ) = struct.unpack("<BBBHBBHHHHH", data)

    def __str__(self) -> str:
        return (
            f"firmware {self.fw_major}.{self.fw_minor}.{self.fw_build}  "
            f"rpc {self.rpc_major}.{self.rpc_minor}.{self.rpc_build}  "
            f"max packet {self.max_packet}B  max message {self.max_message}B  "
            f"max chunk {self.max_chunk}B  product group {self.product_group}"
        )


# ---------------------------------------------------------------------------
# Hub connection (Bluetooth)
# ---------------------------------------------------------------------------


class Hub:
    def __init__(self, client: BleakClient, verbose: bool):
        self.client = client
        self.verbose = verbose
        self.info: Info | None = None
        service = client.services.get_service(SERVICE)
        if service is None:
            raise RuntimeError("connected device does not expose the SPIKE Prime BLE service")
        rx = service.get_characteristic(RX_CHAR)
        tx = service.get_characteristic(TX_CHAR)
        if rx is None or tx is None:
            raise RuntimeError("SPIKE service is missing its RX/TX characteristics")
        self._rx = rx
        self._tx = tx
        self._buffer = bytearray()
        self._waiting: dict[int, asyncio.Future] = {}
        self.program_stopped = asyncio.Event()
        self.program_started = asyncio.Event()
        # One frame at a time on the wire: a `stop` from the Stop button can
        # arrive while an upload is mid-chunk.
        self._write_lock = asyncio.Lock()

    async def start(self) -> None:
        await self.client.start_notify(self._tx, self._on_data)

    # LEGO's example cannot handle a message split across BLE packets. Buffer
    # until the 0x02 delimiter, which COBS guarantees never appears inside a frame.
    def _on_data(self, _char, data: bytearray) -> None:
        self._buffer.extend(data)
        while True:
            try:
                end = self._buffer.index(_DELIM)
            except ValueError:
                return
            frame = bytes(self._buffer[:end])
            del self._buffer[: end + 1]
            if frame:
                self._dispatch(unpack(frame))

    def _dispatch(self, msg: bytes) -> None:
        kind = msg[0]
        if self.verbose and kind != CONSOLE_NOTIFY:
            print(f"[hub] <- 0x{kind:02X} {msg[:24].hex(' ')}{' ...' if len(msg) > 24 else ''}")
        if kind == CONSOLE_NOTIFY:
            text = msg[1:].rstrip(b"\0").decode("utf8", "replace")
            sys.stdout.write(text)
            sys.stdout.flush()
            return
        if kind == FLOW_NOTIFY:
            stopped = bool(msg[1])
            if self.verbose:
                print(f"[hub] program {'stopped' if stopped else 'started'}")
            (self.program_stopped if stopped else self.program_started).set()
            return
        if kind == DEVICE_NOTIFY:
            return  # only arrives if --telemetry asked for it; ignore
        fut = self._waiting.pop(kind, None)
        if fut is not None and not fut.done():
            fut.set_result(msg)
        elif self.verbose:
            print(f"[hub] unsolicited message 0x{kind:02X}: {msg.hex(' ')}")

    async def _send(self, payload: bytes) -> None:
        frame = pack(payload)
        size = self.info.max_packet if self.info else len(frame)
        async with self._write_lock:
            for i in range(0, len(frame), size):
                await self.client.write_gatt_char(self._rx, frame[i : i + size], response=False)

    async def request(self, payload: bytes, response_id: int) -> bytes:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._waiting[response_id] = fut
        await self._send(payload)
        try:
            return await asyncio.wait_for(fut, RESPONSE_TIMEOUT)
        except asyncio.TimeoutError as exc:
            self._waiting.pop(response_id, None)
            raise RuntimeError(
                f"hub did not answer message 0x{payload[0]:02X} within {RESPONSE_TIMEOUT:.0f}s"
            ) from exc

    async def status_request(self, payload: bytes, response_id: int) -> bool:
        resp = await self.request(payload, response_id)
        return resp[1] == 0x00

    # -- high-level operations -------------------------------------------

    async def handshake(self) -> Info:
        self.info = Info(await self.request(msg_info_request(), INFO_RESP))
        if self.verbose:
            print(f"[hub] {self.info}")
        return self.info

    async def upload(self, source: bytes, slot: int, name: str) -> None:
        assert self.info is not None
        if not await self.status_request(msg_clear_slot(slot), CLEAR_SLOT_RESP) and self.verbose:
            print(f"[hub] slot {slot} was already empty")
        if not await self.status_request(
            msg_start_upload(name, slot, crc(source)), START_UPLOAD_RESP
        ):
            raise RuntimeError("hub refused the upload (StartFileUpload not acknowledged)")
        running = 0
        chunk_size = self.info.max_chunk
        total = len(source)
        for offset in range(0, total, chunk_size):
            chunk = source[offset : offset + chunk_size]
            running = crc(chunk, running)
            if not await self.status_request(msg_chunk(running, chunk), CHUNK_RESP):
                raise RuntimeError(f"hub rejected chunk at byte {offset}")
            if self.verbose:
                done = min(offset + chunk_size, total)
                print(f"\r[hub] uploading {done}/{total} bytes", end="", flush=True)
        if self.verbose:
            print()

    async def enable_telemetry(self, interval_ms: int) -> None:
        """Ask for periodic DeviceNotifications (sensor/motor/display state).
        Optional - the payloads are noisy and not needed to run programs."""
        if not await self.status_request(
            struct.pack("<BH", DEVICE_NOTIFY_REQ, interval_ms), DEVICE_NOTIFY_RESP
        ):
            raise RuntimeError("hub refused DeviceNotificationRequest")

    async def start_program(self, slot: int) -> None:
        self.program_stopped.clear()
        if not await self.status_request(msg_program_flow(False, slot), FLOW_RESP):
            raise RuntimeError(f"hub refused to start slot {slot}")
        if self.verbose:
            print(f"[hub] start acknowledged for slot {slot}")

    async def stop_program(self) -> None:
        # The slot byte is ignored for stop; any value works.
        if not await self.status_request(msg_program_flow(True, 0), FLOW_RESP):
            raise RuntimeError("hub refused to stop the running program")


def _has_spike_service(adv) -> bool:
    return SERVICE in {u.lower() for u in adv.service_uuids}


async def find_hub(seconds: float, verbose: bool, address: str | None = None,
                   name: str | None = None):
    """First hub advertising the SPIKE service - or, when address/name are
    given, the one matching either. Both are accepted because macOS never
    reveals a peripheral's real Bluetooth address (bleak reports a per-Mac
    UUID there), so on a Mac only the hub's advertised name can identify it."""
    want = address.upper() if address else None
    if verbose:
        target = " or ".join(x for x in (want, name) if x) or "any SPIKE hub"
        print(f"scanning for {target} ({seconds:.0f}s)...", file=sys.stderr)

    def match(device, adv) -> bool:
        if not _has_spike_service(adv):
            return False
        if want is None and name is None:
            return True
        if want and device.address.upper() == want:
            return True
        return bool(name) and (device.name or adv.local_name) == name

    device = await BleakScanner.find_device_by_filter(match, timeout=seconds)
    if device is None:
        if want or name:
            hint = ""
            if sys.platform == "darwin":
                hint = (" On macOS, Bluetooth addresses are hidden, so the robot is matched by its "
                        "name - make sure `ble_name` in hubs.json is filled in and distinct per robot.")
            sys.exit(
                f"hub {' / '.join(x for x in (want, name) if x)} not found. Is that robot on with "
                "its Bluetooth light blinking? It advertises only while connected to nothing "
                f"(SPIKE app included). `spike discover` shows what is in range.{hint}"
            )
        sys.exit(
            "no SPIKE hub found. A hub advertises only while powered on, NOT connected "
            "to the SPIKE app or anything else, and not running a program (blinking light)."
        )
    if verbose:
        print(f"found {device.name or '(unnamed)'} at {device.address}", file=sys.stderr)
    return device


async def connect(verbose: bool, hub_name: str | None = None):
    cfg = hub_config(hub_name)
    address = cfg.get("ble_address") if cfg else None
    name = cfg.get("ble_name") if cfg else None
    if hub_name and not (address or name):
        raise RuntimeError(
            f"hub {hub_name!r} has neither ble_address nor ble_name in hubs.json yet - switch only "
            "that robot on, run `spike discover`, and paste its address and name into hubs.json"
        )
    device = await find_hub(SCAN_SECONDS, verbose, address, name)
    lost = asyncio.Event()
    client = BleakClient(device, disconnected_callback=lambda _c: lost.set())
    await client.connect()
    hub = Hub(client, verbose)
    await hub.start()
    await hub.handshake()
    return client, hub, lost, device


# ---------------------------------------------------------------------------
# USB (mpremote) - same hubs.json, same robot names
# ---------------------------------------------------------------------------


def _lego_usb_ports() -> list:
    try:
        from serial.tools import list_ports  # pyserial, installed with mpremote
    except ImportError:
        raise RuntimeError("pyserial/mpremote not installed - run setup.ps1") from None
    return [p for p in list_ports.comports() if p.vid == LEGO_USB_VID]


def resolve_usb_serial(hub_name: str | None) -> str:
    cfg = hub_config(hub_name)
    if cfg:
        serial_no = cfg.get("usb_serial")
        if not serial_no:
            raise RuntimeError(
                f"hub {hub_name!r} has no usb_serial in hubs.json yet - plug only that robot in, "
                "run `spike discover`, and paste its serial into hubs.json"
            )
        return serial_no
    ports = _lego_usb_ports()
    if len(ports) == 1:
        return ports[0].serial_number
    if not ports:
        raise RuntimeError(
            "no SPIKE hub on USB (vendor id 0694). Hub on? Cable plugged in? "
            "Charge-only cables are the usual culprit."
        )
    names = ", ".join(f"{p.device} serial {p.serial_number}" for p in ports)
    raise RuntimeError(f"more than one hub on USB - say which with --hub NAME. Seen: {names}")


def cmd_usb(args) -> int:
    mp = [sys.executable, "-m", "mpremote"]
    if args.usb_cmd == "devs":
        return subprocess.call(mp + ["devs"])
    serial_no = resolve_usb_serial(getattr(args, "hub", None))
    base = mp + ["connect", f"id:{serial_no}"]
    if args.usb_cmd == "run":
        src = Path(args.file)
        text, included = bundle_source(src)
        if included:
            bundled = ROOT / "build" / src.name
            bundled.parent.mkdir(parents=True, exist_ok=True)
            bundled.write_text(text, encoding="utf-8", newline="\n")
            print(f"[hub] {src.name} + {', '.join(n + '.py' for n in included)} -> {bundled}")
            return subprocess.call(base + ["run", str(bundled)])
        return subprocess.call(base + ["run", args.file])
    if args.usb_cmd == "repl":
        return subprocess.call(base + ["repl"])
    if args.usb_cmd == "stop":
        return subprocess.call(base + ["soft-reset"])
    if args.usb_cmd == "exec":
        return subprocess.call(base + ["exec", args.code])
    raise RuntimeError(f"unknown usb command {args.usb_cmd!r}")


# ---------------------------------------------------------------------------
# Bluetooth commands
# ---------------------------------------------------------------------------


async def cmd_discover(args) -> None:
    """Everything in range, on both transports, with the values hubs.json needs."""
    hubs = load_hubs()
    by_addr = {(h.get("ble_address") or "").upper(): n for n, h in hubs.items() if h.get("ble_address")}
    by_name = {h.get("ble_name"): n for n, h in hubs.items() if h.get("ble_name")}
    by_serial = {h.get("usb_serial"): n for n, h in hubs.items() if h.get("usb_serial")}

    print(f"Bluetooth: scanning {args.seconds:.0f}s (a hub advertises only while connected to nothing)...")
    found: dict[str, tuple[str | None, int]] = {}

    def on_adv(device, adv):
        if _has_spike_service(adv):
            found[device.address.upper()] = (device.name or adv.local_name, adv.rssi)

    scanner = BleakScanner(on_adv)
    await scanner.start()
    await asyncio.sleep(args.seconds)
    await scanner.stop()

    unregistered: list[tuple[str, str | None]] = []
    if found:
        for addr, (name, rssi) in sorted(found.items(), key=lambda kv: -kv[1][1]):
            owner = by_addr.get(addr) or by_name.get(name)
            tag = f"= {owner}" if owner else "  (not in hubs.json)"
            print(f"  {name or '(unnamed)':<20} {addr}  rssi {rssi:>4}  {tag}")
            if not owner:
                unregistered.append((addr, name))
        if sys.platform == "darwin":
            print("  note: macOS hides real Bluetooth addresses - the ids above are UUIDs unique to this Mac.\n"
                  "        hubs.json matches robots by ble_name here, so keep each robot's name distinct.")
    else:
        print("  none advertising")

    print("USB:")
    ports = _lego_usb_ports()
    unregistered_serials: list[str] = []
    if ports:
        for p in ports:
            serial_no = str(p.serial_number or "?")  # pyserial is untyped; pin it to str
            tag = f"= {by_serial[serial_no]}" if serial_no in by_serial else "  (not in hubs.json)"
            print(f"  {p.device:<8} serial {serial_no}  {tag}")
            if serial_no != "?" and serial_no not in by_serial:
                unregistered_serials.append(serial_no)
    else:
        print("  none plugged in")

    if unregistered or unregistered_serials:
        print("\nTo register, add to hubs.json under \"hubs\" (pick your own name):")
        addr, name = unregistered[0] if unregistered else (None, None)
        serial_no = unregistered_serials[0] if unregistered_serials else None
        print(json.dumps({"robotN": {
            "ble_address": addr, "ble_name": name, "usb_serial": serial_no,
            "notes": "ports / build notes here",
        }}, indent=2))
        if len(unregistered) > 1 or len(unregistered_serials) > 1:
            print("(more than one unregistered hub seen - switch on / plug in one at a time to be sure which is which)")


async def cmd_scan(args) -> None:
    found: dict[str, tuple[str | None, int]] = {}

    def on_adv(device, adv):
        if _has_spike_service(adv):
            found[device.address] = (device.name, adv.rssi)

    scanner = BleakScanner(on_adv)
    await scanner.start()
    await asyncio.sleep(args.seconds)
    await scanner.stop()
    if not found:
        print("no SPIKE hub advertising. Is it on, and disconnected from the SPIKE app?")
        return
    for addr, (name, rssi) in found.items():
        print(f"{name or '(unnamed)':<24} {addr}  rssi {rssi}")


async def cmd_info(args) -> None:
    client, hub, _, device = await connect(True, args.hub)
    try:
        print(f"{device.name or '(unnamed)'}  {device.address}")
        print(hub.info)
    finally:
        await client.disconnect()


def program_source(path: Path) -> bytes:
    """The bytes to send to the hub: the file with any local `from x import`
    modules copied in. Says so when it did."""
    text, included = bundle_source(path)
    if included:
        print(f"[hub] {path.name} + {', '.join(n + '.py' for n in included)}")
    return text.encode("utf-8")


def cmd_bundle(args) -> None:
    """Write the one-file version of a program to build/ for the SPIKE app."""
    src = Path(args.file)
    text, included = bundle_source(src)
    out = Path(args.out) if args.out else ROOT / "build" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    what = " + ".join([src.name] + [n + ".py" for n in included])
    print(f"{what} -> {out}  (paste this into the SPIKE app)")


async def _run_file(hub: Hub, lost: asyncio.Event, source: bytes, slot: int,
                    timeout: float) -> None:
    """Upload one program into a slot, start it, and stream output until it
    finishes, the link drops, or the timeout expires. Shared by `run` and the
    interactive session. Ctrl+C during streaming sends a stop, not a quit."""
    # The slot's entry point must be named "program.py" - the hub runs that file
    # when told to start, regardless of the source filename. Uploading under the
    # source name succeeds but the slot then does nothing.
    await hub.upload(source, slot, "program.py")
    await hub.start_program(slot)
    stopped = asyncio.ensure_future(hub.program_stopped.wait())
    dropped = asyncio.ensure_future(lost.wait())
    try:
        done, _ = await asyncio.wait(
            {stopped, dropped}, timeout=timeout or None,
            return_when=asyncio.FIRST_COMPLETED,
        )
    except asyncio.CancelledError:
        if not lost.is_set():
            await hub.stop_program()
        print("\n[hub] stopped by Ctrl+C")
        raise
    finally:
        stopped.cancel()
        dropped.cancel()
    if not done:
        print(f"\n[hub] still running after {timeout:.0f}s (no finish notification)",
              file=sys.stderr)
    elif lost.is_set() and not hub.program_stopped.is_set():
        print("\n[hub] connection lost while the program was running", file=sys.stderr)


async def cmd_upload(args, start: bool) -> None:
    path = Path(args.file)
    source = program_source(path)
    client, hub, lost, _ = await connect(args.verbose, args.hub)
    try:
        if getattr(args, "telemetry", 0):
            await hub.enable_telemetry(args.telemetry)
        if not start:
            await hub.upload(source, args.slot, "program.py")
            print(f"[hub] {path.name} -> slot {args.slot} ({len(source)} bytes)")
            return
        if args.no_wait:
            await hub.upload(source, args.slot, "program.py")
            await hub.start_program(args.slot)
            return
        await _run_file(hub, lost, source, args.slot, args.timeout)
    finally:
        if client.is_connected:
            await client.disconnect()


async def cmd_start(args) -> None:
    client, hub, _, _ = await connect(args.verbose, args.hub)
    try:
        await hub.start_program(args.slot)
        print(f"[hub] started slot {args.slot}")
    finally:
        await client.disconnect()


async def cmd_stop(args) -> None:
    client, hub, _, _ = await connect(args.verbose, args.hub)
    try:
        await hub.stop_program()
        print("[hub] stop sent")
    finally:
        await client.disconnect()


# ---------------------------------------------------------------------------
# Session, and the control port that lets the VS Code buttons drive it
# ---------------------------------------------------------------------------
#
# `spike session` listens on a localhost TCP port while it is connected.
# `spike send run FILE` / `spike send stop` / `spike send quit` connect to that
# port, hand over one line, and relay everything the session prints while it
# carries the command out. The status-bar buttons in VS Code (.vscode/
# settings.json -> tasks.json) are nothing more than those three commands.
# With no session open, `send run` and `send stop` fall back to the one-shot
# `run` / `stop`, so the Run button always works.

SESSION_PORT = 47355                    # localhost only; `spike session --port N` overrides
SESSION_LOCK = ROOT / ".spike-session"  # exists while a session is open: {"port", "pid", "hub"}


class _Tee:
    """stdout/stderr wrapper. Everything the session prints also goes to the
    `spike send` client whose command is being carried out right now, so the
    Run button's panel shows the program's output live."""

    def __init__(self, base, sinks: set):
        self.base = base
        self.sinks = sinks

    def write(self, s: str) -> int:
        for w in list(self.sinks):
            try:
                w.write(s.encode("utf-8", "replace"))
            except Exception:  # client went away mid-stream; keep the session going
                self.sinks.discard(w)
        return self.base.write(s)

    def flush(self) -> None:
        self.base.flush()

    def __getattr__(self, name):
        return getattr(self.base, name)


def _session_port() -> int:
    """Port of the session on this PC, from the lock file, else the default."""
    try:
        return int(json.loads(SESSION_LOCK.read_text()).get("port", SESSION_PORT))
    except (OSError, ValueError, AttributeError):
        return SESSION_PORT


async def _relay(port: int, line: str) -> bool:
    """Hand one command to the open session and print what it prints until it
    is finished. False when no session answers on that port."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), 2.0)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.write((line + "\n").encode("utf-8"))
    await writer.drain()
    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            sys.stdout.write(chunk.decode("utf-8", "replace"))
            sys.stdout.flush()
    except asyncio.CancelledError:
        # Ctrl+C in the Run panel: stop the robot, not just this relay.
        try:
            _r, w2 = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 2.0)
            w2.write(b"stop\n")
            await w2.drain()
            w2.close()
        except (OSError, asyncio.TimeoutError):
            pass
        raise
    finally:
        writer.close()
    return True


async def cmd_send(args) -> None:
    """Drive the open session from outside (the VS Code buttons use this)."""
    words: list[str] = args.words
    cmd = words[0]
    path: Path | None = None
    if cmd in ("run", "r"):
        if len(words) < 2:
            sys.exit("usage: spike send run FILE")
        path = Path(" ".join(words[1:]))
        if path.suffix.lower() != ".py" or not path.is_file():
            sys.exit(f"not a Python program: {path}\n"
                     "Click on the program you want to run in the editor, then click Run.")
        line = f"run {path.resolve()}"
    elif cmd in ("stop", "quit", "ping"):
        line = cmd
    else:
        sys.exit(f"spike send: unknown command {cmd!r} (run FILE | stop | quit | ping)")

    if await _relay(_session_port(), line):
        return

    # No session answered: clear a stale lock file and do the job one-shot.
    SESSION_LOCK.unlink(missing_ok=True)
    if cmd in ("run", "r"):
        assert path is not None
        print("[send] no session open - connecting just for this run "
              "(click Connect once to stay connected between runs)", file=sys.stderr)
        one_shot = argparse.Namespace(
            file=str(path), slot=args.slot, hub=args.hub, verbose=args.verbose,
            telemetry=0, no_wait=False, timeout=0.0)
        await cmd_upload(one_shot, start=True)
    elif cmd == "stop":
        print("[send] no session open - connecting to send stop", file=sys.stderr)
        await cmd_stop(args)
    elif cmd == "ping":
        sys.exit("no session open")
    else:
        print("[send] no session open - nothing to disconnect")


async def cmd_session(args) -> None:
    """Connect once and stay connected: run files repeatedly with no rescans.
    Commands arrive from the keyboard (spike> prompt) and from `spike send`
    over a localhost socket; both feed one queue and run one at a time.
    `stop` from the socket is handled at once, because a running program
    keeps the queue busy while its output streams."""
    port: int = args.port
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    sinks: set = set()                                   # clients attached to the command in progress
    state: dict = {"hub": None, "busy": False}

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.readline(), 10.0)
        except asyncio.TimeoutError:
            writer.close()
            return
        line = raw.decode("utf-8", "replace").strip()
        cmd = line.split()[0] if line else ""
        hub: Hub | None = state["hub"]

        async def say(text: str) -> None:
            writer.write((text + "\n").encode("utf-8"))
            await writer.drain()

        if hub is None:
            await say("[session] still connecting - try again in a moment")
            writer.close()
            return
        try:
            if cmd == "stop":
                await hub.stop_program()
                await say("[hub] stop sent")
                writer.close()
                return
            if state["busy"] and cmd in ("run", "r", "quit", "exit", "q"):
                await say("[hub] stopping the running program first")
                await hub.stop_program()
        except RuntimeError as e:
            await say(f"error: {e}")
            writer.close()
            return
        done: asyncio.Future = loop.create_future()
        await queue.put((line, writer, done))
        try:
            await done
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    try:
        server = await asyncio.start_server(handle, "127.0.0.1", port)
    except OSError:
        if await _relay(port, "ping"):
            sys.exit(f"another spike session is already open on this PC (port {port}). "
                     "Click Disconnect there (or type quit at its prompt) first.")
        sys.exit(f"port {port} is taken by another program. "
                 "Start with `spike session --port N`; `spike send` reads N from .spike-session.")

    try:
        client, hub, lost, device = await connect(args.verbose, args.hub)
    except BaseException:
        server.close()
        raise
    state["hub"] = hub
    last: str | None = args.file
    slot = args.slot
    SESSION_LOCK.write_text(json.dumps(
        {"port": port, "pid": os.getpid(), "hub": device.name or device.address}))

    def read_stdin() -> None:
        # Daemon thread so a `quit` from the socket can end the process while
        # this is still blocked in readline().
        while True:
            try:
                line = sys.stdin.readline()
            except (EOFError, KeyboardInterrupt, ValueError):
                line = ""
            if line == "":
                if state["busy"]:
                    # Ctrl+C meant for the running program aborts this read on
                    # Windows; that is not an end of input. Try again shortly.
                    time.sleep(0.3)
                    continue
                item = (None, None, None)              # real EOF: quit
            else:
                item = (line.strip(), None, None)
            try:
                loop.call_soon_threadsafe(queue.put_nowait, item)
            except RuntimeError:
                return                                  # loop closed; session over
            if item[0] is None:
                return

    threading.Thread(target=read_stdin, name="spike-stdin", daemon=True).start()

    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Tee(real_out, sinks), _Tee(real_err, sinks)
    print(
        f"\nConnected to {device.name or '(unnamed)'} {device.address} - staying connected.\n"
        "  run [file]   upload+start (defaults to the last file)\n"
        "  r            re-run the last file\n"
        "  stop         stop the running program\n"
        f"  slot N       change the target slot (now {slot})\n"
        "  quit         disconnect and exit\n"
        "Ctrl+C stops a running program; Ctrl+C at the prompt quits.\n"
        f"The VS Code buttons (Run / Stop / Disconnect) reach this session on port {port}.\n"
    )

    async def dispatch(line: str | None) -> bool:
        """Carry out one command. True means quit."""
        nonlocal last, slot
        if line is None or line in ("quit", "exit", "q"):
            return True
        if not line:
            return False
        parts = line.split()
        cmd, rest = parts[0], parts[1:]
        if cmd == "stop":
            await hub.stop_program()
            print("[hub] stop sent")
        elif cmd == "ping":
            print(f"[session] connected to {device.name or '(unnamed)'} {device.address}")
        elif cmd == "slot" and rest and rest[0].isdigit():
            slot = int(rest[0])
            print(f"[hub] target slot now {slot}")
        elif cmd in ("run", "r"):
            target = " ".join(rest) if rest else last
            if not target:
                print("no file given and no previous file to re-run")
                return False
            path = Path(target)
            if not path.exists():
                print(f"not found: {path}  (paths are relative to {Path.cwd()})")
                return False
            last = str(path)
            print(f"[hub] running {path.name}")
            state["busy"] = True
            try:
                await _run_file(hub, lost, program_source(path), slot, args.timeout)
            except asyncio.CancelledError:
                pass  # Ctrl+C already handled - back to the prompt
            except RuntimeError as e:
                print(f"error: {e}")
            finally:
                state["busy"] = False
        else:
            print(f"unknown command: {cmd!r}")
        return False

    pending = None      # the quit command's client: it is told "disconnected." last
    try:
        while not lost.is_set():
            print("spike> ", end="", flush=True)
            getter = asyncio.ensure_future(queue.get())
            dropped = asyncio.ensure_future(lost.wait())
            try:
                finished, _ = await asyncio.wait({getter, dropped}, return_when=asyncio.FIRST_COMPLETED)
            except asyncio.CancelledError:
                print()
                break
            finally:
                dropped.cancel()
                if not getter.done():
                    getter.cancel()
            if getter not in finished:
                break                                   # link dropped while idle
            line, writer, done = getter.result()
            if writer is not None:
                print()                                 # keep the button's output off the prompt line
                sinks.add(writer)
            quit_ = False
            try:
                quit_ = await dispatch(line)
            finally:
                if not quit_:
                    sinks.discard(writer)
                    if done is not None and not done.done():
                        done.set_result(None)
            if quit_:
                pending = (writer, done)
                break

        if lost.is_set():
            print("[hub] connection lost.")
    finally:
        try:
            if json.loads(SESSION_LOCK.read_text()).get("pid") == os.getpid():
                SESSION_LOCK.unlink()
        except (OSError, ValueError, AttributeError):
            pass
        server.close()
        if client.is_connected:
            await client.disconnect()
        print("disconnected.")
        if pending is not None:
            sinks.discard(pending[0])
            if pending[1] is not None and not pending[1].done():
                pending[1].set_result(None)
        sys.stdout, sys.stderr = real_out, real_err


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", maxsplit=1)[0])
    p.add_argument("-v", "--verbose", action="store_true", help="show protocol progress")
    sub = p.add_subparsers(dest="cmd", required=True)

    # --hub is accepted after any command that talks to a hub:  spike session --hub robot2
    hubopt = argparse.ArgumentParser(add_help=False)
    hubopt.add_argument("--hub", metavar="NAME", default=None,
                        help="which robot, by its name in hubs.json (default: whichever is available)")

    def slot_arg(sp):
        sp.add_argument("--slot", type=int, default=DEFAULT_SLOT, choices=range(20), metavar="0-19")

    s = sub.add_parser("discover", help="list every hub in range on Bluetooth and USB, with hubs.json values")
    s.add_argument("--seconds", type=float, default=6.0)

    s = sub.add_parser("scan", help="quick Bluetooth-only listing")
    s.add_argument("--seconds", type=float, default=6.0)

    sub.add_parser("info", parents=[hubopt], help="connect and print firmware / protocol details")

    s = sub.add_parser("bundle", help="write build/NAME.py: the program with its `from x import` files copied in (for the SPIKE app)")
    s.add_argument("file")
    s.add_argument("-o", "--out", help="output file (default build/<same name>)")

    for name, help_ in (("run", "upload to a slot, start it, stream print() output"),
                        ("upload", "store a program in a slot without starting it")):
        s = sub.add_parser(name, parents=[hubopt], help=help_)
        s.add_argument("file")
        slot_arg(s)
        s.add_argument("--telemetry", type=int, default=0, metavar="MS",
                       help="also subscribe to device notifications every MS milliseconds")
        if name == "run":
            s.add_argument("--no-wait", action="store_true",
                           help="start it and disconnect instead of streaming output")
            s.add_argument("--timeout", type=float, default=0,
                           help="give up waiting for the program to finish after N seconds (0 = never)")

    s = sub.add_parser("start", parents=[hubopt], help="start the program already in a slot")
    slot_arg(s)

    sub.add_parser("stop", parents=[hubopt], help="stop whatever program is running")

    s = sub.add_parser("session", parents=[hubopt],
                       help="connect once and stay connected; re-run without rescanning")
    s.add_argument("file", nargs="?", help="optional program to start with / default for 'r'")
    slot_arg(s)
    s.add_argument("--timeout", type=float, default=0,
                   help="give up waiting for a program to finish after N seconds (0 = never)")
    s.add_argument("--port", type=int, default=SESSION_PORT, metavar="N",
                   help=f"localhost port the VS Code buttons reach this session on (default {SESSION_PORT})")

    s = sub.add_parser("send", parents=[hubopt],
                       help="drive the open session: run FILE | stop | quit (falls back to one-shot run/stop)")
    s.add_argument("words", nargs="+", metavar="COMMAND",
                   help="run FILE (spaces in FILE are fine), stop, quit, or ping")
    slot_arg(s)

    u = sub.add_parser("usb", help="the same robot over the USB cable, via mpremote")
    usub = u.add_subparsers(dest="usb_cmd", required=True)
    usub.add_parser("devs", help="serial devices mpremote can see")
    s = usub.add_parser("run", parents=[hubopt], help="run a file over USB without storing it")
    s.add_argument("file")
    usub.add_parser("repl", parents=[hubopt], help="interactive MicroPython prompt (Ctrl-] to exit)")
    usub.add_parser("stop", parents=[hubopt], help="soft-reset the hub")
    s = usub.add_parser("exec", parents=[hubopt], help="run one line of Python on the hub")
    s.add_argument("code")

    args = p.parse_args(argv)
    try:
        if args.cmd == "bundle":
            cmd_bundle(args)
            return
        if args.cmd == "usb":
            sys.exit(cmd_usb(args))
        runners = {
            "discover": cmd_discover, "scan": cmd_scan, "info": cmd_info,
            "start": cmd_start, "stop": cmd_stop, "session": cmd_session, "send": cmd_send,
        }
        if args.cmd == "run":
            asyncio.run(cmd_upload(args, start=True))
        elif args.cmd == "upload":
            asyncio.run(cmd_upload(args, start=False))
        else:
            asyncio.run(runners[args.cmd](args))
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        sys.exit(130)
    except BundleError as e:
        sys.exit(f"cannot send this program as one file: {e}")
    except RuntimeError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
