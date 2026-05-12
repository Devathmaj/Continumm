import asyncio
import re
import time

import aiohttp


PING_LOSS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)% packet loss")
PING_RTT_PATTERN = re.compile(r"rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)")


def parse_ping_output(output):
    packet_loss = None
    latency_ms = None
    jitter_ms = None
    response_time_ms = None

    loss_match = PING_LOSS_PATTERN.search(output)
    if loss_match:
        packet_loss = float(loss_match.group(1))

    rtt_match = PING_RTT_PATTERN.search(output)
    if rtt_match:
        latency_ms = float(rtt_match.group(2))
        response_time_ms = latency_ms
        jitter_ms = float(rtt_match.group(4))

    return {
        "packet_loss_percent": packet_loss,
        "latency_ms": latency_ms,
        "jitter_ms": jitter_ms,
        "response_time_ms": response_time_ms,
    }


async def ping_host(ip_address, config):
    args = [
        "ping",
        "-c",
        str(config.PING_COUNT),
        "-W",
        str(config.PING_TIMEOUT_SECONDS),
        ip_address,
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode() + stderr.decode()

    metrics = parse_ping_output(output)
    online = metrics["packet_loss_percent"] is not None and metrics["packet_loss_percent"] < 100

    return {
        "online": online,
        **metrics,
    }


async def http_probe(ip_address, port, config):
    scheme = "https" if port == 443 else "http"
    url = f"{scheme}://{ip_address}:{port}/"
    timeout = aiohttp.ClientTimeout(total=config.HTTP_PROBE_TIMEOUT_SECONDS)

    start = time.perf_counter()
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                await response.read()
        elapsed = (time.perf_counter() - start) * 1000
        return {"http_status": response.status, "http_latency_ms": elapsed}
    except Exception:
        return {"http_status": None, "http_latency_ms": None}
